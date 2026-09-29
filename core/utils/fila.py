# -----------------------------------------------
# HolyCut — fila de jobs no MongoDB
#
# O worker pega um job de forma atômica e fica com a "posse" dele por
# LEASE_MINUTOS. Enquanto trabalha, renova a posse (heartbeat). Se o
# worker cair, a posse vence e outro worker pega o job de novo.
# -----------------------------------------------
import logging
from datetime import timedelta

from pymongo import ReturnDocument

from core.config import LEASE_MINUTOS
from core.modelos.job import (
    STATUS_CONCLUIDO,
    STATUS_ERRO,
    STATUS_EXECUTANDO,
    STATUS_PENDENTE,
    calcular_espera_retry,
)
from core.utils.mongo import agora

COLECAO_JOBS = "jobs"
COLECAO_WORKERS = "workers"


def registrar_worker(db, worker_id: str, recursos: list[str], tipos: list[str], iniciado_em) -> bool:
    """Sinal de vida do worker, usado pelo painel para mostrar quem está online."""
    try:
        db[COLECAO_WORKERS].update_one(
            {"_id": worker_id},
            {"$set": {"recursos": recursos, "tipos": tipos, "iniciado_em": iniciado_em, "visto_em": agora()}},
            upsert=True,
        )
        return True
    except Exception as e:
        logging.error(f"[{worker_id}] Erro ao registrar worker: {e}")
        return False


def enfileirar_job(db, job: dict):
    """Insere um job montado por montar_job(). Retorna o _id ou None."""
    try:
        return db[COLECAO_JOBS].insert_one(job).inserted_id
    except Exception as e:
        logging.error(f"Erro ao enfileirar job {job.get('tipo')}: {e}")
        return None


def pegar_proximo_job(db, tipos: list[str], worker_id: str) -> dict | None:
    """Pega o próximo job pendente de forma atômica. Retorna o job ou None."""
    momento = agora()
    try:
        return db[COLECAO_JOBS].find_one_and_update(
            {
                "status": STATUS_PENDENTE,
                "tipo": {"$in": tipos},
                "disponivel_em": {"$lte": momento},
            },
            {
                "$set": {
                    "status": STATUS_EXECUTANDO,
                    "worker_id": worker_id,
                    "lease_ate": momento + timedelta(minutes=LEASE_MINUTOS),
                    "iniciado_em": momento,
                    "atualizado_em": momento,
                    "mensagem": "Iniciando",
                    "erro": None,
                },
                "$inc": {"tentativas": 1},
            },
            sort=[("prioridade", -1), ("criado_em", 1)],
            return_document=ReturnDocument.AFTER,
        )
    except Exception as e:
        logging.error(f"[{worker_id}] Erro ao buscar job na fila: {e}")
        return None


def _atualizar_posse(db, job_id, worker_id: str, campos: dict) -> bool:
    """Atualiza um job que ainda pertence a este worker. False se a posse foi perdida."""
    momento = agora()
    campos = {**campos, "atualizado_em": momento, "lease_ate": momento + timedelta(minutes=LEASE_MINUTOS)}
    try:
        resultado = db[COLECAO_JOBS].update_one(
            {"_id": job_id, "worker_id": worker_id, "status": STATUS_EXECUTANDO},
            {"$set": campos},
        )
        return resultado.matched_count == 1
    except Exception as e:
        logging.error(f"[{worker_id}] Erro ao atualizar job {job_id}: {e}")
        return False


def renovar_lease(db, job_id, worker_id: str) -> bool:
    """Heartbeat: estende a posse do job."""
    return _atualizar_posse(db, job_id, worker_id, {})


def atualizar_progresso(db, job_id, worker_id: str, progresso: int, mensagem: str = "") -> bool:
    """Grava o progresso (0 a 100) e renova a posse."""
    return _atualizar_posse(db, job_id, worker_id, {
        "progresso": max(0, min(100, int(progresso))),
        "mensagem": mensagem,
    })


def concluir_job(db, job_id, worker_id: str, saida: dict | None = None) -> bool:
    """Marca o job como concluído com o resultado."""
    momento = agora()
    try:
        resultado = db[COLECAO_JOBS].update_one(
            {"_id": job_id, "worker_id": worker_id, "status": STATUS_EXECUTANDO},
            {"$set": {
                "status": STATUS_CONCLUIDO,
                "progresso": 100,
                "mensagem": "Concluído",
                "saida": saida or {},
                "lease_ate": None,
                "concluido_em": momento,
                "atualizado_em": momento,
            }},
        )
        return resultado.matched_count == 1
    except Exception as e:
        logging.error(f"[{worker_id}] Erro ao concluir job {job_id}: {e}")
        return False


def falhar_job(db, job: dict, worker_id: str, erro: str) -> str | None:
    """
    Registra a falha. Se ainda há tentativas, devolve o job para a fila com espera crescente.
    Retorna o novo status ou None se não conseguiu gravar.
    """
    momento = agora()
    esgotou = job.get("tentativas", 1) >= job.get("max_tentativas", 1)
    if esgotou:
        campos = {"status": STATUS_ERRO, "mensagem": "Falhou", "concluido_em": momento}
    else:
        espera = calcular_espera_retry(job.get("tentativas", 1))
        campos = {
            "status": STATUS_PENDENTE,
            "mensagem": f"Nova tentativa em {int(espera.total_seconds() // 60)} min",
            "disponivel_em": momento + espera,
            "worker_id": None,
        }
    campos.update({"erro": erro[:2000], "lease_ate": None, "atualizado_em": momento})
    try:
        resultado = db[COLECAO_JOBS].update_one(
            {"_id": job["_id"], "worker_id": worker_id, "status": STATUS_EXECUTANDO},
            {"$set": campos},
        )
        return campos["status"] if resultado.matched_count == 1 else None
    except Exception as e:
        logging.error(f"[{worker_id}] Erro ao registrar falha do job {job['_id']}: {e}")
        return None


def liberar_jobs_expirados(db) -> int:
    """Devolve para a fila os jobs cujo worker parou de dar sinal. Retorna quantos foram tratados."""
    momento = agora()
    filtro = {"status": STATUS_EXECUTANDO, "lease_ate": {"$lt": momento}}
    try:
        esgotados = db[COLECAO_JOBS].update_many(
            {**filtro, "$expr": {"$gte": ["$tentativas", "$max_tentativas"]}},
            {"$set": {
                "status": STATUS_ERRO,
                "mensagem": "Falhou",
                "erro": "O worker parou de responder durante o processamento.",
                "lease_ate": None,
                "concluido_em": momento,
                "atualizado_em": momento,
            }},
        )
        devolvidos = db[COLECAO_JOBS].update_many(
            filtro,
            {"$set": {
                "status": STATUS_PENDENTE,
                "mensagem": "Na fila (worker anterior parou de responder)",
                "worker_id": None,
                "lease_ate": None,
                "disponivel_em": momento,
                "atualizado_em": momento,
            }},
        )
        total = esgotados.modified_count + devolvidos.modified_count
        if total:
            logging.warning(f"Jobs com posse vencida: {devolvidos.modified_count} devolvidos, "
                            f"{esgotados.modified_count} marcados como erro.")
        return total
    except Exception as e:
        logging.error(f"Erro ao liberar jobs expirados: {e}")
        return 0
