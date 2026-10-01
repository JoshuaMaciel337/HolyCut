# Identidade da igreja, camadas de arte e marca/textos do projeto, contra um MongoDB de verdade
import io
import uuid

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from PIL import Image

from api.main import app
from core.modelos.midia import montar_midia


@pytest.fixture
def cliente(db_limpo):
    with TestClient(app) as cliente:
        entrar(cliente)
        yield cliente


def entrar(cliente, igreja="Igreja Identidade"):
    return cliente.post("/api/auth/cadastro", json={
        "nome_igreja": igreja, "nome": "Pessoa", "email": f"{uuid.uuid4().hex[:8]}@exemplo.com",
        "senha": "senha-segura-1"}).json()


def png(largura=400, altura=200, cor=(255, 138, 0, 255)) -> bytes:
    saida = io.BytesIO()
    Image.new("RGBA", (largura, altura), cor).save(saida, format="PNG")
    return saida.getvalue()


def test_identidade_padrao_e_edicao(cliente):
    inicial = cliente.get("/api/identidade").json()
    assert inicial == {"nome_exibicao": "Igreja Identidade", "instagram": "", "cor_destaque": "#FF8A00",
                       "logo": False, "estrategia": "", "atualizado_em": None}

    editada = cliente.patch("/api/identidade", json={
        "instagram": "https://instagram.com/Igreja.Viva", "cor_destaque": "#7b61ff", "nome_exibicao": "  IEV  "}).json()
    assert editada["instagram"] == "@igreja.viva"
    assert editada["cor_destaque"] == "#7B61FF"
    assert editada["nome_exibicao"] == "IEV"
    assert cliente.patch("/api/identidade", json={"cor_destaque": "laranja"}).status_code == 422


def test_logo_enviar_baixar_e_remover(cliente):
    assert cliente.get("/api/identidade/logo").status_code == 404
    enviado = cliente.put("/api/identidade/logo", content=png(), headers={"Content-Type": "image/png"})
    assert enviado.status_code == 200
    assert enviado.json()["logo"] is True

    baixado = cliente.get("/api/identidade/logo")
    assert baixado.headers["content-type"] == "image/png"
    assert Image.open(io.BytesIO(baixado.content)).size == (400, 200)

    assert cliente.put("/api/identidade/logo", content=b"nao e imagem").status_code == 422
    assert cliente.put("/api/identidade/logo", content=b"x" * (5 * 1024 * 1024 + 10)).status_code == 413
    assert cliente.delete("/api/identidade/logo").json()["logo"] is False
    assert cliente.get("/api/identidade/logo").status_code == 404


def test_camadas_da_previa(cliente):
    texto = {"id": "t1", "texto": "Ele é digno", "estilo": "destaque", "posicao": "base"}
    camada = cliente.post("/api/arte/camada", json={"largura": 360, "altura": 640, "tipo": "texto", "texto": texto})
    assert camada.status_code == 200
    assert camada.headers["content-type"] == "image/png"
    imagem = Image.open(io.BytesIO(camada.content))
    assert imagem.size == (360, 640)
    assert imagem.getchannel("A").getbbox() is not None

    sem_logo = cliente.post("/api/arte/camada", json={"largura": 360, "altura": 640, "tipo": "logo",
                                                      "marca": {"logo": True}})
    assert sem_logo.status_code == 404
    cliente.put("/api/identidade/logo", content=png())
    com_logo = cliente.post("/api/arte/camada", json={"largura": 360, "altura": 640, "tipo": "logo",
                                                      "marca": {"logo": True, "posicao": "base_esquerda"}})
    caixa = Image.open(io.BytesIO(com_logo.content)).getchannel("A").getbbox()
    assert caixa[0] < 60 and caixa[3] > 580     # canto de baixo, à esquerda
    assert cliente.post("/api/arte/camada", json={"largura": 10, "altura": 640, "tipo": "texto",
                                                  "texto": texto}).status_code == 422


def test_projeto_nasce_com_o_logo_e_aceita_textos(cliente, db_limpo):
    cliente.put("/api/identidade/logo", content=png())
    organizacao_id = ObjectId(cliente.get("/api/auth/eu").json()["organizacao"]["id"])
    midia = montar_midia(organizacao_id, None, "Culto.mp4", 10)
    midia.update({"status": "pronta", "duracao": 60.0, "video": {"largura": 1920, "altura": 1080}})
    midia_id = str(db_limpo.midias.insert_one(midia).inserted_id)

    projeto = cliente.post("/api/projetos", json={"midia_id": midia_id}).json()
    assert projeto["marca"] == {"logo": True, "posicao": "topo_direita", "tamanho": 0.16, "opacidade": 0.9}
    assert projeto["textos"] == []

    textos = [{"id": "a", "tipo": "titulo", "texto": "Culto de hoje", "estilo": "manuscrito", "posicao": "topo"},
              {"id": "b", "tipo": "versiculo", "texto": "Tudo posso", "referencia": "Fp 4:13", "inicio": 2, "fim": 6}]
    salvo = cliente.patch(f"/api/projetos/{projeto['id']}", json={"versao": 1, "textos": textos,
                                                                  "marca": {"logo": False}})
    assert salvo.status_code == 200
    assert [t["id"] for t in salvo.json()["textos"]] == ["a", "b"]
    assert salvo.json()["marca"]["logo"] is False

    rota = f"/api/projetos/{projeto['id']}"
    ruim = [{"id": "c", "texto": "x", "inicio": 5, "fim": 3}]
    assert cliente.patch(rota, json={"versao": 2, "textos": ruim}).status_code == 422
    repetido = [{"id": "d", "texto": "x"}, {"id": "d", "texto": "y"}]
    assert cliente.patch(rota, json={"versao": 2, "textos": repetido}).status_code == 422
    muitos = [{"id": str(i), "texto": "x"} for i in range(7)]
    assert cliente.patch(rota, json={"versao": 2, "textos": muitos}).status_code == 422

    exportacao = cliente.post(f"/api/projetos/{projeto['id']}/exportar").json()
    configuracao = db_limpo.exportacoes.find_one({"_id": ObjectId(exportacao["id"])})["configuracao"]
    assert configuracao["textos"][1]["referencia"] == "Fp 4:13"
    assert configuracao["marca"]["logo"] is False


def test_identidade_separada_por_igreja(cliente):
    cliente.put("/api/identidade/logo", content=png())
    cliente.patch("/api/identidade", json={"cor_destaque": "#123456"})
    cliente.post("/api/auth/sair")
    entrar(cliente, igreja="Outra Igreja")
    outra = cliente.get("/api/identidade").json()
    assert outra["logo"] is False and outra["cor_destaque"] == "#FF8A00"
    assert cliente.get("/api/identidade/logo").status_code == 404
