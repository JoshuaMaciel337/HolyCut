# -----------------------------------------------
# HolyCut API — chaves de envio (o agente do OBS no PC da mídia)
#
#   GET    /api/chaves-envio            chaves ativas da igreja
#   POST   /api/chaves-envio            cria uma chave (ela só aparece nesta resposta)
#   DELETE /api/chaves-envio/{id}       revoga a chave
#   GET    /api/chaves-envio/conferir   o agente confere a chave antes de enviar
#   GET    /api/chaves-envio/agente.zip o agente, pronto para o PC da mídia
# -----------------------------------------------
import io
import logging
import re
import zipfile
from pathlib import Path

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from api.dependencias import obter_db, usuario_atual, usuario_ou_chave_envio
from api.esquemas import ChaveEnvioConferirSaida, ChaveEnvioCriadaSaida, ChaveEnvioCriarEntrada, ChaveEnvioSaida
from core.modelos.chave_envio import LIMITE_CHAVES_ATIVAS, gerar_chave, montar_chave_envio
from core.utils.mongo import agora

router = APIRouter(prefix="/api/chaves-envio", tags=["chaves de envio"])
# apps/agente no repositório; /app/agente na imagem da API
PASTA_AGENTE = Path(__file__).resolve().parents[2] / "agente"
ARQUIVOS_AGENTE = ("agendador_gravacoes.py", "iniciar_agente.bat", "requirements.txt", "README.md")
# O endereço vai dentro do .bat: só aceita esquema, domínio e porta (fullmatch: nem uma quebra de linha no
# fim, que no .bat começaria outro comando)
ENDERECO_VALIDO = re.compile(r"https?://[A-Za-z0-9.-]+(:\d{1,5})?")


def chave_para_saida(registro: dict) -> ChaveEnvioSaida:
    return ChaveEnvioSaida.model_validate({**registro, "id": str(registro["_id"])})


@router.get("", response_model=list[ChaveEnvioSaida])
async def listar_chaves(usuario=Depends(usuario_atual), db=Depends(obter_db)):
    cursor = db.chaves_envio.find({"organizacao_id": usuario["organizacao_id"], "revogada_em": None})
    return [chave_para_saida(registro) async for registro in cursor.sort("criado_em", -1)]


@router.post("", response_model=ChaveEnvioCriadaSaida, status_code=status.HTTP_201_CREATED)
async def criar_chave(dados: ChaveEnvioCriarEntrada, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    ativas = await db.chaves_envio.count_documents({"organizacao_id": usuario["organizacao_id"], "revogada_em": None})
    if ativas >= LIMITE_CHAVES_ATIVAS:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"A igreja já tem {LIMITE_CHAVES_ATIVAS} chaves. Revogue uma que não usa mais.")
    chave = gerar_chave()
    registro = montar_chave_envio(usuario["organizacao_id"], usuario["_id"], dados.nome, chave)
    registro["_id"] = (await db.chaves_envio.insert_one(registro)).inserted_id
    logging.info(f"[{usuario['organizacao_id']}] Chave de envio criada: {registro['nome']}")
    return ChaveEnvioCriadaSaida.model_validate({**registro, "id": str(registro["_id"]), "chave": chave})


@router.get("/conferir", response_model=ChaveEnvioConferirSaida)
async def conferir_chave(usuario=Depends(usuario_ou_chave_envio), db=Depends(obter_db)):
    organizacao = await db.organizacoes.find_one({"_id": usuario["organizacao_id"]}, {"nome": 1}) or {}
    chave = usuario.get("chave_envio")
    return ChaveEnvioConferirSaida(igreja=organizacao.get("nome", ""), chave=chave["nome"] if chave else None)


@router.get("/agente.zip")
async def baixar_agente(servidor: str = Query(default="", max_length=200), usuario=Depends(usuario_atual)):
    """O agente em .zip. Com `servidor`, o .bat já vem com o endereço do HolyCut preenchido."""
    if servidor and not ENDERECO_VALIDO.fullmatch(servidor):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Endereço inválido.")
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as pacote:
        for nome in ARQUIVOS_AGENTE:
            conteudo = (PASTA_AGENTE / nome).read_bytes()
            if nome.endswith(".bat"):
                # O Git pode ter trocado o fim de linha; o cmd do Windows precisa de CRLF
                conteudo = conteudo.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
                if servidor:
                    conteudo = conteudo.replace(b"agendador_gravacoes.py %*",
                                                f'agendador_gravacoes.py --servidor "{servidor}" %*'.encode())
            pacote.writestr(f"holycut-agente/{nome}", conteudo)
    return Response(content=memoria.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="holycut-agente.zip"'})


@router.delete("/{chave_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revogar_chave(chave_id: str, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    try:
        filtro = {"_id": ObjectId(chave_id), "organizacao_id": usuario["organizacao_id"], "revogada_em": None}
    except InvalidId as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chave não encontrada.") from e
    resultado = await db.chaves_envio.update_one(filtro, {"$set": {"revogada_em": agora()}})
    if resultado.matched_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Chave não encontrada.")
    logging.info(f"[{usuario['organizacao_id']}] Chave de envio revogada: {chave_id}")
