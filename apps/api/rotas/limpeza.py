# -----------------------------------------------
# HolyCut API — limpeza de áudio da gravação
# O interruptor fica no projeto. O arquivo é um só por gravação.
# -----------------------------------------------
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencias import obter_db, usuario_atual
from api.esquemas import JobSaida, LimpezaSaida, job_para_saida
from api.rotas.midias import buscar_midia
from core.config import MODO_IA
from core.modelos.job import STATUS_ERRO, STATUS_EXECUTANDO, STATUS_PENDENTE, montar_job
from core.modelos.midia import ARQUIVO_AUDIO_LIMPO, STATUS_PRONTA

router = APIRouter(prefix="/api/midias", tags=["limpeza"])


def _saida(midia: dict, job: dict | None) -> LimpezaSaida:
    if ARQUIVO_AUDIO_LIMPO in (midia.get("arquivos") or []):
        return LimpezaSaida(status="pronta", progresso=100, mensagem="Áudio limpo")
    if job and job["status"] in {STATUS_PENDENTE, STATUS_EXECUTANDO}:
        return LimpezaSaida(status=job["status"], progresso=job.get("progresso") or 0,
                            mensagem=job.get("mensagem") or "Na fila")
    if job and job["status"] == STATUS_ERRO:
        return LimpezaSaida(status=STATUS_ERRO, progresso=job.get("progresso") or 0,
                            mensagem=job.get("mensagem") or "", erro=job.get("erro"))
    return LimpezaSaida(status="ausente", mensagem="O áudio desta gravação ainda não foi limpo.")


async def _job(db, midia: dict) -> dict | None:
    return await db.jobs.find_one(
        {"tipo": "limpeza_audio", "entrada.midia_id": str(midia["_id"]), "organizacao_id": midia["organizacao_id"]},
        sort=[("criado_em", -1)],
    )


@router.get("/{midia_id}/limpeza", response_model=LimpezaSaida)
async def obter_limpeza(midia_id: str, db=Depends(obter_db), usuario: dict = Depends(usuario_atual)):
    midia = await buscar_midia(db, midia_id, usuario)
    return _saida(midia, await _job(db, midia))


@router.post("/{midia_id}/limpeza", response_model=JobSaida)
async def pedir_limpeza(midia_id: str, db=Depends(obter_db), usuario: dict = Depends(usuario_atual)):
    if MODO_IA != "real":
        raise HTTPException(status.HTTP_409_CONFLICT, "A limpeza de áudio está desligada neste servidor.")
    midia = await buscar_midia(db, midia_id, usuario)
    if midia["status"] != STATUS_PRONTA:
        raise HTTPException(status.HTTP_409_CONFLICT, "Espere a gravação terminar de ser preparada.")
    if not midia.get("audio"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Esta gravação não tem áudio para limpar.")
    if ARQUIVO_AUDIO_LIMPO in (midia.get("arquivos") or []):
        raise HTTPException(status.HTTP_409_CONFLICT, "O áudio desta gravação já foi limpo.")

    ativo = await db.jobs.find_one({
        "tipo": "limpeza_audio",
        "entrada.midia_id": str(midia["_id"]),
        "organizacao_id": midia["organizacao_id"],
        "status": {"$in": [STATUS_PENDENTE, STATUS_EXECUTANDO]},
    })
    if ativo:
        return job_para_saida(ativo)
    job = montar_job("limpeza_audio", midia["organizacao_id"], {"midia_id": str(midia["_id"])})
    job["_id"] = (await db.jobs.insert_one(job)).inserted_id
    return job_para_saida(job)
