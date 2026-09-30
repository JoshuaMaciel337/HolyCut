# -----------------------------------------------
# HolyCut API — exportações (os vídeos finais, prontos para postar)
# -----------------------------------------------
import re
import unicodedata

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from api.dependencias import obter_db, usuario_atual
from api.esquemas import (
    AprovacaoCriadaSaida,
    AprovacaoCriarEntrada,
    ExportacaoSaida,
    aprovacao_para_saida,
    exportacao_para_saida,
)
from core.modelos.aprovacao import montar_aprovacao
from core.modelos.job import STATUS_ERRO as STATUS_JOB_ERRO
from core.modelos.job import STATUS_EXECUTANDO, STATUS_PENDENTE
from core.modelos.projeto import (
    ARQUIVO_CAPA_EXPORTADA,
    ARQUIVOS_EXPORTACAO,
    STATUS_EXPORTACAO_PROCESSANDO,
    STATUS_EXPORTACAO_PRONTA,
    chave_exportacao,
    pasta_da_exportacao,
)
from core.utils import storage
from core.utils.mongo import agora

router = APIRouter(prefix="/api/exportacoes", tags=["exportacoes"])

TIPOS_ARQUIVO = {".mp4": "video/mp4", ".jpg": "image/jpeg"}


# -----------------------------------------------
# FUNÇÕES AUXILIARES
# -----------------------------------------------
def nome_de_arquivo(nome: str, extensao: str = ".mp4") -> str:
    """'Reel · Culto de Domingo!' → 'reel-culto-de-domingo.mp4'."""
    sem_acento = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode()
    base = re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")[:60].strip("-")
    return f"{base or 'holycut'}{extensao}"


async def para_saida(db, exportacoes: list[dict]) -> list[ExportacaoSaida]:
    ids = [e["job_id"] for e in exportacoes if e["status"] == STATUS_EXPORTACAO_PROCESSANDO and e.get("job_id")]
    jobs = {}
    if ids:
        cursor = db.jobs.find({"_id": {"$in": ids}}, {"status": 1, "progresso": 1, "mensagem": 1, "erro": 1})
        jobs = {job["_id"]: job async for job in cursor}
    return [exportacao_para_saida(e, jobs.get(e.get("job_id"))) for e in exportacoes]


async def buscar_exportacao(db, exportacao_id: str, usuario: dict) -> dict:
    try:
        filtro = {"_id": ObjectId(exportacao_id), "organizacao_id": usuario["organizacao_id"]}
    except InvalidId as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exportação não encontrada.") from e
    exportacao = await db.exportacoes.find_one(filtro)
    if exportacao is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Exportação não encontrada.")
    return exportacao


async def apagar_exportacoes(db, filtro: dict):
    """Apaga exportações, seus arquivos e os renders que ainda estavam na fila."""
    momento = agora()
    async for exportacao in db.exportacoes.find(filtro, {"organizacao_id": 1}):
        await db.jobs.update_many(
            {"entrada.exportacao_id": str(exportacao["_id"]), "status": {"$in": [STATUS_PENDENTE, STATUS_EXECUTANDO]}},
            {"$set": {"status": STATUS_JOB_ERRO, "erro": "A exportação foi excluída.", "mensagem": "Cancelado",
                      "lease_ate": None, "concluido_em": momento, "atualizado_em": momento}},
        )
        pasta = pasta_da_exportacao(exportacao["organizacao_id"], exportacao["_id"])
        await run_in_threadpool(storage.remover_pasta, pasta)
    await db.exportacoes.delete_many(filtro)


# -----------------------------------------------
# ROTAS
# -----------------------------------------------
@router.get("", response_model=list[ExportacaoSaida])
async def listar_exportacoes(projeto_id: str | None = None, midia_id: str | None = None,
                             limite: int = Query(default=20, ge=1, le=100),
                             usuario=Depends(usuario_atual), db=Depends(obter_db)):
    """Do projeto, da gravação (todos os cortes de um culto) ou da igreja toda."""
    filtro = {"organizacao_id": usuario["organizacao_id"]}
    for campo, valor in (("projeto_id", projeto_id), ("midia_id", midia_id)):
        if valor:
            try:
                filtro[campo] = ObjectId(valor)
            except InvalidId:
                return []
    cursor = db.exportacoes.find(filtro).sort("criado_em", -1).limit(limite)
    return await para_saida(db, [e async for e in cursor])


@router.get("/{exportacao_id}", response_model=ExportacaoSaida)
async def ver_exportacao(exportacao_id: str, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    return (await para_saida(db, [await buscar_exportacao(db, exportacao_id, usuario)]))[0]


@router.get("/{exportacao_id}/arquivos/{nome}")
async def baixar_arquivo(exportacao_id: str, nome: str, baixar: bool = False,
                         usuario=Depends(usuario_atual), db=Depends(obter_db)):
    """O vídeo final ou a capa. Com baixar=true, o navegador salva o arquivo com um nome legível."""
    exportacao = await buscar_exportacao(db, exportacao_id, usuario)
    if nome not in ARQUIVOS_EXPORTACAO or nome not in exportacao.get("arquivos", []):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Arquivo não encontrado.")
    caminho = storage.caminho_local(chave_exportacao(exportacao["organizacao_id"], exportacao["_id"], nome))
    if not caminho.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Arquivo não encontrado.")
    baixar_com_nome = baixar and nome != ARQUIVO_CAPA_EXPORTADA
    nome_download = nome_de_arquivo(exportacao["nome"], caminho.suffix) if baixar_com_nome else None
    return FileResponse(
        caminho,
        media_type=TIPOS_ARQUIVO.get(caminho.suffix, "application/octet-stream"),
        filename=nome_download,
        content_disposition_type="attachment" if baixar else "inline",
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.post("/{exportacao_id}/aprovacao", response_model=AprovacaoCriadaSaida, status_code=status.HTTP_201_CREATED)
async def pedir_aprovacao(exportacao_id: str, dados: AprovacaoCriarEntrada | None = None,
                          usuario=Depends(usuario_atual), db=Depends(obter_db)):
    """Gera o link de aprovação. Pedir de novo troca o link: o anterior deixa de valer."""
    exportacao = await buscar_exportacao(db, exportacao_id, usuario)
    if exportacao["status"] != STATUS_EXPORTACAO_PRONTA:
        raise HTTPException(status.HTTP_409_CONFLICT, "Espere o vídeo ficar pronto para pedir a aprovação.")
    token, aprovacao = montar_aprovacao(usuario["_id"], (dados or AprovacaoCriarEntrada()).para)
    await db.exportacoes.update_one({"_id": exportacao["_id"]}, {"$set": {"aprovacao": aprovacao}})
    return AprovacaoCriadaSaida(token=token, aprovacao=aprovacao_para_saida(aprovacao))


@router.delete("/{exportacao_id}/aprovacao", status_code=status.HTTP_204_NO_CONTENT)
async def cancelar_aprovacao(exportacao_id: str, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    exportacao = await buscar_exportacao(db, exportacao_id, usuario)
    await db.exportacoes.update_one({"_id": exportacao["_id"]}, {"$unset": {"aprovacao": ""}})


@router.delete("/{exportacao_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_exportacao(exportacao_id: str, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    exportacao = await buscar_exportacao(db, exportacao_id, usuario)
    await apagar_exportacoes(db, {"_id": exportacao["_id"]})
