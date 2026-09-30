# Os filtros de cor do FFmpeg batem com a conta da prévia? FFmpeg de verdade; pulado sem FFmpeg.
import shutil
import subprocess

import numpy as np
import pytest
from PIL import Image

from core.utils.cores import IDS_FILTROS, filtro_ffmpeg
from tests.test_cores import aplicar

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg não instalado")


@pytest.fixture(scope="module")
def paleta(tmp_path_factory):
    """Uma imagem com muitas cores: gradiente de matiz na horizontal e de brilho na vertical."""
    x = np.linspace(0, 1, 256)[None, :, None]
    y = np.linspace(0.1, 1, 128)[:, None, None]
    fases = np.array([0, 2 / 3, 4 / 3]) * np.pi
    rgb = ((np.sin(2 * np.pi * x + fases) + 1) / 2 * y * 255).round().astype(np.uint8)
    caminho = tmp_path_factory.mktemp("cores") / "paleta.png"
    Image.fromarray(rgb, "RGB").save(caminho)
    return caminho, rgb


@pytest.mark.parametrize("filtro", [f for f in IDS_FILTROS if f != "natural"])
@pytest.mark.parametrize("intensidade", [1.0, 0.5])
def test_ffmpeg_igual_a_previa(paleta, tmp_path, filtro, intensidade):
    caminho, rgb = paleta
    saida = tmp_path / "saida.png"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(caminho),
                    "-vf", f"format=gbrp,{filtro_ffmpeg(filtro, intensidade)},format=rgb24", str(saida)],
                   check=True, timeout=60)
    do_ffmpeg = np.asarray(Image.open(saida).convert("RGB")).astype(int)
    esperado = aplicar(rgb.reshape(-1, 3), filtro, intensidade).reshape(rgb.shape)
    diferenca = np.abs(do_ffmpeg - esperado)
    assert diferenca.mean() < 1.0, f"{filtro}: diferença média {diferenca.mean():.2f}"
    assert diferenca.max() <= 4
