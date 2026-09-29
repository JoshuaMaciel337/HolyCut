# -----------------------------------------------
# HolyCut API — saúde e estado do sistema
# -----------------------------------------------
import logging
from datetime import timedelta

from fastapi import APIRouter, Depends

from api.dependencias import obter_db, usuario_atual
from api.esquemas import SistemaSaida, worker_para_saida
from core.config import MODO_IA, VERSAO
from core.utils.mongo import agora

router = APIRouter(prefix="/api", tags=["sistema"])
WORKER_ONLINE_SEGUNDOS = 60


async def mongo_responde(db) -> bool:
    try:
        await db.command("ping")
        return True
    except Exception as e:
        logging.error(f"MongoDB não respondeu: {e}")
        return False


@router.get("/saude")
async def saude(db=Depends(obter_db)):
    """Pública. Usada pelo Docker e pela página de manutenção."""
    mongo = await mongo_responde(db)
    return {"status": "ok" if mongo else "degradado", "mongo": mongo, "versao": VERSAO,
            "horario": agora().isoformat()}


@router.get("/sistema", response_model=SistemaSaida)
async def sistema(_usuario=Depends(usuario_atual), db=Depends(obter_db)):
    """Workers online, para o painel mostrar se o notebook com a GPU está ligado."""
    limite = agora() - timedelta(seconds=WORKER_ONLINE_SEGUNDOS)
    workers = [worker_para_saida(w) async for w in db.workers.find({"visto_em": {"$gte": limite}})]
    return SistemaSaida(mongo=True, modo_ia=MODO_IA, workers=workers)
