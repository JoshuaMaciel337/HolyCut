# -----------------------------------------------
# HolyCut — o que a pessoa muda na fala, sem alterar a transcrição
#
# Corrigir uma palavra só troca o texto da legenda. Apagar uma palavra, ou
# um vício de fala na intensidade escolhida, tira aquele instante do vídeo.
# A transcrição original continua no banco. O projeto guarda só a diferença.
# -----------------------------------------------
import re

ID_PALAVRA = re.compile(r"^w\d{1,8}$")
MAXIMO_ALTERACOES = 4000
MAXIMO_LETRAS = 40
FOLGA_ENTRE_CORTES = 0.08   # dois cortes quase juntos viram um só, para não sobrar um fiapo de áudio
VICIOS = ("leve", "media", "forte")
_ORDEM = {"leve": 1, "media": 2, "forte": 3}

# Do mais contido ao mais agressivo. "é", "amém" e "Jesus" não entram:
# são fala de verdade, e a intensidade forte já alcança "então", "assim" e "aí".
_LEVES = {"né", "ne", "hum", "hm", "hmm", "aham", "uhum", "ah", "uh", "eh", "hã", "ã", "éh"}
_MEDIOS = _LEVES | {"tipo", "sabe", "entendeu", "tá", "ta", "ok", "okay"}
_FORTES = _MEDIOS | {"então", "entao", "assim", "aí", "ai"}


def normalizar_palavra(texto: str) -> str:
    """Minúsculas, sem pontuação. 'Né,' e 'né' são o mesmo vício."""
    return re.sub(r"[^\w]", "", (texto or "").lower(), flags=re.UNICODE)


def nivel_do_vicio(texto: str) -> str | None:
    """A intensidade mais baixa que já tira esta palavra, ou None se ela fica."""
    normal = normalizar_palavra(texto)
    if not normal:
        return None
    if normal in _LEVES:
        return "leve"
    if normal in _MEDIOS:
        return "media"
    if normal in _FORTES:
        return "forte"
    return None


def _texto_limpo(texto: str) -> str:
    return " ".join(str(texto).split())


def ids_validos(valor) -> list[str]:
    """Ids de palavra que dá para guardar. O que não tem cara de id é ignorado."""
    if not isinstance(valor, list):
        return []
    ids = []
    for item in valor[:MAXIMO_ALTERACOES]:
        texto = str(item)
        if ID_PALAVRA.fullmatch(texto) and texto not in ids:
            ids.append(texto)
    return ids


def edicoes_validas(valor) -> dict[str, str]:
    """Correções que dá para guardar. Texto vazio ou id estranho ficam de fora."""
    if not isinstance(valor, dict):
        return {}
    limpas = {}
    for chave, texto in list(valor.items())[:MAXIMO_ALTERACOES]:
        if not ID_PALAVRA.fullmatch(str(chave)):
            continue
        escrito = _texto_limpo(texto)
        if escrito and len(escrito) <= MAXIMO_LETRAS:
            limpas[str(chave)] = escrito
    return limpas


def conferir_edicoes(valor: dict) -> dict[str, str]:
    """A mesma limpeza, mas recusa o que a tela não deveria ter enviado."""
    if len(valor) > MAXIMO_ALTERACOES:
        raise ValueError("Há correções demais.")
    limpas = {}
    for chave, texto in valor.items():
        if not ID_PALAVRA.fullmatch(str(chave)):
            raise ValueError("Identificador de palavra inválido.")
        escrito = _texto_limpo(texto)
        if not escrito or len(escrito) > MAXIMO_LETRAS:
            raise ValueError("A correção precisa ter de 1 a 40 letras.")
        limpas[str(chave)] = escrito
    return limpas


def conferir_ids(valor: list) -> list[str]:
    if len(valor) > MAXIMO_ALTERACOES:
        raise ValueError("Há palavras demais nessa lista.")
    ids = []
    for item in valor:
        if not ID_PALAVRA.fullmatch(str(item)):
            raise ValueError("Identificador de palavra inválido.")
        if item not in ids:
            ids.append(str(item))
    return ids


def palavra_cortada(palavra: dict, legenda: dict) -> bool:
    """
    Sai do vídeo se a pessoa apagou, ou se é um vício da intensidade ligada
    e ela não devolveu nem corrigiu essa palavra. Corrigir muda a legenda e mantém o som.
    """
    identificador = str(palavra.get("id") or "")
    if identificador in set(legenda.get("apagadas") or []):
        return True
    if identificador in (legenda.get("edicoes") or {}):
        return False
    if identificador in set(legenda.get("mantidas") or []):
        return False
    escolha = legenda.get("vicios")
    nivel = nivel_do_vicio(palavra.get("texto") or "")
    if not escolha or not nivel or escolha not in _ORDEM:
        return False
    return _ORDEM[nivel] <= _ORDEM[escolha]


def texto_exibido(palavra: dict, legenda: dict) -> str:
    """O que a legenda escreve: a correção, se houver, senão a transcrição."""
    return (legenda.get("edicoes") or {}).get(palavra.get("id"), palavra.get("texto") or "")


def palavras_visiveis(palavras: list[dict], legenda: dict) -> list[dict]:
    """Palavras que continuam na legenda, já com o texto corrigido."""
    visiveis = []
    for palavra in palavras:
        if palavra_cortada(palavra, legenda):
            continue
        texto = texto_exibido(palavra, legenda).strip()
        if not texto:
            continue
        visiveis.append({**palavra, "texto": texto})
    return visiveis


def fundir_cortes(cortes: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Junta cortes que se encostam ou se sobrepõem. A ordem de entrada não importa."""
    ordenados = sorted((round(inicio, 2), round(fim, 2)) for inicio, fim in cortes if fim > inicio)
    if not ordenados:
        return []
    fundidos = [list(ordenados[0])]
    for inicio, fim in ordenados[1:]:
        if inicio <= fundidos[-1][1] + FOLGA_ENTRE_CORTES:
            fundidos[-1][1] = max(fundidos[-1][1], fim)
        else:
            fundidos.append([inicio, fim])
    return [(inicio, fim) for inicio, fim in fundidos]


def cortes_da_fala(palavras: list[dict], legenda: dict) -> list[tuple[float, float]]:
    """Intervalos da gravação que saem porque a palavra foi apagada ou é um vício."""
    brutos = [(palavra["inicio"], palavra["fim"]) for palavra in palavras if palavra_cortada(palavra, legenda)]
    return fundir_cortes(brutos)


def palavras_para_edicao(palavras: list[dict], partes: list[dict]) -> list[dict]:
    """Palavras que caem dentro de alguma parte, com o nível de vício, para o editor."""
    dentro = []
    for palavra in palavras:
        meio = (palavra["inicio"] + palavra["fim"]) / 2
        if not any(parte["inicio"] <= meio < parte["fim"] for parte in partes):
            continue
        dentro.append({
            "id": palavra["id"],
            "texto": palavra["texto"],
            "inicio": palavra["inicio"],
            "fim": palavra["fim"],
            "vicio": nivel_do_vicio(palavra["texto"]),
            "segmento": palavra.get("segmento") or "",
        })
    return dentro
