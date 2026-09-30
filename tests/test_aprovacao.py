# Aprovação pelo link: regras puras
from datetime import datetime, timedelta

import pytest

from core.config import TZ
from core.modelos.aprovacao import AJUSTES, APROVADO, PENDENTE, expirada, hash_do_token, montar_aprovacao, responder

MOMENTO = datetime(2026, 9, 30, 12, 0, tzinfo=TZ)


def test_montar_aprovacao():
    token, aprovacao = montar_aprovacao("u1", "  Pr.  João ", MOMENTO)
    assert len(token) >= 40 and aprovacao["token_hash"] == hash_do_token(token)
    assert token not in str(aprovacao)                        # o token não fica guardado
    assert (aprovacao["status"], aprovacao["para"]) == (PENDENTE, "Pr. João")
    assert aprovacao["expira_em"] == MOMENTO + timedelta(days=7)
    assert montar_aprovacao("u1")[0] != montar_aprovacao("u1")[0]


def test_expira_so_sem_resposta():
    _, aprovacao = montar_aprovacao("u1", momento=MOMENTO)
    assert not expirada(aprovacao, MOMENTO + timedelta(days=6))
    assert expirada(aprovacao, MOMENTO + timedelta(days=7))
    respondida = responder(aprovacao, APROVADO, "Pr. João", momento=MOMENTO + timedelta(days=1))
    assert not expirada(respondida, MOMENTO + timedelta(days=30))


def test_responder():
    _, aprovacao = montar_aprovacao("u1", momento=MOMENTO)
    with pytest.raises(ValueError, match="precisa mudar"):
        responder(aprovacao, AJUSTES, "Pr. João", "   ")
    with pytest.raises(ValueError):
        responder(aprovacao, "talvez", "Pr. João")
    ajustes = responder(aprovacao, AJUSTES, " Pr.  João ", "  Cortar o começo  ")
    assert (ajustes["status"], ajustes["respondido_por"]) == (AJUSTES, "Pr. João")
    assert ajustes["comentario"] == "Cortar o começo"
    assert responder(aprovacao, APROVADO, "Ana")["comentario"] is None
