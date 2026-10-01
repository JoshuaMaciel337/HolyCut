# -----------------------------------------------
# HolyCut API — rosto e momentos da gravação
# -----------------------------------------------
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencias import obter_db, usuario_atual
from api.esquemas import JobSaida, MomentosSaida, RostoSaida, job_para_saida
from api.rotas.midias import buscar_midia
from core.config import MODO_IA
from core.modelos.job import STATUS_ERRO, STATUS_EXECUTANDO, STATUS_PENDENTE, montar_job
from core.modelos.midia import STATUS_PRONTA

router = APIRouter(prefix="/api/midias", tags=["analise"])


def _andamento(saida, documento: dict | None, job: dict | None, vazio: str):
    if job and job["status"] in {STATUS_PENDENTE, STATUS_EXECUTANDO}:
        return saida(status=job["status"], progresso=job.get("progresso") or 0,
                     mensagem=job.get("mensagem") or "Na fila")
    if documento:
        return None
    if job and job["status"] == STATUS_ERRO:
        return saida(status=STATUS_ERRO, progresso=job.get("progresso") or 0,
                     mensagem=job.get("mensagem") or "", erro=job.get("erro"))
    return saida(status="ausente", mensagem=vazio)


async def _ultimo_job(db, midia: dict, tipo: str) -> dict | None:
    return await db.jobs.find_one(
        {"tipo": tipo, "entrada.midia_id": str(midia["_id"]), "organizacao_id": midia["organizacao_id"]},
        sort=[("criado_em", -1)],
    )


async def _enfileirar(db, midia: dict, tipo: str) -> dict:
    if midia["status"] != STATUS_PRONTA:
        raise HTTPException(status.HTTP_409_CONFLICT, "Espere a gravação terminar de ser preparada.")
    ativo = await db.jobs.find_one({
        "tipo": tipo,
        "entrada.midia_id": str(midia["_id"]),
        "organizacao_id": midia["organizacao_id"],
        "status": {"$in": [STATUS_PENDENTE, STATUS_EXECUTANDO]},
    })
    if ativo:
        return job_para_saida(ativo)
    job = montar_job(tipo, midia["organizacao_id"], {"midia_id": str(midia["_id"])})
    job["_id"] = (await db.jobs.insert_one(job)).inserted_id
    return job_para_saida(job)


@router.get("/{midia_id}/rosto", response_model=RostoSaida)
async def obter_rosto(midia_id: str, db=Depends(obter_db), usuario: dict = Depends(usuario_atual)):
    midia = await buscar_midia(db, midia_id, usuario)
    documento = await db.rostos.find_one({"midia_id": midia["_id"], "organizacao_id": midia["organizacao_id"]})
    job = await _ultimo_job(db, midia, "enquadramento_rosto")
    andamento = _andamento(RostoSaida, documento, job, "O rosto desta gravação ainda não foi acompanhado.")
    if andamento is not None:
        return andamento
    return RostoSaida(status="pronta", progresso=100, mensagem="Rosto marcado", quadros=documento.get("quadros") or [])


@router.post("/{midia_id}/rosto", response_model=JobSaida)
async def pedir_rosto(midia_id: str, db=Depends(obter_db), usuario: dict = Depends(usuario_atual)):
    midia = await buscar_midia(db, midia_id, usuario)
    if not midia.get("video"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Esta gravação não tem vídeo.")
    return await _enfileirar(db, midia, "enquadramento_rosto")


@router.get("/{midia_id}/momentos", response_model=MomentosSaida)
async def obter_momentos(midia_id: str, db=Depends(obter_db), usuario: dict = Depends(usuario_atual)):
    midia = await buscar_midia(db, midia_id, usuario)
    documento = await db.momentos.find_one({"midia_id": midia["_id"], "organizacao_id": midia["organizacao_id"]})
    job = await _ultimo_job(db, midia, "momentos")
    andamento = _andamento(MomentosSaida, documento, job, "Os momentos desta gravação ainda não foram marcados.")
    if andamento is not None:
        return andamento
    return MomentosSaida(status="pronta", progresso=100, mensagem="Momentos prontos",
                         gerado_por_ia=bool(documento.get("gerado_por_ia")),
                         momentos=documento.get("momentos") or [], cenas=documento.get("cenas") or [])


@router.post("/{midia_id}/momentos", response_model=JobSaida)
async def pedir_momentos(midia_id: str, db=Depends(obter_db), usuario: dict = Depends(usuario_atual)):
    if MODO_IA != "real":
        raise HTTPException(status.HTTP_409_CONFLICT, "Os momentos com IA estão desligados neste servidor.")
    midia = await buscar_midia(db, midia_id, usuario)
    return await _enfileirar(db, midia, "momentos")
