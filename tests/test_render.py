# Planejamento do render e recorte do enquadramento: funções puras
import re

import pytest

from core.modelos.projeto import calcular_recorte, montar_exportacao, montar_projeto
from core.utils.render import (
    alinhar,
    duracao_dos_trechos,
    expressao_selecao,
    montar_filtro,
    planejar_trechos,
)


# -----------------------------------------------
# TRECHOS
# -----------------------------------------------
def test_trechos_sem_cortes_sao_o_trecho_inteiro():
    assert planejar_trechos(10.0, 25.0, []) == [(0.0, 15.0)]


def test_trechos_descontam_os_cortes_e_ficam_relativos_ao_inicio():
    cortes = [(3.12, 3.88), (12.12, 12.88), (40.0, 41.0)]  # o último fica fora do trecho
    assert planejar_trechos(10.0, 20.0, cortes) == [(0.0, alinhar(2.12)), (alinhar(2.88), 10.0)]


def test_corte_que_atravessa_as_bordas_do_trecho():
    assert planejar_trechos(5.0, 15.0, [(4.0, 6.0), (14.0, 16.0)]) == [(1.0, 9.0)]


def test_trecho_de_menos_de_dois_quadros_e_descartado():
    assert planejar_trechos(0.0, 10.0, [(1.0, 1.04), (1.05, 3.0)]) == [(0.0, 1.0), (3.0, 10.0)]


def test_tudo_cortado_fica_vazio():
    assert planejar_trechos(2.0, 4.0, [(0.0, 10.0)]) == []


def test_tempos_alinhados_aos_quadros():
    for a, b in planejar_trechos(0.0, 60.0, [(3.12, 3.88), (7.12, 7.88)]):
        assert round(a * 30, 6).is_integer() and round(b * 30, 6).is_integer()


def test_expressao_e_duracao():
    trechos = [(0.0, 1.5), (alinhar(2.3333), 4.0)]
    assert expressao_selecao(trechos) == "gte(t,-0.0167)*lt(t,1.4833)+gte(t,2.3167)*lt(t,3.9833)"
    assert duracao_dos_trechos(trechos) == 3.167


def test_expressao_seleciona_o_numero_certo_de_quadros():
    # Conta os quadros de 1/30 s que a expressão deixa passar, como o FFmpeg faz
    trechos = planejar_trechos(2.0, 18.0, [(3.147, 3.853), (7.147, 7.853), (11.147, 11.853), (15.147, 15.853)])
    termos = expressao_selecao(trechos).split("+")
    limites = [tuple(float(x) for x in re.findall(r"-?[\d.]+", termo)) for termo in termos]
    quadros = sum(1 for k in range(16 * 30) if any(a <= k / 30 < b for a, b in limites))
    assert quadros == round(duracao_dos_trechos(trechos) * 30)


# -----------------------------------------------
# ENQUADRAMENTO
# -----------------------------------------------
def test_recorte_vertical_de_video_horizontal_no_centro():
    assert calcular_recorte(1920, 1080, "9:16") == {"x": 656, "y": 0, "largura": 606, "altura": 1080}


def test_recorte_segue_o_ponto_mas_nao_sai_da_imagem():
    esquerda = calcular_recorte(1920, 1080, "9:16", x=0.0)
    direita = calcular_recorte(1920, 1080, "9:16", x=1.0)
    assert esquerda["x"] == 0
    assert direita["x"] + direita["largura"] <= 1920
    assert direita["x"] == 1314


def test_recorte_com_zoom():
    recorte = calcular_recorte(1920, 1080, "9:16", x=0.5, y=0.3, zoom=2.0)
    assert (recorte["largura"], recorte["altura"]) == (302, 540)
    assert recorte["y"] == 54  # 0.3 * 1080 - 540 / 2


@pytest.mark.parametrize(("largura", "altura", "proporcao", "esperado"), [
    (1080, 1920, "9:16", (1080, 1920)),   # já está em pé
    (1080, 1920, "16:9", (1080, 606)),    # vídeo em pé para o YouTube: faixa horizontal
    (1920, 1080, "1:1", (1080, 1080)),
    (1920, 1080, "4:5", (864, 1080)),
])
def test_recorte_por_proporcao(largura, altura, proporcao, esperado):
    recorte = calcular_recorte(largura, altura, proporcao)
    assert (recorte["largura"], recorte["altura"]) == esperado


# -----------------------------------------------
# FILTRO
# -----------------------------------------------
def test_filtro_com_audio():
    recorte = calcular_recorte(1920, 1080, "9:16")
    filtro = montar_filtro([[(0.0, 2.0), (3.0, 5.0)]], recorte, 1080, 1920, tem_audio=True)
    video, audio = filtro.split(";\n")
    assert "fps=30,select='gte(t,-0.0167)*lt(t,1.9833)+gte(t,2.9833)*lt(t,4.9833)'" in video
    assert "crop=606:1080:656:0,scale=1080:1920" in video
    assert video.endswith("[v]")
    assert "aresample=48000,asetnsamples=n=1600:p=0,aselect=" in audio
    assert "loudnorm=I=-14" in audio
    assert "afade=t=out:st=3.920:d=0.08[a]" in audio


def test_filtro_sem_audio_e_sem_normalizar():
    recorte = calcular_recorte(1080, 1920, "9:16")
    assert ";" not in montar_filtro([[(0.0, 2.0)]], recorte, 1080, 1920, tem_audio=False)
    com_audio = montar_filtro([[(0.0, 2.0)]], recorte, 1080, 1920, tem_audio=True, normalizar=False)
    assert "loudnorm" not in com_audio


def test_filtro_com_duas_partes_emenda_com_concat():
    recorte = calcular_recorte(1920, 1080, "9:16")
    partes = [[(0.0, 2.0)], [(0.0, 1.0), (1.5, 3.0)]]     # 2 s + 2,5 s
    grafo = montar_filtro(partes, recorte, 1080, 1920, tem_audio=True, camadas=[(0, 4)],
                          musica={"entrada": 3, "volume": 0.3, "abaixar_na_fala": False}).split(";\n")
    assert grafo[0].startswith("[0:v]setpts=PTS-STARTPTS") and grafo[0].endswith("[p0v]")
    assert grafo[1].startswith("[0:a]asetpts=PTS-STARTPTS") and grafo[1].endswith("[p0a]")
    assert grafo[2].startswith("[1:v]") and grafo[3].startswith("[1:a]")
    assert grafo[4] == "[p0v][p0a][p1v][p1a]concat=n=2:v=1:a=1[pv][pa]"
    assert grafo[5].startswith("[pv]crop=606:1080:656:0,scale=1080:1920")
    assert grafo[6].startswith("[base0][2:v]overlay=0:0")      # a camada vem depois das duas partes
    assert grafo[7] == "[pa]anull,aformat=channel_layouts=stereo[voz]"
    assert "atrim=0:4.500" in grafo[8]                         # a música tem a duração do vídeo todo
    assert "afade=t=out:st=4.420" in grafo[-1]

    sem_audio = montar_filtro([[(0.0, 1.0)], [(0.0, 1.0)]], recorte, 1080, 1920, tem_audio=False).split(";\n")
    assert sem_audio[2] == "[p0v][p1v]concat=n=2:v=1:a=0[pv]"
    assert sem_audio[-1].endswith("[v]") and "[pa]" not in ";".join(sem_audio)


def test_filtro_com_musica_abaixando_sob_a_fala():
    recorte = calcular_recorte(1920, 1080, "9:16")
    musica = {"entrada": 3, "volume": 0.3, "abaixar_na_fala": True}
    partes = montar_filtro([[(0.0, 2.0), (3.0, 5.0)]], recorte, 1080, 1920, tem_audio=True,
                           camadas=[(0, 4), (1, 2)], musica=musica).split(";\n")
    assert partes[-4].endswith("asplit=2[voz][chave]")        # a voz vai para a mixagem e para a chave
    assert partes[-3] == ("[3:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:4.000,"
                          "asetpts=PTS-STARTPTS,volume=0.300[musica0]")
    assert partes[-2].startswith("[musica0][chave]sidechaincompress=threshold=0.02:ratio=10:")
    assert partes[-2].endswith("[musica]")
    assert partes[-1].startswith("[voz][musica]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14")
    assert partes[-1].endswith("[a]")
    assert len(re.findall(r"\[a\]", ";".join(partes))) == 1


def test_filtro_com_musica_sem_abaixar_e_sem_audio_na_gravacao():
    recorte = calcular_recorte(1920, 1080, "9:16")
    musica = {"entrada": 1, "volume": 0.5, "abaixar_na_fala": False}
    sem_abaixar = montar_filtro([[(0.0, 2.0)]], recorte, 1080, 1920, tem_audio=True, musica=musica)
    assert "sidechaincompress" not in sem_abaixar
    assert "[voz][musica]amix=inputs=2" in sem_abaixar

    so_musica = montar_filtro([[(0.0, 2.0)]], recorte, 1080, 1920, tem_audio=False, musica=musica).split(";\n")
    assert len(so_musica) == 2 and "[0:a]" not in so_musica[1]   # a gravação muda não entra no áudio
    assert so_musica[1].startswith("[1:a]aresample=48000") and so_musica[1].endswith("[a]")


def test_filtro_com_rosto_poe_o_sendcmd_antes_do_crop():
    recorte = calcular_recorte(1920, 1080, "9:16")
    grafo = montar_filtro([[(0.0, 2.0)]], recorte, 1080, 1920, tem_audio=False, comandos_rosto="C:/dados/rosto.txt")
    assert "sendcmd=filename=C\\:/dados/rosto.txt,crop=" in grafo


def test_filtro_com_audio_limpo_nao_desloca_as_camadas():
    recorte = calcular_recorte(1920, 1080, "9:16")
    uma = montar_filtro([[(0.0, 2.0)]], recorte, 1080, 1920, tem_audio=True, audio_limpo=(2, [(5.0, 9.0)]))
    assert "[2:a]atrim=start=5.000:end=9.000" in uma
    assert "[0:a]" not in uma

    partes = [[(0.0, 2.0)], [(0.0, 1.0)]]
    grafo = montar_filtro(partes, recorte, 1080, 1920, tem_audio=True, camadas=[(0, 3)],
                          audio_limpo=(4, [(12.0, 20.0), (30.0, 40.0)])).split(";\n")
    assert grafo[0].startswith("[4:a]asplit=2")
    assert "atrim=start=12.000:end=20.000" in grafo[2]
    assert "atrim=start=30.000:end=40.000" in grafo[4]
    assert all("[0:a]" not in linha and "[1:a]" not in linha for linha in grafo)
    assert any(linha.startswith("[base0][2:v]overlay") for linha in grafo)
    with pytest.raises(ValueError):
        montar_filtro(partes, recorte, 1080, 1920, tem_audio=True, audio_limpo=(1, [(0.0, 1.0)]))


# -----------------------------------------------
# PROJETO E EXPORTAÇÃO
# -----------------------------------------------
def test_projeto_e_exportacao_guardam_a_configuracao():
    midia = {"_id": "m1", "nome": "Culto de domingo", "duracao": 2400.456}
    projeto = montar_projeto("org1", midia, "u1")
    assert projeto["nome"] == "Reel · Culto de domingo"
    assert projeto["partes"] == [{"id": "p1", "inicio": 0.0, "fim": 2400.46}]
    assert projeto["silencios"] == {"intensidade": "media"}
    assert projeto["audio"] == {"normalizar": True, "limpeza": False}
    assert projeto["musica"] == {"id": None, "volume": 0.25, "abaixar_na_fala": True, "inicio": 0.0}
    with pytest.raises(ValueError):
        montar_projeto("org1", midia, "u1", proporcao="3:2")

    projeto["_id"] = "p1"
    exportacao = montar_exportacao(projeto, "u1")
    assert exportacao["configuracao"]["partes"] == projeto["partes"]
    assert exportacao["configuracao"]["musica"] == projeto["musica"]
    assert (exportacao["largura"], exportacao["altura"]) == (1080, 1920)
    projeto["partes"][0]["fim"] = 30.0         # editar o projeto depois
    projeto["enquadramento"]["zoom"] = 2.0
    assert exportacao["configuracao"]["partes"][0]["fim"] == 2400.46
    assert exportacao["configuracao"]["enquadramento"]["zoom"] == 1.0
