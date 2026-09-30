# Aprovação pelo celular: o editor pede, quem aprova responde pelo link, sem conta
import uuid
from contextlib import contextmanager
from datetime import timedelta

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from api.main import app
from core.modelos.midia import montar_midia
from core.modelos.projeto import chave_exportacao, montar_exportacao, montar_projeto
from core.utils import storage
from core.utils.mongo import agora


@pytest.fixture
def cliente(db_limpo):
    with TestClient(app) as cliente:
        entrar(cliente)
        yield cliente


def entrar(cliente, igreja="Igreja Aprovação"):
    return cliente.post("/api/auth/cadastro", json={
        "nome_igreja": igreja, "nome": "Pessoa", "email": f"{uuid.uuid4().hex[:8]}@exemplo.com",
        "senha": "senha-segura-1"}).json()


@contextmanager
def sem_sessao(cliente):
    """Como quem abre o link no celular: sem o cookie de sessão da igreja."""
    cookies = dict(cliente.cookies)
    cliente.cookies.clear()
    try:
        yield cliente
    finally:
        cliente.cookies.update(cookies)


def exportacao_pronta(db, cliente, status="pronta") -> str:
    organizacao_id = ObjectId(cliente.get("/api/auth/eu").json()["organizacao"]["id"])
    midia = montar_midia(organizacao_id, None, "Culto.mp4", 10)
    midia.update({"status": "pronta", "duracao": 60.0, "video": {"largura": 1920, "altura": 1080}})
    midia["_id"] = db.midias.insert_one(midia).inserted_id
    projeto = montar_projeto(organizacao_id, midia, None)
    projeto["_id"] = db.projetos.insert_one(projeto).inserted_id
    exportacao = montar_exportacao(projeto, None)
    exportacao.update({"status": status, "arquivos": ["video.mp4", "capa.jpg"], "duracao": 22.5})
    exportacao["_id"] = db.exportacoes.insert_one(exportacao).inserted_id
    storage.salvar_bytes(chave_exportacao(organizacao_id, exportacao["_id"], "video.mp4"), b"video-final")
    return str(exportacao["_id"])


def test_pedir_e_aprovar_pelo_link(cliente, db_limpo):
    exportacao_id = exportacao_pronta(db_limpo, cliente)
    pedido = cliente.post(f"/api/exportacoes/{exportacao_id}/aprovacao", json={"para": "Pr. João"})
    assert pedido.status_code == 201
    token = pedido.json()["token"]
    lista = cliente.get("/api/exportacoes").json()
    assert lista[0]["aprovacao"]["status"] == "pendente" and lista[0]["aprovacao"]["para"] == "Pr. João"
    assert "token" not in str(lista[0]["aprovacao"])           # nem o token nem o hash saem da API

    with sem_sessao(cliente) as celular:                      # o pastor, sem conta nem sessão
        pagina = celular.get(f"/api/aprovar/{token}").json()
        assert (pagina["igreja"], pagina["nome"], pagina["duracao"]) == ("Igreja Aprovação", "Reel · Culto", 22.5)
        assert pagina["aprovacao"]["status"] == "pendente"
        video = celular.get(f"/api/aprovar/{token}/arquivos/video.mp4")
        assert video.status_code == 200 and video.content == b"video-final"
        assert celular.get(f"/api/aprovar/{token}/arquivos/imagem.jpg").status_code == 404
        assert celular.get("/api/aprovar/token-que-nao-existe").status_code == 404
        # Com o link, não dá para ver o resto da igreja
        assert celular.get(f"/api/exportacoes/{exportacao_id}").status_code == 401

        assert celular.post(f"/api/aprovar/{token}", json={"decisao": "ajustes", "nome": "Pr. João"}).status_code == 422
        aprovado = celular.post(f"/api/aprovar/{token}", json={"decisao": "aprovado", "nome": "Pr. João"})
        assert aprovado.status_code == 200 and aprovado.json()["aprovacao"]["respondido_por"] == "Pr. João"
        assert celular.post(f"/api/aprovar/{token}", json={"decisao": "ajustes", "nome": "Outro",
                                                           "comentario": "x"}).status_code == 409

    resposta = cliente.get(f"/api/exportacoes/{exportacao_id}").json()["aprovacao"]
    assert (resposta["status"], resposta["respondido_por"]) == ("aprovado", "Pr. João")


def test_pedir_ajustes_trocar_link_e_expirar(cliente, db_limpo):
    exportacao_id = exportacao_pronta(db_limpo, cliente)
    primeiro = cliente.post(f"/api/exportacoes/{exportacao_id}/aprovacao").json()["token"]
    ajustes = cliente.post(f"/api/aprovar/{primeiro}", json={"decisao": "ajustes", "nome": "Ana",
                                                             "comentario": "Tirar o silêncio do começo"})
    assert ajustes.json()["aprovacao"]["comentario"] == "Tirar o silêncio do começo"

    # Depois de ajustar, o editor pede de novo: o link anterior deixa de valer
    segundo = cliente.post(f"/api/exportacoes/{exportacao_id}/aprovacao").json()["token"]
    assert cliente.get(f"/api/aprovar/{primeiro}").status_code == 404
    assert cliente.get(f"/api/aprovar/{segundo}").json()["aprovacao"]["status"] == "pendente"

    # Passou a validade sem resposta
    db_limpo.exportacoes.update_one({"_id": ObjectId(exportacao_id)},
                                    {"$set": {"aprovacao.expira_em": agora() - timedelta(minutes=1)}})
    assert cliente.get(f"/api/aprovar/{segundo}").json()["aprovacao"]["expirada"] is True
    assert cliente.get(f"/api/aprovar/{segundo}/arquivos/video.mp4").status_code == 410
    assert cliente.post(f"/api/aprovar/{segundo}", json={"decisao": "aprovado", "nome": "Ana"}).status_code == 410

    assert cliente.delete(f"/api/exportacoes/{exportacao_id}/aprovacao").status_code == 204
    assert cliente.get(f"/api/aprovar/{segundo}").status_code == 404
    assert cliente.get(f"/api/exportacoes/{exportacao_id}").json()["aprovacao"] is None


def test_aprovacao_so_de_video_pronto_e_da_propria_igreja(cliente, db_limpo):
    processando = exportacao_pronta(db_limpo, cliente, status="processando")
    assert cliente.post(f"/api/exportacoes/{processando}/aprovacao").status_code == 409
    pronta = exportacao_pronta(db_limpo, cliente)
    token = cliente.post(f"/api/exportacoes/{pronta}/aprovacao").json()["token"]
    cliente.post("/api/auth/sair")
    entrar(cliente, igreja="Outra Igreja")
    assert cliente.post(f"/api/exportacoes/{pronta}/aprovacao").status_code == 404
    assert cliente.delete(f"/api/exportacoes/{pronta}/aprovacao").status_code == 404
    # Excluir o vídeo apaga o pedido junto
    db_limpo.exportacoes.delete_one({"_id": ObjectId(pronta)})
    assert cliente.get(f"/api/aprovar/{token}").status_code == 404
