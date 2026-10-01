# -----------------------------------------------
# HolyCut API — cortes sugeridos da pregação
# -----------------------------------------------
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencias import obter_db, usuario_atual
from api.esquemas import JobSaida, ProjetoSaida, SugestoesSaida, job_para_saida, projeto_para_saida
from api.rotas.identidade import carregar_identidade
from api.rotas.midias import buscar_midia
from core.config import MODO_IA
from core.modelos.job import STATUS_ERRO, STATUS_EXECUTANDO, STATUS_PENDENTE, montar_job
from core.modelos.midia import STATUS_PRONTA
from core.modelos.projeto import montar_projeto

router = APIRouter(prefix="/api/midias", tags=["sugestoes"])


def _saida(documento: dict | None, job: dict | None) -> SugestoesSaida:
    if job and job["status"] in {STATUS_PENDENTE, STATUS_EXECUTANDO}:
        return SugestoesSaida(status=job["status"], progresso=job.get("progresso") or 0,
                              mensagem=job.get("mensagem") or "Na fila")
    if documento:
        return SugestoesSaida(status="pronta", progresso=100, mensagem="Cortes sugeridos",
                              gerado_por_ia=True, cortes=documento.get("cortes") or [])
    if job and job["status"] == STATUS_ERRO:
        return SugestoesSaida(status=STATUS_ERRO, progresso=job.get("progresso") or 0,
                              mensagem=job.get("mensagem") or "", erro=job.get("erro"))
    return SugestoesSaida(status="ausente", mensagem="Os cortes desta pregação ainda não foram sugeridos.")


async def _job(db, midia: dict) -> dict | None:
    return await db.jobs.find_one(
        {"tipo": "sugestao_cortes", "entrada.midia_id": str(midia["_id"]), "organizacao_id": midia["organizacao_id"]},
        sort=[("criado_em", -1)],
    )


@router.get("/{midia_id}/sugestoes", response_model=SugestoesSaida)
async def obter_sugestoes(midia_id: str, db=Depends(obter_db), usuario: dict = Depends(usuario_atual)):
    midia = await buscar_midia(db, midia_id, usuario)
    documento = await db.sugestoes.find_one({"midia_id": midia["_id"], "organizacao_id": midia["organizacao_id"]})
    return _saida(documento, await _job(db, midia))


@router.post("/{midia_id}/sugestoes", response_model=JobSaida)
async def pedir_sugestoes(midia_id: str, db=Depends(obter_db), usuario: dict = Depends(usuario_atual)):
    if MODO_IA != "real":
        raise HTTPException(status.HTTP_409_CONFLICT, "A sugestão de cortes está desligada neste servidor.")
    midia = await buscar_midia(db, midia_id, usuario)
    if midia["status"] != STATUS_PRONTA:
        raise HTTPException(status.HTTP_409_CONFLICT, "Espere a gravação terminar de ser preparada.")
    transcricao = await db.transcricoes.find_one({"midia_id": midia["_id"], "organizacao_id": midia["organizacao_id"]})
    if transcricao is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Espere a transcrição ficar pronta.")
    ativo = await db.jobs.find_one({
        "tipo": "sugestao_cortes",
        "entrada.midia_id": str(midia["_id"]),
        "organizacao_id": midia["organizacao_id"],
        "status": {"$in": [STATUS_PENDENTE, STATUS_EXECUTANDO]},
    })
    if ativo:
        return job_para_saida(ativo)
    job = montar_job("sugestao_cortes", midia["organizacao_id"], {"midia_id": str(midia["_id"])})
    job["_id"] = (await db.jobs.insert_one(job)).inserted_id
    return job_para_saida(job)


@router.post("/{midia_id}/sugestoes/{corte_id}/reel", response_model=ProjetoSaida, status_code=status.HTTP_201_CREATED)
async def abrir_corte(midia_id: str, corte_id: str, db=Depends(obter_db), usuario: dict = Depends(usuario_atual)):
    midia = await buscar_midia(db, midia_id, usuario)
    if not midia.get("video"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Para criar um Reel, a gravação precisa ter vídeo.")
    documento = await db.sugestoes.find_one({"midia_id": midia["_id"], "organizacao_id": midia["organizacao_id"]})
    corte = next((item for item in (documento or {}).get("cortes") or [] if item.get("id") == corte_id), None)
    if corte is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Esse corte não está mais na lista.")
    projeto = montar_projeto(usuario["organizacao_id"], midia, usuario["_id"], corte["titulo"][:120],
                             identidade=await carregar_identidade(db, usuario["organizacao_id"]))
    projeto["partes"] = [
        {"id": f"p{indice + 1}", "inicio": parte["inicio"], "fim": parte["fim"]}
        for indice, parte in enumerate(corte["partes"])
    ]
    projeto["publicacao"] = {
        "legenda": corte.get("legenda_post") or corte["titulo"],
        "hashtags": corte.get("hashtags") or [],
        "gerado_por_ia": True,
    }
    projeto["_id"] = (await db.projetos.insert_one(projeto)).inserted_id
    return projeto_para_saida(projeto)
