# -----------------------------------------------
# HolyCut — figuras sobre o vídeo (PNG da igreja ou ícone desenhado aqui)
# A imagem fica em org_<id>/projetos/<id>/figuras/<id>.png. O ícone não tem arquivo.
# -----------------------------------------------
import secrets

ICONES = ("cruz", "biblia", "chama", "estrela")
NOMES_ICONES = {"cruz": "Cruz", "biblia": "Bíblia", "chama": "Chama", "estrela": "Estrela"}
MAX_FIGURAS = 8
TAMANHO_PADRAO = 0.28


def nova_figura(icone: str | None, nome: str) -> dict:
    """Figura nova, no centro do quadro, pelo vídeo inteiro."""
    return {
        "id": secrets.token_hex(4),
        "nome": (nome or "Imagem")[:40],
        "icone": icone,
        "inicio": 0.0,
        "fim": None,
        "tamanho": TAMANHO_PADRAO,
        "opacidade": 1.0,
        "x": 0.5,
        "y": 0.42,
        "rotacao": 0.0,
    }


def pasta_figuras(organizacao_id, projeto_id) -> str:
    return f"org_{organizacao_id}/projetos/{projeto_id}/figuras"


def chave_figura(organizacao_id, projeto_id, figura_id) -> str:
    return f"{pasta_figuras(organizacao_id, projeto_id)}/{figura_id}.png"
