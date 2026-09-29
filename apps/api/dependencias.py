# -----------------------------------------------
# HolyCut API — dependências das rotas
# -----------------------------------------------
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends, HTTPException, Request, status

from api.seguranca import ler_token
from core.config import COOKIE_NOME


def obter_db(request: Request):
    return request.app.state.db


async def usuario_atual(request: Request, db=Depends(obter_db)) -> dict:
    """Usuário dono do cookie de sessão. Responde 401 se não houver sessão válida."""
    token = request.cookies.get(COOKIE_NOME)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Faça login para continuar.")
    dados = ler_token(token)
    if dados is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sua sessão expirou. Entre de novo.")
    try:
        usuario_id = ObjectId(dados["sub"])
    except (InvalidId, TypeError) as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão inválida. Entre de novo.") from e

    usuario = await db.usuarios.find_one({"_id": usuario_id})
    if not usuario or not usuario.get("ativo", True):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessão inválida. Entre de novo.")
    return usuario
