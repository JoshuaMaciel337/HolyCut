# Baixar no celular pelo QR code e trocar a capa de um vídeo pronto
import shutil
import subprocess
import uuid
from datetime import timedelta

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from api.main import app
from core.config import FFMPEG
from core.modelos.link_celular import instante_da_capa, link_vencido, montar_link_celular
from core.modelos.projeto import chave_exportacao
from core.utils import storage
from core.utils.fila import pegar_proximo_job
from core.utils.mongo import agora
from worker.worker_principal import processar_job

VIDEO = b"video-exportado-de-teste"


@pytest.fixture
def cliente(db_limpo):
    with TestClient(app) as cliente:
        cliente.post("/api/auth/cadastro", json={
            "nome_igreja": "Igreja do Celular", "nome": "Pessoa", "email": f"{uuid.uuid4().hex[:8]}@exemplo.com",
            "senha": "senha-segura-1"})
        yield cliente


def exportacao_pronta(db, organizacao_id, conteudo: bytes = VIDEO, duracao: float = 15.0,
                      formato: str = "video") -> ObjectId:
    momento = agora()
    exportacao_id = db.exportacoes.insert_one({
        "organizacao_id": organizacao_id, "projeto_id": ObjectId(), "midia_id": ObjectId(),
        "nome": "Reel · Ele é Digno",
        "formato": formato, "status": "pronta", "arquivos": ["video.mp4", "capa.jpg"], "duracao": duracao,
        "largura": 1080, "altura": 1920, "criado_em": momento, "atualizado_em": momento,
    }).inserted_id
    storage.salvar_bytes(chave_exportacao(organizacao_id, exportacao_id, "video.mp4"), conteudo)
    return exportacao_id


def test_regras_do_link_e_da_capa():
    token, link = montar_link_celular()
    assert len(token) >= 40 and token not in str(link)   # o banco guarda só o hash
    assert not link_vencido(link) and link_vencido(link, link["expira_em"] + timedelta(seconds=1))
    assert link_vencido(None)
    assert instante_da_capa(7.256, 15) == 7.26 and instante_da_capa(-3, 15) == 0 and instante_da_capa(99, 15) == 14.9


def test_qr_code_baixa_o_video_sem_conta(cliente, db_limpo):
    organizacao_id = ObjectId(cliente.get("/api/auth/eu").json()["organizacao"]["id"])
    exportacao_id = exportacao_pronta(db_limpo, organizacao_id)
    link = cliente.post(f"/api/exportacoes/{exportacao_id}/link-celular").json()
    assert link["caminho"].startswith("/api/baixar/")

    svg = cliente.get("/api/qrcode.svg", params={"texto": f"http://192.168.0.10:3000{link['caminho']}"})
    assert svg.status_code == 200 and svg.headers["content-type"].startswith("image/svg+xml") and "<svg" in svg.text

    sessao = dict(cliente.cookies)
    cliente.cookies.clear()   # o celular não tem a sessão do computador
    baixado = cliente.get(link["caminho"])
    assert baixado.status_code == 200 and baixado.content == VIDEO
    disposicao = baixado.headers["content-disposition"]
    assert "attachment" in disposicao and ".mp4" in disposicao
    assert cliente.get("/api/qrcode.svg", params={"texto": "x"}).status_code == 401
    cliente.cookies.update(sessao)
    # Gerar outro QR invalida o anterior; o vencido também não abre
    novo = cliente.post(f"/api/exportacoes/{exportacao_id}/link-celular").json()
    assert cliente.get(link["caminho"]).status_code == 404
    db_limpo.exportacoes.update_one({"_id": exportacao_id}, {"$set": {"link_celular.expira_em": agora()}})
    assert cliente.get(novo["caminho"]).status_code == 404
    assert cliente.get("/api/baixar/token-inventado").status_code == 404

    imagem = exportacao_pronta(db_limpo, organizacao_id, formato="imagem")
    assert cliente.post(f"/api/exportacoes/{imagem}/link-celular").status_code == 409


@pytest.mark.skipif(shutil.which(FFMPEG) is None, reason="FFmpeg não instalado")
def test_trocar_a_capa_tira_o_quadro_do_video_pronto(cliente, db_limpo, tmp_path):
    organizacao_id = ObjectId(cliente.get("/api/auth/eu").json()["organizacao"]["id"])
    video = tmp_path / "video.mp4"
    subprocess.run([FFMPEG, "-hide_banner", "-loglevel", "error", "-f", "lavfi",
                    "-i", "testsrc=size=320x568:rate=30:d=4", "-pix_fmt", "yuv420p", str(video)], check=True)
    exportacao_id = exportacao_pronta(db_limpo, organizacao_id, video.read_bytes(), duracao=4.0)
    assert cliente.post(f"/api/exportacoes/{exportacao_id}/capa", json={"instante": 2.5}).status_code == 200

    job = pegar_proximo_job(db_limpo, ["capa_exportacao"], "w-teste")
    assert processar_job(db_limpo, job, "w-teste") == "concluido"
    exportacao = db_limpo.exportacoes.find_one({"_id": exportacao_id})
    assert exportacao["capa_instante"] == 2.5 and exportacao["capa_versao"] == 1
    capa = storage.caminho_local(chave_exportacao(organizacao_id, exportacao_id, "capa.jpg"))
    assert capa.is_file() and capa.read_bytes()[:2] == b"\xff\xd8"   # JPG
    assert cliente.get(f"/api/exportacoes/{exportacao_id}").json()["capa_versao"] == 1
