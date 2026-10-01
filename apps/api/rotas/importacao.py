# -----------------------------------------------
# HolyCut API — importar pelo link e o canal do YouTube da igreja
#
# Só vídeos da própria igreja: do YouTube, só os do canal cadastrado (o
# worker confere nos dados do vídeo); do Drive, a pessoa confirma. O
# download roda no worker (job importar_link), e a gravação aparece no
# acervo com o progresso desde o começo.
# -----------------------------------------------
import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from starlette.concurrency import run_in_threadpool

from api.dependencias import obter_db, usuario_atual
from api.esquemas import CanalYoutubeEntrada, CanalYoutubeSaida, ImportarEntrada, MidiaSaida
from api.rotas.midias import para_saida
from core.config import ESPACO_MINIMO_LIVRE_BYTES
from core.modelos.importacao import ler_link, montar_importacao, normalizar_canal
from core.modelos.midia import STATUS_ERRO
from core.utils import storage
from core.utils.mongo import agora

router = APIRouter(prefix="/api", tags=["importacao"])


@router.post("/midias/importar", response_model=MidiaSaida, status_code=status.HTTP_201_CREATED)
async def importar_link(dados: ImportarEntrada, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    link = ler_link(dados.url)
    if link is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            "Cole o link de um vídeo do YouTube ou de um arquivo do Google Drive.")
    organizacao_id = usuario["organizacao_id"]
    if link["origem"] == "youtube":
        organizacao = await db.organizacoes.find_one({"_id": organizacao_id}, {"canal_youtube": 1}) or {}
        if not organizacao.get("canal_youtube"):
            raise HTTPException(status.HTTP_409_CONFLICT, "Cadastre o canal do YouTube da igreja em Envio automático. "
                                                          "Só dá para importar vídeos dele.")
    elif not dados.confirmo_que_e_da_igreja:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Confirme que o vídeo do Drive é da igreja.")
    existente = await db.midias.find_one({"organizacao_id": organizacao_id, "importacao.id": link["id"],
                                          "status": {"$ne": STATUS_ERRO}}, {"nome": 1})
    if existente:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Esse vídeo já está no acervo: {existente['nome']}.")
    if await run_in_threadpool(storage.espaco_livre) < ESPACO_MINIMO_LIVRE_BYTES:
        raise HTTPException(status.HTTP_507_INSUFFICIENT_STORAGE, "O disco do servidor está cheio.")

    midia, job = montar_importacao(organizacao_id, usuario["_id"], link, agora())
    midia["_id"] = (await db.midias.insert_one(midia)).inserted_id
    job["entrada"]["midia_id"] = str(midia["_id"])
    job["_id"] = (await db.jobs.insert_one(job)).inserted_id
    await db.midias.update_one({"_id": midia["_id"]}, {"$set": {"job_ingestao_id": job["_id"]}})
    logging.info(f"[{organizacao_id}] Importação na fila: {link['url']}")
    return (await para_saida(db, [{**midia, "job_ingestao_id": job["_id"]}]))[0]


def _canal_para_saida(canal: dict | None) -> CanalYoutubeSaida:
    if not canal:
        return CanalYoutubeSaida(configurado=False)
    return CanalYoutubeSaida(configurado=True, canal=canal.get("entrada") or "", id=canal.get("id"),
                             handle=canal.get("handle"), monitorar=bool(canal.get("monitorar")),
                             ultima_verificacao=canal.get("ultima_verificacao"), ultimo_erro=canal.get("ultimo_erro"))


@router.get("/canal-youtube", response_model=CanalYoutubeSaida)
async def ver_canal(usuario=Depends(usuario_atual), db=Depends(obter_db)):
    organizacao = await db.organizacoes.find_one({"_id": usuario["organizacao_id"]}, {"canal_youtube": 1}) or {}
    return _canal_para_saida(organizacao.get("canal_youtube"))


@router.put("/canal-youtube", response_model=CanalYoutubeSaida)
async def salvar_canal(dados: CanalYoutubeEntrada, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    """O canal da igreja. Ligar o monitor faz o HolyCut importar sozinho cada live que terminar."""
    try:
        canal = normalizar_canal(dados.canal)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from e
    organizacao = await db.organizacoes.find_one({"_id": usuario["organizacao_id"]}, {"canal_youtube": 1}) or {}
    atual = organizacao.get("canal_youtube") or {}
    mesmo = bool(atual) and ((canal["id"] and canal["id"] == atual.get("id"))
                             or (canal["handle"] and canal["handle"] == atual.get("handle")))
    base = atual if mesmo else {}
    novo = {**base, "entrada": " ".join(dados.canal.split()), "id": canal["id"] or base.get("id"),
            "handle": canal["handle"] or base.get("handle"), "monitorar": dados.monitorar}
    if dados.monitorar and not (mesmo and atual.get("monitorar")):
        # Daqui para a frente: na primeira volta, o que já terminou só fica como visto
        novo.update({"primeira_volta": True, "vistos": [], "ultimo_erro": None})
        novo.pop("proxima_verificacao", None)
    await db.organizacoes.update_one({"_id": usuario["organizacao_id"]},
                                     {"$set": {"canal_youtube": novo, "atualizado_em": agora()}})
    return _canal_para_saida(novo)


@router.delete("/canal-youtube", status_code=status.HTTP_204_NO_CONTENT)
async def remover_canal(usuario=Depends(usuario_atual), db=Depends(obter_db)):
    await db.organizacoes.update_one({"_id": usuario["organizacao_id"]}, {"$unset": {"canal_youtube": ""}})
    return Response(status_code=status.HTTP_204_NO_CONTENT)
