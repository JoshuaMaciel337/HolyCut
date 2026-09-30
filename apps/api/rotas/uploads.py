# -----------------------------------------------
# HolyCut API — upload retomável pelo protocolo tus 1.0.0
#
#   POST   /api/uploads        cria o envio (Upload-Length, Upload-Metadata)
#   HEAD   /api/uploads/{id}   quanto já chegou (Upload-Offset)
#   PATCH  /api/uploads/{id}   manda o próximo pedaço
#   DELETE /api/uploads/{id}   cancela um envio em andamento
#
# O navegador usa o tus-js-client em pedaços de 8 MB. Se a internet cair,
# ele pergunta quanto chegou (HEAD) e continua dali. Cada envio já nasce
# como uma mídia, com status "enviando". A decisão está em
# docs/decisoes/0001-upload-tus-na-api.md.
# -----------------------------------------------
import asyncio
import base64
import binascii
import logging

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, Request, Response, status
from starlette.concurrency import run_in_threadpool
from starlette.requests import ClientDisconnect

from api.dependencias import obter_db, usuario_atual
from core.config import ESPACO_MINIMO_LIVRE_BYTES, UPLOAD_MAX_BYTES
from core.modelos.job import montar_job
from core.modelos.midia import (
    STATUS_ENVIANDO,
    STATUS_PROCESSANDO,
    chave_arquivo,
    extensao_aceita,
    montar_midia,
    pasta_da_midia,
)
from core.utils import storage
from core.utils.mongo import agora

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

TUS_VERSAO = "1.0.0"
TIPO_CONTEUDO_PATCH = "application/offset+octet-stream"
TAMANHO_ESCRITA = 1024 * 1024  # junta 1 MB antes de gravar no disco
PRIORIDADE_INGESTAO = 5
_travas: dict[str, asyncio.Lock] = {}


# -----------------------------------------------
# FUNÇÕES AUXILIARES
# -----------------------------------------------
def resposta_tus(codigo: int, cabecalhos: dict | None = None, mensagem: str = "") -> Response:
    return Response(
        content=mensagem,
        status_code=codigo,
        media_type="text/plain; charset=utf-8" if mensagem else None,
        headers={"Tus-Resumable": TUS_VERSAO, "Cache-Control": "no-store", **(cabecalhos or {})},
    )


def ler_metadados(cabecalho: str) -> dict[str, str]:
    """'filename Y3VsdG8ubXA0,filetype dmlkZW8vbXA0' → {'filename': 'culto.mp4', ...}."""
    metadados = {}
    for par in cabecalho.split(","):
        chave, _, valor = par.strip().partition(" ")
        if not chave:
            continue
        try:
            metadados[chave] = base64.b64decode(valor, validate=True).decode("utf-8") if valor else ""
        except (binascii.Error, UnicodeDecodeError):
            metadados[chave] = ""
    return metadados


def versao_invalida(request: Request) -> Response | None:
    if request.headers.get("tus-resumable") != TUS_VERSAO:
        return resposta_tus(status.HTTP_412_PRECONDITION_FAILED, {"Tus-Version": TUS_VERSAO},
                            "Versão do protocolo tus não suportada.")
    return None


async def buscar_envio(db, upload_id: str, usuario: dict) -> dict | None:
    try:
        return await db.midias.find_one({"_id": ObjectId(upload_id), "organizacao_id": usuario["organizacao_id"]})
    except InvalidId:
        return None


def chave_original(midia: dict) -> str:
    return chave_arquivo(midia["organizacao_id"], midia["_id"], midia["original"])


async def concluir_envio(db, midia: dict, usuario: dict):
    """Último pedaço chegou: a mídia vai para a fila de ingestão."""
    job = montar_job("ingestao", midia["organizacao_id"], {"midia_id": str(midia["_id"])},
                     prioridade=PRIORIDADE_INGESTAO, criado_por=usuario["_id"])
    job_id = (await db.jobs.insert_one(job)).inserted_id
    momento = agora()
    await db.midias.update_one({"_id": midia["_id"], "status": STATUS_ENVIANDO}, {"$set": {
        "status": STATUS_PROCESSANDO,
        "bytes_recebidos": midia["tamanho_total"],
        "job_ingestao_id": job_id,
        "enviado_em": momento,
        "atualizado_em": momento,
    }})
    logging.info(f"[{midia['organizacao_id']}] Envio concluído: {midia['nome_original']} "
                 f"({midia['tamanho_total'] / 1024**2:.1f} MB). Ingestão na fila.")


# -----------------------------------------------
# ROTAS
# -----------------------------------------------
@router.options("")
@router.options("/{upload_id}")
async def descobrir(upload_id: str | None = None):
    return Response(status_code=status.HTTP_204_NO_CONTENT, headers={
        "Tus-Resumable": TUS_VERSAO,
        "Tus-Version": TUS_VERSAO,
        "Tus-Extension": "creation,termination",
        "Tus-Max-Size": str(UPLOAD_MAX_BYTES),
    })


@router.post("")
async def criar_envio(request: Request, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    if erro := versao_invalida(request):
        return erro
    try:
        total = int(request.headers.get("upload-length", ""))
    except ValueError:
        return resposta_tus(status.HTTP_400_BAD_REQUEST, mensagem="Tamanho do arquivo não informado.")
    if total <= 0:
        return resposta_tus(status.HTTP_400_BAD_REQUEST, mensagem="O arquivo está vazio.")
    if total > UPLOAD_MAX_BYTES:
        limite = UPLOAD_MAX_BYTES / 1024**3
        return resposta_tus(status.HTTP_413_CONTENT_TOO_LARGE,
                            mensagem=f"O arquivo passa do limite de {limite:.0f} GB.")

    metadados = ler_metadados(request.headers.get("upload-metadata", ""))
    nome = metadados.get("filename", "")
    if not extensao_aceita(nome):
        return resposta_tus(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            mensagem="Formato não aceito. Envie um vídeo (MP4, MOV, MKV...) "
                                     "ou um áudio (MP3, WAV, M4A...).")
    livre = await run_in_threadpool(storage.espaco_livre)
    if livre - total < ESPACO_MINIMO_LIVRE_BYTES:
        logging.warning(f"Envio recusado por falta de espaço: {total / 1024**3:.1f} GB, "
                        f"{livre / 1024**3:.1f} GB livres.")
        return resposta_tus(status.HTTP_507_INSUFFICIENT_STORAGE,
                            mensagem="O servidor está sem espaço para esse arquivo. "
                                     "Avise o responsável pelo HolyCut.")

    midia = montar_midia(usuario["organizacao_id"], usuario["_id"], nome, total, metadados.get("filetype", ""))
    midia["_id"] = (await db.midias.insert_one(midia)).inserted_id
    if not await run_in_threadpool(storage.salvar_bytes, chave_original(midia), b""):
        await db.midias.delete_one({"_id": midia["_id"]})
        return resposta_tus(status.HTTP_500_INTERNAL_SERVER_ERROR, mensagem="Não foi possível começar o envio.")
    return resposta_tus(status.HTTP_201_CREATED, {"Location": f"/api/uploads/{midia['_id']}", "Upload-Offset": "0"})


@router.head("/{upload_id}")
async def consultar_envio(upload_id: str, request: Request, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    if erro := versao_invalida(request):
        return erro
    midia = await buscar_envio(db, upload_id, usuario)
    recebido = await run_in_threadpool(storage.tamanho, chave_original(midia)) if midia else None
    if recebido is None:
        return resposta_tus(status.HTTP_404_NOT_FOUND)
    return resposta_tus(status.HTTP_200_OK, {"Upload-Offset": str(recebido),
                                             "Upload-Length": str(midia["tamanho_total"])})


@router.patch("/{upload_id}")
async def receber_pedaco(upload_id: str, request: Request, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    if erro := versao_invalida(request):
        return erro
    if request.headers.get("content-type") != TIPO_CONTEUDO_PATCH:
        return resposta_tus(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, mensagem="Content-Type inválido.")
    try:
        deslocamento = int(request.headers.get("upload-offset", ""))
    except ValueError:
        return resposta_tus(status.HTTP_400_BAD_REQUEST, mensagem="Upload-Offset ausente.")
    midia = await buscar_envio(db, upload_id, usuario)
    if midia is None:
        return resposta_tus(status.HTTP_404_NOT_FOUND)
    if midia["status"] != STATUS_ENVIANDO:
        return resposta_tus(status.HTTP_409_CONFLICT, {"Upload-Offset": str(midia["tamanho_total"])},
                            "Este envio já terminou.")

    trava = _travas.setdefault(upload_id, asyncio.Lock())
    if trava.locked():
        return resposta_tus(status.HTTP_423_LOCKED, mensagem="Este arquivo já está sendo enviado em outra aba.")
    try:
        async with trava:
            caminho = storage.caminho_local(chave_original(midia))
            atual = await run_in_threadpool(storage.tamanho, chave_original(midia))
            if atual is None:
                return resposta_tus(status.HTTP_404_NOT_FOUND)
            if deslocamento != atual:
                return resposta_tus(status.HTTP_409_CONFLICT, {"Upload-Offset": str(atual)},
                                    "A posição do envio não confere. Retomando de onde parou.")

            restante = midia["tamanho_total"] - atual
            recebido, excedeu, buffer = 0, False, bytearray()
            arquivo = await run_in_threadpool(open, caminho, "ab")
            try:
                async for pedaco in request.stream():
                    if recebido + len(buffer) + len(pedaco) > restante:
                        pedaco, excedeu = pedaco[: restante - recebido - len(buffer)], True
                    buffer += pedaco
                    if len(buffer) >= TAMANHO_ESCRITA:
                        await run_in_threadpool(arquivo.write, bytes(buffer))
                        recebido += len(buffer)
                        buffer.clear()
                    if excedeu:
                        break
            except ClientDisconnect:
                logging.info(f"[{midia['organizacao_id']}] Conexão caiu no meio de um pedaço de {midia['_id']}.")
            finally:
                if buffer:
                    await run_in_threadpool(arquivo.write, bytes(buffer))
                    recebido += len(buffer)
                await run_in_threadpool(arquivo.close)

            novo = atual + recebido
            await db.midias.update_one({"_id": midia["_id"]},
                                       {"$set": {"bytes_recebidos": novo, "atualizado_em": agora()}})
            if novo == midia["tamanho_total"]:
                await concluir_envio(db, midia, usuario)
    finally:
        if not trava.locked():
            _travas.pop(upload_id, None)

    if excedeu:
        return resposta_tus(status.HTTP_413_CONTENT_TOO_LARGE, {"Upload-Offset": str(novo)},
                            "Chegou mais do que o tamanho informado do arquivo.")
    return resposta_tus(status.HTTP_204_NO_CONTENT, {"Upload-Offset": str(novo)})


@router.delete("/{upload_id}")
async def cancelar_envio(upload_id: str, request: Request, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    if erro := versao_invalida(request):
        return erro
    midia = await buscar_envio(db, upload_id, usuario)
    if midia is None:
        return resposta_tus(status.HTTP_404_NOT_FOUND)
    if midia["status"] != STATUS_ENVIANDO:
        return resposta_tus(status.HTTP_409_CONFLICT, mensagem="O envio já terminou. Exclua pela mídia.")
    await run_in_threadpool(storage.remover_pasta, pasta_da_midia(midia["organizacao_id"], midia["_id"]))
    await db.midias.delete_one({"_id": midia["_id"]})
    return resposta_tus(status.HTTP_204_NO_CONTENT)
