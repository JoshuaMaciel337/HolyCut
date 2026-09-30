# Projetos e exportações pela API, contra um MongoDB de verdade
import uuid

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from api.main import app
from core.modelos.midia import montar_midia
from core.modelos.projeto import chave_exportacao
from core.utils import storage


@pytest.fixture
def cliente(db_limpo):
    with TestClient(app) as cliente:
        entrar(cliente)
        yield cliente


def entrar(cliente, igreja="Igreja Projetos"):
    resposta = cliente.post("/api/auth/cadastro", json={
        "nome_igreja": igreja, "nome": "Pessoa", "email": f"{uuid.uuid4().hex[:8]}@exemplo.com",
        "senha": "senha-segura-1"})
    return resposta.json()


def criar_midia(db, cliente, status="pronta", com_video=True, duracao=120.0):
    organizacao_id = ObjectId(cliente.get("/api/auth/eu").json()["organizacao"]["id"])
    midia = montar_midia(organizacao_id, None, "Culto de domingo.mp4", 1000)
    midia.update({"status": status, "duracao": duracao, "audio": {"codec": "aac", "canais": 2, "taxa": 48000},
                  "video": {"codec": "h264", "largura": 1920, "altura": 1080, "fps": 30, "rotacao": 0}
                  if com_video else None})
    return str(db.midias.insert_one(midia).inserted_id)


def test_criar_e_editar_projeto(cliente, db_limpo):
    midia_id = criar_midia(db_limpo, cliente)
    criado = cliente.post("/api/projetos", json={"midia_id": midia_id})
    assert criado.status_code == 201
    projeto = criado.json()
    assert projeto["nome"] == "Reel · Culto de domingo"
    assert projeto["proporcao"] == "9:16"
    assert projeto["partes"] == [{"id": "p1", "inicio": 0.0, "fim": 120.0}]
    assert projeto["versao"] == 1

    editado = cliente.patch(f"/api/projetos/{projeto['id']}", json={
        "versao": 1, "partes": [{"id": "p1", "inicio": 30.5, "fim": 500}],
        "enquadramento": {"x": 0.3, "y": 0.5, "zoom": 1.2}, "silencios": {"intensidade": None}, "proporcao": "4:5"})
    assert editado.status_code == 200
    corpo = editado.json()
    assert corpo["partes"] == [{"id": "p1", "inicio": 30.5, "fim": 120.0}]   # o fim não passa da gravação
    assert corpo["silencios"] == {"intensidade": None}
    assert corpo["proporcao"] == "4:5"
    assert corpo["versao"] == 2

    # Outra aba ainda com a versão 1: recusa em vez de apagar o trabalho
    velho = cliente.patch(f"/api/projetos/{projeto['id']}", json={"versao": 1, "nome": "Outro nome"})
    assert velho.status_code == 409
    assert cliente.get(f"/api/projetos/{projeto['id']}").json()["nome"] == "Reel · Culto de domingo"

    listados = cliente.get("/api/projetos", params={"midia_id": midia_id}).json()
    assert [p["id"] for p in listados] == [projeto["id"]]


def test_validacoes_do_projeto(cliente, db_limpo):
    assert cliente.post("/api/projetos", json={"midia_id": criar_midia(db_limpo, cliente, status="processando")}
                        ).status_code == 409
    assert cliente.post("/api/projetos", json={"midia_id": criar_midia(db_limpo, cliente, com_video=False)}
                        ).status_code == 422
    assert cliente.post("/api/projetos", json={"midia_id": "nao-existe"}).status_code == 404

    projeto = cliente.post("/api/projetos", json={"midia_id": criar_midia(db_limpo, cliente)}).json()
    rota = f"/api/projetos/{projeto['id']}"
    curta = [{"id": "p1", "inicio": 10, "fim": 10.5}]
    assert cliente.patch(rota, json={"versao": 1, "partes": curta}).status_code == 422
    assert cliente.patch(rota, json={"versao": 1, "enquadramento": {"x": 1.5, "y": 0.5, "zoom": 1}}).status_code == 422
    assert cliente.patch(rota, json={"versao": 1, "proporcao": "3:2"}).status_code == 422
    assert cliente.patch(rota, json={"versao": 1, "silencios": {"intensidade": "maxima"}}).status_code == 422


def test_linha_do_tempo_com_varias_partes(cliente, db_limpo):
    projeto = cliente.post("/api/projetos", json={"midia_id": criar_midia(db_limpo, cliente)}).json()
    rota = f"/api/projetos/{projeto['id']}"
    # A ordem é a da lista, e a mesma parte da gravação pode entrar de novo (como gancho no começo)
    partes = [{"id": "b", "inicio": 50, "fim": 60}, {"id": "a", "inicio": 10, "fim": 20},
              {"id": "c", "inicio": 50, "fim": 55}]
    salvo = cliente.patch(rota, json={"versao": 1, "partes": partes}).json()
    assert [(p["id"], p["inicio"]) for p in salvo["partes"]] == [("b", 50.0), ("a", 10.0), ("c", 50.0)]

    repetido = [{"id": "a", "inicio": 0, "fim": 5}, {"id": "a", "inicio": 9, "fim": 15}]
    assert cliente.patch(rota, json={"versao": 2, "partes": repetido}).status_code == 422
    demais = [{"id": f"p{i}", "inicio": i, "fim": i + 2} for i in range(31)]
    assert cliente.patch(rota, json={"versao": 2, "partes": demais}).status_code == 422
    assert cliente.patch(rota, json={"versao": 2, "partes": []}).status_code == 422

    # Projeto de antes da linha do tempo, só com "trecho": vira uma parte, e o trecho sai ao salvar
    db_limpo.projetos.update_one({"_id": ObjectId(projeto["id"])},
                                 {"$set": {"trecho": {"inicio": 5.0, "fim": 9.0}}, "$unset": {"partes": ""}})
    antigo = cliente.get(rota).json()
    assert antigo["partes"] == [{"id": "p1", "inicio": 5.0, "fim": 9.0}]
    cliente.patch(rota, json={"versao": antigo["versao"], "partes": [{"id": "p1", "inicio": 5, "fim": 12}]})
    documento = db_limpo.projetos.find_one({"_id": ObjectId(projeto["id"])})
    assert "trecho" not in documento and documento["partes"][0]["fim"] == 12.0


def test_exportar_guarda_a_configuracao_e_poe_o_render_na_fila(cliente, db_limpo):
    projeto = cliente.post("/api/projetos", json={"midia_id": criar_midia(db_limpo, cliente)}).json()
    rota = f"/api/projetos/{projeto['id']}"
    cliente.patch(rota, json={"versao": 1, "partes": [{"id": "p1", "inicio": 10, "fim": 40}]})

    exportacao = cliente.post(f"/api/projetos/{projeto['id']}/exportar").json()
    assert exportacao["status"] == "processando"
    assert exportacao["processamento"]["status"] == "pendente"
    assert (exportacao["largura"], exportacao["altura"]) == (1080, 1920)
    job = db_limpo.jobs.find_one({"entrada.exportacao_id": exportacao["id"]})
    assert job["tipo"] == "renderizacao"

    cliente.patch(f"/api/projetos/{projeto['id']}", json={"versao": 2, "partes": [{"id": "p1", "inicio": 0, "fim": 5}]})
    salvo = db_limpo.exportacoes.find_one({"_id": ObjectId(exportacao["id"])})
    assert salvo["configuracao"]["partes"] == [{"id": "p1", "inicio": 10.0, "fim": 40.0}]
    assert salvo["versao_projeto"] == 2

    listadas = cliente.get("/api/exportacoes", params={"projeto_id": projeto["id"]}).json()
    assert [e["id"] for e in listadas] == [exportacao["id"]]


def test_baixar_video_exportado(cliente, db_limpo):
    projeto = cliente.post("/api/projetos", json={"midia_id": criar_midia(db_limpo, cliente)}).json()
    exportacao = cliente.post(f"/api/projetos/{projeto['id']}/exportar").json()
    salvo = db_limpo.exportacoes.find_one({"_id": ObjectId(exportacao["id"])})
    storage.salvar_bytes(chave_exportacao(salvo["organizacao_id"], salvo["_id"], "video.mp4"), b"mp4" * 100)
    db_limpo.exportacoes.update_one({"_id": salvo["_id"]}, {"$set": {"status": "pronta", "arquivos": ["video.mp4"]}})

    base = f"/api/exportacoes/{exportacao['id']}/arquivos/video.mp4"
    assert "attachment" not in cliente.get(base).headers.get("content-disposition", "")  # abre na página
    baixado = cliente.get(base, params={"baixar": "true"})
    assert baixado.status_code == 200
    assert baixado.headers["content-disposition"] == 'attachment; filename="reel-culto-de-domingo.mp4"'
    assert cliente.get(f"/api/exportacoes/{exportacao['id']}/arquivos/capa.jpg").status_code == 404


def test_excluir_projeto_e_midia_apagam_em_cascata(cliente, db_limpo):
    midia_id = criar_midia(db_limpo, cliente)
    projeto = cliente.post("/api/projetos", json={"midia_id": midia_id}).json()
    exportacao = cliente.post(f"/api/projetos/{projeto['id']}/exportar").json()
    salvo = db_limpo.exportacoes.find_one({"_id": ObjectId(exportacao["id"])})
    storage.salvar_bytes(chave_exportacao(salvo["organizacao_id"], salvo["_id"], "video.mp4"), b"x")
    pasta = storage.caminho_local(f"org_{salvo['organizacao_id']}/exportacoes/{salvo['_id']}")

    assert cliente.delete(f"/api/projetos/{projeto['id']}").status_code == 204
    assert db_limpo.exportacoes.count_documents({}) == 0
    assert not pasta.exists()
    assert db_limpo.jobs.find_one({"entrada.exportacao_id": exportacao["id"]})["status"] == "erro"

    outro = cliente.post("/api/projetos", json={"midia_id": midia_id}).json()
    cliente.post(f"/api/projetos/{outro['id']}/exportar")
    assert cliente.delete(f"/api/midias/{midia_id}").status_code == 204
    assert db_limpo.projetos.count_documents({}) == 0
    assert db_limpo.exportacoes.count_documents({}) == 0


def test_projetos_sao_separados_por_igreja(cliente, db_limpo):
    projeto = cliente.post("/api/projetos", json={"midia_id": criar_midia(db_limpo, cliente)}).json()
    exportacao = cliente.post(f"/api/projetos/{projeto['id']}/exportar").json()
    cliente.post("/api/auth/sair")
    entrar(cliente, igreja="Outra Igreja")

    assert cliente.get("/api/projetos").json() == []
    assert cliente.get(f"/api/projetos/{projeto['id']}").status_code == 404
    assert cliente.patch(f"/api/projetos/{projeto['id']}", json={"versao": 1, "nome": "x"}).status_code == 404
    assert cliente.post(f"/api/projetos/{projeto['id']}/exportar").status_code == 404
    assert cliente.get("/api/exportacoes").json() == []
    assert cliente.get(f"/api/exportacoes/{exportacao['id']}").status_code == 404
    assert cliente.delete(f"/api/exportacoes/{exportacao['id']}").status_code == 404
