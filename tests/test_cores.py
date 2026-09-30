# Filtros de cor: as operações e a cadeia do FFmpeg
import numpy as np
import pytest

from core.utils import cores
from core.utils.cores import IDS_FILTROS, filtro_ffmpeg, operacoes
from core.utils.render import montar_filtro


def aplicar(rgb: np.ndarray, filtro: str, intensidade: float = 1.0) -> np.ndarray:
    """A mesma conta que a prévia (filtro SVG) e o FFmpeg fazem, em numpy, para conferir."""
    atual = rgb.astype(float) / 255
    for tipo, valor in operacoes(filtro, intensidade):
        if tipo == "matriz":
            atual = np.clip(atual @ np.array(valor).T, 0, 1)
        else:
            atual = np.clip(atual * valor + 0.5 * (1 - valor), 0, 1)
    return np.round(atual * 255).astype(int)


def test_seis_filtros():
    assert IDS_FILTROS == ["natural", "quente", "frio", "cinema", "pb", "vivo"]
    assert operacoes("natural") == []
    assert operacoes("nao-existe") == []
    assert filtro_ffmpeg("natural") == ""


def test_intensidade_zero_desliga_e_meia_intensidade_fica_no_meio():
    assert operacoes("vivo", 0.0) == []
    cheia, meia = operacoes("vivo", 1.0), operacoes("vivo", 0.5)
    assert meia[0][1][0][0] == pytest.approx(1 + (cheia[0][1][0][0] - 1) / 2)
    assert meia[1][1] == pytest.approx(1 + (cheia[1][1] - 1) / 2)


def test_preto_e_branco_tira_toda_a_cor():
    pixels = aplicar(np.array([[255, 138, 0], [30, 90, 200]]), "pb")
    for r, g, b in pixels:
        assert r == g == b


def test_quente_puxa_para_o_vermelho_e_frio_para_o_azul():
    cinza = np.array([[128, 128, 128]])
    (r, _, b), = aplicar(cinza, "quente")
    assert r > 128 > b
    (r, _, b), = aplicar(cinza, "frio")
    assert b > 128 > r


def test_cadeia_do_ffmpeg():
    cadeia = filtro_ffmpeg("pb")
    assert cadeia.startswith("colorchannelmixer=rr=0.2126:rg=0.7152:rb=0.0722:")
    assert "colorlevels=rimin=0.0536:rimax=0.9464" in cadeia      # contraste 1,12


def test_contraste_menor_que_um_comprime_a_saida(monkeypatch):
    monkeypatch.setattr(cores, "FILTROS", [("suave", "Suave", [("contraste", 0.8)])])
    assert cores.filtro_ffmpeg("suave") == ("colorlevels=romin=0.1000:romax=0.9000:gomin=0.1000:gomax=0.9000:"
                                           "bomin=0.1000:bomax=0.9000")


def test_filtro_de_cor_vem_antes_do_fundo_no_render():
    recorte = {"x": 0, "y": 0, "largura": 1080, "altura": 1920}
    filtro = montar_filtro([[(0.0, 5.0)]], recorte, 1080, 1920, tem_audio=False,
                           fundo={"desfoque": 10, "escurecer": 0.3}, cor={"filtro": "pb", "intensidade": 1})
    cadeia = filtro.split(";\n")[0]
    assert cadeia.index("format=gbrp") < cadeia.index("colorchannelmixer=rr=0.2126") < cadeia.index("gblur")
    assert "format=gbrp" not in montar_filtro([[(0.0, 5.0)]], recorte, 1080, 1920, tem_audio=False,
                                              cor={"filtro": "natural"})
