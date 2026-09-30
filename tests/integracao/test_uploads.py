# Upload tus e rotas de mídias contra um MongoDB de verdade
import base64
import os
import uuid

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from api.main import app
from core.modelos.midia import chave_arquivo
from core.utils import storage

TUS = {"Tus-Resumable": "1.0.0"}
PEDACO = {**TUS, "Content-Type": "application/offset+octet-stream"}


@pytest.fixture
def cliente(db_limpo):
    with TestClient(app) as cliente:
        entrar(cliente)
        yield cliente


def entrar(cliente, igreja="Igreja Upload"):
    resposta = cliente.post("/api/auth/cadastro", json={
        "nome_igreja": igreja, "nome": "Pessoa Upload",
        "email": f"{uuid.uuid4().hex[:8]}@exemplo.com", "senha": "senha-segura-1",
    })
    assert resposta.status_code == 201
    return resposta.json()


def metadados(nome="Culto de domingo.mp4", tipo="video/mp4"):
    def b64(texto):
        return base64.b64encode(texto.encode()).decode()
    return f"filename {b64(nome)},filetype {b64(tipo)}"


def criar_envio(cliente, tamanho, nome="Culto de domingo.mp4"):
    return cliente.post("/api/uploads", headers={**TUS, "Upload-Length": str(tamanho),
                                                 "Upload-Metadata": metadados(nome)})


def test_envio_em_pedacos_ate_a_fila_de_ingestao(cliente, db_limpo):
    conteudo = os.urandom(3 * 1024 * 1024 + 123)
    criado = criar_envio(cliente, len(conteudo))
    assert criado.status_code == 201
    assert criado.headers["Tus-Resumable"] == "1.0.0"
    local = criado.headers["Location"]
    midia_id = local.rsplit("/", 1)[1]

    assert cliente.head(local, headers=TUS).headers["Upload-Offset"] == "0"
    lista = cliente.get("/api/midias").json()
    assert [(m["id"], m["status"], m["nome"]) for m in lista] == [(midia_id, "enviando", "Culto de domingo")]

    meio = 2 * 1024 * 1024
    primeiro = cliente.patch(local, headers={**PEDACO, "Upload-Offset": "0"}, content=conteudo[:meio])
    assert primeiro.status_code == 204
    assert primeiro.headers["Upload-Offset"] == str(meio)

    # Pedaço repetido (a internet caiu e o navegador mandou de novo): recusa e diz onde parou
    repetido = cliente.patch(local, headers={**PEDACO, "Upload-Offset": "0"}, content=conteudo[:meio])
    assert repetido.status_code == 409
    assert repetido.headers["Upload-Offset"] == str(meio)
    assert cliente.head(local, headers=TUS).headers["Upload-Offset"] == str(meio)

    ultimo = cliente.patch(local, headers={**PEDACO, "Upload-Offset": str(meio)}, content=conteudo[meio:])
    assert ultimo.status_code == 204
    assert ultimo.headers["Upload-Offset"] == str(len(conteudo))

    midia = db_limpo.midias.find_one({"_id": ObjectId(midia_id)})
    assert midia["status"] == "processando"
    assert midia["bytes_recebidos"] == len(conteudo)
    caminho = storage.caminho_local(chave_arquivo(midia["organizacao_id"], midia["_id"], "original.mp4"))
    assert caminho.read_bytes() == conteudo

    job = db_limpo.jobs.find_one({"_id": midia["job_ingestao_id"]})
    assert job["tipo"] == "ingestao"
    assert job["entrada"] == {"midia_id": midia_id}
    vista = cliente.get(f"/api/midias/{midia_id}").json()
    assert vista["status"] == "processando"
    assert vista["processamento"] == {"status": "pendente", "progresso": 0, "mensagem": "Na fila"}

    # Depois de terminado, não aceita mais pedaços nem cancelamento pelo tus
    depois = cliente.patch(local, headers={**PEDACO, "Upload-Offset": str(len(conteudo))}, content=b"x")
    assert depois.status_code == 409
    assert cliente.delete(local, headers=TUS).status_code == 409


def test_envio_recusado(cliente, monkeypatch):
    assert criar_envio(cliente, 100, nome="planilha.xlsx").status_code == 415
    assert criar_envio(cliente, 0).status_code == 400
    assert criar_envio(cliente, 10**15).status_code == 413
    sem_versao = cliente.post("/api/uploads", headers={"Upload-Length": "10", "Upload-Metadata": metadados()})
    assert sem_versao.status_code == 412

    monkeypatch.setattr(storage, "espaco_livre", lambda: 1024**3)  # 1 GB livre, abaixo da margem de 2 GB
    sem_espaco = criar_envio(cliente, 1000)
    assert sem_espaco.status_code == 507
    assert "sem espaço" in sem_espaco.text


def test_pedaco_invalido(cliente):
    local = criar_envio(cliente, 10).headers["Location"]
    sem_tipo = cliente.patch(local, headers={**TUS, "Upload-Offset": "0"}, content=b"12345")
    assert sem_tipo.status_code == 415
    grande = cliente.patch(local, headers={**PEDACO, "Upload-Offset": "0"}, content=b"x" * 25)
    assert grande.status_code == 413
    assert grande.headers["Upload-Offset"] == "10"  # guarda só o tamanho declarado


def test_cancelar_envio_apaga_tudo(cliente, db_limpo):
    local = criar_envio(cliente, 1000).headers["Location"]
    midia_id = ObjectId(local.rsplit("/", 1)[1])
    midia = db_limpo.midias.find_one({"_id": midia_id})
    pasta = storage.caminho_local(f"org_{midia['organizacao_id']}/midias/{midia_id}")
    assert pasta.is_dir()

    assert cliente.delete(local, headers=TUS).status_code == 204
    assert db_limpo.midias.count_documents({}) == 0
    assert not pasta.exists()
    assert cliente.head(local, headers=TUS).status_code == 404


def test_envios_e_midias_sao_separados_por_igreja(cliente):
    local = criar_envio(cliente, 10).headers["Location"]
    midia_id = local.rsplit("/", 1)[1]
    cliente.post("/api/auth/sair")
    entrar(cliente, igreja="Outra Igreja")

    assert cliente.head(local, headers=TUS).status_code == 404
    assert cliente.patch(local, headers={**PEDACO, "Upload-Offset": "0"}, content=b"1").status_code == 404
    assert cliente.get("/api/midias").json() == []
    assert cliente.get(f"/api/midias/{midia_id}").status_code == 404
    assert cliente.delete(f"/api/midias/{midia_id}").status_code == 404


def test_arquivos_da_midia_com_range(cliente, db_limpo):
    conteudo = b"0123456789" * 1000
    local = criar_envio(cliente, len(conteudo)).headers["Location"]
    midia_id = ObjectId(local.rsplit("/", 1)[1])
    cliente.patch(local, headers={**PEDACO, "Upload-Offset": "0"}, content=conteudo)
    midia = db_limpo.midias.find_one({"_id": midia_id})

    # Simula a ingestão pronta
    storage.salvar_bytes(chave_arquivo(midia["organizacao_id"], midia_id, "proxy.mp4"), conteudo)
    db_limpo.midias.update_one({"_id": midia_id},
                               {"$set": {"status": "pronta", "arquivos": ["proxy.mp4", "audio.wav"]}})

    base = f"/api/midias/{midia_id}/arquivos"
    trecho = cliente.get(f"{base}/proxy.mp4", headers={"Range": "bytes=10-19"})
    assert trecho.status_code == 206
    assert trecho.content == b"0123456789"
    assert trecho.headers["content-type"] == "video/mp4"
    assert cliente.get(f"{base}/audio.wav").status_code == 404        # arquivo interno
    assert cliente.get(f"{base}/original.mp4").status_code == 404     # original não é servido
    assert cliente.get(f"{base}/..%2F..%2Fsegredo").status_code == 404
    assert cliente.get(f"/api/midias/{midia_id}").json()["arquivos"] == ["proxy.mp4"]


def test_renomear_e_excluir_midia(cliente, db_limpo):
    local = criar_envio(cliente, 5).headers["Location"]
    midia_id = local.rsplit("/", 1)[1]
    cliente.patch(local, headers={**PEDACO, "Upload-Offset": "0"}, content=b"12345")

    renomeada = cliente.patch(f"/api/midias/{midia_id}", json={"nome": "  Culto   de Santa Ceia "})
    assert renomeada.json()["nome"] == "Culto de Santa Ceia"

    assert cliente.delete(f"/api/midias/{midia_id}").status_code == 204
    assert cliente.get(f"/api/midias/{midia_id}").status_code == 404
    job = db_limpo.jobs.find_one({"entrada.midia_id": midia_id})
    assert job["status"] == "erro"
    assert job["erro"] == "A mídia foi excluída."


def test_midia_mostra_erro_quando_a_ingestao_falha_de_vez(cliente, db_limpo):
    local = criar_envio(cliente, 3).headers["Location"]
    midia_id = local.rsplit("/", 1)[1]
    cliente.patch(local, headers={**PEDACO, "Upload-Offset": "0"}, content=b"abc")
    db_limpo.jobs.update_one({"entrada.midia_id": midia_id},
                             {"$set": {"status": "erro", "erro": "O worker parou de responder."}})
    vista = cliente.get(f"/api/midias/{midia_id}").json()
    assert vista["status"] == "erro"
    assert vista["erro"] == "O worker parou de responder."
