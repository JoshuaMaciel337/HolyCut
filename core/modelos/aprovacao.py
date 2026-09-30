# -----------------------------------------------
# HolyCut — aprovação de um vídeo exportado
#
# O editor manda um link (pelo WhatsApp, por exemplo) e o pastor ou líder
# assiste e aprova pelo celular, sem precisar de conta. O link leva um token
# aleatório; o banco guarda só o hash dele. Ele vale 7 dias e só mostra
# aquele vídeo. A aprovação fica dentro da própria exportação: um pedido
# de cada vez, e pedir de novo invalida o link anterior.
# Funções puras: montam e calculam, sem acessar o banco.
# -----------------------------------------------
import hashlib
import secrets
from datetime import datetime, timedelta

from core.config import TZ

DIAS_VALIDADE = 7
PENDENTE = "pendente"
APROVADO = "aprovado"
AJUSTES = "ajustes"          # pediu ajustes, com um comentário
DECISOES = (APROVADO, AJUSTES)


def hash_do_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def montar_aprovacao(pedido_por, para: str = "", momento: datetime | None = None) -> tuple[str, dict]:
    """(token para o link, registro que fica na exportação)."""
    momento = momento or datetime.now(TZ)
    token = secrets.token_urlsafe(32)
    return token, {
        "status": PENDENTE,
        "token_hash": hash_do_token(token),
        "para": " ".join(para.split())[:60],
        "pedido_por": pedido_por,
        "pedido_em": momento,
        "expira_em": momento + timedelta(days=DIAS_VALIDADE),
        "respondido_por": None,
        "comentario": None,
        "respondido_em": None,
    }


def expirada(aprovacao: dict, momento: datetime | None = None) -> bool:
    """Só um pedido ainda sem resposta expira. Uma resposta dada continua valendo."""
    return aprovacao["status"] == PENDENTE and (momento or datetime.now(TZ)) >= aprovacao["expira_em"]


def responder(aprovacao: dict, decisao: str, nome: str, comentario: str = "", momento: datetime | None = None) -> dict:
    if decisao not in DECISOES:
        raise ValueError("Decisão desconhecida.")
    comentario = comentario.strip()[:500]
    if decisao == AJUSTES and not comentario:
        raise ValueError("Escreva o que precisa mudar no vídeo.")
    return {**aprovacao, "status": decisao, "respondido_por": " ".join(nome.split())[:60],
            "comentario": comentario or None, "respondido_em": momento or datetime.now(TZ)}
