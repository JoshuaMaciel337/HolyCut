# Blocos do culto e a pregação de ponta a ponta, com o Ollama simulado:
# o job, a marcação da pessoa (que a IA não troca) e o vídeo 16:9 da mensagem
import uuid

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

import worker.tarefas.blocos as tarefa_blocos
from api.main import app
from core.modelos.job import montar_job
from core.modelos.midia import ARQUIVO_NIVEIS, chave_arquivo, montar_midia
from core.utils import storage
from core.utils.fila import enfileirar_job, pegar_proximo_job
from core.utils.ollama import ErroOllama
from tests.test_blocos import DURACAO, niveis_do_culto, palavras_do_culto
from worker.worker_principal import processar_job


@pytest.fixture
def cliente(db_limpo):
    with TestClient(app) as cliente:
        cliente.post("/api/auth/cadastro", json={
            "nome_igreja": "Igreja dos Blocos", "nome": "Pessoa", "email": f"{uuid.uuid4().hex[:8]}@exemplo.com",
            "senha": "senha-segura-1"})
        yield cliente


def culto_transcrito(db, organizacao_id) -> ObjectId:
    midia = montar_midia(organizacao_id, None, "Culto.mp4", 10)
    midia.update({"status": "pronta", "duracao": DURACAO, "video": {"largura": 1920, "altura": 1080},
                  "arquivos": [ARQUIVO_NIVEIS]})
    midia_id = db.midias.insert_one(midia).inserted_id
    storage.salvar_bytes(chave_arquivo(organizacao_id, midia_id, ARQUIVO_NIVEIS), niveis_do_culto().tobytes())
    palavras = palavras_do_culto()
    db.transcricoes.insert_one({
        "organizacao_id": organizacao_id, "midia_id": midia_id, "gerado_por_ia": True,
        "segmentos": [{"inicio": 0.0, "fim": DURACAO, "texto": "", "palavras": palavras}], "versiculos": [],
    })
    return midia_id


def rodar_blocos(db, organizacao_id, midia_id, monkeypatch, falhar=False):
    def ollama_simulado(sistema, usuario, esquema, descarregar=False, imagens=None):
        if falhar:
            raise ErroOllama("sem conexão")
        assert "lista" not in usuario and "Começa em" in usuario   # a parte vai com a posição no culto
        if "avisos" in usuario:
            return {"tipo": "avisos"}
        if "oferta" in usuario:
            return {"tipo": "batismo"}   # fora da lista: fica o nome pelas palavras-chave
        return {"tipo": "pregacao"}

    monkeypatch.setattr(tarefa_blocos, "completar_json", ollama_simulado)
    enfileirar_job(db, montar_job("blocos_culto", organizacao_id, {"midia_id": str(midia_id)}))
    job = pegar_proximo_job(db, ["blocos_culto"], "w-teste")
    return processar_job(db, job, "w-teste")


def test_blocos_marcam_a_pregacao_e_a_pessoa_tem_a_palavra_final(cliente, db_limpo, monkeypatch):
    organizacao_id = ObjectId(cliente.get("/api/auth/eu").json()["organizacao"]["id"])
    midia_id = culto_transcrito(db_limpo, organizacao_id)
    assert cliente.get(f"/api/midias/{midia_id}/blocos").json()["status"] == "ausente"
    assert cliente.post(f"/api/midias/{midia_id}/blocos").status_code == 409   # sem IA neste servidor

    assert rodar_blocos(db_limpo, organizacao_id, midia_id, monkeypatch) == "concluido"
    blocos = cliente.get(f"/api/midias/{midia_id}/blocos").json()
    assert blocos["status"] == "pronta" and blocos["nomes_pelo_modelo"] is True
    assert [bloco["tipo"] for bloco in blocos["blocos"]] == ["louvor", "avisos", "oferta", "louvor", "pregacao"]
    assert blocos["pregacao"] == {"inicio": 724.5, "fim": 1490.75}
    midia = cliente.get(f"/api/midias/{midia_id}").json()
    assert midia["pregacao"] == {"inicio": 724.5, "fim": 1490.75, "origem": "ia"}

    # A pessoa ajusta. Rodar os blocos de novo não troca a marcação dela.
    assert cliente.put(f"/api/midias/{midia_id}/pregacao", json={"inicio": 700, "fim": 710}).status_code == 422
    marcada = cliente.put(f"/api/midias/{midia_id}/pregacao", json={"inicio": 730, "fim": 1480}).json()
    assert marcada["pregacao"] == {"inicio": 730.0, "fim": 1480.0, "origem": "pessoa"}
    assert rodar_blocos(db_limpo, organizacao_id, midia_id, monkeypatch) == "concluido"
    assert cliente.get(f"/api/midias/{midia_id}").json()["pregacao"]["origem"] == "pessoa"

    # O vídeo da mensagem: 16:9, só a pregação, sem cortar silêncio nem gravar legenda
    projeto = cliente.post(f"/api/midias/{midia_id}/pregacao/projeto")
    assert projeto.status_code == 201
    projeto = projeto.json()
    assert projeto["tipo"] == "mensagem" and projeto["proporcao"] == "16:9"
    assert [(parte["inicio"], parte["fim"]) for parte in projeto["partes"]] == [(730.0, 1480.0)]
    assert projeto["silencios"]["intensidade"] is None and projeto["legenda"]["ativa"] is False
    assert projeto["nome"] == "Mensagem · Culto"

    assert cliente.delete(f"/api/midias/{midia_id}/pregacao").json()["pregacao"] is None
    assert cliente.post(f"/api/midias/{midia_id}/pregacao/projeto").status_code == 409


def test_sem_o_modelo_ficam_os_nomes_pelas_palavras(db_limpo, monkeypatch):
    organizacao_id = ObjectId()
    midia_id = culto_transcrito(db_limpo, organizacao_id)
    assert rodar_blocos(db_limpo, organizacao_id, midia_id, monkeypatch, falhar=True) == "concluido"
    documento = db_limpo.blocos.find_one({"midia_id": midia_id})
    assert documento["modelo"] is None
    assert [bloco["tipo"] for bloco in documento["blocos"]] == ["louvor", "avisos", "oferta", "louvor", "pregacao"]
    assert db_limpo.midias.find_one({"_id": midia_id})["pregacao"]["origem"] == "ia"


def test_sem_transcricao_o_job_falha_sem_repetir(db_limpo, monkeypatch):
    organizacao_id = ObjectId()
    midia = montar_midia(organizacao_id, None, "Culto.mp4", 10)
    midia.update({"status": "pronta", "duracao": DURACAO})
    midia_id = db_limpo.midias.insert_one(midia).inserted_id
    assert rodar_blocos(db_limpo, organizacao_id, midia_id, monkeypatch) == "erro"
    job = db_limpo.jobs.find_one({"tipo": "blocos_culto"})
    assert job["tentativas"] == 1 and "transcrição" in job["erro"]
