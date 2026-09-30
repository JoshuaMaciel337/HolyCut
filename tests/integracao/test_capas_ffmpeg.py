# Capas do acervo de ponta a ponta: a ingestão desenha, e o job capas_culto redesenha. FFmpeg de verdade.
import shutil
import subprocess

import numpy as np
import pytest
from bson import ObjectId
from PIL import Image

from core.modelos.culto import ARQUIVO_BANNER, ARQUIVO_FUNDO_CAPA, ARQUIVO_POSTER
from core.modelos.job import montar_job
from core.modelos.midia import chave_arquivo, montar_midia
from core.utils import storage
from core.utils.arte import para_jpeg
from core.utils.fila import enfileirar_job
from tests.integracao.test_renderizacao import midia_pronta, rodar

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg não instalado")


def abrir(midia, nome) -> Image.Image:
    caminho = storage.caminho_local(chave_arquivo(midia["organizacao_id"], midia["_id"], nome))
    with Image.open(caminho) as imagem:
        return imagem.convert("RGB")


def redesenhar(db, midia_id):
    enfileirar_job(db, montar_job("capas_culto", db.midias.find_one({"_id": midia_id})["organizacao_id"],
                                  {"midia_id": str(midia_id)}))
    rodar(db, "capas_culto")
    return db.midias.find_one({"_id": midia_id})


def test_ingestao_desenha_as_capas_e_o_job_redesenha(db_limpo):
    midia = midia_pronta(db_limpo, largura=640, altura=360, duracao=6)
    assert {ARQUIVO_POSTER, ARQUIVO_BANNER} <= set(midia["arquivos"])
    assert abrir(midia, ARQUIVO_POSTER).size == (600, 900) and abrir(midia, ARQUIVO_BANNER).size == (1280, 720)
    versao = midia["capa"]["versao"]

    # Outro quadro e uma ficha: o banner muda
    antes = np.asarray(abrir(midia, ARQUIVO_BANNER), dtype=int)
    db_limpo.midias.update_one({"_id": midia["_id"]}, {"$set": {
        "nome": "Inconformados no altar", "capa": {**midia["capa"], "instante": 4.0},
        "ficha": {"data": "2026-08-15", "pregador": "Pr. Joelson", "serie": "Romanos", "descricao": ""}}})
    midia = redesenhar(db_limpo, midia["_id"])
    assert midia["capa"]["versao"] > versao
    assert np.abs(np.asarray(abrir(midia, ARQUIVO_BANNER), dtype=int) - antes).mean() > 3

    # Imagem enviada pela igreja: o fundo passa a ser ela (azul), não o quadro do vídeo
    fundo = storage.caminho_local(chave_arquivo(midia["organizacao_id"], midia["_id"], ARQUIVO_FUNDO_CAPA))
    fundo.write_bytes(para_jpeg(Image.new("RGB", (1600, 900), (20, 60, 220))))
    db_limpo.midias.update_one({"_id": midia["_id"]}, {"$set": {"capa.personalizada": True}})
    midia = redesenhar(db_limpo, midia["_id"])
    topo = np.asarray(abrir(midia, ARQUIVO_POSTER).crop((0, 0, 600, 250)), dtype=int).mean(axis=(0, 1))
    assert topo[2] > topo[0] + 80 and topo[2] > topo[1] + 60


def test_gravacao_so_de_audio_ganha_capa_na_cor_da_igreja(db_limpo):
    midia = montar_midia(ObjectId(), ObjectId(), "Culto de oração.m4a", 1)
    midia["_id"] = db_limpo.midias.insert_one(midia).inserted_id
    original = storage.caminho_local(chave_arquivo(midia["organizacao_id"], midia["_id"], midia["original"]))
    original.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                    "-i", "sine=frequency=220:sample_rate=48000:duration=4", "-c:a", "aac", str(original)],
                   check=True, timeout=60)
    db_limpo.midias.update_one({"_id": midia["_id"]}, {"$set": {"status": "processando"}})
    enfileirar_job(db_limpo, montar_job("ingestao", midia["organizacao_id"], {"midia_id": str(midia["_id"])}))
    rodar(db_limpo, "ingestao")
    midia = db_limpo.midias.find_one({"_id": midia["_id"]})
    assert midia["status"] == "pronta" and not midia.get("video")
    poster = abrir(midia, ARQUIVO_POSTER)
    canto = np.asarray(poster.crop((420, 120, 540, 240)), dtype=int).mean(axis=(0, 1))
    assert canto[0] > canto[2]                        # o brilho laranja padrão da igreja, sem vídeo
