# -----------------------------------------------
# Tarefa "capa_exportacao" — trocar a capa de um vídeo já exportado
#
# A pessoa pausa o vídeo pronto no quadro que quer e pede a capa dali.
# Tira o quadro do MP4 final, sem renderizar de novo, e sobe a versão da
# capa para o navegador não mostrar a antiga do cache.
# -----------------------------------------------
import logging
from collections.abc import Callable

from bson import ObjectId

from core.modelos.job import ErroDefinitivo
from core.modelos.link_celular import instante_da_capa
from core.modelos.projeto import (
    ARQUIVO_CAPA_EXPORTADA,
    ARQUIVO_VIDEO_EXPORTADO,
    STATUS_EXPORTACAO_PRONTA,
    chave_exportacao,
)
from core.utils import storage
from core.utils.mongo import agora
from worker.tarefas.renderizacao import extrair_capa


def executar_capa_exportacao(db, job: dict, reportar: Callable[[int, str], None]) -> dict:
    exportacao_id = ObjectId(job["entrada"]["exportacao_id"])
    organizacao_id = job["organizacao_id"]
    exportacao = db.exportacoes.find_one({"_id": exportacao_id, "organizacao_id": organizacao_id})
    if exportacao is None or exportacao["status"] != STATUS_EXPORTACAO_PRONTA:
        raise ErroDefinitivo("O vídeo foi excluído ou ainda não ficou pronto.")
    video = storage.caminho_local(chave_exportacao(organizacao_id, exportacao_id, ARQUIVO_VIDEO_EXPORTADO))
    if not video.is_file():
        raise ErroDefinitivo("O vídeo exportado não foi encontrado no servidor.")
    instante = instante_da_capa(job["entrada"].get("instante") or 0, exportacao.get("duracao") or 0)
    reportar(30, "Tirando o quadro da capa")
    extrair_capa(video, storage.caminho_local(chave_exportacao(organizacao_id, exportacao_id, ARQUIVO_CAPA_EXPORTADA)),
                 instante)
    db.exportacoes.update_one({"_id": exportacao_id}, {"$set": {"capa_instante": instante, "atualizado_em": agora()},
                                                       "$inc": {"capa_versao": 1}})
    reportar(100, "Capa trocada")
    logging.info(f"[{organizacao_id}] [exportacao {exportacao_id}] Capa no quadro de {instante:.2f}s.")
    return {"exportacao_id": str(exportacao_id), "instante": instante}
