# -----------------------------------------------
# HolyCut API — jobs da fila
# -----------------------------------------------
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.dependencias import obter_db, usuario_atual
from api.esquemas import JobCriarEntrada, JobSaida, job_para_saida
from core.modelos.job import montar_job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", response_model=JobSaida, status_code=status.HTTP_201_CREATED)
async def criar_job(dados: JobCriarEntrada, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    entrada = {"duracao": dados.duracao, "falhar": dados.falhar} if dados.tipo == "teste" else {}
    job = montar_job(dados.tipo, usuario["organizacao_id"], entrada, criado_por=usuario["_id"])
    job["_id"] = (await db.jobs.insert_one(job)).inserted_id
    return job_para_saida(job)


@router.get("", response_model=list[JobSaida])
async def listar_jobs(limite: int = Query(default=20, ge=1, le=100),
                      usuario=Depends(usuario_atual), db=Depends(obter_db)):
    cursor = db.jobs.find({"organizacao_id": usuario["organizacao_id"]}).sort("criado_em", -1).limit(limite)
    return [job_para_saida(job) async for job in cursor]


@router.get("/{job_id}", response_model=JobSaida)
async def ver_job(job_id: str, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    try:
        filtro = {"_id": ObjectId(job_id), "organizacao_id": usuario["organizacao_id"]}
    except InvalidId as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job não encontrado.") from e
    job = await db.jobs.find_one(filtro)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job não encontrado.")
    return job_para_saida(job)
