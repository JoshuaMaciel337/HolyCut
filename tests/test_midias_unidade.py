# Testes de mídia e upload que não precisam de banco nem de FFmpeg
import base64
import wave

import numpy as np
import pytest

from api.rotas.uploads import ler_metadados
from core.modelos.midia import STATUS_ENVIANDO, extensao_aceita, montar_midia, nome_para_exibir
from core.utils.ffmpeg import ler_progresso, resumir_sondagem
from worker.tarefas.ingestao import analisar_audio, planejar_miniaturas


def b64(texto: str) -> str:
    return base64.b64encode(texto.encode()).decode()


# -----------------------------------------------
# UPLOAD
# -----------------------------------------------
def test_ler_metadados_do_tus():
    cabecalho = f"filename {b64('Culto domingo.MP4')},filetype {b64('video/mp4')},vazio,quebrado ###"
    assert ler_metadados(cabecalho) == {
        "filename": "Culto domingo.MP4", "filetype": "video/mp4", "vazio": "", "quebrado": "",
    }
    assert ler_metadados("") == {}


@pytest.mark.parametrize(("nome", "esperado"), [
    ("culto.MP4", ".mp4"), ("pregação.mov", ".mov"), ("louvor.m4a", ".m4a"),
    ("planilha.xlsx", None), ("sem_extensao", None), ("C:\\Videos\\culto.mkv", ".mkv"),
])
def test_extensao_aceita(nome, esperado):
    assert extensao_aceita(nome) == esperado


def test_montar_midia():
    midia = montar_midia("org1", "u1", "C:\\Videos\\Culto 29-09.MP4", 1234, "video/mp4")
    assert midia["status"] == STATUS_ENVIANDO
    assert midia["nome"] == "Culto 29-09"
    assert midia["original"] == "original.mp4"
    assert midia["bytes_recebidos"] == 0
    assert nome_para_exibir("   .mp4") == "Gravação"
    with pytest.raises(ValueError):
        montar_midia("org1", "u1", "virus.exe", 10)


# -----------------------------------------------
# FFPROBE E FFMPEG
# -----------------------------------------------
def test_resumir_sondagem_de_video_de_celular_em_pe():
    sondagem = {
        "format": {"duration": "61.5"},
        "streams": [
            {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080,
             "avg_frame_rate": "30000/1001", "side_data_list": [{"rotation": -90}]},
            {"codec_type": "audio", "codec_name": "aac", "channels": 2, "sample_rate": "48000"},
        ],
    }
    resumo = resumir_sondagem(sondagem)
    assert resumo["duracao"] == 61.5
    assert resumo["video"] == {"codec": "h264", "largura": 1080, "altura": 1920, "fps": 29.97, "rotacao": 270}
    assert resumo["audio"] == {"codec": "aac", "canais": 2, "taxa": 48000}


def test_resumir_sondagem_ignora_capa_de_mp3():
    sondagem = {"format": {"duration": "10"}, "streams": [
        {"codec_type": "video", "codec_name": "mjpeg", "width": 500, "height": 500,
         "disposition": {"attached_pic": 1}},
        {"codec_type": "audio", "codec_name": "mp3", "channels": 2, "sample_rate": "44100"},
    ]}
    resumo = resumir_sondagem(sondagem)
    assert resumo["video"] is None
    assert resumo["audio"]["codec"] == "mp3"


def test_ler_progresso():
    assert ler_progresso("out_time_us=1500000") == 1.5
    assert ler_progresso("out_time_ms=2500000\n") == 2.5
    assert ler_progresso("out_time_us=N/A") is None
    assert ler_progresso("progress=continue") is None


# -----------------------------------------------
# INGESTÃO
# -----------------------------------------------
def test_forma_de_onda_de_um_wav_sintetico(tmp_path):
    taxa = 16000
    silencio = np.zeros(taxa, dtype=np.int16)                                   # 1 s mudo
    tom = (np.sin(np.linspace(0, 440 * 2 * np.pi, taxa)) * 16383).astype(np.int16)  # 1 s a 50%
    caminho = tmp_path / "audio.wav"
    with wave.open(str(caminho), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(taxa)
        wav.writeframes(np.concatenate([silencio, tom, tom[:400]]).tobytes())

    forma, niveis = analisar_audio(caminho, picos_por_segundo=20)
    picos = forma["picos"]
    assert forma["picos_por_segundo"] == 20
    assert len(picos) == 41                      # 2 s a 20 por segundo, mais meio pico no fim
    assert max(picos[:20]) == 0
    assert all(48 <= p <= 51 for p in picos[20:40])

    assert niveis.dtype.name == "int8"
    assert len(niveis) == 203                    # 2 s a 100 por segundo, mais o pedaço do fim
    assert set(niveis[:100].tolist()) == {-90}   # silêncio digital: o piso de 16 bits é 1/32767 ≈ -90 dB
    assert all(-7 <= n <= -5 for n in niveis[101:199])  # tom a 50% do máximo ≈ -6 dB


def test_planejar_miniaturas():
    assert planejar_miniaturas(30)["total"] == 10       # mínimo
    assert planejar_miniaturas(2400)["total"] == 100    # máximo numa pregação de 40 min
    plano = planejar_miniaturas(500)
    assert plano == {"total": 50, "colunas": 10, "linhas": 5, "intervalo": 10.0}
