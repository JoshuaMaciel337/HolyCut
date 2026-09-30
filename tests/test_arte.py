# Arte sobre o vídeo (logo e textos) e identidade da igreja: sem banco nem FFmpeg
import io

import pytest
from PIL import Image, ImageFont

from core.modelos.identidade import marca_padrao, normalizar_instagram
from core.utils.arte import (
    ErroImagem,
    camada_logo,
    camada_texto,
    carregar_fonte,
    preparar_logo,
    quebrar_linhas,
)
from core.utils.render import montar_filtro


def png_com_margem(cor=(255, 138, 0, 255)) -> bytes:
    """Logo 200x100 com 50 px de transparência em volta."""
    imagem = Image.new("RGBA", (300, 200), (0, 0, 0, 0))
    imagem.paste(Image.new("RGBA", (200, 100), cor), (50, 50))
    saida = io.BytesIO()
    imagem.save(saida, format="PNG")
    return saida.getvalue()


def opacos(imagem: Image.Image, caixa: tuple[int, int, int, int]) -> int:
    return sum(1 for valor in imagem.crop(caixa).getchannel("A").get_flattened_data() if valor > 128)


# -----------------------------------------------
# LOGO
# -----------------------------------------------
def test_preparar_logo_corta_a_transparencia_em_volta():
    logo = Image.open(io.BytesIO(preparar_logo(png_com_margem())))
    assert logo.size == (200, 100)
    assert logo.mode == "RGBA"


def test_preparar_logo_recusa_o_que_nao_e_imagem():
    with pytest.raises(ErroImagem):
        preparar_logo(b"isto nao e uma imagem")
    transparente = io.BytesIO()
    Image.new("RGBA", (10, 10), (0, 0, 0, 0)).save(transparente, format="PNG")
    with pytest.raises(ErroImagem):
        preparar_logo(transparente.getvalue())


def test_preparar_logo_reduz_imagens_grandes_e_aceita_jpg():
    saida = io.BytesIO()
    Image.new("RGB", (3000, 1500), (10, 20, 30)).save(saida, format="JPEG")
    assert Image.open(io.BytesIO(preparar_logo(saida.getvalue()))).size == (1024, 512)


@pytest.mark.parametrize(("posicao", "caixa_com_logo"), [
    ("topo_direita", (700, 60, 1020, 200)),
    ("base_esquerda", (60, 1700, 400, 1860)),
])
def test_camada_logo_no_canto_escolhido(posicao, caixa_com_logo):
    camada = camada_logo(1080, 1920, preparar_logo(png_com_margem()), posicao, tamanho=0.2, opacidade=1)
    assert camada.size == (1080, 1920)
    assert opacos(camada, caixa_com_logo) > 1000
    assert opacos(camada, (400, 800, 680, 1100)) == 0  # o meio fica livre


def test_camada_logo_com_opacidade():
    camada = camada_logo(1080, 1920, preparar_logo(png_com_margem()), "topo_esquerda", tamanho=0.2, opacidade=0.5)
    alfa = max(camada.crop((64, 64, 280, 150)).getchannel("A").get_flattened_data())
    assert 120 <= alfa <= 135


# -----------------------------------------------
# TEXTO
# -----------------------------------------------
def test_fontes_usam_o_mesmo_motor_de_layout_em_todo_lugar():
    # Prévia (API) e vídeo (worker) precisam medir o texto do mesmo jeito
    for familia in ("display", "texto", "manuscrita"):
        assert carregar_fonte(familia, "forte", 40).layout_engine == ImageFont.Layout.BASIC


def test_quebrar_linhas_respeita_a_largura_e_as_quebras_digitadas():
    fonte = carregar_fonte("texto", "forte", 40)
    linhas = quebrar_linhas("Porque Deus amou o mundo de tal maneira\nJoão", fonte, 300)
    assert linhas[-1] == "João"
    assert all(fonte.getlength(linha) <= 300 for linha in linhas)
    assert len(linhas) >= 3


@pytest.mark.parametrize(("posicao", "faixa_y"), [
    ("topo", (100, 450)), ("centro", (760, 1160)), ("base", (1300, 1800)),
])
def test_camada_texto_na_posicao_escolhida(posicao, faixa_y):
    camada = camada_texto(1080, 1920, "Ele é digno", "destaque", posicao, "#FF8A00")
    assert opacos(camada, (0, faixa_y[0], 1080, faixa_y[1])) > 5000
    fora = (0, 0, 1080, faixa_y[0]) if posicao != "topo" else (0, faixa_y[1], 1080, 1920)
    assert opacos(camada, fora) == 0


def test_estilo_destaque_usa_a_cor_da_igreja():
    camada = camada_texto(1080, 1920, "Culto de hoje", "destaque", "centro", "#7B61FF")
    cores = [p for p in camada.get_flattened_data() if p[3] > 200 and p[:3] != (255, 255, 255)]
    assert any(abs(r - 0x7B) < 10 and abs(g - 0x61) < 10 and abs(b - 0xFF) < 10 for r, g, b, _ in cores[:5000])


def test_texto_longo_diminui_a_fonte_para_caber():
    longo = " ".join(["palavra"] * 80)
    camada = camada_texto(1080, 1920, longo, "limpo", "centro", "#FF8A00")
    caixa = camada.getchannel("A").getbbox()
    assert caixa is not None and caixa[0] > 50 and caixa[2] < 1030


def test_versiculo_com_referencia_e_texto_vazio():
    com_ref = camada_texto(1080, 1920, "Tudo posso", "limpo", "centro", "#FF8A00", referencia="Filipenses 4:13")
    sem_ref = camada_texto(1080, 1920, "Tudo posso", "limpo", "centro", "#FF8A00")
    assert com_ref.getchannel("A").getbbox()[3] > sem_ref.getchannel("A").getbbox()[3]
    assert camada_texto(1080, 1920, "   ", "manuscrito", "base").getchannel("A").getbbox() is None


# -----------------------------------------------
# IDENTIDADE E FILTRO
# -----------------------------------------------
@pytest.mark.parametrize(("entrada", "esperado"), [
    (" @Igreja.Viva ", "@igreja.viva"),
    ("https://www.instagram.com/igreja_viva/", "@igreja_viva"),
    ("igreja viva!", "@igrejaviva"),
    ("", ""),
])
def test_normalizar_instagram(entrada, esperado):
    assert normalizar_instagram(entrada) == esperado


def test_marca_padrao_liga_o_logo_so_se_houver_logo():
    assert marca_padrao({"logo": True})["logo"] is True
    assert marca_padrao({})["logo"] is False
    assert marca_padrao(None)["posicao"] == "topo_direita"


def test_filtro_com_camadas():
    recorte = {"x": 0, "y": 0, "largura": 1080, "altura": 1920}
    filtro = montar_filtro([[(0.0, 10.0)]], recorte, 1080, 1920, tem_audio=False, camadas=[(0.0, 10.0), (2.0, 99.0)])
    linhas = filtro.split(";\n")
    assert linhas[0].endswith("setsar=1[base0]")
    assert linhas[1] == "[base0][1:v]overlay=0:0:enable='between(t,0.000,10.000)'[base1]"
    assert linhas[2] == "[base1][2:v]overlay=0:0:enable='between(t,2.000,10.000)',format=yuv420p[v]"
