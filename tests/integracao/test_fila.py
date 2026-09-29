# Fila de jobs contra um MongoDB de verdade
import gzip
from datetime import timedelta

import bson

from backup.agendador_backup import executar_backup
from core.modelos.job import STATUS_CONCLUIDO, STATUS_ERRO, STATUS_EXECUTANDO, STATUS_PENDENTE, montar_job
from core.utils.fila import (
    atualizar_progresso,
    concluir_job,
    enfileirar_job,
    falhar_job,
    liberar_jobs_expirados,
    pegar_proximo_job,
    renovar_lease,
)
from core.utils.mongo import agora
from worker.worker_principal import processar_job


def novo_job(db, tipo="teste", prioridade=0, **extras):
    job = montar_job(tipo, "org1", extras.pop("entrada", {}), prioridade=prioridade)
    job.update(extras)
    return enfileirar_job(db, job)


def test_pega_por_prioridade_e_depois_por_ordem(db_limpo):
    primeiro = novo_job(db_limpo, criado_em=agora() - timedelta(minutes=2))
    urgente = novo_job(db_limpo, prioridade=10)
    novo_job(db_limpo, criado_em=agora() - timedelta(minutes=1))

    assert pegar_proximo_job(db_limpo, ["teste"], "w1")["_id"] == urgente
    assert pegar_proximo_job(db_limpo, ["teste"], "w1")["_id"] == primeiro


def test_nao_pega_tipo_de_outro_recurso_nem_job_futuro(db_limpo):
    novo_job(db_limpo, tipo="diagnostico_gpu")
    novo_job(db_limpo, disponivel_em=agora() + timedelta(minutes=5))
    assert pegar_proximo_job(db_limpo, ["teste"], "w1") is None


def test_dois_workers_nao_pegam_o_mesmo_job(db_limpo):
    novo_job(db_limpo)
    assert pegar_proximo_job(db_limpo, ["teste"], "w1") is not None
    assert pegar_proximo_job(db_limpo, ["teste"], "w2") is None


def test_progresso_e_conclusao_exigem_posse(db_limpo):
    job_id = novo_job(db_limpo)
    job = pegar_proximo_job(db_limpo, ["teste"], "w1")
    assert job["status"] == STATUS_EXECUTANDO and job["tentativas"] == 1

    assert atualizar_progresso(db_limpo, job_id, "w1", 40, "Transcrevendo")
    assert not atualizar_progresso(db_limpo, job_id, "intruso", 90, "")
    assert renovar_lease(db_limpo, job_id, "w1")
    assert concluir_job(db_limpo, job_id, "w1", {"ok": True})

    salvo = db_limpo.jobs.find_one({"_id": job_id})
    assert salvo["status"] == STATUS_CONCLUIDO
    assert salvo["progresso"] == 100
    assert salvo["saida"] == {"ok": True}


def test_falha_volta_para_fila_e_depois_esgota(db_limpo):
    job_id = novo_job(db_limpo, max_tentativas=2)

    job = pegar_proximo_job(db_limpo, ["teste"], "w1")
    assert falhar_job(db_limpo, job, "w1", "erro 1") == STATUS_PENDENTE
    salvo = db_limpo.jobs.find_one({"_id": job_id})
    assert salvo["disponivel_em"] > agora() + timedelta(seconds=30)

    db_limpo.jobs.update_one({"_id": job_id}, {"$set": {"disponivel_em": agora()}})
    job = pegar_proximo_job(db_limpo, ["teste"], "w1")
    assert job["tentativas"] == 2
    assert falhar_job(db_limpo, job, "w1", "erro 2") == STATUS_ERRO
    assert db_limpo.jobs.find_one({"_id": job_id})["erro"] == "erro 2"


def test_job_de_worker_que_caiu_volta_para_fila(db_limpo):
    devolvido = novo_job(db_limpo)
    esgotado = novo_job(db_limpo, max_tentativas=1)
    pegar_proximo_job(db_limpo, ["teste"], "w-caiu")
    pegar_proximo_job(db_limpo, ["teste"], "w-caiu")
    db_limpo.jobs.update_many({}, {"$set": {"lease_ate": agora() - timedelta(minutes=1)}})

    assert liberar_jobs_expirados(db_limpo) == 2
    assert db_limpo.jobs.find_one({"_id": devolvido})["status"] == STATUS_PENDENTE
    assert db_limpo.jobs.find_one({"_id": esgotado})["status"] == STATUS_ERRO


def test_worker_processa_job_de_teste_de_ponta_a_ponta(db_limpo):
    ok_id = novo_job(db_limpo, entrada={"duracao": 1}, prioridade=1)
    falha_id = novo_job(db_limpo, entrada={"duracao": 1, "falhar": True})

    assert processar_job(db_limpo, pegar_proximo_job(db_limpo, ["teste"], "w1"), "w1") == "concluido"
    assert processar_job(db_limpo, pegar_proximo_job(db_limpo, ["teste"], "w1"), "w1") == STATUS_PENDENTE

    assert db_limpo.jobs.find_one({"_id": ok_id})["status"] == STATUS_CONCLUIDO
    falho = db_limpo.jobs.find_one({"_id": falha_id})
    assert falho["status"] == STATUS_PENDENTE
    assert "Falha simulada" in falho["erro"]


def test_backup_exporta_colecoes_em_bson(db_limpo, tmp_path):
    novo_job(db_limpo)
    novo_job(db_limpo)
    destino = executar_backup(pasta=tmp_path, retencao_dias=14)
    assert destino is not None

    with gzip.open(destino / "jobs.bson.gz", "rb") as arquivo:
        documentos = bson.decode_all(arquivo.read())
    assert len(documentos) == 2
    assert documentos[0]["tipo"] == "teste"
