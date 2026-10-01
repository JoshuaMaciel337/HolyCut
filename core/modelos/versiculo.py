# -----------------------------------------------
# HolyCut — versículo citado na fala
# Só entra quando dá para ler livro, capítulo e versículo no que foi dito.
# O texto mostrado é a fala, não uma tradução da Bíblia.
# -----------------------------------------------
from core.modelos.sermon import token
from core.modelos.transcricao import LIVROS

_PALAVRAS = {
    "um": 1, "uma": 1, "dois": 2, "duas": 2, "tres": 3, "quatro": 4, "cinco": 5,
    "seis": 6, "sete": 7, "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12,
    "treze": 13, "catorze": 14, "quatorze": 14, "quinze": 15, "dezesseis": 16,
    "dezessete": 17, "dezoito": 18, "dezenove": 19, "vinte": 20, "trinta": 30,
    "quarenta": 40, "cinquenta": 50,
}
_LIVROS = {token(livro): livro for livro in LIVROS}
_ROTULOS = {"capitulo", "versiculo", "versiculos", "verso", "versos"}


def _numero(pedaço: str) -> int | None:
    if pedaço.isdigit():
        valor = int(pedaço)
        return valor if 1 <= valor <= 176 else None
    return _PALAVRAS.get(pedaço)


def detectar_versiculos(palavras: list[dict]) -> list[dict]:
    """Referências ditas em voz alta. Sem capítulo e versículo, omite."""
    tokens = [token(palavra["texto"]) for palavra in palavras]
    achados = []
    indice = 0
    while indice < len(tokens):
        livro = _LIVROS.get(tokens[indice])
        if livro is None:
            indice += 1
            continue
        capitulo = versiculo = None
        fim = indice
        for frente in range(indice + 1, min(indice + 8, len(tokens))):
            pedaço = tokens[frente]
            if pedaço in _ROTULOS or not pedaço:
                fim = frente
                continue
            valor = _numero(pedaço)
            if valor is None:
                break
            fim = frente
            if capitulo is None:
                capitulo = valor
            else:
                versiculo = valor
                break
        if capitulo is not None and versiculo is not None:
            citacao = " ".join(palavra["texto"] for palavra in palavras[indice:fim + 1])[:180]
            achados.append({
                "referencia": f"{livro} {capitulo}:{versiculo}",
                "inicio": round(float(palavras[indice]["inicio"]), 2),
                "fim": round(float(palavras[fim]["fim"]), 2),
                "citacao": citacao,
            })
            indice = fim + 1
        else:
            indice += 1
    unicos = []
    for item in achados:
        if unicos and unicos[-1]["referencia"] == item["referencia"] and item["inicio"] - unicos[-1]["fim"] < 8:
            continue
        unicos.append(item)
    return unicos
