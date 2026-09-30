# -----------------------------------------------
# HolyCut API — mídias (as gravações enviadas)
# -----------------------------------------------
import logging
from functools import lru_cache
from pathlib import Path
from typing import Literal

import numpy as np
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from api.dependencias import obter_db, usuario_atual
from api.esquemas import MidiaAtualizarEntrada, MidiaSaida, SilenciosSaida, midia_para_saida
from api.rotas.exportacoes import apagar_exportacoes
from core.modelos.job import STATUS_ERRO as STATUS_JOB_ERRO
from core.modelos.job import STATUS_EXECUTANDO, STATUS_PENDENTE
from core.modelos.midia import (
    ARQUIVO_NIVEIS,
    ARQUIVOS_PUBLICOS,
    STATUS_PROCESSANDO,
    chave_arquivo,
    pasta_da_midia,
)
from core.utils import storage
from core.utils.mongo import agora
from core.utils.silencios import INTENSIDADES, MARGEM_PADRAO, detectar_silencios, tempo_cortado

router = APIRouter(prefix="/api/midias", tags=["midias"])

TIPOS_ARQUIVO = {
    ".mp4": "video/mp4",
    ".m4a": "audio/mp4",
    ".json": "application/json",
    ".jpg": "image/jpeg",
}
# Os arquivos de uma mídia não mudam depois de gerados
CACHE_ARQUIVOS = "private, max-age=86400"


# -----------------------------------------------
# FUNÇÕES AUXILIARES
# -----------------------------------------------
async def buscar_midia(db, midia_id: str, usuario: dict) -> dict:
    try:
        filtro = {"_id": ObjectId(midia_id), "organizacao_id": usuario["organizacao_id"]}
    except InvalidId as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mídia não encontrada.") from e
    midia = await db.midias.find_one(filtro)
    if midia is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mídia não encontrada.")
    return midia


async def jobs_de_ingestao(db, midias: list[dict]) -> dict:
    """Jobs de ingestão das mídias em processamento, numa consulta só."""
    ids = [m["job_ingestao_id"] for m in midias if m["status"] == STATUS_PROCESSANDO and m.get("job_ingestao_id")]
    if not ids:
        return {}
    cursor = db.jobs.find({"_id": {"$in": ids}}, {"status": 1, "progresso": 1, "mensagem": 1, "erro": 1})
    return {job["_id"]: job async for job in cursor}


@lru_cache(maxsize=16)
def _ler_niveis(caminho: str, _modificado_em: float) -> np.ndarray:
    return np.fromfile(caminho, dtype=np.int8)


def carregar_niveis(caminho: Path) -> np.ndarray:
    """Níveis de 10 ms da mídia. Ficam em memória: o arquivo não muda depois da ingestão."""
    return _ler_niveis(str(caminho), caminho.stat().st_mtime)


async def para_saida(db, midias: list[dict]) -> list[MidiaSaida]:
    jobs = await jobs_de_ingestao(db, midias)
    return [midia_para_saida(m, jobs.get(m.get("job_ingestao_id"))) for m in midias]


# -----------------------------------------------
# ROTAS
# -----------------------------------------------
@router.get("", response_model=list[MidiaSaida])
async def listar_midias(limite: int = Query(default=30, ge=1, le=100),
                        usuario=Depends(usuario_atual), db=Depends(obter_db)):
    cursor = db.midias.find({"organizacao_id": usuario["organizacao_id"]}).sort("criado_em", -1).limit(limite)
    return await para_saida(db, [m async for m in cursor])


@router.get("/{midia_id}", response_model=MidiaSaida)
async def ver_midia(midia_id: str, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    return (await para_saida(db, [await buscar_midia(db, midia_id, usuario)]))[0]


@router.patch("/{midia_id}", response_model=MidiaSaida)
async def renomear_midia(midia_id: str, dados: MidiaAtualizarEntrada,
                         usuario=Depends(usuario_atual), db=Depends(obter_db)):
    midia = await buscar_midia(db, midia_id, usuario)
    await db.midias.update_one({"_id": midia["_id"]}, {"$set": {"nome": dados.nome, "atualizado_em": agora()}})
    return (await para_saida(db, [{**midia, "nome": dados.nome}]))[0]


@router.delete("/{midia_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_midia(midia_id: str, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    midia = await buscar_midia(db, midia_id, usuario)
    momento = agora()
    # Jobs que ainda iam mexer nesta mídia param aqui
    await db.jobs.update_many(
        {"entrada.midia_id": str(midia["_id"]), "status": {"$in": [STATUS_PENDENTE, STATUS_EXECUTANDO]}},
        {"$set": {"status": STATUS_JOB_ERRO, "erro": "A mídia foi excluída.", "mensagem": "Cancelado",
                  "lease_ate": None, "concluido_em": momento, "atualizado_em": momento}},
    )
    await apagar_exportacoes(db, {"midia_id": midia["_id"]})
    await db.projetos.delete_many({"midia_id": midia["_id"]})
    await db.midias.delete_one({"_id": midia["_id"]})
    await run_in_threadpool(storage.remover_pasta, pasta_da_midia(midia["organizacao_id"], midia["_id"]))
    logging.info(f"[{midia['organizacao_id']}] Mídia excluída: {midia['nome']}")


@router.get("/{midia_id}/arquivos/{nome}")
async def baixar_arquivo(midia_id: str, nome: str, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    """Serve a cópia leve, a capa, as miniaturas e a forma de onda. Aceita Range para o player."""
    midia = await buscar_midia(db, midia_id, usuario)
    if nome not in ARQUIVOS_PUBLICOS or nome not in midia.get("arquivos", []):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Arquivo não encontrado.")
    caminho = storage.caminho_local(chave_arquivo(midia["organizacao_id"], midia["_id"], nome))
    if not caminho.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Arquivo não encontrado.")
    return FileResponse(caminho, media_type=TIPOS_ARQUIVO.get(caminho.suffix, "application/octet-stream"),
                        headers={"Cache-Control": CACHE_ARQUIVOS})


@router.get("/{midia_id}/silencios", response_model=SilenciosSaida)
async def silencios_da_midia(
    midia_id: str,
    intensidade: Literal["leve", "media", "forte"] = "media",
    limiar_db: float | None = Query(default=None, ge=-80, le=-10),
    duracao_minima: float | None = Query(default=None, ge=0.1, le=10),
    usuario=Depends(usuario_atual),
    db=Depends(obter_db),
):
    """Trechos de silêncio para a intensidade escolhida. limiar_db e duracao_minima ajustam fino."""
    midia = await buscar_midia(db, midia_id, usuario)
    if ARQUIVO_NIVEIS not in midia.get("arquivos", []):
        raise HTTPException(status.HTTP_409_CONFLICT, "Esta gravação ainda não tem a análise do áudio.")
    parametros = {**INTENSIDADES[intensidade]}
    if limiar_db is not None:
        parametros["limiar_db"] = limiar_db
    if duracao_minima is not None:
        parametros["duracao_minima"] = duracao_minima

    caminho = storage.caminho_local(chave_arquivo(midia["organizacao_id"], midia["_id"], ARQUIVO_NIVEIS))
    niveis = await run_in_threadpool(carregar_niveis, caminho)
    cortes = detectar_silencios(niveis, margem=MARGEM_PADRAO, duracao=midia["duracao"], **parametros)
    removido = tempo_cortado(cortes)
    return SilenciosSaida(intensidade=intensidade, margem=MARGEM_PADRAO, silencios=cortes, tempo_cortado=removido,
                          duracao_final=round(max(midia["duracao"] - removido, 0), 2), **parametros)
