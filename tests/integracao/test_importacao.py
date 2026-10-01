# Importar pelo link e o monitor do canal, com o yt-dlp e o feed simulados:
# a API, o job (canal conferido, live no ar, download) e a primeira volta do monitor
import uuid
from datetime import timedelta

import pytest
import requests
from bson import ObjectId
from fastapi.testclient import TestClient

import worker.tarefas.importacao as tarefa_importacao
from api.main import app
from core.utils.fila import pegar_proximo_job
from core.utils.mongo import agora
from tests.test_importacao import CANAL, FEED, VIDEO
from worker.worker_principal import processar_job

METADADOS = {"title": "Culto de Domingo", "channel": "Igreja Viva", "channel_id": CANAL, "uploader_id": "@IgrejaViva",
             "live_status": "was_live", "duration": 5400, "release_timestamp": 1790600400}


@pytest.fixture
def cliente(db_limpo):
    with TestClient(app) as cliente:
        cliente.post("/api/auth/cadastro", json={
            "nome_igreja": "Igreja Viva", "nome": "Pessoa", "email": f"{uuid.uuid4().hex[:8]}@exemplo.com",
            "senha": "senha-segura-1"})
        yield cliente


@pytest.fixture
def youtube(monkeypatch):
    """yt-dlp simulado: os metadados mudam pelo dicionário; o download grava um .mp4 de mentira."""
    estado = {"metadados": dict(METADADOS), "lidos": []}

    def ler(url):
        estado["lidos"].append(url)
        return estado["metadados"]

    def baixar(url, pasta, reportar):
        reportar(50, "Baixando o vídeo")
        arquivo = pasta / "original.mp4"
        arquivo.write_bytes(b"video-de-teste")
        return arquivo

    monkeypatch.setattr(tarefa_importacao, "ler_metadados", ler)
    monkeypatch.setattr(tarefa_importacao, "baixar", baixar)
    monkeypatch.setattr(tarefa_importacao.storage, "espaco_livre", lambda: 500 * 1024**3)
    return estado


def rodar(db):
    job = pegar_proximo_job(db, ["importar_link"], "w-teste")
    return processar_job(db, job, "w-teste"), job


def test_importar_pelo_link_do_canal_da_igreja(cliente, db_limpo, youtube):
    organizacao_id = ObjectId(cliente.get("/api/auth/eu").json()["organizacao"]["id"])
    link = f"https://youtu.be/{VIDEO}"
    assert cliente.post("/api/midias/importar", json={"url": link}).status_code == 409   # sem canal cadastrado
    assert cliente.post("/api/midias/importar", json={"url": "https://vimeo.com/123"}).status_code == 422
    assert cliente.put("/api/canal-youtube", json={"canal": "a"}).status_code == 422
    canal = cliente.put("/api/canal-youtube", json={"canal": "youtube.com/@IgrejaViva"}).json()
    assert canal["configurado"] and canal["handle"] == "@igrejaviva" and canal["monitorar"] is False

    resposta = cliente.post("/api/midias/importar", json={"url": link})
    assert resposta.status_code == 201
    midia = resposta.json()
    assert midia["nome"] == "Importando do YouTube" and midia["processamento"]["status"] == "pendente"
    assert midia["importacao"]["origem"] == "youtube"
    assert cliente.post("/api/midias/importar", json={"url": link}).status_code == 409   # já está no acervo

    resultado, _ = rodar(db_limpo)
    assert resultado == "concluido"
    documento = db_limpo.midias.find_one({"_id": ObjectId(midia["id"])})
    assert documento["nome"] == "Culto de Domingo" and documento["nome_original"] == "Culto de Domingo.mp4"
    assert documento["ficha"]["data"] == "2026-09-28" and documento["tamanho_total"] == len(b"video-de-teste")
    ingestao = db_limpo.jobs.find_one({"_id": documento["job_ingestao_id"]})
    assert ingestao["tipo"] == "ingestao" and ingestao["status"] == "pendente"
    # O @ cadastrado vira o id do canal, que o feed RSS precisa
    assert db_limpo.organizacoes.find_one({"_id": organizacao_id})["canal_youtube"]["id"] == CANAL
    assert cliente.get(f"/api/midias/{midia['id']}").json()["processamento"]["status"] == "pendente"


def test_drive_pede_confirmacao_e_video_de_outro_canal_nao_entra(cliente, db_limpo, youtube):
    drive = "https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUvWxYz0123456/view"
    assert cliente.post("/api/midias/importar", json={"url": drive}).status_code == 422
    confirmado = cliente.post("/api/midias/importar", json={"url": drive, "confirmo_que_e_da_igreja": True})
    assert confirmado.status_code == 201
    db_limpo.jobs.delete_many({})

    cliente.put("/api/canal-youtube", json={"canal": "@outraigreja"})
    midia = cliente.post("/api/midias/importar", json={"url": f"https://youtu.be/{VIDEO}"}).json()
    resultado, job = rodar(db_limpo)
    assert resultado == "erro"
    documento = db_limpo.midias.find_one({"_id": ObjectId(midia["id"])})
    assert documento["status"] == "erro" and "não é do canal da igreja" in documento["erro"]
    assert db_limpo.jobs.find_one({"_id": job["_id"]})["tentativas"] == 1


def test_live_no_ar_espera_sem_gastar_tentativas(cliente, db_limpo, youtube):
    cliente.put("/api/canal-youtube", json={"canal": CANAL})
    midia = cliente.post("/api/midias/importar", json={"url": f"https://youtu.be/{VIDEO}"}).json()
    youtube["metadados"] = {**METADADOS, "live_status": "is_live"}
    resultado, job = rodar(db_limpo)
    assert resultado == "concluido"
    documento = db_limpo.midias.find_one({"_id": ObjectId(midia["id"])})
    novo = db_limpo.jobs.find_one({"_id": documento["job_ingestao_id"]})
    assert novo["tipo"] == "importar_link" and novo["entrada"]["esperas"] == 1 and novo["_id"] != job["_id"]
    assert novo["disponivel_em"] > agora() + timedelta(minutes=9) and "ainda está no ar" in novo["mensagem"]
    assert documento["nome"] == "Culto de Domingo"   # o título já aparece enquanto espera
    assert pegar_proximo_job(db_limpo, ["importar_link"], "w-teste") is None   # só daqui a 10 min


class RespostaFeed:
    def __init__(self, texto):
        self.text = texto

    def raise_for_status(self):
        return None


def test_monitor_importa_daqui_para_a_frente(cliente, db_limpo, youtube, monkeypatch):
    organizacao_id = ObjectId(cliente.get("/api/auth/eu").json()["organizacao"]["id"])
    cliente.put("/api/canal-youtube", json={"canal": CANAL, "monitorar": True})
    lidos = []
    monkeypatch.setattr(tarefa_importacao.requests, "get", lambda url, timeout: lidos.append(url) or RespostaFeed(FEED))
    situacao = {"AAAAAAAAAAA": "was_live", "BBBBBBBBBBB": "is_upcoming"}
    monkeypatch.setattr(tarefa_importacao, "ler_metadados",
                        lambda url: {**METADADOS, "live_status": situacao[url.rsplit("=", 1)[1]]})

    # Primeira volta: o culto de quarta já tinha terminado e só fica visto; a live agendada espera
    assert tarefa_importacao.verificar_canais(db_limpo) == 0
    assert lidos == [f"https://www.youtube.com/feeds/videos.xml?channel_id={CANAL}"]
    canal = db_limpo.organizacoes.find_one({"_id": organizacao_id})["canal_youtube"]
    assert canal["vistos"] == ["AAAAAAAAAAA"] and canal["primeira_volta"] is False and canal["ultimo_erro"] is None
    # Reservada: dentro do intervalo, ninguém lê o feed de novo
    assert tarefa_importacao.verificar_canais(db_limpo) == 0 and len(lidos) == 1

    # A live de domingo terminou: na volta seguinte, ela entra
    situacao["BBBBBBBBBBB"] = "was_live"
    db_limpo.organizacoes.update_one({"_id": organizacao_id}, {"$set": {"canal_youtube.proxima_verificacao": agora()}})
    assert tarefa_importacao.verificar_canais(db_limpo) == 1
    midia = db_limpo.midias.find_one({"organizacao_id": organizacao_id, "importacao.id": "BBBBBBBBBBB"})
    assert midia["criado_por"] is None
    assert db_limpo.jobs.find_one({"_id": midia["job_ingestao_id"]})["tipo"] == "importar_link"

    # O feed fora do ar fica registrado no canal, para a tela mostrar
    def fora_do_ar(url, timeout):
        raise requests.ConnectionError("sem internet")

    monkeypatch.setattr(tarefa_importacao.requests, "get", fora_do_ar)
    db_limpo.organizacoes.update_one({"_id": organizacao_id}, {"$set": {"canal_youtube.proxima_verificacao": agora()}})
    assert tarefa_importacao.verificar_canais(db_limpo) == 0
    assert "sem internet" in cliente.get("/api/canal-youtube").json()["ultimo_erro"]
    assert cliente.delete("/api/canal-youtube").status_code == 204
    assert cliente.get("/api/canal-youtube").json()["configurado"] is False
