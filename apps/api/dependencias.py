# -----------------------------------------------
# HolyCut API — dependências das rotas
# -----------------------------------------------
from datetime import timedelta

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends, HTTPException, Request, status

from api.seguranca import ler_token
from core.config import COOKIE_NOME
from core.modelos.chave_envio import PREFIXO_CHAVE, hash_da_chave
from core.utils.mongo import agora

# Registrar o último uso da chave a cada pedaço de 8 MB seria uma escrita por pedaço; basta de tempos em tempos
INTERVALO_REGISTRO_USO = timedelta(minutes=5)


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


async def usuario_ou_chave_envio(request: Request, db=Depends(obter_db)) -> dict:
    """
    Para as rotas de envio: aceita a sessão do navegador ou uma chave de envio no cabeçalho
    Authorization (o agente do OBS). Com a chave, age em nome de quem a criou.
    """
    autorizacao = request.headers.get("authorization", "")
    if not autorizacao.lower().startswith("bearer "):
        return await usuario_atual(request, db)
    chave = autorizacao[7:].strip()
    registro = await db.chaves_envio.find_one({"hash": hash_da_chave(chave), "revogada_em": None}) \
        if chave.startswith(PREFIXO_CHAVE) else None
    if registro is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Chave de envio inválida ou revogada. Crie outra no site.")
    usuario = await db.usuarios.find_one({"_id": registro["criado_por"]})
    if not usuario or not usuario.get("ativo", True) or usuario["organizacao_id"] != registro["organizacao_id"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Quem criou esta chave não tem mais acesso. Crie outra.")
    momento = agora()
    if registro.get("ultimo_uso_em") is None or momento - registro["ultimo_uso_em"] > INTERVALO_REGISTRO_USO:
        await db.chaves_envio.update_one({"_id": registro["_id"]}, {"$set": {"ultimo_uso_em": momento}})
    return {**usuario, "chave_envio": registro}
