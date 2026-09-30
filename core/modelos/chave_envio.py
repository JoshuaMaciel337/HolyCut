# -----------------------------------------------
# HolyCut — chaves de envio
#
# O agente que roda no PC da mídia envia a gravação do OBS sozinho, sem
# ninguém logado no navegador. Ele se identifica com uma chave criada no
# site. A chave aparece uma vez só; o banco guarda apenas o hash dela.
# Uma chave só serve para enviar gravações, e pode ser revogada.
# Funções puras: montam e calculam, sem acessar o banco.
# -----------------------------------------------
import hashlib
import secrets
from datetime import datetime

from core.config import TZ

PREFIXO_CHAVE = "hc_"
LIMITE_CHAVES_ATIVAS = 10


def gerar_chave() -> str:
    return PREFIXO_CHAVE + secrets.token_urlsafe(32)


def hash_da_chave(chave: str) -> str:
    # A chave tem 256 bits aleatórios: um SHA-256 basta (não é senha escolhida por pessoa)
    return hashlib.sha256(chave.encode()).hexdigest()


def montar_chave_envio(organizacao_id, criado_por, nome: str, chave: str, momento: datetime | None = None) -> dict:
    momento = momento or datetime.now(TZ)
    return {
        "organizacao_id": organizacao_id,
        "criado_por": criado_por,
        "nome": " ".join(nome.split())[:60],
        "hash": hash_da_chave(chave),
        "inicio": chave[:len(PREFIXO_CHAVE) + 6],   # para a pessoa reconhecer a chave na lista
        "criado_em": momento,
        "ultimo_uso_em": None,
        "revogada_em": None,
    }
