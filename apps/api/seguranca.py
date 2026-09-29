# -----------------------------------------------
# HolyCut API — senhas, sessão e limite de tentativas
# -----------------------------------------------
import re
import threading
import time
import unicodedata
from collections import deque
from datetime import datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Request

from core.config import (
    JANELA_TENTATIVAS_MINUTOS,
    JWT_ALGORITMO,
    JWT_SEGREDO,
    MAX_TENTATIVAS_LOGIN,
    SESSAO_DIAS,
    TZ,
)

_hasher = PasswordHasher()
# Usado quando o e-mail não existe, para o tempo de resposta não revelar isso
HASH_FALSO = _hasher.hash("senha-que-nao-existe")


# -----------------------------------------------
# SENHAS
# -----------------------------------------------
def gerar_hash_senha(senha: str) -> str:
    return _hasher.hash(senha)


def verificar_senha(hash_salvo: str, senha: str) -> bool:
    try:
        return _hasher.verify(hash_salvo, senha)
    except (VerificationError, InvalidHashError):
        return False


def precisa_novo_hash(hash_salvo: str) -> bool:
    """True quando os parâmetros do argon2 mudaram e o hash deve ser refeito."""
    try:
        return _hasher.check_needs_rehash(hash_salvo)
    except InvalidHashError:
        return True


# -----------------------------------------------
# SESSÃO
# -----------------------------------------------
def criar_token(usuario_id: str, organizacao_id: str, momento: datetime | None = None) -> str:
    momento = momento or datetime.now(TZ)
    payload = {
        "sub": usuario_id,
        "org": organizacao_id,
        "iat": int(momento.timestamp()),
        "exp": int((momento + timedelta(days=SESSAO_DIAS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SEGREDO, algorithm=JWT_ALGORITMO)


def ler_token(token: str) -> dict | None:
    """Payload do token, ou None se inválido ou expirado."""
    try:
        return jwt.decode(token, JWT_SEGREDO, algorithms=[JWT_ALGORITMO], options={"require": ["sub", "exp"]})
    except jwt.PyJWTError:
        return None


# -----------------------------------------------
# LIMITE DE TENTATIVAS DE LOGIN
# Fica em memória: é zerado quando a API reinicia, o que basta para
# um único servidor. Com vários servidores, mover para o Mongo.
# -----------------------------------------------
class LimitadorTentativas:
    def __init__(self, maximo: int = MAX_TENTATIVAS_LOGIN, janela_minutos: int = JANELA_TENTATIVAS_MINUTOS):
        self.maximo = maximo
        self.janela = janela_minutos * 60
        self._falhas: dict[str, deque] = {}
        self._lock = threading.Lock()

    def _limpar_antigas(self, chave: str, instante: float) -> deque:
        falhas = self._falhas.setdefault(chave, deque())
        while falhas and instante - falhas[0] > self.janela:
            falhas.popleft()
        return falhas

    def bloqueado(self, chave: str) -> bool:
        with self._lock:
            return len(self._limpar_antigas(chave, time.monotonic())) >= self.maximo

    def registrar_falha(self, chave: str):
        with self._lock:
            instante = time.monotonic()
            self._limpar_antigas(chave, instante).append(instante)

    def limpar(self, chave: str):
        with self._lock:
            self._falhas.pop(chave, None)


# -----------------------------------------------
# UTILIDADES
# -----------------------------------------------
def gerar_slug(texto: str) -> str:
    """'Igreja Batista da Graça' → 'igreja-batista-da-graca'."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")
    return slug[:60].strip("-") or "igreja"


def ip_do_cliente(request: Request) -> str:
    """IP real do visitante. Atrás do túnel da Cloudflare ele vem no cabeçalho CF-Connecting-IP."""
    for cabecalho in ("cf-connecting-ip", "x-forwarded-for"):
        valor = request.headers.get(cabecalho)
        if valor:
            return valor.split(",")[0].strip()
    return request.client.host if request.client else "desconhecido"
