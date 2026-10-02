# -----------------------------------------------
# HolyCut API — sons sintetizados pelo próprio app
# -----------------------------------------------
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from api.dependencias import usuario_atual
from core.utils.sons import sintetizar

router = APIRouter(prefix="/api/efeitos", tags=["efeitos"])


@router.get("/{tipo}")
async def baixar_efeito(tipo: str, _usuario=Depends(usuario_atual)):
    if tipo not in ("sopro", "toque"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Esse som não existe.")
    return Response(sintetizar(tipo), media_type="audio/wav",
                    headers={"Cache-Control": "private, max-age=86400"})
