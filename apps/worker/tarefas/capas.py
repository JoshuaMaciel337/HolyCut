# -----------------------------------------------
# Tarefa "capas_culto" — o pôster e o banner do culto no acervo
#
# O fundo é a imagem que a igreja enviou, ou um quadro da cópia leve do
# vídeo (no instante escolhido), ou, numa gravação só de áudio, um fundo na
# cor da igreja. Por cima entram o título, a série, "pregador · data" e o
# logo, com as fontes da marca. Roda no fim da ingestão e sempre que a
# ficha ou a escolha da capa mudam.
# -----------------------------------------------
import logging
import time
from collections.abc import Callable

from bson import ObjectId
from PIL import Image

from core.modelos.culto import (
    ARQUIVO_BANNER,
    ARQUIVO_FUNDO_CAPA,
    ARQUIVO_POSTER,
    TAMANHO_BANNER,
    TAMANHO_POSTER,
    ficha_do_culto,
    linha_de_informacao,
)
from core.modelos.identidade import chave_logo, identidade_padrao
from core.modelos.job import ErroDefinitivo
from core.modelos.midia import ARQUIVO_PROXY_VIDEO, STATUS_PRONTA, chave_arquivo
from core.utils import storage
from core.utils.arte import desenhar_capa, para_jpeg
from core.utils.ffmpeg import executar_ffmpeg
from core.utils.mongo import agora

ARQUIVO_QUADRO = "quadro_capa.jpg"   # temporário


def instante_padrao(duracao: float | None) -> float:
    """O mesmo ponto da capa pequena da ingestão: 10% da gravação, no máximo aos 30 s."""
    return round(min((duracao or 0) * 0.1, 30.0), 2)


def carregar_fundo(midia: dict) -> Image.Image | None:
    organizacao_id, midia_id = midia["organizacao_id"], midia["_id"]
    capa = midia.get("capa") or {}
    enviada = storage.caminho_local(chave_arquivo(organizacao_id, midia_id, ARQUIVO_FUNDO_CAPA))
    if capa.get("personalizada") and enviada.is_file():
        with Image.open(enviada) as imagem:
            return imagem.convert("RGB")
    if not midia.get("video") or ARQUIVO_PROXY_VIDEO not in midia.get("arquivos", []):
        return None
    instante = capa.get("instante")
    if instante is None:
        instante = instante_padrao(midia.get("duracao"))
    instante = min(max(float(instante), 0.0), max((midia.get("duracao") or 1) - 0.5, 0.0))
    proxy = storage.caminho_local(chave_arquivo(organizacao_id, midia_id, ARQUIVO_PROXY_VIDEO))
    quadro = storage.caminho_local(chave_arquivo(organizacao_id, midia_id, ARQUIVO_QUADRO))
    executar_ffmpeg(["-ss", f"{instante:.2f}", "-i", str(proxy), "-frames:v", "1", "-q:v", "2", "-update", "1",
                     str(quadro)])
    try:
        with Image.open(quadro) as imagem:
            return imagem.convert("RGB")
    finally:
        storage.remover(chave_arquivo(organizacao_id, midia_id, ARQUIVO_QUADRO))


def gerar_capas(db, midia: dict) -> int:
    """Desenha e salva o pôster e o banner. Devolve a versão nova, que o site usa para trocar a imagem."""
    organizacao_id, midia_id = midia["organizacao_id"], midia["_id"]
    organizacao = db.organizacoes.find_one({"_id": organizacao_id}, {"nome": 1, "identidade": 1}) or {}
    identidade = {**identidade_padrao(organizacao.get("nome", "")), **(organizacao.get("identidade") or {})}
    logo = storage.caminho_local(chave_logo(organizacao_id))
    logo_png = logo.read_bytes() if identidade.get("logo") and logo.is_file() else None

    ficha = ficha_do_culto(midia)
    fundo = carregar_fundo(midia)
    for nome, (largura, altura) in ((ARQUIVO_POSTER, TAMANHO_POSTER), (ARQUIVO_BANNER, TAMANHO_BANNER)):
        imagem = desenhar_capa(fundo, largura, altura, midia["nome"], linha_de_informacao(ficha), ficha["serie"],
                               identidade["cor_destaque"], logo_png)
        if not storage.salvar_bytes(chave_arquivo(organizacao_id, midia_id, nome), para_jpeg(imagem)):
            raise RuntimeError(f"Não foi possível salvar {nome}.")
    versao = int(time.time() * 1000)
    db.midias.update_one({"_id": midia_id}, {
        "$addToSet": {"arquivos": {"$each": [ARQUIVO_POSTER, ARQUIVO_BANNER]}},
        "$set": {"capa.versao": versao, "atualizado_em": agora()},
    })
    logging.info(f"[{organizacao_id}] Capas do culto {midia_id} desenhadas ({'com' if fundo else 'sem'} imagem).")
    return versao


def executar_capas_culto(db, job: dict, reportar: Callable[[int, str], None]) -> dict:
    midia = db.midias.find_one({"_id": ObjectId(job["entrada"]["midia_id"])})
    if midia is None:
        raise ErroDefinitivo("A gravação foi excluída.")
    if midia["status"] != STATUS_PRONTA:
        # A ingestão desenha as capas quando termina; não há o que fazer antes disso
        return {"midia_id": str(midia["_id"]), "ignorado": True}
    reportar(20, "Desenhando as capas")
    versao = gerar_capas(db, midia)
    reportar(100, "Capas prontas")
    return {"midia_id": str(midia["_id"]), "versao": versao}
