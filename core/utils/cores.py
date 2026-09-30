# -----------------------------------------------
# HolyCut — filtros de cor
#
# Cada filtro é uma sequência de operações que existe igual no FFmpeg e no
# navegador, com a mesma matemática:
#   - "matriz": 3x3 sobre (R, G, B) entre 0 e 1. FFmpeg: colorchannelmixer.
#     Prévia: feColorMatrix de um filtro SVG com color-interpolation-filters="sRGB".
#   - "contraste": c*x + 0,5*(1 - c). FFmpeg: colorlevels. Prévia: feColorMatrix com deslocamento.
# Cada operação limita o resultado entre 0 e 1, nos dois lados.
# A intensidade (0 a 1) aproxima cada operação da identidade.
# As matrizes de saturação, sépia e cinza são as da especificação Filter Effects do CSS.
# -----------------------------------------------

IDENTIDADE = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


def _saturacao(s: float) -> list[list[float]]:
    return [
        [0.213 + 0.787 * s, 0.715 - 0.715 * s, 0.072 - 0.072 * s],
        [0.213 - 0.213 * s, 0.715 + 0.285 * s, 0.072 - 0.072 * s],
        [0.213 - 0.213 * s, 0.715 - 0.715 * s, 0.072 + 0.928 * s],
    ]


def _sepia(a: float) -> list[list[float]]:
    b = 1 - a
    return [
        [0.393 + 0.607 * b, 0.769 - 0.769 * b, 0.189 - 0.189 * b],
        [0.349 - 0.349 * b, 0.686 + 0.314 * b, 0.168 - 0.168 * b],
        [0.272 - 0.272 * b, 0.534 - 0.534 * b, 0.131 + 0.869 * b],
    ]


def _cinza(a: float) -> list[list[float]]:
    b = 1 - a
    return [
        [0.2126 + 0.7874 * b, 0.7152 - 0.7152 * b, 0.0722 - 0.0722 * b],
        [0.2126 - 0.2126 * b, 0.7152 + 0.2848 * b, 0.0722 - 0.0722 * b],
        [0.2126 - 0.2126 * b, 0.7152 - 0.7152 * b, 0.0722 + 0.9278 * b],
    ]


def _canais(r: float, g: float, b: float) -> list[list[float]]:
    """Ganho por canal: é o balanço de branco (mais vermelho = quente, mais azul = frio)."""
    return [[r, 0.0, 0.0], [0.0, g, 0.0], [0.0, 0.0, b]]


# (id, nome, operações na intensidade máxima)
FILTROS = [
    ("natural", "Natural", []),
    ("quente", "Quente", [("matriz", _canais(1.08, 1.0, 0.88)), ("matriz", _saturacao(1.1))]),
    ("frio", "Frio", [("matriz", _canais(0.92, 0.99, 1.1)), ("matriz", _saturacao(0.95)), ("contraste", 1.03)]),
    ("cinema", "Cinema", [("contraste", 1.18), ("matriz", _saturacao(0.82)), ("matriz", _sepia(0.12)),
                          ("matriz", _canais(0.97, 0.97, 0.97))]),
    ("pb", "P&B", [("matriz", _cinza(1.0)), ("contraste", 1.12)]),
    ("vivo", "Vivo", [("matriz", _saturacao(1.4)), ("contraste", 1.08)]),
]
IDS_FILTROS = [identificador for identificador, _, _ in FILTROS]


def operacoes(filtro: str, intensidade: float = 1.0) -> list[tuple[str, object]]:
    """Operações do filtro já com a intensidade aplicada. Filtro desconhecido: nenhuma."""
    intensidade = min(max(intensidade, 0.0), 1.0)
    base = next((ops for identificador, _, ops in FILTROS if identificador == filtro), [])
    resultado = []
    for tipo, valor in base:
        if tipo == "matriz":
            resultado.append((tipo, [[IDENTIDADE[i][j] + (valor[i][j] - IDENTIDADE[i][j]) * intensidade
                                      for j in range(3)] for i in range(3)]))
        else:
            resultado.append((tipo, 1 + (valor - 1) * intensidade))
    return resultado if intensidade > 0 else []


def filtro_ffmpeg(filtro: str, intensidade: float = 1.0) -> str:
    """Cadeia de filtros do FFmpeg para um quadro em gbrp. Vazia se não houver nada a fazer."""
    partes = []
    for tipo, valor in operacoes(filtro, intensidade):
        if tipo == "matriz":
            nomes = ("rr", "rg", "rb", "gr", "gg", "gb", "br", "bg", "bb")
            coeficientes = [coeficiente for linha in valor for coeficiente in linha]
            pares = zip(nomes, coeficientes, strict=True)
            partes.append("colorchannelmixer=" + ":".join(f"{nome}={c:.4f}" for nome, c in pares))
        else:
            c = valor
            if c >= 1:  # expande: pega uma faixa menor da entrada
                minimo, maximo = 0.5 - 0.5 / c, 0.5 + 0.5 / c
                partes.append("colorlevels=" + ":".join(f"{canal}imin={minimo:.4f}:{canal}imax={maximo:.4f}"
                                                        for canal in "rgb"))
            else:       # comprime: a saída ocupa uma faixa menor
                minimo, maximo = 0.5 - 0.5 * c, 0.5 + 0.5 * c
                partes.append("colorlevels=" + ":".join(f"{canal}omin={minimo:.4f}:{canal}omax={maximo:.4f}"
                                                        for canal in "rgb"))
    return ",".join(partes)
