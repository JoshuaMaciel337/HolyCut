# -----------------------------------------------
# HolyCut API
#
#   uvicorn api.main:app --reload     (com "apps" e a raiz no PYTHONPATH)
#
# Documentação interativa em /api/docs
# -----------------------------------------------
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from api.rotas import auth, eventos, exportacoes, identidade, jobs, midias, modelos, projetos, sistema, uploads
from core.config import COOKIE_SEGURO, DATABASE_NAME, JWT_SEGREDO, VERSAO
from core.utils.mongo import conectar, criar_cliente_async, criar_indices

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)

ROTULOS_CAMPOS = {
    "nome_igreja": "Nome da igreja",
    "nome": "Seu nome",
    "email": "E-mail",
    "senha": "Senha",
    "tipo": "Tipo",
    "duracao": "Duração",
}


# -----------------------------------------------
# INICIALIZAÇÃO
# -----------------------------------------------
def preparar_banco():
    """Cria os índices com o cliente síncrono do core, uma vez na subida."""
    db = conectar()
    if db is None:
        logging.error("MongoDB indisponível na subida da API. As rotas vão responder erro até ele voltar.")
        return
    criar_indices(db)
    db.client.close()


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    if JWT_SEGREDO.startswith("dev-") and COOKIE_SEGURO:
        logging.warning("JWT_SEGREDO de desenvolvimento em uso com COOKIE_SEGURO=true. "
                        "Defina um segredo no .env.")
    await run_in_threadpool(preparar_banco)
    cliente = criar_cliente_async()
    app.state.db = cliente[DATABASE_NAME]
    logging.info(f"HolyCut API {VERSAO} pronta. Banco: {DATABASE_NAME}.")
    yield
    await cliente.close()


app = FastAPI(
    title="HolyCut API",
    version=VERSAO,
    lifespan=ciclo_de_vida,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url=None,
)


# -----------------------------------------------
# ERROS DE VALIDAÇÃO EM PORTUGUÊS
# -----------------------------------------------
def traduzir_erro(erro: dict) -> str:
    campo = str(erro.get("loc", ["", "campo"])[-1])
    rotulo = ROTULOS_CAMPOS.get(campo, campo)
    tipo = erro.get("type", "")
    contexto = erro.get("ctx") or {}
    if tipo == "missing":
        return f"{rotulo} é obrigatório."
    if tipo == "string_too_short":
        return f"{rotulo} precisa ter pelo menos {contexto.get('min_length')} caracteres."
    if tipo == "string_too_long":
        return f"{rotulo} pode ter no máximo {contexto.get('max_length')} caracteres."
    if campo == "email":
        return "E-mail inválido."
    return f"{rotulo}: valor inválido."


@app.exception_handler(RequestValidationError)
async def tratar_erro_validacao(_request: Request, exc: RequestValidationError):
    mensagens = [traduzir_erro(e) for e in exc.errors()]
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                        content={"detail": mensagens[0] if mensagens else "Dados inválidos.",
                                 "erros": mensagens})


# -----------------------------------------------
# ROTAS
# -----------------------------------------------
app.include_router(sistema.router)
app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(eventos.router)
app.include_router(uploads.router)
app.include_router(midias.router)
app.include_router(projetos.router)
app.include_router(exportacoes.router)
app.include_router(identidade.router)
app.include_router(modelos.router)
