# API contra um MongoDB de verdade
import uuid

import pytest
from fastapi.testclient import TestClient

from api.main import app


@pytest.fixture
def cliente(db_limpo):
    with TestClient(app) as cliente:
        yield cliente


def cadastrar(cliente, igreja="Igreja Teste", email=None, senha="senha-segura-1"):
    email = email or f"{uuid.uuid4().hex[:8]}@exemplo.com"
    resposta = cliente.post("/api/auth/cadastro", json={
        "nome_igreja": igreja, "nome": "Pessoa Teste", "email": email, "senha": senha,
    })
    return resposta, email


def test_saude(cliente):
    resposta = cliente.get("/api/saude")
    assert resposta.status_code == 200
    assert resposta.json()["mongo"] is True


def test_cadastro_cria_sessao_e_organizacao(cliente):
    resposta, email = cadastrar(cliente, igreja="Igreja Batista da Graça")
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["usuario"]["email"] == email
    assert corpo["usuario"]["papel"] == "dono"
    assert corpo["organizacao"]["slug"] == "igreja-batista-da-graca"

    eu = cliente.get("/api/auth/eu")
    assert eu.status_code == 200
    assert eu.json()["organizacao"]["nome"] == "Igreja Batista da Graça"


def test_slug_repetido_ganha_sufixo_e_email_repetido_e_recusado(cliente):
    _, email = cadastrar(cliente, igreja="Comunidade Viva")
    segunda, _ = cadastrar(cliente, igreja="Comunidade Viva")
    assert segunda.json()["organizacao"]["slug"] == "comunidade-viva-2"

    repetido, _ = cadastrar(cliente, email=email.upper())
    assert repetido.status_code == 409


def test_validacao_responde_em_portugues(cliente):
    resposta = cliente.post("/api/auth/cadastro", json={
        "nome_igreja": "Igreja", "nome": "Pessoa", "email": "a@exemplo.com", "senha": "curta",
    })
    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "Senha precisa ter pelo menos 8 caracteres."


def test_login_sair_e_senha_errada(cliente):
    _, email = cadastrar(cliente)
    assert cliente.post("/api/auth/sair").status_code == 204
    assert cliente.get("/api/auth/eu").status_code == 401

    errado = cliente.post("/api/auth/entrar", json={"email": email, "senha": "errada"})
    assert errado.status_code == 401
    assert errado.json()["detail"] == "E-mail ou senha incorretos."

    certo = cliente.post("/api/auth/entrar", json={"email": email, "senha": "senha-segura-1"})
    assert certo.status_code == 200
    assert cliente.get("/api/auth/eu").status_code == 200


def test_login_bloqueia_depois_de_muitas_tentativas(cliente):
    _, email = cadastrar(cliente)
    cliente.post("/api/auth/sair")
    codigos = [cliente.post("/api/auth/entrar", json={"email": email, "senha": "errada"}).status_code
               for _ in range(6)]
    assert codigos[:5] == [401] * 5
    assert codigos[5] == 429


def test_jobs_sao_separados_por_organizacao(cliente):
    cadastrar(cliente, igreja="Igreja A")
    criado = cliente.post("/api/jobs", json={"tipo": "teste", "duracao": 5})
    assert criado.status_code == 201
    job = criado.json()
    assert job["status"] == "pendente"
    assert job["recurso"] == "cpu"
    assert [j["id"] for j in cliente.get("/api/jobs").json()] == [job["id"]]
    assert cliente.get(f"/api/jobs/{job['id']}").status_code == 200

    cliente.post("/api/auth/sair")
    cadastrar(cliente, igreja="Igreja B")
    assert cliente.get("/api/jobs").json() == []
    assert cliente.get(f"/api/jobs/{job['id']}").status_code == 404
    assert cliente.get("/api/jobs/id-invalido").status_code == 404


def test_rotas_protegidas_exigem_sessao(cliente):
    for rota in ("/api/auth/eu", "/api/jobs", "/api/sistema", "/api/eventos"):
        assert cliente.get(rota).status_code == 401
