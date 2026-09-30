# Modelos, Stories e exportação em imagem pela API, contra um MongoDB de verdade
import uuid

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from api.main import app
from core.modelos.midia import montar_midia


@pytest.fixture
def cliente(db_limpo):
    with TestClient(app) as cliente:
        entrar(cliente)
        yield cliente


def entrar(cliente, igreja="Igreja Modelos"):
    return cliente.post("/api/auth/cadastro", json={
        "nome_igreja": igreja, "nome": "Pessoa", "email": f"{uuid.uuid4().hex[:8]}@exemplo.com",
        "senha": "senha-segura-1"}).json()


def criar_midia(db, cliente, duracao=90.0):
    organizacao_id = ObjectId(cliente.get("/api/auth/eu").json()["organizacao"]["id"])
    midia = montar_midia(organizacao_id, None, "Culto de domingo.mp4", 10)
    midia.update({"status": "pronta", "duracao": duracao, "video": {"largura": 1920, "altura": 1080}})
    return str(db.midias.insert_one(midia).inserted_id)


def test_lista_de_modelos_prontos(cliente):
    modelos = cliente.get("/api/modelos").json()
    assert [(m["id"], m["pronto"]) for m in modelos] == [
        ("culto-de-hoje", True), ("frase-da-pregacao", True), ("versiculo", True)]
    assert modelos[2]["fundo"] == {"escurecer": 0.45, "desfoque": 14}


def test_criar_story_com_modelo(cliente, db_limpo):
    cliente.patch("/api/identidade", json={"instagram": "@igreja.modelo"})
    midia_id = criar_midia(db_limpo, cliente)
    story = cliente.post("/api/projetos", json={"midia_id": midia_id, "tipo": "story",
                                                "modelo_id": "culto-de-hoje", "inicio": 20}).json()
    assert story["tipo"] == "story"
    assert story["nome"] == "Story · Culto de domingo"
    assert story["trecho"] == {"inicio": 20.0, "fim": 35.0}
    assert story["modelo_id"] == "culto-de-hoje"
    assert [t["texto"] for t in story["textos"]] == ["Culto de hoje", "Domingo · 19h", "@igreja.modelo"]
    assert story["marca"]["logo"] is False   # a igreja ainda não enviou logo
    assert story["fundo"]["escurecer"] == 0.35

    assert cliente.post("/api/projetos", json={"midia_id": midia_id, "modelo_id": "nao-existe"}).status_code == 404


def test_salvar_usar_e_apagar_modelo_da_igreja(cliente, db_limpo):
    midia_id = criar_midia(db_limpo, cliente)
    projeto = cliente.post("/api/projetos", json={"midia_id": midia_id, "tipo": "story",
                                                  "modelo_id": "versiculo"}).json()
    cliente.patch(f"/api/projetos/{projeto['id']}", json={
        "versao": 1, "fundo": {"escurecer": 0.6, "desfoque": 4},
        "textos": [{"id": "a", "tipo": "frase", "texto": "Nossa frase", "estilo": "manuscrito", "tamanho": 1.4}]})

    salvo = cliente.post("/api/modelos", json={"nome": "  Frase  da  igreja ", "projeto_id": projeto["id"]})
    assert salvo.status_code == 201
    modelo = salvo.json()
    assert modelo["nome"] == "Frase da igreja" and modelo["pronto"] is False
    assert modelo["fundo"] == {"escurecer": 0.6, "desfoque": 4}
    assert modelo["textos"][0]["tamanho"] == 1.4
    assert cliente.get("/api/modelos").json()[0]["id"] == modelo["id"]   # os da igreja vêm primeiro

    novo = cliente.post("/api/projetos", json={"midia_id": midia_id, "tipo": "story", "modelo_id": modelo["id"]}).json()
    assert novo["textos"][0]["texto"] == "Nossa frase"
    assert novo["fundo"]["escurecer"] == 0.6
    assert novo["modelo_id"] == modelo["id"]

    assert cliente.delete("/api/modelos/versiculo").status_code == 403
    assert cliente.delete(f"/api/modelos/{modelo['id']}").status_code == 204
    assert len(cliente.get("/api/modelos").json()) == 3


def test_modelos_separados_por_igreja(cliente, db_limpo):
    midia_id = criar_midia(db_limpo, cliente)
    projeto = cliente.post("/api/projetos", json={"midia_id": midia_id}).json()
    modelo = cliente.post("/api/modelos", json={"nome": "Da primeira", "projeto_id": projeto["id"]}).json()
    cliente.post("/api/auth/sair")
    entrar(cliente, igreja="Outra Igreja")
    assert [m["id"] for m in cliente.get("/api/modelos").json()] == ["culto-de-hoje", "frase-da-pregacao", "versiculo"]
    assert cliente.delete(f"/api/modelos/{modelo['id']}").status_code == 404
    assert cliente.post("/api/modelos", json={"nome": "x", "projeto_id": projeto["id"]}).status_code == 404


def test_exportar_imagem(cliente, db_limpo):
    projeto = cliente.post("/api/projetos", json={"midia_id": criar_midia(db_limpo, cliente)}).json()
    imagem = cliente.post(f"/api/projetos/{projeto['id']}/exportar", json={"formato": "imagem", "instante": 7.5}).json()
    assert (imagem["formato"], imagem["instante"]) == ("imagem", 7.5)
    video = cliente.post(f"/api/projetos/{projeto['id']}/exportar").json()   # sem corpo: vídeo, como antes
    assert video["formato"] == "video"
    assert cliente.post(f"/api/projetos/{projeto['id']}/exportar", json={"formato": "gif"}).status_code == 422
