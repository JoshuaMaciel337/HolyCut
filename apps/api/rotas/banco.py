# -----------------------------------------------
# HolyCut API — imagens e vídeos da Pixabay para ilustrar o culto
# A chave fica no servidor. A tela só recebe miniatura, autor e a página.
# -----------------------------------------------
import logging
import secrets
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pymongo import ReturnDocument
from starlette.concurrency import run_in_threadpool

from api.dependencias import obter_db, usuario_atual
from api.esquemas import (
    BuscaBancoEntrada,
    ProjetoSaida,
    ResultadoBancoSaida,
    SugestaoBancoSaida,
    UsarBancoEntrada,
    projeto_para_saida,
)
from api.rotas.projetos import buscar_projeto
from core.modelos.banco import MAX_APOIOS, chave_apoio, consulta_da_frase, credito
from core.modelos.figura import MAX_FIGURAS, chave_figura, nova_figura
from core.utils import storage
from core.utils.arte import ErroImagem, preparar_logo
from core.utils.mongo import agora
from core.utils.pixabay import ErroPixabay, baixar_arquivo, buscar, configurada, obter

router = APIRouter(prefix="/api", tags=["banco"])
CACHE_HORAS = 24


def _publico(item: dict) -> dict:
    return {campo: item.get(campo) for campo in ("id", "tipo", "nome", "autor", "pagina", "miniatura", "duracao")}


def _exigir_chave():
    if not configurada():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "A busca de imagens ainda não está configurada.")


@router.get("/banco/buscar", response_model=list[ResultadoBancoSaida])
async def buscar_banco(q: str = Query(min_length=2, max_length=100),
                       tipo: str = Query(pattern="^(imagem|video)$"),
                       usuario=Depends(usuario_atual), db=Depends(obter_db)):
    """Fotos ou vídeos. A resposta fica guardada por 24 horas, como a Pixabay pede."""
    _exigir_chave()
    consulta = " ".join(q.split())
    chave_cache = f"{tipo}:{consulta.casefold()}"
    guardado = await db.cache_pixabay.find_one({"chave": chave_cache, "expira_em": {"$gt": agora()}})
    if guardado:
        return guardado["itens"]
    try:
        itens = [_publico(item) for item in await run_in_threadpool(buscar, tipo, consulta)]
    except ErroPixabay as erro:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(erro)) from erro
    await db.cache_pixabay.update_one(
        {"chave": chave_cache},
        {"$set": {"itens": itens, "expira_em": agora() + timedelta(hours=CACHE_HORAS)}},
        upsert=True,
    )
    logging.info(f"[{usuario['organizacao_id']}] Busca na Pixabay: {len(itens)} {tipo}")
    return itens


@router.post("/banco/sugerir", response_model=SugestaoBancoSaida)
async def sugerir_busca(dados: BuscaBancoEntrada, usuario=Depends(usuario_atual)):
    """A frase dita vira uma busca visual. Sem o modelo, a busca é a própria frase."""
    return await run_in_threadpool(consulta_da_frase, dados.frase)


@router.post("/projetos/{projeto_id}/banco", response_model=ProjetoSaida)
async def usar_do_banco(projeto_id: str, dados: UsarBancoEntrada,
                        usuario=Depends(usuario_atual), db=Depends(obter_db)):
    """Baixa o arquivo para o armazenamento da igreja e coloca no projeto."""
    _exigir_chave()
    projeto = await buscar_projeto(db, projeto_id, usuario)
    if dados.tipo == "imagem" and len(projeto.get("figuras") or []) >= MAX_FIGURAS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Dá para colocar até 8 figuras no vídeo.")
    if dados.tipo == "video" and len(projeto.get("apoios") or []) >= MAX_APOIOS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Dá para colocar até 4 vídeos de apoio.")
    try:
        item = await run_in_threadpool(obter, dados.tipo, dados.pixabay_id)
        conteudo = await run_in_threadpool(baixar_arquivo, item["arquivo"], dados.tipo)
    except ErroPixabay as erro:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(erro)) from erro
    if dados.tipo == "imagem":
        return await _guardar_imagem(db, projeto, usuario, dados, item, conteudo)
    return await _guardar_video(db, projeto, usuario, dados, item, conteudo)


async def _guardar_imagem(db, projeto, usuario, dados, item, conteudo) -> ProjetoSaida:
    try:
        png = await run_in_threadpool(preparar_logo, conteudo)
    except ErroImagem as erro:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(erro)) from erro
    figura = nova_figura(None, item["nome"])
    figura["credito"] = credito(item["autor"])
    figura["inicio"] = dados.inicio
    figura["fim"] = dados.inicio + 5
    chave = chave_figura(usuario["organizacao_id"], projeto["_id"], figura["id"])
    if not await run_in_threadpool(storage.salvar_bytes, chave, png):
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Não foi possível salvar a imagem.")
    resultado = await db.projetos.find_one_and_update(
        {"_id": projeto["_id"], "versao": dados.versao},
        {"$push": {"figuras": figura}, "$inc": {"versao": 1}, "$set": {"atualizado_em": agora()}},
        return_document=ReturnDocument.AFTER,
    )
    if resultado is None:
        await run_in_threadpool(storage.remover, chave)
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Este projeto foi alterado em outra aba ou por outra pessoa. Recarregue a página.")
    return projeto_para_saida(resultado)


async def _guardar_video(db, projeto, usuario, dados, item, conteudo) -> ProjetoSaida:
    duracao = int(item.get("duracao") or 6)
    apoio = {
        "id": secrets.token_hex(4),
        "nome": item["nome"][:40],
        "credito": credito(item["autor"]),
        "inicio": dados.inicio,
        "fim": dados.inicio + min(duracao, 8),
        "pixabay_id": int(item["id"]),
    }
    chave = chave_apoio(usuario["organizacao_id"], projeto["_id"], apoio["id"])
    if not await run_in_threadpool(storage.salvar_bytes, chave, conteudo):
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Não foi possível salvar o vídeo.")
    resultado = await db.projetos.find_one_and_update(
        {"_id": projeto["_id"], "versao": dados.versao},
        {"$push": {"apoios": apoio}, "$inc": {"versao": 1}, "$set": {"atualizado_em": agora()}},
        return_document=ReturnDocument.AFTER,
    )
    if resultado is None:
        await run_in_threadpool(storage.remover, chave)
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Este projeto foi alterado em outra aba ou por outra pessoa. Recarregue a página.")
    return projeto_para_saida(resultado)


@router.get("/projetos/{projeto_id}/apoios/{apoio_id}")
async def ver_apoio(projeto_id: str, apoio_id: str, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    """O vídeo baixado, só para quem está na igreja dona do projeto."""
    if len(apoio_id) != 8:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vídeo de apoio não encontrado.")
    projeto = await buscar_projeto(db, projeto_id, usuario)
    if apoio_id not in {item["id"] for item in projeto.get("apoios") or []}:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vídeo de apoio não encontrado.")
    caminho = storage.caminho_local(chave_apoio(usuario["organizacao_id"], projeto["_id"], apoio_id))
    if not caminho.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "O vídeo de apoio ainda não está no disco.")
    return FileResponse(caminho, media_type="video/mp4", headers={"Cache-Control": "private, max-age=3600"})
