# -----------------------------------------------
# HolyCut API — o link de aprovação (público, sem conta)
#
#   GET  /api/aprovar/{token}                  o vídeo e a situação do pedido
#   GET  /api/aprovar/{token}/arquivos/{nome}  o vídeo, a imagem ou a capa, para assistir
#   POST /api/aprovar/{token}                  aprova ou pede ajustes
#
# O token vale como senha daquele vídeo: é aleatório (256 bits), o banco
# guarda só o hash, e ele não abre nada além desta exportação.
# -----------------------------------------------
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from api.dependencias import obter_db
from api.esquemas import AprovacaoPublicaSaida, AprovacaoRespostaEntrada, aprovacao_para_saida
from core.modelos.aprovacao import PENDENTE, expirada, hash_do_token, responder
from core.modelos.projeto import ARQUIVOS_EXPORTACAO, STATUS_EXPORTACAO_PRONTA, chave_exportacao
from core.utils import storage

router = APIRouter(prefix="/api/aprovar", tags=["aprovação"])
TIPOS_ARQUIVO = {".mp4": "video/mp4", ".jpg": "image/jpeg"}


async def buscar_pelo_token(db, token: str) -> dict:
    exportacao = await db.exportacoes.find_one({"aprovacao.token_hash": hash_do_token(token)}) if token else None
    if exportacao is None or exportacao["status"] != STATUS_EXPORTACAO_PRONTA:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Este link não vale mais. Peça um novo a quem enviou.")
    return exportacao


async def para_saida(db, exportacao: dict) -> AprovacaoPublicaSaida:
    organizacao = await db.organizacoes.find_one({"_id": exportacao["organizacao_id"]}, {"nome": 1}) or {}
    return AprovacaoPublicaSaida.model_validate({
        **exportacao, "igreja": organizacao.get("nome", ""), "aprovacao": aprovacao_para_saida(exportacao["aprovacao"]),
    })


@router.get("/{token}", response_model=AprovacaoPublicaSaida)
async def ver_pedido(token: str, db=Depends(obter_db)):
    return await para_saida(db, await buscar_pelo_token(db, token))


@router.get("/{token}/arquivos/{nome}")
async def assistir(token: str, nome: str, db=Depends(obter_db)):
    exportacao = await buscar_pelo_token(db, token)
    if expirada(exportacao["aprovacao"]):
        raise HTTPException(status.HTTP_410_GONE, "Este link expirou. Peça um novo a quem enviou.")
    if nome not in ARQUIVOS_EXPORTACAO or nome not in exportacao.get("arquivos", []):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Arquivo não encontrado.")
    caminho = storage.caminho_local(chave_exportacao(exportacao["organizacao_id"], exportacao["_id"], nome))
    if not caminho.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Arquivo não encontrado.")
    return FileResponse(caminho, media_type=TIPOS_ARQUIVO.get(caminho.suffix, "application/octet-stream"),
                        headers={"Cache-Control": "private, no-store", "Referrer-Policy": "no-referrer"})


@router.post("/{token}", response_model=AprovacaoPublicaSaida)
async def responder_pedido(token: str, dados: AprovacaoRespostaEntrada, db=Depends(obter_db)):
    exportacao = await buscar_pelo_token(db, token)
    aprovacao = exportacao["aprovacao"]
    if aprovacao["status"] != PENDENTE:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este vídeo já foi respondido.")
    if expirada(aprovacao):
        raise HTTPException(status.HTTP_410_GONE, "Este link expirou. Peça um novo a quem enviou.")
    try:
        respondida = responder(aprovacao, dados.decisao, dados.nome, dados.comentario)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from e
    # Só grava se ninguém respondeu nem trocou o link no meio do caminho
    resultado = await db.exportacoes.update_one(
        {"_id": exportacao["_id"], "aprovacao.token_hash": aprovacao["token_hash"], "aprovacao.status": PENDENTE},
        {"$set": {"aprovacao": respondida}},
    )
    if resultado.matched_count == 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "Este vídeo já foi respondido.")
    logging.info(f"[{exportacao['organizacao_id']}] Vídeo {exportacao['_id']}: {dados.decisao} "
                 f"por {respondida['respondido_por']}")
    return await para_saida(db, {**exportacao, "aprovacao": respondida})
