# Pacote para DaVinci e Premiere: quadros, o XML dos cortes e o SRT
import xml.etree.ElementTree as ET

import pytest

from core.modelos.pacote_edicao import clipes_da_linha_do_tempo, gerar_srt, gerar_xml, leia_me, taxa_de_quadros

NTSC_30 = 30000 / 1001
VIDEO = {"largura": 1920, "altura": 1080, "fps": 29.97}
CLIPES = [{"start": 0, "end": 90, "in": 300, "out": 390}, {"start": 90, "end": 150, "in": 600, "out": 660}]


@pytest.mark.parametrize(("fps", "esperado"), [
    (29.97, (30, True)), (30.0, (30, False)), (25, (25, False)), (23.976, (24, True)), (59.94, (60, True)),
    (None, (30, False)),
])
def test_taxa_de_quadros(fps, esperado):
    assert taxa_de_quadros(fps)[:2] == esperado


def test_centenas_de_cortes_nao_escorregam():
    # 300 trechos de 0,1 s: arredondar cada clipe sozinho somaria o erro na linha do tempo
    partes = [({"inicio": 100.0}, [(indice * 0.2, indice * 0.2 + 0.1) for indice in range(300)])]
    clipes = clipes_da_linha_do_tempo(partes, NTSC_30)
    assert clipes[-1]["end"] == round(30.0 * NTSC_30)
    assert all(clipe["out"] - clipe["in"] == clipe["end"] - clipe["start"] for clipe in clipes)
    assert all(anterior["end"] == atual["start"] for anterior, atual in zip(clipes, clipes[1:], strict=False))
    assert clipes[1]["in"] == round(100.2 * NTSC_30)


def test_xml_tem_cada_trecho_no_video_e_nas_duas_faixas_de_audio():
    texto = gerar_xml("Pregação & Culto", "Culto 28-09.mkv", 3600.0, VIDEO, {"canais": 2, "taxa": 48000}, CLIPES)
    assert texto.startswith('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n<xmeml version="5">')
    sequencia = ET.fromstring(texto).find("sequence")
    assert sequencia.findtext("name") == "Pregação & Culto"
    assert sequencia.findtext("duration") == "150" and sequencia.findtext("rate/ntsc") == "TRUE"
    assert sequencia.findtext("media/video/format/samplecharacteristics/width") == "1920"
    video = sequencia.findall("media/video/track/clipitem")
    assert [(clipe.findtext("start"), clipe.findtext("in"), clipe.findtext("out")) for clipe in video] == [
        ("0", "300", "390"), ("90", "600", "660")]
    faixas = sequencia.findall("media/audio/track")
    assert len(faixas) == 2 and all(len(faixa.findall("clipitem")) == 2 for faixa in faixas)
    assert faixas[1].find("clipitem/sourcetrack").findtext("trackindex") == "2"
    # A gravação é descrita uma vez, inteira (é a folga); os outros clipes só apontam para ela
    arquivos = sequencia.findall(".//file")
    completos = [arquivo for arquivo in arquivos if arquivo.find("pathurl") is not None]
    assert len(completos) == 1 and all(arquivo.get("id") == "arquivo-1" for arquivo in arquivos)
    assert completos[0].findtext("pathurl") == "file://localhost/Culto%2028-09.mkv"
    assert completos[0].findtext("duration") == str(round(3600 * NTSC_30))
    assert completos[0].findtext("media/audio/channelcount") == "2"
    # Vídeo e as duas faixas de áudio do mesmo trecho ficam ligados
    assert [link.findtext("linkclipref") for link in video[1].findall("link")] == ["video-2", "audio-1-2", "audio-2-2"]


def test_xml_de_gravacao_sem_audio():
    texto = gerar_xml("Culto", "culto.mp4", 60.0, {**VIDEO, "fps": 25}, None, CLIPES)
    sequencia = ET.fromstring(texto).find("sequence")
    assert sequencia.find("media/audio") is None and sequencia.findtext("rate/ntsc") == "FALSE"
    assert len(sequencia.find("media/video/track/clipitem").findall("link")) == 1


def test_srt_e_leia_me():
    blocos = [{"inicio": 0.0, "fim": 1.5, "palavras": [{"texto": "A"}, {"texto": "graça"}]},
              {"inicio": 2.0, "fim": 2.5, "palavras": [{"texto": " "}]},
              {"inicio": 3725.25, "fim": 3726.0, "palavras": [{"texto": "Amém."}]}]
    assert gerar_srt(blocos) == ("1\n00:00:00,000 --> 00:00:01,500\nA graça\n\n"
                                 "2\n01:02:05,250 --> 01:02:06,000\nAmém.\n")
    assert gerar_srt([]) == ""
    texto = leia_me("Mensagem · Culto", "Culto 28-09.mkv", "mensagem-culto", True, "16:9")
    assert "mensagem-culto.xml" in texto and "mensagem-culto.srt" in texto and "(Culto 28-09.mkv)" in texto
    assert ".srt" not in leia_me("Reel", "a.mp4", "reel", False, "9:16")
