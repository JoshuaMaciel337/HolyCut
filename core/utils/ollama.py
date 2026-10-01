# -----------------------------------------------
# HolyCut — cliente do Ollama com saída em JSON
# O modelo é descarregado no fim (keep_alive 0) para a GPU ficar livre.
# -----------------------------------------------
import json
import logging
from urllib import error, request

from core.config import OLLAMA_MODELO, OLLAMA_URL

TEMPO_LIMITE_SEGUNDOS = 180


class ErroOllama(RuntimeError):
    pass


def completar_json(sistema: str, usuario: str, esquema: dict, descarregar: bool = False,
                   imagens: list[str] | None = None) -> dict:
    """Uma resposta. O esquema é o JSON Schema que o Ollama precisa seguir."""
    mensagem = {"role": "user", "content": usuario}
    if imagens:
        mensagem["images"] = imagens
    corpo = {
        "model": OLLAMA_MODELO,
        "stream": False,
        "format": esquema,
        "keep_alive": 0 if descarregar else "10m",
        "think": False,
        "messages": [
            {"role": "system", "content": sistema},
            mensagem,
        ],
        "options": {"temperature": 0.2},
    }
    try:
        return _pedir(corpo)
    except ErroOllama as erro:
        if "think" not in str(erro):
            raise
        corpo.pop("think", None)
        return _pedir(corpo)


def _pedir(corpo: dict) -> dict:
    dados = json.dumps(corpo).encode()
    pedido = request.Request(
        f"{OLLAMA_URL.rstrip('/')}/api/chat",
        data=dados,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(pedido, timeout=TEMPO_LIMITE_SEGUNDOS) as resposta:
            bruto = json.loads(resposta.read().decode())
    except error.HTTPError as erro:
        detalhe = erro.read().decode(errors="replace")[:300]
        raise ErroOllama(f"Ollama respondeu {erro.code}: {detalhe}") from erro
    except (error.URLError, TimeoutError, json.JSONDecodeError) as erro:
        raise ErroOllama(f"Não foi possível falar com o Ollama: {erro}") from erro
    texto = ((bruto.get("message") or {}).get("content") or "").strip()
    try:
        return json.loads(texto)
    except json.JSONDecodeError as erro:
        logging.warning("Ollama devolveu texto que não é JSON: %s", texto[:200])
        raise ErroOllama("O modelo não devolveu JSON.") from erro
