# -----------------------------------------------
# HolyCut API — projetos (Reels montados a partir de uma gravação)
# -----------------------------------------------
import logging

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pymongo import ReturnDocument

from api.dependencias import obter_db, usuario_atual
from api.esquemas import (
    ExportacaoSaida,
    ExportarEntrada,
    ProjetoAtualizarEntrada,
    ProjetoCriarEntrada,
    ProjetoSaida,
    exportacao_para_saida,
    projeto_para_saida,
)
from api.rotas.exportacoes import apagar_exportacoes
from api.rotas.identidade import carregar_identidade
from api.rotas.modelos import buscar_modelo
from api.rotas.musicas import buscar_musica
from core.modelos.job import montar_job
from core.modelos.midia import STATUS_PRONTA
from core.modelos.projeto import DURACAO_MINIMA_TRECHO, montar_exportacao, montar_projeto
from core.utils.mongo import agora

router = APIRouter(prefix="/api/projetos", tags=["projetos"])
PRIORIDADE_RENDER = 3


# -----------------------------------------------
# FUNÇÕES AUXILIARES
# -----------------------------------------------
def para_object_id(valor: str, mensagem: str) -> ObjectId:
    try:
        return ObjectId(valor)
    except (InvalidId, TypeError) as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, mensagem) from e


async def buscar_projeto(db, projeto_id: str, usuario: dict) -> dict:
    projeto = await db.projetos.find_one({"_id": para_object_id(projeto_id, "Projeto não encontrado."),
                                          "organizacao_id": usuario["organizacao_id"]})
    if projeto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Projeto não encontrado.")
    return projeto


async def buscar_midia_do_projeto(db, midia_id, usuario: dict) -> dict:
    midia = await db.midias.find_one({"_id": midia_id, "organizacao_id": usuario["organizacao_id"]})
    if midia is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "A gravação deste projeto não existe mais.")
    return midia


# -----------------------------------------------
# ROTAS
# -----------------------------------------------
@router.post("", response_model=ProjetoSaida, status_code=status.HTTP_201_CREATED)
async def criar_projeto(dados: ProjetoCriarEntrada, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    midia = await buscar_midia_do_projeto(db, para_object_id(dados.midia_id, "Gravação não encontrada."), usuario)
    if midia["status"] != STATUS_PRONTA:
        raise HTTPException(status.HTTP_409_CONFLICT, "A gravação ainda está sendo preparada.")
    if not midia.get("video"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Para criar um Reel, a gravação precisa ter vídeo.")
    modelo = await buscar_modelo(db, dados.modelo_id, usuario) if dados.modelo_id else None
    projeto = montar_projeto(usuario["organizacao_id"], midia, usuario["_id"], dados.nome, dados.proporcao,
                             identidade=await carregar_identidade(db, usuario["organizacao_id"]),
                             tipo=dados.tipo, modelo=modelo, inicio=dados.inicio)
    projeto["_id"] = (await db.projetos.insert_one(projeto)).inserted_id
    return projeto_para_saida(projeto)


@router.get("", response_model=list[ProjetoSaida])
async def listar_projetos(midia_id: str | None = None, limite: int = Query(default=30, ge=1, le=100),
                          usuario=Depends(usuario_atual), db=Depends(obter_db)):
    filtro = {"organizacao_id": usuario["organizacao_id"]}
    if midia_id:
        filtro["midia_id"] = para_object_id(midia_id, "Gravação não encontrada.")
    cursor = db.projetos.find(filtro).sort("atualizado_em", -1).limit(limite)
    return [projeto_para_saida(p) async for p in cursor]


@router.get("/{projeto_id}", response_model=ProjetoSaida)
async def ver_projeto(projeto_id: str, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    return projeto_para_saida(await buscar_projeto(db, projeto_id, usuario))


@router.patch("/{projeto_id}", response_model=ProjetoSaida)
async def atualizar_projeto(projeto_id: str, dados: ProjetoAtualizarEntrada,
                            usuario=Depends(usuario_atual), db=Depends(obter_db)):
    projeto = await buscar_projeto(db, projeto_id, usuario)
    campos = dados.model_dump(exclude_unset=True, exclude={"versao"})
    if dados.trecho is not None:
        midia = await buscar_midia_do_projeto(db, projeto["midia_id"], usuario)
        fim = min(dados.trecho.fim, round(midia["duracao"], 2))
        if fim - dados.trecho.inicio < DURACAO_MINIMA_TRECHO:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "O trecho precisa ter pelo menos 1 segundo.")
        campos["trecho"] = {"inicio": round(dados.trecho.inicio, 2), "fim": fim}
    for texto in dados.textos or []:
        if texto.fim is not None and texto.fim <= texto.inicio:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "O texto precisa terminar depois de começar.")
    if dados.textos is not None and len({texto.id for texto in dados.textos}) != len(dados.textos):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Dois textos com o mesmo identificador.")
    if dados.musica is not None and dados.musica.id is not None:
        await buscar_musica(db, dados.musica.id, usuario)
    if not campos:
        return projeto_para_saida(projeto)

    campos["atualizado_em"] = agora()
    resultado = await db.projetos.find_one_and_update(
        {"_id": projeto["_id"], "versao": dados.versao},
        {"$set": campos, "$inc": {"versao": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if resultado is None:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Este projeto foi alterado em outra aba ou por outra pessoa. Recarregue a página.")
    return projeto_para_saida(resultado)


@router.delete("/{projeto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_projeto(projeto_id: str, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    projeto = await buscar_projeto(db, projeto_id, usuario)
    await apagar_exportacoes(db, {"projeto_id": projeto["_id"]})
    await db.projetos.delete_one({"_id": projeto["_id"]})


@router.post("/{projeto_id}/exportar", response_model=ExportacaoSaida, status_code=status.HTTP_201_CREATED)
async def exportar_projeto(projeto_id: str, dados: ExportarEntrada | None = None,
                           usuario=Depends(usuario_atual), db=Depends(obter_db)):
    dados = dados or ExportarEntrada()
    projeto = await buscar_projeto(db, projeto_id, usuario)
    await buscar_midia_do_projeto(db, projeto["midia_id"], usuario)
    exportacao = montar_exportacao(projeto, usuario["_id"], formato=dados.formato, instante=dados.instante)
    exportacao["_id"] = (await db.exportacoes.insert_one(exportacao)).inserted_id
    job = montar_job("renderizacao", usuario["organizacao_id"], {"exportacao_id": str(exportacao["_id"])},
                     prioridade=PRIORIDADE_RENDER, criado_por=usuario["_id"])
    job["_id"] = (await db.jobs.insert_one(job)).inserted_id
    await db.exportacoes.update_one({"_id": exportacao["_id"]}, {"$set": {"job_id": job["_id"]}})
    logging.info(f"[{usuario['organizacao_id']}] Exportação na fila: {projeto['nome']}")
    return exportacao_para_saida({**exportacao, "job_id": job["_id"]}, job)
