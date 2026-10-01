# HolyStudy de ponta a ponta, com o Ollama simulado: o job, a API e a exclusão em cascata
import uuid

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

import worker.tarefas.estudo as tarefa_estudo
from api.main import app
from core.modelos.job import montar_job
from core.modelos.midia import montar_midia
from core.utils.fila import enfileirar_job, pegar_proximo_job
from core.utils.ollama import ErroOllama
from tests.test_estudo import FALA, palavras_da_fala
from worker.worker_principal import processar_job

RESPOSTA = {
    "frases_centrais": [{"frase": "A graça de Deus nos alcança antes de nós sabermos orar", "importancia": 9},
                        {"frase": "Jesus disse que a igreja precisa de mais dinheiro", "importancia": 10}],
    "temas": ["Graça", "Dinheiro"],
    "personagens": ["Davi", "Paulo"],
    "perguntas": [{"pergunta": "Quando você percebeu a graça antes de saber orar?",
                   "frase_base": "A graça de Deus nos alcança antes de nós sabermos orar"}],
    "aplicacoes": ["procure alguém que você precisa perdoar e dê o primeiro passo"],
}


@pytest.fixture
def cliente(db_limpo):
    with TestClient(app) as cliente:
        cliente.post("/api/auth/cadastro", json={
            "nome_igreja": "Igreja do Estudo", "nome": "Pessoa", "email": f"{uuid.uuid4().hex[:8]}@exemplo.com",
            "senha": "senha-segura-1"})
        yield cliente


def culto_transcrito(db, organizacao_id) -> ObjectId:
    midia = montar_midia(organizacao_id, None, "Culto.mp4", 10)
    midia.update({"status": "pronta", "duracao": 60.0, "video": {"largura": 1920, "altura": 1080}})
    midia_id = db.midias.insert_one(midia).inserted_id
    db.transcricoes.insert_one({
        "organizacao_id": organizacao_id, "midia_id": midia_id, "gerado_por_ia": True,
        "segmentos": [{"inicio": 0.0, "fim": 40.0, "texto": FALA, "palavras": palavras_da_fala()}],
        "versiculos": [{"referencia": "Romanos 12:2", "inicio": 2.5, "fim": 3.4, "citacao": "Romanos doze"}],
    })
    return midia_id


def rodar_estudo(db, organizacao_id, midia_id, monkeypatch, resposta=RESPOSTA, falhar=False):
    def ollama_simulado(sistema, usuario, esquema, descarregar=False, imagens=None):
        if falhar:
            raise ErroOllama("sem conexão")
        assert "palavra por palavra" in sistema and "[0.0]" in usuario   # a fala vai com o tempo de cada linha
        return resposta

    monkeypatch.setattr(tarefa_estudo, "completar_json", ollama_simulado)
    enfileirar_job(db, montar_job("estudo_culto", organizacao_id, {"midia_id": str(midia_id)}))
    job = pegar_proximo_job(db, ["estudo_culto"], "w-teste")
    return processar_job(db, job, "w-teste"), db.jobs.find_one({"_id": job["_id"]})


def test_estudo_pela_api(cliente, db_limpo, monkeypatch):
    organizacao_id = ObjectId(cliente.get("/api/auth/eu").json()["organizacao"]["id"])
    midia_id = culto_transcrito(db_limpo, organizacao_id)
    assert cliente.get(f"/api/midias/{midia_id}/estudo").json()["status"] == "ausente"
    # Na máquina sem IA, pedir o estudo responde que a IA está desligada
    assert cliente.post(f"/api/midias/{midia_id}/estudo").status_code == 409

    resultado, _ = rodar_estudo(db_limpo, organizacao_id, midia_id, monkeypatch)
    assert resultado == "concluido"
    estudo = cliente.get(f"/api/midias/{midia_id}/estudo").json()
    assert estudo["status"] == "pronta" and estudo["gerado_por_ia"] is True
    # A frase sai como está na transcrição, com a pontuação; a inventada sobre dinheiro some
    assert [frase["texto"] for frase in estudo["resumo"]] == ["A graça de Deus nos alcança antes de nós sabermos orar."]
    assert estudo["temas"] == ["Graça"] and estudo["personagens"] == ["Davi"]   # "Dinheiro" e "Paulo" não foram ditos
    assert estudo["perguntas"][0]["base"]["inicio"] == pytest.approx(17.0)   # "A graça" é a 35ª palavra, a 0,5 s cada
    assert estudo["aplicacoes"][0]["texto"].startswith("procure alguém")
    assert estudo["versiculos_chave"][0]["referencia"] == "Romanos 12:2"
    assert estudo["oracao"].startswith("Encerrem o encontro orando")


def test_estudo_sem_nada_dito_ou_sem_modelo_falha_sem_repetir(db_limpo, monkeypatch):
    organizacao_id = ObjectId()
    midia_id = culto_transcrito(db_limpo, organizacao_id)
    inventado = {"frases_centrais": [{"frase": "uma frase que o pastor nunca falou no culto", "importancia": 9}],
                 "temas": [], "personagens": [], "perguntas": [], "aplicacoes": []}
    resultado, job = rodar_estudo(db_limpo, organizacao_id, midia_id, monkeypatch, resposta=inventado)
    assert resultado == "erro" and job["tentativas"] == 1 and "disse de fato" in job["erro"]
    assert db_limpo.estudos.count_documents({}) == 0

    resultado, job = rodar_estudo(db_limpo, organizacao_id, midia_id, monkeypatch, falhar=True)
    assert resultado == "erro" and "modelo de linguagem" in job["erro"]


def test_excluir_o_culto_apaga_o_que_a_ia_tirou_dele(cliente, db_limpo, monkeypatch):
    organizacao_id = ObjectId(cliente.get("/api/auth/eu").json()["organizacao"]["id"])
    midia_id = culto_transcrito(db_limpo, organizacao_id)
    rodar_estudo(db_limpo, organizacao_id, midia_id, monkeypatch)
    for colecao in ("sugestoes", "rostos", "momentos"):
        db_limpo[colecao].insert_one({"organizacao_id": organizacao_id, "midia_id": midia_id})
    assert cliente.delete(f"/api/midias/{midia_id}").status_code == 204
    for colecao in ("transcricoes", "sugestoes", "rostos", "momentos", "estudos"):
        assert db_limpo[colecao].count_documents({"midia_id": midia_id}) == 0, colecao
