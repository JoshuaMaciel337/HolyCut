# -----------------------------------------------
# HolyCut API — biblioteca de músicas da igreja
#
#   GET    /api/musicas                 lista da igreja
#   POST   /api/musicas                 cadastra título, artista e licença
#   PUT    /api/musicas/{id}/arquivo    o corpo é o próprio áudio (até 40 MB)
#   GET    /api/musicas/{id}/arquivo    a faixa pronta, para ouvir na prévia
#   PATCH  /api/musicas/{id}            corrige os dados
#   DELETE /api/musicas/{id}            apaga a faixa e tira dos projetos
#
# A licença é obrigatória no cadastro: sem ela a faixa não entra.
# -----------------------------------------------
import logging
from pathlib import PurePath

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from api.dependencias import obter_db, usuario_atual
from api.esquemas import MusicaAtualizarEntrada, MusicaCriarEntrada, MusicaSaida
from core.config import ESPACO_MINIMO_LIVRE_BYTES
from core.modelos.job import STATUS_ERRO as STATUS_JOB_ERRO
from core.modelos.job import STATUS_EXECUTANDO, STATUS_PENDENTE, montar_job
from core.modelos.musica import (
    ARQUIVO_MUSICA,
    EXTENSOES_MUSICA,
    LICENCAS,
    MUSICA_MAX_BYTES,
    STATUS_PROCESSANDO,
    STATUS_PRONTA,
    ErroLicenca,
    chave_musica,
    montar_musica,
    pasta_da_musica,
    validar_licenca,
)
from core.utils import storage
from core.utils.mongo import agora

router = APIRouter(prefix="/api/musicas", tags=["musicas"])
PRIORIDADE_MUSICA = 6   # é rápida, e a pessoa está esperando para usar
LIMITE_MUSICAS = 200


# -----------------------------------------------
# FUNÇÕES AUXILIARES
# -----------------------------------------------
def musica_para_saida(musica: dict) -> MusicaSaida:
    return MusicaSaida.model_validate({**musica, "id": str(musica["_id"]),
                                       "licenca_nome": LICENCAS.get(musica["licenca"], musica["licenca"])})


async def buscar_musica(db, musica_id: str, usuario: dict) -> dict:
    try:
        musica = await db.musicas.find_one({"_id": ObjectId(musica_id), "organizacao_id": usuario["organizacao_id"]})
    except InvalidId:
        musica = None
    if musica is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Música não encontrada.")
    return musica


# -----------------------------------------------
# ROTAS
# -----------------------------------------------
@router.get("", response_model=list[MusicaSaida])
async def listar_musicas(usuario=Depends(usuario_atual), db=Depends(obter_db)):
    cursor = db.musicas.find({"organizacao_id": usuario["organizacao_id"]}).sort("criado_em", -1)
    return [musica_para_saida(m) async for m in cursor.limit(LIMITE_MUSICAS)]


@router.post("", response_model=MusicaSaida, status_code=status.HTTP_201_CREATED)
async def cadastrar_musica(dados: MusicaCriarEntrada, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    if await db.musicas.count_documents({"organizacao_id": usuario["organizacao_id"]}) >= LIMITE_MUSICAS:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "A biblioteca já tem 200 músicas. Apague alguma para enviar outra.")
    try:
        musica = montar_musica(usuario["organizacao_id"], usuario["_id"], dados.titulo, dados.artista,
                               dados.licenca, dados.atribuicao, dados.fonte)
    except ErroLicenca as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from e
    musica["_id"] = (await db.musicas.insert_one(musica)).inserted_id
    return musica_para_saida(musica)


@router.put("/{musica_id}/arquivo", response_model=MusicaSaida)
async def enviar_arquivo(musica_id: str, request: Request, nome: str = Query(max_length=255),
                         usuario=Depends(usuario_atual), db=Depends(obter_db)):
    """O corpo é o próprio áudio. `nome` é o nome do arquivo no computador, para saber o formato."""
    musica = await buscar_musica(db, musica_id, usuario)
    if musica["status"] == STATUS_PROCESSANDO:
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta música ainda está sendo preparada.")
    extensao = PurePath(nome).suffix.lower()
    if extensao not in EXTENSOES_MUSICA:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Envie MP3, M4A, AAC, WAV, OGG ou FLAC.")
    if await run_in_threadpool(storage.espaco_livre) - MUSICA_MAX_BYTES < ESPACO_MINIMO_LIVRE_BYTES:
        raise HTTPException(status.HTTP_507_INSUFFICIENT_STORAGE, "O servidor está sem espaço. Avise o suporte.")

    conteudo = bytearray()
    async for pedaco in request.stream():
        conteudo += pedaco
        if len(conteudo) > MUSICA_MAX_BYTES:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "A música pode ter no máximo 40 MB.")
    if not conteudo:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Envie o arquivo da música.")

    organizacao_id = usuario["organizacao_id"]
    original = f"original{extensao}"
    await run_in_threadpool(storage.remover, chave_musica(organizacao_id, musica["_id"], ARQUIVO_MUSICA))
    if not await run_in_threadpool(storage.salvar_bytes, chave_musica(organizacao_id, musica["_id"], original),
                                   bytes(conteudo)):
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Não foi possível salvar a música.")
    job = montar_job("preparar_musica", organizacao_id, {"musica_id": str(musica["_id"])},
                     prioridade=PRIORIDADE_MUSICA, criado_por=usuario["_id"])
    job["_id"] = (await db.jobs.insert_one(job)).inserted_id
    campos = {"status": STATUS_PROCESSANDO, "original": original, "job_id": job["_id"], "duracao": None,
              "erro": None, "atualizado_em": agora()}
    await db.musicas.update_one({"_id": musica["_id"]}, {"$set": campos})
    logging.info(f"[{organizacao_id}] Música enviada: {musica['titulo']} ({len(conteudo) / 1024 / 1024:.1f} MB)")
    return musica_para_saida({**musica, **campos})


@router.get("/{musica_id}/arquivo")
async def ouvir_musica(musica_id: str, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    """A faixa já preparada (AAC). Aceita Range, para o player da prévia pular para qualquer ponto."""
    musica = await buscar_musica(db, musica_id, usuario)
    caminho = storage.caminho_local(chave_musica(musica["organizacao_id"], musica["_id"], ARQUIVO_MUSICA))
    if musica["status"] != STATUS_PRONTA or not caminho.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "A música ainda não está pronta.")
    return FileResponse(caminho, media_type="audio/mp4", headers={"Cache-Control": "private, max-age=86400"})


@router.patch("/{musica_id}", response_model=MusicaSaida)
async def atualizar_musica(musica_id: str, dados: MusicaAtualizarEntrada,
                           usuario=Depends(usuario_atual), db=Depends(obter_db)):
    musica = await buscar_musica(db, musica_id, usuario)
    campos = {k: v.strip() for k, v in dados.model_dump(exclude_unset=True, exclude_none=True).items()}
    if "titulo" in campos and not campos["titulo"]:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Escreva o título da música.")
    try:
        validar_licenca(campos.get("licenca", musica["licenca"]), campos.get("atribuicao", musica["atribuicao"]))
    except ErroLicenca as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from e
    if campos:
        campos["atualizado_em"] = agora()
        await db.musicas.update_one({"_id": musica["_id"]}, {"$set": campos})
    return musica_para_saida({**musica, **campos})


@router.delete("/{musica_id}", status_code=status.HTTP_204_NO_CONTENT)
async def apagar_musica(musica_id: str, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    musica = await buscar_musica(db, musica_id, usuario)
    momento = agora()
    await db.jobs.update_many(
        {"entrada.musica_id": str(musica["_id"]), "status": {"$in": [STATUS_PENDENTE, STATUS_EXECUTANDO]}},
        {"$set": {"status": STATUS_JOB_ERRO, "erro": "A música foi excluída.", "mensagem": "Cancelado",
                  "lease_ate": None, "concluido_em": momento, "atualizado_em": momento}},
    )
    # Os projetos que usavam a faixa ficam sem música (a versão muda, para uma aba aberta recarregar)
    await db.projetos.update_many(
        {"organizacao_id": musica["organizacao_id"], "musica.id": str(musica["_id"])},
        {"$set": {"musica.id": None, "atualizado_em": momento}, "$inc": {"versao": 1}},
    )
    await db.musicas.delete_one({"_id": musica["_id"]})
    await run_in_threadpool(storage.remover_pasta, pasta_da_musica(musica["organizacao_id"], musica["_id"]))
    logging.info(f"[{musica['organizacao_id']}] Música excluída: {musica['titulo']}")
