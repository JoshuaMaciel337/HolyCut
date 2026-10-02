# -----------------------------------------------
# HolyCut — efeitos do vídeo (brilho, luz, tremor, zoom, transição e som)
# Os números daqui são os mesmos da prévia e do FFmpeg.
# -----------------------------------------------

BRILHO_MAXIMO = 0.3
# Fração da largura do quadro que o tremor desloca, no máximo
AMPLITUDE_TREMOR = 0.012
FREQUENCIA_TREMOR_X = 7
FREQUENCIA_TREMOR_Y = 11
ZOOM_MAXIMO_EFEITO = 1.35
FADE_TRANSICAO = 0.2
SIGMA_TRANSICAO = 14
SIGMA_LUZ = 18
VOLUME_SOM = 0.35
SONS = ("nenhum", "sopro", "toque")
TRANSICOES = ("corte", "escurecer", "fusao", "desfoque")

EFEITOS_PADRAO = {
    "brilho": 0.0,
    "tremor": 0.0,
    "luz": 0.0,
    "contorno": False,
    "transicao": "corte",
    "zoom": None,
    "som": {"id": "nenhum", "inicio": 0.0},
}


def efeitos_do_projeto(config: dict | None) -> dict:
    """Completa o que o projeto antigo não tinha. Sem efeito, o filtro continua o de antes."""
    bruto = (config or {}).get("efeitos") or {}
    som = bruto.get("som") or {}
    zoom = bruto.get("zoom")
    return {
        "brilho": float(bruto.get("brilho") or 0),
        "tremor": float(bruto.get("tremor") or 0),
        "luz": float(bruto.get("luz") or 0),
        "contorno": bool(bruto.get("contorno")),
        "transicao": bruto.get("transicao") if bruto.get("transicao") in TRANSICOES else "corte",
        "zoom": zoom if isinstance(zoom, dict) else None,
        "som": {
            "id": som.get("id") if som.get("id") in SONS else "nenhum",
            "inicio": float(som.get("inicio") or 0),
        },
    }


def amplitude_tremor(largura: int, tremor: float) -> int:
    """Pixels pares. Zero quando o tremor está desligado."""
    if tremor <= 0:
        return 0
    amp = int(round(largura * AMPLITUDE_TREMOR * min(tremor, 1)))
    amp = max(amp, 2)
    return amp - amp % 2


def ganho_brilho(brilho: float) -> float:
    return 1 + max(min(brilho, BRILHO_MAXIMO), -BRILHO_MAXIMO)
