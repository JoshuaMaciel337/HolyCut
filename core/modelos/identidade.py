# -----------------------------------------------
# HolyCut — identidade da igreja (logo, cor e @) e como ela entra nos vídeos
# Funções puras: montam e validam, sem acessar o banco.
# -----------------------------------------------
import re

COR_PADRAO = "#FF8A00"  # laranja da marca HolyCut, até a igreja escolher a sua
POSICOES_LOGO = ("topo_esquerda", "topo_direita", "base_esquerda", "base_direita")
TAMANHO_LOGO_PADRAO = 0.16    # fração da largura do vídeo
OPACIDADE_LOGO_PADRAO = 0.9
ARQUIVO_LOGO = "logo.png"


def chave_logo(organizacao_id) -> str:
    return f"org_{organizacao_id}/identidade/{ARQUIVO_LOGO}"


def cor_valida(cor: str) -> bool:
    return bool(re.fullmatch(r"#[0-9A-Fa-f]{6}", cor or ""))


def normalizar_instagram(valor: str) -> str:
    """' @Igreja.Viva ' ou 'instagram.com/igreja.viva' → '@igreja.viva'."""
    valor = (valor or "").strip().lower()
    valor = re.sub(r"^(https?://)?(www\.)?instagram\.com/", "", valor).strip("/")
    valor = re.sub(r"[^a-z0-9._]", "", valor.lstrip("@"))[:30]
    return f"@{valor}" if valor else ""


def identidade_padrao(nome_igreja: str) -> dict:
    return {
        "nome_exibicao": nome_igreja,
        "instagram": "",
        "cor_destaque": COR_PADRAO,
        "logo": False,
        "estrategia": "",
    }


def marca_padrao(identidade: dict | None) -> dict:
    """Como o logo entra num projeto novo: ligado se a igreja já tem logo."""
    identidade = identidade or {}
    return {
        "logo": bool(identidade.get("logo")),
        "posicao": "topo_direita",
        "tamanho": TAMANHO_LOGO_PADRAO,
        "opacidade": OPACIDADE_LOGO_PADRAO,
    }
