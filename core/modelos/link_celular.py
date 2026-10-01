# -----------------------------------------------
# HolyCut — link para baixar um vídeo exportado no celular (pelo QR code)
#
# O celular não tem a sessão do computador, então o QR leva um link com um
# token aleatório que vale 24 horas e só baixa aquele vídeo. O banco guarda
# só o hash, como no link de aprovação. Gerar outro invalida o anterior.
# Funções puras: montam e conferem, sem acessar o banco.
# -----------------------------------------------
import secrets
from datetime import datetime, timedelta

from core.config import TZ
from core.modelos.aprovacao import hash_do_token

HORAS_VALIDADE = 24


def montar_link_celular(momento: datetime | None = None) -> tuple[str, dict]:
    """(token que vai no QR, registro que fica na exportação)."""
    momento = momento or datetime.now(TZ)
    token = secrets.token_urlsafe(32)
    return token, {"token_hash": hash_do_token(token), "criado_em": momento,
                   "expira_em": momento + timedelta(hours=HORAS_VALIDADE)}


def link_vencido(link: dict | None, momento: datetime | None = None) -> bool:
    return not link or (momento or datetime.now(TZ)) >= link["expira_em"]


def instante_da_capa(instante: float, duracao: float) -> float:
    """O quadro pedido, dentro do vídeo: o último quadro inteiro fica a 0,1 s do fim."""
    return round(min(max(float(instante), 0.0), max(float(duracao) - 0.1, 0.0)), 2)
