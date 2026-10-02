# -----------------------------------------------
# HolyCut — o rosto vira o centro do recorte
# A prévia e o render usam o mesmo degrau: o valor vale até o próximo quadro.
# -----------------------------------------------

ZOOM_ENFASE = 1.25
# O contorno não mede o corpo: a trilha só guarda o centro do rosto.
# A caixa é esta fração da gravação, a mesma na prévia e no drawbox.
FRACAO_LARGURA_CONTORNO = 0.22
FRACAO_ALTURA_CONTORNO = 0.32
ESPESSURA_CONTORNO = 6


def suavizar(amostras: list[tuple[float, float, float]], alfa: float = 0.35,
             minimo: float = 0.03) -> list[dict]:
    """(tempo, x, y) normalizados. Descarta o quadro que quase não andou."""
    if not amostras:
        return []
    x = y = None
    quadros = []
    for tempo, bruto_x, bruto_y in amostras:
        bruto_x, bruto_y = min(max(bruto_x, 0.0), 1.0), min(max(bruto_y, 0.0), 1.0)
        x = bruto_x if x is None else x + alfa * (bruto_x - x)
        y = bruto_y if y is None else y + alfa * (bruto_y - y)
        ponto = {"t": round(float(tempo), 2), "x": round(x, 4), "y": round(y, 4), "zoom": 1.0}
        if not quadros or abs(ponto["x"] - quadros[-1]["x"]) >= minimo or abs(ponto["y"] - quadros[-1]["y"]) >= minimo:
            quadros.append(ponto)
    return quadros


def aplicar_enfases(quadros: list[dict], picos: list[tuple[float, float]], zoom: float = ZOOM_ENFASE) -> list[dict]:
    """Sobe o zoom nos picos de energia em que já há um rosto."""
    if not quadros or not picos:
        return quadros
    for quadro in quadros:
        if any(inicio <= quadro["t"] <= fim for inicio, fim in picos):
            quadro["zoom"] = zoom
    return quadros


def quadro_em(quadros: list[dict], tempo: float) -> dict | None:
    """O quadro vigente naquele instante da gravação."""
    vigente = None
    for quadro in quadros:
        if quadro["t"] <= tempo:
            vigente = quadro
        else:
            break
    return vigente


def instante_no_final(partes: list[tuple[float, float]], grupos: list[list[tuple[float, float]]],
                      tempo: float) -> float | None:
    """Tempo da gravação → tempo do vídeo final. None se o instante foi cortado."""
    saida = 0.0
    for (inicio_parte, _), trechos in zip(partes, grupos, strict=True):
        relativo = tempo - inicio_parte
        cursor = 0.0
        for começo, fim in trechos:
            if começo <= relativo < fim:
                return round(saida + cursor + (relativo - começo), 3)
            cursor += fim - começo
        saida += cursor
    return None


def caixa_contorno(x: float, y: float, recorte: dict, largura_saida: int, altura_saida: int,
                   largura_origem: int, altura_origem: int) -> tuple[int, int, int, int]:
    """Retângulo no vídeo final: o centro é o rosto e o tamanho é a fração da gravação."""
    centro_x = (x * largura_origem - recorte["x"]) / recorte["largura"] * largura_saida
    centro_y = (y * altura_origem - recorte["y"]) / recorte["altura"] * altura_saida
    largura = FRACAO_LARGURA_CONTORNO * largura_origem / recorte["largura"] * largura_saida
    altura = FRACAO_ALTURA_CONTORNO * altura_origem / recorte["altura"] * altura_saida
    largura = max(int(round(largura)), 2)
    altura = max(int(round(altura)), 2)
    largura -= largura % 2
    altura -= altura % 2
    return int(round(centro_x - largura / 2)), int(round(centro_y - altura / 2)), largura, altura


def comandos_de_contorno(caixas: list[tuple[float, int, int, int, int]]) -> str:
    """Arquivo do sendcmd. caixas são (tempo do vídeo final, x, y, largura, altura)."""
    linhas = []
    for tempo, x, y, largura, altura in caixas:
        linhas.append(f"{tempo:.3f} drawbox x {x}, drawbox y {y}, drawbox w {largura}, drawbox h {altura};")
    return "\n".join(linhas) + ("\n" if linhas else "")


def comandos_de_recorte(recortes: list[tuple[float, dict]]) -> str:
    """Arquivo do sendcmd. recortes são (tempo do vídeo final, recorte em pixels)."""
    linhas = []
    for tempo, recorte in recortes:
        linhas.append(
            f"{tempo:.3f} crop w {recorte['largura']}, crop h {recorte['altura']}, "
            f"crop x {recorte['x']}, crop y {recorte['y']};"
        )
    return "\n".join(linhas) + ("\n" if linhas else "")
