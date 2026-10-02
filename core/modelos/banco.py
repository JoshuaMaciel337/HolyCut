# -----------------------------------------------
# HolyCut — a frase dita vira uma busca visual na Pixabay
# A consulta é de imagem (lugar, objeto, gente). Não é um texto novo da pregação.
# -----------------------------------------------
from core.config import MODO_IA
from core.utils.ollama import ErroOllama, completar_json

SISTEMA = (
    "Você escolhe uma busca curta de foto ou vídeo para ilustrar uma frase dita num culto. "
    "Use só palavras visuais: lugar, objeto, pessoa, natureza ou gesto. "
    "Não repita a frase, não escreva ensinamento e não invente citação. "
    "Se a frase não sugere uma imagem, devolva usar=false e consulta vazia. "
    "A consulta tem no máximo seis palavras, em português."
)
ESQUEMA = {
    "type": "object",
    "properties": {
        "usar": {"type": "boolean"},
        "consulta": {"type": "string"},
        "tipo": {"type": "string", "enum": ["imagem", "video"]},
    },
    "required": ["usar", "consulta", "tipo"],
}


def _limpa(texto: str, limite: int) -> str:
    return " ".join(texto.split())[:limite]


def consulta_da_frase(frase: str) -> dict:
    """
    {usar, consulta, tipo}. Sem o modelo, a busca é a própria frase.
    Se o modelo falhar, a frase também serve, para a busca não parar.
    """
    frase = _limpa(frase, 240)
    if len(frase) < 2:
        return {"usar": False, "consulta": "", "tipo": "imagem"}
    if MODO_IA != "real":
        return {"usar": True, "consulta": _limpa(frase, 80), "tipo": "imagem"}
    try:
        resposta = completar_json(SISTEMA, frase, ESQUEMA, descarregar=True)
    except ErroOllama:
        return {"usar": True, "consulta": _limpa(frase, 80), "tipo": "imagem"}
    consulta = _limpa(str(resposta.get("consulta") or ""), 100)
    tipo = resposta.get("tipo") if resposta.get("tipo") in ("imagem", "video") else "imagem"
    if not resposta.get("usar") or len(consulta) < 2:
        return {"usar": False, "consulta": "", "tipo": "imagem"}
    return {"usar": True, "consulta": consulta, "tipo": tipo}


def credito(autor: str) -> str:
    nome = autor.strip() or "Pixabay"
    return f"{nome} · Pixabay"[:120]


MAX_APOIOS = 4


def pasta_apoios(organizacao_id, projeto_id) -> str:
    return f"org_{organizacao_id}/projetos/{projeto_id}/apoios"


def chave_apoio(organizacao_id, projeto_id, apoio_id) -> str:
    return f"{pasta_apoios(organizacao_id, projeto_id)}/{apoio_id}.mp4"
