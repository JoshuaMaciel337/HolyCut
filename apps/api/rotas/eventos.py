# -----------------------------------------------
# HolyCut API — eventos ao vivo (Server-Sent Events)
#
# O navegador abre /api/eventos e recebe cada mudança nos jobs da sua
# organização. Com o Mongo em replica set, usa change streams. Sem
# replica set, cai para uma consulta periódica.
# -----------------------------------------------
import asyncio
import json
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pymongo.errors import OperationFailure

from api.dependencias import obter_db, usuario_atual
from api.esquemas import job_para_saida
from core.utils.mongo import agora

router = APIRouter(prefix="/api", tags=["eventos"])

INTERVALO_PING_SEGUNDOS = 15      # mantém a conexão viva no túnel da Cloudflare
INTERVALO_CONSULTA_SEGUNDOS = 2   # só no modo sem replica set
CODIGO_SEM_REPLICA_SET = 40573


def formatar_evento(nome: str, dados: dict) -> str:
    return f"event: {nome}\ndata: {json.dumps(dados, ensure_ascii=False, default=str)}\n\n"


def evento_job(doc: dict) -> str:
    return formatar_evento("job", job_para_saida(doc).model_dump(mode="json"))


async def via_change_stream(db, organizacao_id, request: Request):
    pipeline = [{"$match": {
        "operationType": {"$in": ["insert", "update", "replace"]},
        "fullDocument.organizacao_id": organizacao_id,
    }}]
    fluxo = await db.jobs.watch(pipeline, full_document="updateLookup",
                                max_await_time_ms=INTERVALO_PING_SEGUNDOS * 1000)
    try:
        yield ": conectado\n\n"
        while not await request.is_disconnected():
            mudanca = await fluxo.try_next()
            if mudanca is None:
                yield ": ping\n\n"
            elif mudanca.get("fullDocument"):
                yield evento_job(mudanca["fullDocument"])
    finally:
        await fluxo.close()


async def via_consulta_periodica(db, organizacao_id, request: Request):
    desde = agora()
    ultimo_ping = asyncio.get_running_loop().time()
    yield ": conectado\n\n"
    while not await request.is_disconnected():
        cursor = db.jobs.find({"organizacao_id": organizacao_id, "atualizado_em": {"$gt": desde}})
        async for doc in cursor.sort("atualizado_em", 1):
            desde = max(desde, doc["atualizado_em"])
            yield evento_job(doc)
        instante = asyncio.get_running_loop().time()
        if instante - ultimo_ping >= INTERVALO_PING_SEGUNDOS:
            ultimo_ping = instante
            yield ": ping\n\n"
        await asyncio.sleep(INTERVALO_CONSULTA_SEGUNDOS)


@router.get("/eventos")
async def eventos(request: Request, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    organizacao_id = usuario["organizacao_id"]

    async def gerar():
        yield "retry: 3000\n\n"
        try:
            async for evento in via_change_stream(db, organizacao_id, request):
                yield evento
        except OperationFailure as e:
            if e.code != CODIGO_SEM_REPLICA_SET:
                raise
            logging.warning("Mongo sem replica set: eventos por consulta periódica.")
            async for evento in via_consulta_periodica(db, organizacao_id, request):
                yield evento

    return StreamingResponse(gerar(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache, no-transform",
        "X-Accel-Buffering": "no",
    })
