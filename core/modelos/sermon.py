# -----------------------------------------------
# HolyCut — cortes sugeridos a partir da fala real
#
# O modelo só propõe. O que não for uma frase dita na transcrição é descartado.
# O título guardado é o trecho da transcrição, não a paráfrase do modelo.
# -----------------------------------------------
import re
import unicodedata

MINIMO_CORTES = 1
MAXIMO_CORTES = 10
DURACAO_MINIMA = 8.0
DURACAO_MAXIMA = 90.0
PARTE_MINIMA = 3.0
MAXIMO_PARTES_CORTE = 4
MINIMO_PALAVRAS_TITULO = 3
MAXIMO_HASHTAGS = 6
JANELA_SEGUNDOS = 480.0
SOBREPOSICAO_JANELA = 60.0

MODELO_LLM = "gemma3:4b"


def _sem_acento(texto: str) -> str:
    base = unicodedata.normalize("NFD", (texto or "").lower())
    return "".join(letra for letra in base if unicodedata.category(letra) != "Mn")


def token(texto: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _sem_acento(texto))


def palavras_do_documento(transcricao: dict | None) -> list[dict]:
    palavras = []
    for segmento in (transcricao or {}).get("segmentos") or []:
        for palavra in segmento.get("palavras") or []:
            escrito = " ".join(str(palavra.get("texto") or "").split())
            if not escrito:
                continue
            try:
                inicio, fim = float(palavra["inicio"]), float(palavra["fim"])
            except (KeyError, TypeError, ValueError):
                continue
            palavras.append({"texto": escrito, "inicio": inicio, "fim": max(fim, inicio)})
    return palavras


def _encontrar(palavras: list[dict], frase: str) -> str | None:
    """Devolve a frase como está na transcrição, se as palavras batem em sequência."""
    alvo = [token(pedaço) for pedaço in frase.split()]
    alvo = [pedaço for pedaço in alvo if pedaço]
    if len(alvo) < MINIMO_PALAVRAS_TITULO:
        return None
    tokens = [token(palavra["texto"]) for palavra in palavras]
    limite = len(tokens) - len(alvo) + 1
    for inicio in range(max(limite, 0)):
        if tokens[inicio:inicio + len(alvo)] == alvo:
            return " ".join(palavra["texto"] for palavra in palavras[inicio:inicio + len(alvo)])
    return None


def _partes(bruto: dict, duracao: float) -> list[tuple[float, float]]:
    origem = bruto.get("partes")
    if not isinstance(origem, list) or not origem:
        origem = [{"inicio": bruto.get("inicio"), "fim": bruto.get("fim")}]
    partes = []
    for item in origem[:MAXIMO_PARTES_CORTE]:
        if not isinstance(item, dict):
            continue
        try:
            inicio, fim = float(item["inicio"]), float(item["fim"])
        except (KeyError, TypeError, ValueError):
            continue
        inicio, fim = max(0.0, inicio), min(fim, duracao)
        if fim - inicio >= PARTE_MINIMA:
            partes.append((round(inicio, 2), round(fim, 2)))
    partes.sort()
    fundidas: list[tuple[float, float]] = []
    for inicio, fim in partes:
        if fundidas and inicio - fundidas[-1][1] <= 0.4:
            fundidas[-1] = (fundidas[-1][0], max(fundidas[-1][1], fim))
        else:
            fundidas.append((inicio, fim))
    total = sum(fim - inicio for inicio, fim in fundidas)
    if not fundidas or total < DURACAO_MINIMA or total > DURACAO_MAXIMA:
        return []
    return fundidas


def _hashtags(brutas, palavras: list[dict]) -> list[str]:
    conhecidas = {token(palavra["texto"]) for palavra in palavras}
    saida = []
    for item in brutas or []:
        limpo = token(str(item).lstrip("#"))
        if len(limpo) < 4 or limpo not in conhecidas or f"#{limpo}" in saida:
            continue
        saida.append(f"#{limpo}")
        if len(saida) == MAXIMO_HASHTAGS:
            break
    return saida


def _nota(valor) -> float | None:
    try:
        nota = float(valor)
    except (TypeError, ValueError):
        return None
    if nota < 0 or nota > 10:
        return None
    return round(nota, 1)


def validar_cortes(brutos, palavras: list[dict], duracao: float) -> list[dict]:
    """Fica só o corte cujo título é uma frase dita. O resto é omitido."""
    if not isinstance(brutos, list):
        return []
    cortes = []
    for bruto in brutos:
        if not isinstance(bruto, dict):
            continue
        titulo = _encontrar(palavras, str(bruto.get("titulo") or ""))
        partes = _partes(bruto, duracao)
        nota = _nota(bruto.get("nota"))
        if titulo is None or not partes or nota is None:
            continue
        legenda = _encontrar(palavras, str(bruto.get("legenda_post") or "")) or titulo
        motivo = " ".join(str(bruto.get("motivo") or "").split())[:240] or "Trecho escolhido da pregação."
        cortes.append({
            "titulo": titulo[:120],
            "motivo": motivo,
            "nota": nota,
            "partes": [{"inicio": inicio, "fim": fim} for inicio, fim in partes],
            "legenda_post": legenda[:500],
            "hashtags": _hashtags(bruto.get("hashtags"), palavras),
        })
    cortes.sort(key=lambda corte: corte["nota"], reverse=True)
    vistos = set()
    unicos = []
    for corte in cortes:
        chave = tuple((parte["inicio"], parte["fim"]) for parte in corte["partes"])
        if chave in vistos:
            continue
        vistos.add(chave)
        corte["id"] = f"c{len(unicos) + 1:02d}"
        unicos.append(corte)
        if len(unicos) == MAXIMO_CORTES:
            break
    return unicos


def janelas(palavras: list[dict], segundos: float = JANELA_SEGUNDOS,
            sobreposicao: float = SOBREPOSICAO_JANELA) -> list[list[dict]]:
    """Pedaços da pregação para o modelo caber no contexto. A fala não é resumida."""
    if not palavras:
        return []
    passo = max(segundos - sobreposicao, 30.0)
    inicio = palavras[0]["inicio"]
    fim_total = palavras[-1]["fim"]
    grupos = []
    while inicio < fim_total:
        fim = inicio + segundos
        grupo = [palavra for palavra in palavras if palavra["inicio"] < fim and palavra["fim"] > inicio]
        if grupo:
            grupos.append(grupo)
        if fim >= fim_total:
            break
        inicio += passo
    return grupos


def texto_para_o_modelo(palavras: list[dict]) -> str:
    """Uma linha por frase curta, com o tempo de início. É a fala, sem correção."""
    linhas = []
    bloco: list[dict] = []
    for palavra in palavras:
        bloco.append(palavra)
        if len(bloco) >= 14:
            linhas.append(f"[{bloco[0]['inicio']:.1f}] " + " ".join(item["texto"] for item in bloco))
            bloco = []
    if bloco:
        linhas.append(f"[{bloco[0]['inicio']:.1f}] " + " ".join(item["texto"] for item in bloco))
    return "\n".join(linhas)


ESQUEMA_CORTES = {
    "type": "object",
    "properties": {
        "cortes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "titulo": {"type": "string"},
                    "motivo": {"type": "string"},
                    "nota": {"type": "number"},
                    "inicio": {"type": "number"},
                    "fim": {"type": "number"},
                    "partes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"inicio": {"type": "number"}, "fim": {"type": "number"}},
                            "required": ["inicio", "fim"],
                        },
                    },
                    "legenda_post": {"type": "string"},
                    "hashtags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["titulo", "motivo", "nota", "inicio", "fim"],
            },
        },
    },
    "required": ["cortes"],
}


def prompt_do_corte(estrategia: str) -> str:
    extra = f" Estratégia da igreja: {estrategia.strip()[:400]}." if estrategia and estrategia.strip() else ""
    return (
        "Você escolhe cortes de uma pregação já transcrita. "
        "O título e a legenda do post têm de ser frases copiadas da transcrição, palavra por palavra. "
        "Não corrija o português, não resumir com palavras suas e não invente versículo. "
        "Cada corte dura entre 8 e 90 segundos. A nota vai de 0 a 10. "
        "As hashtags só usam palavras que aparecem na fala. "
        "Devolva de 2 a 4 cortes deste trecho."
        + extra
    )
