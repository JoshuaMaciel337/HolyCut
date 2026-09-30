# Biblioteca de músicas pela API, contra um MongoDB de verdade (sem FFmpeg: o job fica na fila)
import uuid

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from api.main import app
from core.modelos.midia import montar_midia
from core.modelos.musica import chave_musica
from core.utils import storage


@pytest.fixture
def cliente(db_limpo):
    with TestClient(app) as cliente:
        entrar(cliente)
        yield cliente


def entrar(cliente, igreja="Igreja Música"):
    return cliente.post("/api/auth/cadastro", json={
        "nome_igreja": igreja, "nome": "Pessoa", "email": f"{uuid.uuid4().hex[:8]}@exemplo.com",
        "senha": "senha-segura-1"}).json()


def cadastrar(cliente, **dados):
    return cliente.post("/api/musicas", json={"titulo": "Hino", "licenca": "propria", **dados})


def test_cadastro_exige_licenca(cliente):
    assert cliente.post("/api/musicas", json={"titulo": "Sem licença"}).status_code == 422
    assert cadastrar(cliente, licenca="youtube").status_code == 422
    sem_atribuicao = cadastrar(cliente, licenca="cc_by")
    assert sem_atribuicao.status_code == 422
    assert "atribuição" in sem_atribuicao.json()["detail"]

    musica = cadastrar(cliente, licenca="cc_by", atribuicao="Autor, via site (CC BY 4.0)").json()
    assert musica["status"] == "aguardando_arquivo"
    assert musica["licenca_nome"] == "Creative Commons com atribuição (CC BY)"
    assert [m["id"] for m in cliente.get("/api/musicas").json()] == [musica["id"]]
    # Trocar para CC BY sem atribuição também é recusado
    outra = cadastrar(cliente).json()
    assert cliente.patch(f"/api/musicas/{outra['id']}", json={"licenca": "cc_by"}).status_code == 422
    renomeada = cliente.patch(f"/api/musicas/{outra['id']}", json={"titulo": " Novo título "}).json()
    assert renomeada["titulo"] == "Novo título"


def test_envio_do_arquivo_poe_o_job_na_fila(cliente, db_limpo):
    musica = cadastrar(cliente).json()
    url = f"/api/musicas/{musica['id']}/arquivo"
    assert cliente.put(url, params={"nome": "hino.exe"}, content=b"x").status_code == 422
    assert cliente.put(url, params={"nome": "hino.mp3"}, content=b"").status_code == 422

    enviada = cliente.put(url, params={"nome": "Hino Final.MP3"}, content=b"audio-de-mentira")
    assert enviada.status_code == 200
    assert enviada.json()["status"] == "processando"
    job = db_limpo.jobs.find_one({"tipo": "preparar_musica"})
    assert job["entrada"] == {"musica_id": musica["id"]}
    documento = db_limpo.musicas.find_one({"_id": ObjectId(musica["id"])})
    assert documento["original"] == "original.mp3"
    assert storage.caminho_local(chave_musica(documento["organizacao_id"], documento["_id"], "original.mp3")).is_file()
    # Enquanto prepara, não aceita outro arquivo, e ainda não dá para ouvir
    assert cliente.put(url, params={"nome": "outra.mp3"}, content=b"x").status_code == 409
    assert cliente.get(url).status_code == 404


def test_projeto_usa_musica_da_igreja_e_perde_ao_apagar(cliente, db_limpo):
    organizacao_id = ObjectId(cliente.get("/api/auth/eu").json()["organizacao"]["id"])
    midia = montar_midia(organizacao_id, None, "Culto.mp4", 10)
    midia.update({"status": "pronta", "duracao": 60.0, "video": {"largura": 1920, "altura": 1080}})
    midia_id = str(db_limpo.midias.insert_one(midia).inserted_id)
    projeto = cliente.post("/api/projetos", json={"midia_id": midia_id}).json()
    assert projeto["musica"] == {"id": None, "volume": 0.25, "abaixar_na_fala": True, "inicio": 0.0}

    musica = cadastrar(cliente).json()
    salvo = cliente.patch(f"/api/projetos/{projeto['id']}", json={
        "versao": 1, "musica": {"id": musica["id"], "volume": 0.4, "abaixar_na_fala": False, "inicio": 12}})
    assert salvo.json()["musica"] == {"id": musica["id"], "volume": 0.4, "abaixar_na_fala": False, "inicio": 12.0}
    assert cliente.patch(f"/api/projetos/{projeto['id']}",
                         json={"versao": 2, "musica": {"id": str(ObjectId())}}).status_code == 404
    assert cliente.patch(f"/api/projetos/{projeto['id']}",
                         json={"versao": 2, "musica": {"id": musica["id"], "volume": 1.5}}).status_code == 422
    exportacao = cliente.post(f"/api/projetos/{projeto['id']}/exportar").json()
    configuracao = db_limpo.exportacoes.find_one({"_id": ObjectId(exportacao["id"])})["configuracao"]
    assert configuracao["musica"]["id"] == musica["id"]

    assert cliente.delete(f"/api/musicas/{musica['id']}").status_code == 204
    depois = cliente.get(f"/api/projetos/{projeto['id']}").json()
    assert depois["musica"]["id"] is None and depois["versao"] == 3
    assert cliente.get("/api/musicas").json() == []


def test_musicas_separadas_por_igreja(cliente):
    musica = cadastrar(cliente).json()
    cliente.post("/api/auth/sair")
    entrar(cliente, igreja="Outra Igreja")
    assert cliente.get("/api/musicas").json() == []
    assert cliente.delete(f"/api/musicas/{musica['id']}").status_code == 404
    envio = cliente.put(f"/api/musicas/{musica['id']}/arquivo", params={"nome": "a.mp3"}, content=b"x")
    assert envio.status_code == 404
    assert cliente.get("/api/musicas/nao-e-id/arquivo").status_code == 404
