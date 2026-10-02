# -----------------------------------------------
# HolyCut — título e legenda do post a partir do corte que ficou
# A frase guardada é a que foi dita. O que o modelo parafrasear é descartado.
# -----------------------------------------------
from core.config import MODO_IA
from core.modelos.sermon import _encontrar, _hashtags
from core.utils.ollama import ErroOllama, completar_json

SISTEMA = (
    "Você escolhe o título e a legenda de um post a partir da fala de um culto. "
    "titulo e legenda_post têm de ser uma sequência de palavras que aparece na fala, "
    "sem corrigir o português e sem resumir com palavras novas. "
    "hashtags só com palavras que foram ditas, sem o símbolo. "
    "Se não houver uma frase clara, devolva usar=false."
)
ESQUEMA = {
    "type": "object",
    "properties": {
        "usar": {"type": "boolean"},
        "titulo": {"type": "string"},
        "legenda_post": {"type": "string"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["usar", "titulo", "legenda_post", "hashtags"],
}


def _frase_inicial(palavras: list[dict]) -> str | None:
    texto = " ".join(palavra["texto"] for palavra in palavras[:12]).strip()
    return _encontrar(palavras, texto)


def textos_do_corte(palavras: list[dict]) -> dict | None:
    """
    {titulo, legenda, hashtags}. None quando não há uma frase dita para mostrar.
    Sem o modelo, o título é o começo da fala que ficou no corte.
    """
    if _frase_inicial(palavras) is None:
        return None
    if MODO_IA != "real":
        frase = _frase_inicial(palavras)
        return {"titulo": frase[:120], "legenda": frase[:500], "hashtags": []}
    fala = " ".join(palavra["texto"] for palavra in palavras)[:6000]
    try:
        resposta = completar_json(SISTEMA, fala, ESQUEMA, descarregar=True)
    except ErroOllama:
        frase = _frase_inicial(palavras)
        return {"titulo": frase[:120], "legenda": frase[:500], "hashtags": []}
    if not resposta.get("usar"):
        return None
    titulo = _encontrar(palavras, str(resposta.get("titulo") or ""))
    if titulo is None:
        return None
    legenda = _encontrar(palavras, str(resposta.get("legenda_post") or "")) or titulo
    return {
        "titulo": titulo[:120],
        "legenda": legenda[:500],
        "hashtags": _hashtags(resposta.get("hashtags"), palavras),
    }
