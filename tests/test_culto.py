# Acervo: ficha do culto, fileiras e capas (funções puras)
import io
from datetime import UTC, datetime

import numpy as np
import pytest
from PIL import Image

from core.modelos.culto import ficha_do_culto, formatar_data, linha_de_informacao, montar_fileiras
from core.utils.arte import ErroImagem, desenhar_capa, preparar_fundo_capa


def test_ficha_do_culto():
    # Enviada às 23h de 30/09 em São Paulo, que são 02h de 01/10 em UTC: o culto é do dia 30
    midia = {"enviado_em": datetime(2026, 10, 1, 2, 0, tzinfo=UTC)}
    assert ficha_do_culto(midia) == {"data": "2026-09-30", "pregador": "", "serie": "", "descricao": ""}
    salva = {**midia, "ficha": {"data": "2026-08-15", "pregador": "Pr. Joelson", "serie": "Romanos", "descricao": ""}}
    assert ficha_do_culto(salva)["data"] == "2026-08-15"
    assert formatar_data("2026-08-15") == "15/08/2026" and formatar_data("x") == ""
    assert linha_de_informacao(ficha_do_culto(salva)) == "Pr. Joelson · 15/08/2026"
    assert linha_de_informacao({"pregador": "", "data": "2026-08-15"}) == "15/08/2026"


def test_fileiras_do_acervo():
    cultos = [
        {"id": "c4", "serie": "Romanos", "pregador": "Pr. Ana", "cortes": 2},
        {"id": "c3", "serie": "", "pregador": "Pr. Bruno", "cortes": 0},
        {"id": "c2", "serie": "Romanos", "pregador": "Pr. Ana", "cortes": 0},
        {"id": "c1", "serie": "Família", "pregador": "Pr. Carla", "cortes": 1},
    ]
    fileiras = {f["id"]: f for f in montar_fileiras(cultos, ["c2", "c9", "c2", "c1"])}
    assert fileiras["recentes"]["ids"] == ["c4", "c3", "c2", "c1"]
    assert fileiras["editando"]["ids"] == ["c2", "c1"]          # sem repetir e sem culto que não existe
    assert fileiras["cortes"]["ids"] == ["c4", "c1"]
    assert fileiras["serie:Romanos"]["ids"] == ["c4", "c2"] and fileiras["serie:Romanos"]["titulo"] == "Série: Romanos"
    assert "pregador:Pr. Ana" in fileiras                         # dois cultos: ganha fileira
    assert "pregador:Pr. Bruno" not in fileiras                   # um só: não
    ordem = [f["id"] for f in montar_fileiras(cultos, [])]
    assert ordem.index("serie:Romanos") < ordem.index("serie:Família")   # a série mais recente vem antes
    assert "editando" not in ordem


def claridade(imagem: Image.Image, caixa) -> float:
    return float(np.asarray(imagem.crop(caixa).convert("L"), dtype=np.float32).mean())


def test_capa_poster_e_banner():
    quadro = Image.new("RGB", (1280, 720), (230, 220, 40))       # quadro bem claro, o pior caso
    poster = desenhar_capa(quadro, 600, 900, "Inconformados no altar", "Pr. Joelson · 15/08/2026", "Romanos 12",
                           "#FF8A00")
    banner = desenhar_capa(quadro, 1280, 720, "Inconformados no altar", "Pr. Joelson · 15/08/2026", "", "#FF8A00")
    assert poster.size == (600, 900) and banner.size == (1280, 720)
    # O degradê escurece onde o texto fica, e o texto branco aparece por cima
    assert claridade(poster, (0, 0, 600, 200)) > claridade(poster, (500, 800, 600, 900)) + 60
    area_titulo = np.asarray(poster.crop((30, 450, 570, 850)))
    assert (area_titulo.min(axis=2) > 235).sum() > 1500          # pixels brancos do título
    laranja = (np.abs(area_titulo.astype(int) - (255, 138, 0)).sum(axis=2) < 60).sum()
    assert laranja > 150                                          # a série e a faixa na cor da igreja


def test_capa_com_titulo_comprido_e_sem_video():
    titulo = "Culto de oração com um título comprido demais " * 4
    capa = desenhar_capa(None, 600, 900, titulo, "", "", "#7B61FF")
    assert capa.size == (600, 900)
    # Sem vídeo: o fundo escuro com o brilho da cor da igreja no canto de cima
    canto = np.asarray(capa.crop((420, 120, 540, 240)), dtype=int).mean(axis=(0, 1))
    assert canto[2] > canto[1] + 20                              # puxa para o violeta


def test_imagem_enviada_para_a_capa():
    with pytest.raises(ErroImagem):
        preparar_fundo_capa(b"isto nao e imagem")
    png = io.BytesIO()
    Image.new("RGBA", (3000, 1500), (255, 0, 0, 128)).save(png, format="PNG")
    jpeg = Image.open(io.BytesIO(preparar_fundo_capa(png.getvalue())))
    assert jpeg.format == "JPEG" and max(jpeg.size) == 1920 and jpeg.mode == "RGB"
