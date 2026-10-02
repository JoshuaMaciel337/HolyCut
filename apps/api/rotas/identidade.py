# -----------------------------------------------
# HolyCut API — identidade da igreja (logo, cor, @) e camadas de arte
# -----------------------------------------------
import logging

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from api.dependencias import obter_db, usuario_atual
from api.esquemas import CamadaEntrada, IdentidadeAtualizarEntrada, IdentidadeSaida
from core.config import LOGO_MAX_BYTES
from core.modelos.figura import chave_figura
from core.modelos.identidade import chave_logo, identidade_padrao, normalizar_instagram
from core.utils import storage
from core.utils.arte import (
    ErroImagem,
    camada_figura,
    camada_logo,
    camada_texto,
    desenhar_icone,
    para_png,
    posicionar,
    preparar_logo,
)
from core.utils.mongo import agora

router = APIRouter(prefix="/api", tags=["identidade"])


# -----------------------------------------------
# FUNÇÕES AUXILIARES
# -----------------------------------------------
async def carregar_identidade(db, organizacao_id) -> dict:
    """Identidade salva, completada com os valores padrão."""
    organizacao = await db.organizacoes.find_one({"_id": organizacao_id}, {"nome": 1, "identidade": 1})
    if organizacao is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Igreja não encontrada.")
    return {**identidade_padrao(organizacao["nome"]), **(organizacao.get("identidade") or {})}


def ler_logo(organizacao_id) -> bytes | None:
    caminho = storage.caminho_local(chave_logo(organizacao_id))
    return caminho.read_bytes() if caminho.is_file() else None


# -----------------------------------------------
# ROTAS
# -----------------------------------------------
@router.get("/identidade", response_model=IdentidadeSaida)
async def ver_identidade(usuario=Depends(usuario_atual), db=Depends(obter_db)):
    return IdentidadeSaida.model_validate(await carregar_identidade(db, usuario["organizacao_id"]))


@router.patch("/identidade", response_model=IdentidadeSaida)
async def atualizar_identidade(dados: IdentidadeAtualizarEntrada, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    campos = dados.model_dump(exclude_unset=True, exclude_none=True)
    if "instagram" in campos:
        campos["instagram"] = normalizar_instagram(campos["instagram"])
    if "cor_destaque" in campos:
        campos["cor_destaque"] = campos["cor_destaque"].upper()
    if "nome_exibicao" in campos:
        campos["nome_exibicao"] = " ".join(campos["nome_exibicao"].split())
    if "estrategia" in campos:
        campos["estrategia"] = " ".join(campos["estrategia"].split())[:400]
    if campos:
        campos["atualizado_em"] = agora()
        await db.organizacoes.update_one({"_id": usuario["organizacao_id"]},
                                         {"$set": {f"identidade.{k}": v for k, v in campos.items()}})
    return IdentidadeSaida.model_validate(await carregar_identidade(db, usuario["organizacao_id"]))


@router.put("/identidade/logo", response_model=IdentidadeSaida)
async def enviar_logo(request: Request, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    """O corpo é a própria imagem (PNG, JPG ou WEBP). A transparência do PNG é mantida."""
    conteudo = bytearray()
    async for pedaco in request.stream():
        conteudo += pedaco
        if len(conteudo) > LOGO_MAX_BYTES:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "O logo pode ter no máximo 5 MB.")
    if not conteudo:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Envie uma imagem.")
    try:
        png = await run_in_threadpool(preparar_logo, bytes(conteudo))
    except ErroImagem as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from e
    if not await run_in_threadpool(storage.salvar_bytes, chave_logo(usuario["organizacao_id"]), png):
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Não foi possível salvar o logo.")
    await db.organizacoes.update_one({"_id": usuario["organizacao_id"]},
                                     {"$set": {"identidade.logo": True, "identidade.atualizado_em": agora()}})
    logging.info(f"[{usuario['organizacao_id']}] Logo atualizado ({len(png) / 1024:.0f} KB).")
    return IdentidadeSaida.model_validate(await carregar_identidade(db, usuario["organizacao_id"]))


@router.get("/identidade/logo")
async def baixar_logo(usuario=Depends(usuario_atual)):
    caminho = storage.caminho_local(chave_logo(usuario["organizacao_id"]))
    if not caminho.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "A igreja ainda não enviou o logo.")
    return FileResponse(caminho, media_type="image/png", headers={"Cache-Control": "private, no-cache"})


@router.delete("/identidade/logo", response_model=IdentidadeSaida)
async def remover_logo(usuario=Depends(usuario_atual), db=Depends(obter_db)):
    await run_in_threadpool(storage.remover, chave_logo(usuario["organizacao_id"]))
    await db.organizacoes.update_one({"_id": usuario["organizacao_id"]},
                                     {"$set": {"identidade.logo": False, "identidade.atualizado_em": agora()}})
    return IdentidadeSaida.model_validate(await carregar_identidade(db, usuario["organizacao_id"]))


@router.post("/arte/camada", response_class=Response)
async def desenhar_camada(dados: CamadaEntrada, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    """A mesma camada PNG que o render vai sobrepor ao vídeo, no tamanho da moldura da prévia."""
    identidade = await carregar_identidade(db, usuario["organizacao_id"])
    if dados.tipo == "logo":
        marca = dados.marca
        logo = await run_in_threadpool(ler_logo, usuario["organizacao_id"])
        if marca is None or logo is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "A igreja ainda não enviou o logo.")
        imagem = await run_in_threadpool(camada_logo, dados.largura, dados.altura, logo, marca.posicao,
                                         marca.tamanho, marca.opacidade)
        imagem = await run_in_threadpool(posicionar, imagem, marca.x, marca.y, marca.rotacao)
    elif dados.tipo == "figura":
        figura = dados.figura
        if figura is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Informe a figura.")
        if figura.icone:
            png = await run_in_threadpool(desenhar_icone, figura.icone)
        else:
            if not dados.projeto_id:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Informe o projeto da figura.")
            try:
                projeto_id = ObjectId(dados.projeto_id)
            except InvalidId as e:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "A imagem desta figura não está mais no projeto.") from e
            caminho = storage.caminho_local(chave_figura(usuario["organizacao_id"], projeto_id, figura.id))
            if not caminho.is_file():
                raise HTTPException(status.HTTP_404_NOT_FOUND, "A imagem desta figura não está mais no projeto.")
            png = await run_in_threadpool(caminho.read_bytes)
        imagem = await run_in_threadpool(
            camada_figura, dados.largura, dados.altura, png, figura.tamanho, figura.opacidade,
        )
        imagem = await run_in_threadpool(posicionar, imagem, figura.x, figura.y, figura.rotacao)
    else:
        texto = dados.texto
        if texto is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Informe o texto.")
        imagem = await run_in_threadpool(camada_texto, dados.largura, dados.altura, texto.texto, texto.estilo,
                                         texto.posicao, identidade["cor_destaque"], texto.referencia, texto.tamanho)
        imagem = await run_in_threadpool(posicionar, imagem, texto.x, texto.y, texto.rotacao)
    png = await run_in_threadpool(para_png, imagem)
    # A caixa do elemento vai junto, para a prévia desenhar a seleção com as alças em cima dele
    caixa = imagem.getbbox() or (0, 0, 0, 0)
    return Response(content=png, media_type="image/png",
                    headers={"Cache-Control": "no-store", "X-Caixa": ",".join(str(valor) for valor in caixa),
                             "Access-Control-Expose-Headers": "X-Caixa"})
