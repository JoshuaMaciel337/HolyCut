# -----------------------------------------------
# HolyCut — pedaços da limpeza de áudio
# -----------------------------------------------
from core.utils.limpeza import fatias


def test_audio_curto_vira_um_pedaco():
    assert fatias(1000, 48000) == [(0, 1000)]
    assert fatias(0, 48000) == []


def test_pedacos_se_sobrepoem_meio_segundo():
    taxa = 48_000
    total = int(taxa * 45)
    pedacos = fatias(total, taxa)
    assert pedacos[0] == (0, int(taxa * 30))
    assert pedacos[1][0] == int(taxa * 29.5)
    assert pedacos[0][1] - pedacos[1][0] == int(taxa * 0.5)
    assert pedacos[-1][1] == total
    assert pedacos[-1][0] < pedacos[-1][1]
