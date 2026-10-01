# Pacote para DaVinci e Premiere pela API: o .zip com XML, SRT e o passo a passo,
# com as mesmas contas de corte do render, e o download da gravação original
import io
import uuid
import xml.etree.ElementTree as ET
import zipfile

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient

from api.main import app
from core.modelos.midia import chave_arquivo, montar_midia
from core.utils import storage

NTSC_30 = 30000 / 1001
ORIGINAL = b"gravacao-original-de-teste"


@pytest.fixture
def cliente(db_limpo):
    with TestClient(app) as cliente:
        cliente.post("/api/auth/cadastro", json={
            "nome_igreja": "Igreja do Pacote", "nome": "Pessoa", "email": f"{uuid.uuid4().hex[:8]}@exemplo.com",
            "senha": "senha-segura-1"})
        yield cliente


def culto(db, organizacao_id, com_arquivo=True) -> ObjectId:
    midia = montar_midia(organizacao_id, None, "Culto 28-09.mkv", len(ORIGINAL))
    midia.update({"status": "pronta", "duracao": 600.0, "video": {"largura": 1920, "altura": 1080, "fps": 29.97},
                  "audio": {"codec": "aac", "canais": 2, "taxa": 48000}})
    midia_id = db.midias.insert_one(midia).inserted_id
    if com_arquivo:
        storage.salvar_bytes(chave_arquivo(organizacao_id, midia_id, midia["original"]), ORIGINAL)
    palavras = [{"id": f"w{indice}", "texto": texto, "inicio": inicio, "fim": inicio + 0.4}
                for indice, (texto, inicio) in enumerate([("Deus", 11.0), ("é", 12.0), ("fiel", 13.0),
                                                          ("Amém", 101.0)], start=1)]
    segmento = {"id": "s1", "inicio": 11.0, "fim": 101.4, "texto": "", "palavras": palavras}
    db.transcricoes.insert_one({"organizacao_id": organizacao_id, "midia_id": midia_id, "segmentos": [segmento]})
    return midia_id


def test_pacote_leva_os_cortes_do_editor_e_a_legenda(cliente, db_limpo):
    organizacao_id = ObjectId(cliente.get("/api/auth/eu").json()["organizacao"]["id"])
    midia_id = culto(db_limpo, organizacao_id)
    projeto = cliente.post("/api/projetos", json={"midia_id": str(midia_id)}).json()
    # Duas partes, sem corte de silêncio, e a palavra "é" apagada pelo texto
    resposta = cliente.patch(f"/api/projetos/{projeto['id']}", json={
        "versao": projeto["versao"], "silencios": {"intensidade": None},
        "partes": [{"id": "p1", "inicio": 10.0, "fim": 20.0}, {"id": "p2", "inicio": 100.0, "fim": 105.0}],
        "legenda": {**projeto["legenda"], "apagadas": ["w2"]}})
    assert resposta.status_code == 200, resposta.text

    resposta = cliente.get(f"/api/projetos/{projeto['id']}/pacote-edicao")
    assert resposta.status_code == 200 and resposta.headers["content-type"] == "application/zip"
    assert 'filename="reel-culto-28-09.zip"' in resposta.headers["content-disposition"]
    pacote = zipfile.ZipFile(io.BytesIO(resposta.content))
    assert set(pacote.namelist()) == {"reel-culto-28-09.xml", "reel-culto-28-09.srt", "LEIA-ME.txt"}

    sequencia = ET.fromstring(pacote.read("reel-culto-28-09.xml")).find("sequence")
    entradas = [round(int(clipe.findtext("in")) / NTSC_30, 1)
                for clipe in sequencia.findall("media/video/track/clipitem")]
    # A parte 1 se divide onde o "é" foi apagado; a parte 2 vem inteira
    assert entradas == [10.0, 12.4, 100.0]
    assert sequencia.findtext(".//file/pathurl") == "file://localhost/Culto%2028-09.mkv"
    assert len(sequencia.findall("media/audio/track")) == 2

    srt = pacote.read("reel-culto-28-09.srt").decode()
    # O "é" apagado some da legenda; a parte 1 fica com 9,6 s, então o "Amém" (101 s) entra aos 10,6 s
    assert srt == ("1\n00:00:01,000 --> 00:00:01,400\nDeus\n\n2\n00:00:02,600 --> 00:00:03,000\nfiel\n\n"
                   "3\n00:00:10,600 --> 00:00:11,000\nAmém\n")
    assert "Culto 28-09.mkv" in pacote.read("LEIA-ME.txt").decode()


def test_original_baixa_com_o_nome_de_origem(cliente, db_limpo):
    organizacao_id = ObjectId(cliente.get("/api/auth/eu").json()["organizacao"]["id"])
    midia_id = culto(db_limpo, organizacao_id)
    resposta = cliente.get(f"/api/midias/{midia_id}/original")
    assert resposta.status_code == 200 and resposta.content == ORIGINAL
    disposicao = resposta.headers["content-disposition"]
    assert "attachment" in disposicao and "Culto" in disposicao
    sem_arquivo = culto(db_limpo, organizacao_id, com_arquivo=False)
    assert cliente.get(f"/api/midias/{sem_arquivo}/original").status_code == 404
