# -----------------------------------------------
# HolyCut — sons curtos sintetizados aqui
# Não há amostra de terceiro: o sopro e o toque saem de fórmulas, então a licença é a do HolyCut.
# -----------------------------------------------
import io
import math
import struct
import wave

from core.utils.render import TAXA_AUDIO

DURACAO = {"sopro": 0.45, "toque": 0.28}


def _sopro(i: int, _n: int) -> float:
    t = i / TAXA_AUDIO
    envelope = math.sin(math.pi * min(t / 0.45, 1)) ** 2
    ruido = math.sin(i * 12.9898) * 43758.5453
    ruido = ruido - math.floor(ruido)
    return (ruido * 2 - 1) * 0.35 * envelope


def _toque(i: int, _n: int) -> float:
    t = i / TAXA_AUDIO
    return math.sin(2 * math.pi * 880 * t) * math.exp(-t * 14) * 0.5


def sintetizar(tipo: str) -> bytes:
    """WAV estéreo em 48 kHz. Tipo desconhecido devolve o toque."""
    formula = _sopro if tipo == "sopro" else _toque
    segundos = DURACAO.get(tipo, DURACAO["toque"])
    n = int(TAXA_AUDIO * segundos)
    memoria = io.BytesIO()
    with wave.open(memoria, "wb") as arquivo:
        arquivo.setnchannels(2)
        arquivo.setsampwidth(2)
        arquivo.setframerate(TAXA_AUDIO)
        quadros = bytearray()
        for i in range(n):
            amostra = max(min(int(formula(i, n) * 32767), 32767), -32768)
            quadros += struct.pack("<hh", amostra, amostra)
        arquivo.writeframes(quadros)
    return memoria.getvalue()
