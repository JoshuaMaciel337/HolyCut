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
    filtro = montar_filtro([(0.0, 2.0), (3.0, 5.0)], recorte, 1080, 1920, tem_audio=True)
    video, audio = filtro.split(";\n")
    assert "fps=30,select='gte(t,-0.0167)*lt(t,1.9833)+gte(t,2.9833)*lt(t,4.9833)'" in video
    assert "crop=606:1080:656:0,scale=1080:1920" in video
    assert video.endswith("[v]")
    assert "aresample=48000,asetnsamples=n=1600:p=0,aselect=" in audio
    assert "loudnorm=I=-14" in audio
    assert "afade=t=out:st=3.920:d=0.08[a]" in audio


def test_filtro_sem_audio_e_sem_normalizar():
    recorte = calcular_recorte(1080, 1920, "9:16")
    assert ";" not in montar_filtro([(0.0, 2.0)], recorte, 1080, 1920, tem_audio=False)
    com_audio = montar_filtro([(0.0, 2.0)], recorte, 1080, 1920, tem_audio=True, normalizar=False)
    assert "loudnorm" not in com_audio


# -----------------------------------------------
# PROJETO E EXPORTAÇÃO
# -----------------------------------------------
def test_projeto_e_exportacao_guardam_a_configuracao():
    midia = {"_id": "m1", "nome": "Culto de domingo", "duracao": 2400.456}
    projeto = montar_projeto("org1", midia, "u1")
    assert projeto["nome"] == "Reel · Culto de domingo"
    assert projeto["trecho"] == {"inicio": 0.0, "fim": 2400.46}
    assert projeto["silencios"] == {"intensidade": "media"}
    with pytest.raises(ValueError):
        montar_projeto("org1", midia, "u1", proporcao="3:2")

    projeto["_id"] = "p1"
    exportacao = montar_exportacao(projeto, "u1")
    assert exportacao["configuracao"]["trecho"] == projeto["trecho"]
    assert (exportacao["largura"], exportacao["altura"]) == (1080, 1920)
    projeto["trecho"]["fim"] = 30.0            # editar o projeto depois
    projeto["enquadramento"]["zoom"] = 2.0
    assert exportacao["configuracao"]["trecho"]["fim"] == 2400.46
    assert exportacao["configuracao"]["enquadramento"]["zoom"] == 1.0
