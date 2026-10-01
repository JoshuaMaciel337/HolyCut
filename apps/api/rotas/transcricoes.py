# -----------------------------------------------
# HolyCut API — transcrição da gravação
# -----------------------------------------------
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from api.dependencias import obter_db, usuario_atual
from api.esquemas import JobSaida, TranscricaoSaida, job_para_saida
from api.rotas.midias import buscar_midia
from core.config import MODO_IA
from core.modelos.job import STATUS_ERRO, STATUS_EXECUTANDO, STATUS_PENDENTE, montar_job
from core.modelos.midia import STATUS_PRONTA
from core.modelos.transcricao import exportar_srt, exportar_txt

router = APIRouter(prefix="/api/midias", tags=["transcricao"])


def _saida(documento: dict | None, job: dict | None) -> TranscricaoSaida:
    """O job andando ganha da transcrição antiga. Sem os dois, a aba explica que ainda não há texto."""
    if job and job["status"] in {STATUS_PENDENTE, STATUS_EXECUTANDO}:
        return TranscricaoSaida(status=job["status"], progresso=job.get("progresso") or 0,
                                mensagem=job.get("mensagem") or "Na fila")
    if job and job["status"] == STATUS_ERRO and documento is None:
        return TranscricaoSaida(status=STATUS_ERRO, progresso=job.get("progresso") or 0,
                                mensagem=job.get("mensagem") or "", erro=job.get("erro"))
    if documento is None:
        return TranscricaoSaida(status="ausente", mensagem="A transcrição ainda não foi feita.")
    return TranscricaoSaida.model_validate({
        **documento,
        "status": "pronta",
        "progresso": 100,
        "mensagem": "Transcrição pronta",
    })


async def _documento_e_job(db, midia: dict):
    documento = await db.transcricoes.find_one({
        "midia_id": midia["_id"], "organizacao_id": midia["organizacao_id"],
    })
    job = await db.jobs.find_one(
        {"tipo": "transcricao", "entrada.midia_id": str(midia["_id"]), "organizacao_id": midia["organizacao_id"]},
        sort=[("criado_em", -1)],
    )
    return documento, job


@router.get("/{midia_id}/transcricao", response_model=TranscricaoSaida)
async def obter_transcricao(midia_id: str, db=Depends(obter_db), usuario: dict = Depends(usuario_atual)):
    midia = await buscar_midia(db, midia_id, usuario)
    documento, job = await _documento_e_job(db, midia)
    return _saida(documento, job)


@router.post("/{midia_id}/transcricao", response_model=JobSaida)
async def pedir_transcricao(midia_id: str, db=Depends(obter_db), usuario: dict = Depends(usuario_atual)):
    if MODO_IA != "real":
        raise HTTPException(status.HTTP_409_CONFLICT, "A transcrição com IA está desligada neste servidor.")
    midia = await buscar_midia(db, midia_id, usuario)
    if midia["status"] != STATUS_PRONTA:
        raise HTTPException(status.HTTP_409_CONFLICT, "Espere a gravação terminar de ser preparada.")
    if not midia.get("audio"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Esta gravação não tem áudio para transcrever.")

    ativo = await db.jobs.find_one({
        "tipo": "transcricao",
        "entrada.midia_id": str(midia["_id"]),
        "organizacao_id": midia["organizacao_id"],
        "status": {"$in": [STATUS_PENDENTE, STATUS_EXECUTANDO]},
    })
    if ativo:
        return job_para_saida(ativo)
    job = montar_job("transcricao", midia["organizacao_id"], {"midia_id": str(midia["_id"])})
    job["_id"] = (await db.jobs.insert_one(job)).inserted_id
    return job_para_saida(job)


async def _texto(midia_id: str, db, usuario: dict, exportar, nome: str) -> Response:
    midia = await buscar_midia(db, midia_id, usuario)
    documento = await db.transcricoes.find_one({
        "midia_id": midia["_id"], "organizacao_id": midia["organizacao_id"],
    })
    if documento is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "A transcrição ainda não está pronta.")
    conteudo = exportar(documento.get("segmentos") or [])
    return Response(conteudo, media_type="text/plain; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"'})


@router.get("/{midia_id}/transcricao.srt")
async def baixar_srt(midia_id: str, db=Depends(obter_db), usuario: dict = Depends(usuario_atual)):
    return await _texto(midia_id, db, usuario, exportar_srt, "transcricao.srt")


@router.get("/{midia_id}/transcricao.txt")
async def baixar_txt(midia_id: str, db=Depends(obter_db), usuario: dict = Depends(usuario_atual)):
    return await _texto(midia_id, db, usuario, exportar_txt, "transcricao.txt")
