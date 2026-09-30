# Detecção de silêncios sobre os níveis de 10 ms
import numpy as np

from core.utils.silencios import INTENSIDADES, detectar_silencios, tempo_cortado, trechos_mantidos

FALA, SILENCIO, RUIDO_DA_NAVE = -12, -90, -38


def niveis(*partes: tuple[int, float]) -> np.ndarray:
    """niveis((FALA, 2.0), (SILENCIO, 1.0)) → 2 s de fala e 1 s de silêncio, a 100 quadros por segundo."""
    return np.concatenate([np.full(round(segundos * 100), db, dtype=np.int8) for db, segundos in partes])


def test_corta_silencio_com_margem_para_a_fala():
    audio = niveis((FALA, 2.0), (SILENCIO, 1.0), (FALA, 2.0))
    assert detectar_silencios(audio, limiar_db=-35, duracao_minima=0.6, margem=0.12) == [(2.12, 2.88)]


def test_pausa_curta_nao_e_cortada():
    audio = niveis((FALA, 2.0), (SILENCIO, 0.4), (FALA, 2.0))
    assert detectar_silencios(audio, limiar_db=-35, duracao_minima=0.6) == []


def test_silencio_no_comeco_e_no_fim_sai_inteiro():
    audio = niveis((SILENCIO, 1.5), (FALA, 3.0), (SILENCIO, 2.0))
    assert detectar_silencios(audio, limiar_db=-35, duracao_minima=0.6, margem=0.12) == [(0.0, 1.38), (4.62, 6.5)]


def test_intensidade_decide_o_que_e_silencio():
    # Ar-condicionado da nave a -38 dB: só a intensidade leve (-40 dB) não corta
    audio = niveis((FALA, 2.0), (RUIDO_DA_NAVE, 1.5), (FALA, 2.0))
    assert detectar_silencios(audio, **INTENSIDADES["leve"]) == []
    assert detectar_silencios(audio, **INTENSIDADES["media"]) == [(2.12, 3.38)]
    assert detectar_silencios(audio, **INTENSIDADES["forte"]) == [(2.12, 3.38)]


def test_trechos_mantidos_e_tempo_cortado():
    cortes = [(0.0, 1.38), (4.62, 6.5)]
    assert trechos_mantidos(6.5, cortes) == [(1.38, 4.62)]
    assert trechos_mantidos(10.0, [(2.0, 3.0), (5.0, 6.0)]) == [(0.0, 2.0), (3.0, 5.0), (6.0, 10.0)]
    assert trechos_mantidos(5.0, []) == [(0.0, 5.0)]
    assert tempo_cortado(cortes) == 3.26


def test_audio_vazio():
    assert detectar_silencios(np.array([], dtype=np.int8), limiar_db=-35, duracao_minima=0.6) == []
