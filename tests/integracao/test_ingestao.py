# Ingestão de ponta a ponta: FFmpeg de verdade e MongoDB de verdade.
# Pulado quando o FFmpeg não está instalado. No Docker e no CI ele roda.
import json
import os
import shutil
import subprocess

import pytest
from bson import ObjectId

from core.modelos.job import montar_job
from core.modelos.midia import chave_arquivo, montar_midia
from core.utils import storage
from core.utils.fila import enfileirar_job, pegar_proximo_job
from worker.worker_principal import processar_job

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg não instalado")


def gerar(caminho, *entradas_e_saida):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *entradas_e_saida, str(caminho)],
                   check=True, timeout=120)


def preparar_midia(db, nome_arquivo, criar_arquivo):
    midia = montar_midia(ObjectId(), ObjectId(), nome_arquivo, 1)
    midia["_id"] = db.midias.insert_one(midia).inserted_id
    caminho = storage.caminho_local(chave_arquivo(midia["organizacao_id"], midia["_id"], midia["original"]))
    caminho.parent.mkdir(parents=True, exist_ok=True)
    criar_arquivo(caminho)
    db.midias.update_one({"_id": midia["_id"]}, {"$set": {"status": "processando",
                                                          "tamanho_total": caminho.stat().st_size}})
    enfileirar_job(db, montar_job("ingestao", midia["organizacao_id"], {"midia_id": str(midia["_id"])}))
    return midia["_id"]


def processar(db, midia_id):
    job = pegar_proximo_job(db, ["ingestao"], "w-teste")
    assert job["entrada"]["midia_id"] == str(midia_id)
    resultado = processar_job(db, job, "w-teste")
    return resultado, db.midias.find_one({"_id": midia_id}), db.jobs.find_one({"_id": job["_id"]})


def arquivo_da(midia, nome):
    return storage.caminho_local(chave_arquivo(midia["organizacao_id"], midia["_id"], nome))


def sondar_video(caminho):
    saida = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height", "-of", "json", str(caminho)],
                           capture_output=True, text=True, check=True).stdout
    stream = json.loads(saida)["streams"][0]
    return stream["width"], stream["height"]


def test_ingestao_de_video_horizontal(db_limpo):
    midia_id = preparar_midia(db_limpo, "Culto.mp4", lambda c: gerar(
        c, "-f", "lavfi", "-i", "testsrc2=size=1920x1080:rate=60:duration=12",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=12",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest"))

    resultado, midia, job = processar(db_limpo, midia_id)
    assert resultado == "concluido", job.get("erro")
    assert midia["status"] == "pronta"
    assert 11.5 < midia["duracao"] < 12.5
    assert midia["video"]["largura"] == 1920 and midia["video"]["fps"] == 60
    assert set(midia["arquivos"]) == {"proxy.mp4", "audio.wav", "forma_de_onda.json", "niveis.bin",
                                      "miniaturas.jpg", "capa.jpg"}
    assert 1150 <= arquivo_da(midia, "niveis.bin").stat().st_size <= 1250   # 12 s a 100 por segundo
    assert job["progresso"] == 100

    assert sondar_video(arquivo_da(midia, "proxy.mp4")) == (1280, 720)
    forma = json.loads(arquivo_da(midia, "forma_de_onda.json").read_text())
    assert 235 <= len(forma["picos"]) <= 250          # 12 s a 20 picos por segundo
    assert max(forma["picos"]) > 0
    assert midia["miniaturas"]["total"] == 10
    assert (midia["miniaturas"]["largura"], midia["miniaturas"]["altura"]) == (160, 90)
    assert sondar_video(arquivo_da(midia, "capa.jpg")) == (640, 360)


def test_ingestao_de_video_gravado_em_pe_no_celular(db_limpo):
    midia_id = preparar_midia(db_limpo, "Story.mov", lambda c: gerar(
        c, "-f", "lavfi", "-i", "testsrc2=size=1080x1920:rate=30:duration=4",
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest"))

    resultado, midia, _ = processar(db_limpo, midia_id)
    assert resultado == "concluido"
    assert sondar_video(arquivo_da(midia, "proxy.mp4")) == (720, 1280)
    forma = json.loads(arquivo_da(midia, "forma_de_onda.json").read_text())
    assert max(forma["picos"]) == 0                   # áudio mudo
    assert midia["miniaturas"]["largura"] == 160


def test_ingestao_de_audio(db_limpo):
    midia_id = preparar_midia(db_limpo, "Pregacao.m4a", lambda c: gerar(
        c, "-f", "lavfi", "-i", "sine=frequency=220:duration=5", "-c:a", "aac"))

    resultado, midia, _ = processar(db_limpo, midia_id)
    assert resultado == "concluido"
    assert midia["video"] is None
    assert set(midia["arquivos"]) == {"proxy.m4a", "audio.wav", "forma_de_onda.json", "niveis.bin"}
    assert midia["miniaturas"] is None


def test_arquivo_invalido_falha_na_hora_sem_novas_tentativas(db_limpo):
    midia_id = preparar_midia(db_limpo, "Corrompido.mp4", lambda c: c.write_bytes(os.urandom(4096)))

    resultado, midia, job = processar(db_limpo, midia_id)
    assert resultado == "erro"
    assert job["status"] == "erro"
    assert job["tentativas"] == 1
    assert midia["status"] == "erro"
    assert "não é um vídeo ou áudio válido" in midia["erro"]
