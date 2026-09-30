# -----------------------------------------------
# HolyCut API — cadastro, login e sessão
# -----------------------------------------------
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pymongo.errors import DuplicateKeyError
from starlette.concurrency import run_in_threadpool

from api.dependencias import obter_db, usuario_atual
from api.esquemas import (
    CadastroEntrada,
    EntrarEntrada,
    OrganizacaoSaida,
    SessaoSaida,
    UsuarioSaida,
)
from api.seguranca import (
    HASH_FALSO,
    LimitadorTentativas,
    criar_token,
    gerar_hash_senha,
    gerar_slug,
    ip_do_cliente,
    precisa_novo_hash,
    verificar_senha,
)
from core.config import COOKIE_NOME, COOKIE_SEGURO, SESSAO_DIAS
from core.modelos.identidade import identidade_padrao
from core.utils.mongo import agora

router = APIRouter(prefix="/api/auth", tags=["auth"])
limitador = LimitadorTentativas()
MAX_TENTATIVAS_SLUG = 20


# -----------------------------------------------
# FUNÇÕES AUXILIARES
# -----------------------------------------------
def definir_cookie(resposta: Response, token: str):
    resposta.set_cookie(
        COOKIE_NOME, token,
        max_age=SESSAO_DIAS * 24 * 3600,
        httponly=True, secure=COOKIE_SEGURO, samesite="lax", path="/",
    )


async def montar_sessao(db, usuario: dict) -> SessaoSaida:
    organizacao = await db.organizacoes.find_one({"_id": usuario["organizacao_id"]})
    if organizacao is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Organização não encontrada. Entre de novo.")
    return SessaoSaida(
        usuario=UsuarioSaida(id=str(usuario["_id"]), nome=usuario["nome"], email=usuario["email"],
                             papel=usuario["papel"]),
        organizacao=OrganizacaoSaida(id=str(organizacao["_id"]), nome=organizacao["nome"],
                                     slug=organizacao["slug"]),
    )


async def criar_organizacao(db, nome: str):
    """Insere a organização com um slug único. Retorna (_id, slug)."""
    base = gerar_slug(nome)
    momento = agora()
    for tentativa in range(MAX_TENTATIVAS_SLUG):
        slug = base if tentativa == 0 else f"{base}-{tentativa + 1}"
        if await db.organizacoes.find_one({"slug": slug}, {"_id": 1}):
            continue
        try:
            resultado = await db.organizacoes.insert_one({
                "nome": nome, "slug": slug, "plano": "piloto", "identidade": identidade_padrao(nome),
                "criado_em": momento, "atualizado_em": momento,
            })
            return resultado.inserted_id, slug
        except DuplicateKeyError:
            continue
    raise HTTPException(status.HTTP_409_CONFLICT, "Não foi possível criar a organização. Tente outro nome.")


# -----------------------------------------------
# ROTAS
# -----------------------------------------------
@router.post("/cadastro", response_model=SessaoSaida, status_code=status.HTTP_201_CREATED)
async def cadastrar(dados: CadastroEntrada, resposta: Response, db=Depends(obter_db)):
    email = dados.email.lower().strip()
    if await db.usuarios.find_one({"email": email}, {"_id": 1}):
        raise HTTPException(status.HTTP_409_CONFLICT, "Este e-mail já tem cadastro. Entre com sua senha.")

    organizacao_id, slug = await criar_organizacao(db, dados.nome_igreja)
    momento = agora()
    usuario = {
        "nome": dados.nome,
        "email": email,
        "senha_hash": await run_in_threadpool(gerar_hash_senha, dados.senha),
        "organizacao_id": organizacao_id,
        "papel": "dono",
        "ativo": True,
        "criado_em": momento,
        "ultimo_acesso_em": momento,
    }
    try:
        usuario["_id"] = (await db.usuarios.insert_one(usuario)).inserted_id
    except DuplicateKeyError as e:
        await db.organizacoes.delete_one({"_id": organizacao_id})
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Este e-mail já tem cadastro. Entre com sua senha.") from e

    definir_cookie(resposta, criar_token(str(usuario["_id"]), str(organizacao_id)))
    logging.info(f"[{slug}] Nova organização cadastrada.")
    return await montar_sessao(db, usuario)


@router.post("/entrar", response_model=SessaoSaida)
async def entrar(dados: EntrarEntrada, request: Request, resposta: Response, db=Depends(obter_db)):
    email = dados.email.lower().strip()
    chave = f"{ip_do_cliente(request)}|{email}"
    if limitador.bloqueado(chave):
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            "Muitas tentativas. Aguarde alguns minutos e tente de novo.")

    usuario = await db.usuarios.find_one({"email": email})
    hash_salvo = usuario["senha_hash"] if usuario else HASH_FALSO
    senha_correta = await run_in_threadpool(verificar_senha, hash_salvo, dados.senha)
    if not usuario or not senha_correta or not usuario.get("ativo", True):
        limitador.registrar_falha(chave)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "E-mail ou senha incorretos.")

    limitador.limpar(chave)
    atualizacao = {"ultimo_acesso_em": agora()}
    if precisa_novo_hash(usuario["senha_hash"]):
        atualizacao["senha_hash"] = await run_in_threadpool(gerar_hash_senha, dados.senha)
    await db.usuarios.update_one({"_id": usuario["_id"]}, {"$set": atualizacao})

    definir_cookie(resposta, criar_token(str(usuario["_id"]), str(usuario["organizacao_id"])))
    return await montar_sessao(db, usuario)


@router.post("/sair", status_code=status.HTTP_204_NO_CONTENT)
async def sair(resposta: Response):
    resposta.delete_cookie(COOKIE_NOME, path="/", httponly=True, secure=COOKIE_SEGURO, samesite="lax")


@router.get("/eu", response_model=SessaoSaida)
async def eu(usuario=Depends(usuario_atual), db=Depends(obter_db)):
    return await montar_sessao(db, usuario)
