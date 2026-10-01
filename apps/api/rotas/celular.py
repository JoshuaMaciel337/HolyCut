# -----------------------------------------------
# HolyCut API — baixar no celular pelo QR code
#
#   GET /api/baixar/{token}   público: o vídeo daquele link, como download
#   GET /api/qrcode.svg       o QR code de um endereço, para mostrar na tela
#
# O token vale 24 horas e só abre aquele vídeo (core/modelos/link_celular.py).
# -----------------------------------------------
import segno
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse

from api.dependencias import obter_db, usuario_atual
from api.rotas.exportacoes import nome_de_arquivo
from core.modelos.aprovacao import hash_do_token
from core.modelos.link_celular import link_vencido
from core.modelos.projeto import ARQUIVO_VIDEO_EXPORTADO, STATUS_EXPORTACAO_PRONTA, chave_exportacao
from core.utils import storage

router = APIRouter(prefix="/api", tags=["celular"])


@router.get("/baixar/{token}")
async def baixar_pelo_link(token: str, db=Depends(obter_db)):
    exportacao = await db.exportacoes.find_one({"link_celular.token_hash": hash_do_token(token)}) if token else None
    valido = exportacao is not None and exportacao["status"] == STATUS_EXPORTACAO_PRONTA
    if not valido or link_vencido(exportacao.get("link_celular")):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Este link não vale mais. Gere um QR code novo no HolyCut.")
    caminho = storage.caminho_local(chave_exportacao(exportacao["organizacao_id"], exportacao["_id"],
                                                     ARQUIVO_VIDEO_EXPORTADO))
    if not caminho.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "O vídeo não foi encontrado no servidor.")
    return FileResponse(caminho, media_type="video/mp4", filename=nome_de_arquivo(exportacao["nome"]),
                        headers={"Cache-Control": "private, no-store", "Referrer-Policy": "no-referrer"})


@router.get("/qrcode.svg")
async def qrcode(texto: str = Query(min_length=1, max_length=400), _usuario=Depends(usuario_atual)):
    """Preto no branco, com margem: é o que as câmeras de celular leem melhor."""
    svg = segno.make(texto, error="m").svg_inline(scale=8, border=3, dark="#000000", light="#ffffff")
    return Response(svg, media_type="image/svg+xml", headers={"Cache-Control": "private, no-store"})
