# Música da biblioteca de ponta a ponta: preparar a faixa e mixar no Reel. FFmpeg e MongoDB de verdade.
# A "voz" da gravação é um tom de 220 Hz e a música um tom de 880 Hz: filtrando cada faixa de
# frequência, dá para medir o volume da música separado da fala.
import re
import shutil
import subprocess

import pytest
from bson import ObjectId

from core.modelos.job import montar_job
from core.modelos.midia import chave_arquivo, montar_midia
from core.modelos.musica import chave_musica, montar_musica
from core.utils import storage
from core.utils.fila import enfileirar_job, pegar_proximo_job
from tests.integracao.test_renderizacao import exportar, midia_pronta, rodar, sondar
from worker.worker_principal import processar_job

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg não instalado")

SO_MUSICA = "highpass=f=600,highpass=f=600"
SO_VOZ = "lowpass=f=400,lowpass=f=400"


def gerar_tom(caminho, frequencia, duracao):
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                    "-i", f"sine=frequency={frequencia}:sample_rate=44100:duration={duracao}", "-ac", "2",
                    str(caminho)], check=True, timeout=60)


def musica_pronta(db, organizacao_id, duracao=5, arquivo="original.wav", conteudo=None):
    musica = montar_musica(organizacao_id, None, "Tom de teste", "", "propria")
    musica.update({"status": "processando", "original": arquivo})
    musica["_id"] = db.musicas.insert_one(musica).inserted_id
    original = storage.caminho_local(chave_musica(organizacao_id, musica["_id"], arquivo))
    original.parent.mkdir(parents=True, exist_ok=True)
    if conteudo is None:
        gerar_tom(original, 880, duracao)
    else:
        original.write_bytes(conteudo)
    enfileirar_job(db, montar_job("preparar_musica", organizacao_id, {"musica_id": str(musica["_id"])}))
    return musica["_id"]


def nivel(caminho, faixa: str, inicio: float, fim: float) -> float:
    """RMS em dB de uma faixa de frequência entre dois instantes do arquivo."""
    filtro = f"atrim={inicio}:{fim},{faixa},astats=metadata=0"
    saida = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(caminho), "-af", filtro, "-f", "null", "-"],
                           capture_output=True, text=True, timeout=60).stderr
    return float(re.findall(r"RMS level dB:\s+(-?[\d.]+|-inf)", saida)[-1])


def test_preparar_musica(db_limpo):
    organizacao_id = ObjectId()
    musica_id = musica_pronta(db_limpo, organizacao_id, duracao=4)
    rodar(db_limpo, "preparar_musica")
    musica = db_limpo.musicas.find_one({"_id": musica_id})
    assert musica["status"] == "pronta" and musica["original"] is None
    assert abs(musica["duracao"] - 4) < 0.1
    pronta = storage.caminho_local(chave_musica(organizacao_id, musica_id, "musica.m4a"))
    saida = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,sample_rate,channels",
                            "-of", "csv=p=0", str(pronta)], capture_output=True, text=True, check=True).stdout
    assert saida.strip() == "aac,48000,2"
    assert not storage.caminho_local(chave_musica(organizacao_id, musica_id, "original.wav")).exists()


def test_arquivo_que_nao_e_audio_falha_sem_novas_tentativas(db_limpo):
    musica_id = musica_pronta(db_limpo, ObjectId(), arquivo="original.mp3", conteudo=b"isto nao e um mp3")
    job = pegar_proximo_job(db_limpo, ["preparar_musica"], "w-teste")
    assert processar_job(db_limpo, job, "w-teste") == "erro"
    musica = db_limpo.musicas.find_one({"_id": musica_id})
    assert musica["status"] == "erro" and "áudio" in musica["erro"]
    assert db_limpo.jobs.find_one({"_id": job["_id"]})["tentativas"] == 1


@pytest.fixture
def gravacao_e_musica(db_limpo):
    midia = midia_pronta(db_limpo, largura=640, altura=360, duracao=8)
    musica_id = musica_pronta(db_limpo, midia["organizacao_id"], duracao=5)
    rodar(db_limpo, "preparar_musica")
    return midia, str(musica_id)


def reel_com_musica(db, midia, musica_id, abaixar):
    # Sem normalizar: o loudnorm muda o ganho ao longo do tempo e atrapalharia a medida
    exportacao, video = exportar(db, midia, partes=[{"id": "p1", "inicio": 0.0, "fim": 8.0}],
                                 silencios={"intensidade": None}, audio={"normalizar": False},
                                 musica={"id": musica_id, "volume": 0.5, "abaixar_na_fala": abaixar, "inicio": 1.0})
    assert exportacao["status"] == "pronta"
    return video


def test_musica_abaixa_sob_a_fala(db_limpo, gravacao_e_musica):
    midia, musica_id = gravacao_e_musica
    video = reel_com_musica(db_limpo, midia, musica_id, abaixar=True)
    # A gravação fala de 0 a 3 s e fica em silêncio de 3 a 4 s
    durante_a_fala = nivel(video, SO_MUSICA, 1.0, 2.5)
    na_pausa = nivel(video, SO_MUSICA, 3.5, 3.95)
    assert na_pausa - durante_a_fala > 10
    assert nivel(video, SO_VOZ, 1.0, 2.5) - durante_a_fala > 20    # a voz fica bem na frente
    fluxo_video, fluxo_audio = sondar(video)
    assert abs(float(fluxo_audio["duration"]) - float(fluxo_video["duration"])) < 0.07


def test_musica_sem_abaixar_fica_constante_e_repete(db_limpo, gravacao_e_musica):
    midia, musica_id = gravacao_e_musica
    video = reel_com_musica(db_limpo, midia, musica_id, abaixar=False)
    durante_a_fala = nivel(video, SO_MUSICA, 1.0, 2.5)
    assert abs(nivel(video, SO_MUSICA, 3.5, 3.95) - durante_a_fala) < 1.5
    # A faixa tem 5 s e começa no segundo 1: depois de 4 s do vídeo ela recomeça do início
    assert abs(nivel(video, SO_MUSICA, 5.0, 7.5) - durante_a_fala) < 1.5


def test_gravacao_sem_som_ganha_so_a_musica(db_limpo):
    midia = montar_midia(ObjectId(), None, "Sem som.mp4", 1)
    midia["_id"] = db_limpo.midias.insert_one(midia).inserted_id
    original = storage.caminho_local(chave_arquivo(midia["organizacao_id"], midia["_id"], midia["original"]))
    original.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi",
                    "-i", "testsrc2=size=640x360:rate=30:duration=4", "-c:v", "libx264", "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p", str(original)], check=True, timeout=60)
    db_limpo.midias.update_one({"_id": midia["_id"]}, {"$set": {"status": "processando"}})
    enfileirar_job(db_limpo, montar_job("ingestao", midia["organizacao_id"], {"midia_id": str(midia["_id"])}))
    rodar(db_limpo, "ingestao")
    midia = db_limpo.midias.find_one({"_id": midia["_id"]})
    assert not midia.get("audio")

    musica_id = str(musica_pronta(db_limpo, midia["organizacao_id"], duracao=3))
    rodar(db_limpo, "preparar_musica")
    _, video = exportar(db_limpo, midia, musica={"id": musica_id, "volume": 0.5, "abaixar_na_fala": True,
                                                 "inicio": 0.0})
    fluxo_video, fluxo_audio = sondar(video)
    assert fluxo_audio is not None
    assert abs(float(fluxo_audio["duration"]) - float(fluxo_video["duration"])) < 0.07
    assert nivel(video, SO_MUSICA, 0.5, 3.5) > -30          # normalizada, e repetindo depois dos 3 s

    # Música que ainda não ficou pronta: o vídeo sai sem ela, sem falhar
    db_limpo.musicas.update_one({"_id": ObjectId(musica_id)}, {"$set": {"status": "processando"}})
    exportacao, video = exportar(db_limpo, midia, musica={"id": musica_id, "volume": 0.5,
                                                          "abaixar_na_fala": True, "inicio": 0.0})
    assert exportacao["status"] == "pronta"
    assert sondar(video)[1] is None
