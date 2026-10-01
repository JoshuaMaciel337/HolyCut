# -----------------------------------------------
# Tarefa "importar_link" — baixar do YouTube ou do Google Drive
# e o monitor do canal da igreja (verificar_canais, chamado pelo laço do worker)
#
# O yt-dlp lê os dados do vídeo, confere se é do canal da igreja, espera a
# live acabar e baixa até 1080p. Depois o vídeo segue o caminho de um
# envio comum: a ingestão. O monitor lê o feed RSS público do canal a
# cada 10 min e importa a live do culto quando ela termina.
# -----------------------------------------------
import logging
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path

import requests
from bson import ObjectId

from core.config import ESPACO_MINIMO_LIVRE_BYTES, EXTENSOES_VIDEO, INTERVALO_MONITOR_SEGUNDOS
from core.modelos.importacao import (
    DURACAO_MINIMA_CULTO,
    ESPERA_LIVE_MINUTOS,
    FEED_CANAL,
    FORMATO_DOWNLOAD,
    MAXIMO_ESPERAS_LIVE,
    data_do_video,
    do_canal,
    lembrar_visto,
    ler_feed,
    ler_link,
    montar_importacao,
    nome_de_arquivo_do_video,
    precisa_esperar,
    titulo_do_video,
    videos_novos,
)
from core.modelos.job import ErroDefinitivo, montar_job
from core.modelos.midia import PRIORIDADE_INGESTAO, STATUS_ERRO, chave_arquivo
from core.utils import storage
from core.utils.mongo import agora

BITS_POR_SEGUNDO_ESTIMADO = 6_000_000   # 1080p de live, quando o YouTube não informa o tamanho
FALHAS_DEFINITIVAS = ("private video", "video unavailable", "this video is not available", "members-only",
                      "has been removed", "does not exist")


class ErroImportacao(RuntimeError):
    pass


# -----------------------------------------------
# YT-DLP
# -----------------------------------------------
def _yt_dlp():
    try:
        import yt_dlp
    except ImportError as erro:
        raise ErroDefinitivo("O worker ainda não tem o yt-dlp. Reconstrua a imagem do worker.") from erro
    return yt_dlp


def ler_metadados(url: str) -> dict:
    """Os dados do vídeo, sem baixar: título, canal, duração e se a live ainda está no ar."""
    yt_dlp = _yt_dlp()
    opcoes = {"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True}
    try:
        with yt_dlp.YoutubeDL(opcoes) as cliente:
            return cliente.extract_info(url, download=False) or {}
    except yt_dlp.utils.DownloadError as erro:
        raise ErroImportacao(str(erro).removeprefix("ERROR: ")[:300]) from erro


def baixar(url: str, pasta: Path, reportar: Callable[[int, str], None]) -> Path:
    """Baixa para pasta/original.<ext> e devolve o caminho. Vídeo e áudio vêm juntos num .mp4."""
    yt_dlp = _yt_dlp()

    def progresso(estado: dict):
        total = estado.get("total_bytes") or estado.get("total_bytes_estimate") or 0
        if estado.get("status") == "downloading" and total:
            reportar(5 + int(85 * min(estado.get("downloaded_bytes", 0) / total, 1)), "Baixando o vídeo")

    opcoes = {"quiet": True, "no_warnings": True, "noplaylist": True, "format": FORMATO_DOWNLOAD,
              "merge_output_format": "mp4", "outtmpl": str(pasta / "original.%(ext)s"),
              "progress_hooks": [progresso], "overwrites": True}
    try:
        with yt_dlp.YoutubeDL(opcoes) as cliente:
            cliente.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as erro:
        raise ErroImportacao(str(erro).removeprefix("ERROR: ")[:300]) from erro
    prontos = [arquivo for arquivo in pasta.glob("original.*")
               if arquivo.suffix.lower() not in (".part", ".ytdl", ".temp") and arquivo.is_file()]
    if not prontos:
        raise ErroImportacao("O download terminou sem arquivo.")
    return max(prontos, key=lambda arquivo: arquivo.stat().st_size)


def resolver_canal(handle: str) -> str:
    """O id UC... do canal, a partir do @. O feed RSS só aceita o id."""
    yt_dlp = _yt_dlp()
    opcoes = {"quiet": True, "no_warnings": True, "skip_download": True, "extract_flat": True, "playlistend": 1}
    try:
        with yt_dlp.YoutubeDL(opcoes) as cliente:
            info = cliente.extract_info(f"https://www.youtube.com/{handle}", download=False) or {}
    except yt_dlp.utils.DownloadError as erro:
        raise ErroImportacao(f"Não encontrei o canal {handle} no YouTube.") from erro
    canal_id = str(info.get("channel_id") or "")
    if not canal_id.startswith("UC"):
        raise ErroImportacao(f"Não encontrei o canal {handle} no YouTube.")
    return canal_id


def _tamanho_estimado(metadados: dict) -> int:
    formatos = metadados.get("requested_formats") or [metadados]
    informado = sum(int(item.get("filesize") or item.get("filesize_approx") or 0) for item in formatos)
    return max(informado, int(float(metadados.get("duration") or 0) * BITS_POR_SEGUNDO_ESTIMADO / 8))


# -----------------------------------------------
# IMPORTAR UM LINK
# -----------------------------------------------
def _esperar_a_live(db, job: dict, midia: dict, titulo: str) -> dict:
    """A live ainda está no ar: um job novo olha de novo daqui a 10 min. Não gasta as tentativas."""
    esperas = int(job["entrada"].get("esperas") or 0)
    if esperas >= MAXIMO_ESPERAS_LIVE:
        raise ErroDefinitivo("A live passou de 8 horas no ar. Importe de novo quando ela terminar.")
    momento = agora()
    novo = montar_job("importar_link", job["organizacao_id"], {**job["entrada"], "esperas": esperas + 1},
                      prioridade=PRIORIDADE_INGESTAO, criado_por=job.get("criado_por"), momento=momento)
    novo["disponivel_em"] = momento + timedelta(minutes=ESPERA_LIVE_MINUTOS)
    novo["mensagem"] = f"A live ainda está no ar. Nova olhada às {novo['disponivel_em'].strftime('%H:%M')}."
    novo_id = db.jobs.insert_one(novo).inserted_id
    db.midias.update_one({"_id": midia["_id"]}, {"$set": {"nome": titulo, "job_ingestao_id": novo_id,
                                                          "atualizado_em": momento}})
    logging.info("[%s] [midia %s] Live no ar. Nova olhada em %s min.", job["organizacao_id"], midia["_id"],
                 ESPERA_LIVE_MINUTOS)
    return {"midia_id": str(midia["_id"]), "aguardando": True}


def executar_importacao(db, job: dict, reportar: Callable[[int, str], None]) -> dict:
    entrada = job["entrada"]
    midia_id = ObjectId(entrada["midia_id"])
    organizacao_id = job["organizacao_id"]
    midia = db.midias.find_one({"_id": midia_id, "organizacao_id": organizacao_id})
    if midia is None:
        raise ErroDefinitivo("A gravação foi excluída antes da importação.")

    reportar(2, "Lendo o vídeo")
    try:
        metadados = ler_metadados(entrada["url"])
    except ErroImportacao as erro:
        if any(trecho in str(erro).lower() for trecho in FALHAS_DEFINITIVAS):
            raise ErroDefinitivo(f"O vídeo não está disponível para baixar: {erro}") from erro
        raise   # rede, limite do YouTube: a fila tenta de novo mais tarde
    titulo = titulo_do_video(metadados)
    if entrada["origem"] == "youtube":
        organizacao = db.organizacoes.find_one({"_id": organizacao_id}, {"canal_youtube": 1}) or {}
        canal = organizacao.get("canal_youtube")
        if not do_canal(metadados, canal):
            raise ErroDefinitivo("Esse vídeo não é do canal da igreja cadastrado em Envio automático.")
        if not canal.get("id") and metadados.get("channel_id"):
            db.organizacoes.update_one({"_id": organizacao_id},
                                       {"$set": {"canal_youtube.id": metadados["channel_id"]}})
        if precisa_esperar(metadados):
            return _esperar_a_live(db, job, midia, titulo)

    if storage.espaco_livre() - _tamanho_estimado(metadados) < ESPACO_MINIMO_LIVRE_BYTES:
        raise ErroDefinitivo("Não há espaço no disco do servidor para esse vídeo.")
    pasta = storage.caminho_local(chave_arquivo(organizacao_id, midia_id, "original")).parent
    pasta.mkdir(parents=True, exist_ok=True)
    arquivo = baixar(entrada["url"], pasta, reportar)
    extensao = arquivo.suffix.lower()
    if extensao not in EXTENSOES_VIDEO:
        arquivo.unlink(missing_ok=True)
        raise ErroDefinitivo("O link não trouxe um vídeo que o HolyCut aceite.")

    reportar(95, "Preparando a gravação")
    momento = agora()
    ingestao = montar_job("ingestao", organizacao_id, {"midia_id": str(midia_id)}, prioridade=PRIORIDADE_INGESTAO,
                          criado_por=midia.get("criado_por"), momento=momento)
    ingestao_id = db.jobs.insert_one(ingestao).inserted_id
    tamanho = arquivo.stat().st_size
    campos = {"nome": titulo, "nome_original": nome_de_arquivo_do_video(titulo, extensao), "extensao": extensao,
              "original": f"original{extensao}", "tamanho_total": tamanho, "bytes_recebidos": tamanho,
              "job_ingestao_id": ingestao_id, "enviado_em": momento, "atualizado_em": momento,
              "importacao.titulo": titulo, "importacao.canal": metadados.get("channel") or ""}
    data = data_do_video(metadados)
    if data and not (midia.get("ficha") or {}).get("data"):
        campos["ficha.data"] = data
    db.midias.update_one({"_id": midia_id}, {"$set": campos})
    reportar(100, "Vídeo baixado")
    logging.info("[%s] [midia %s] Importado do %s: %s (%.1f MB). Ingestão na fila.", organizacao_id, midia_id,
                 entrada["origem"], titulo, tamanho / 1024**2)
    return {"midia_id": str(midia_id), "tamanho": tamanho}


def criar_importacao(db, organizacao_id, criado_por, link: dict) -> dict:
    """A gravação nova e o job que baixa o vídeo. Usado pelo monitor; a API faz o mesmo pelo Motor."""
    midia, job = montar_importacao(organizacao_id, criado_por, link, agora())
    midia["_id"] = db.midias.insert_one(midia).inserted_id
    job["entrada"]["midia_id"] = str(midia["_id"])
    job["_id"] = db.jobs.insert_one(job).inserted_id
    db.midias.update_one({"_id": midia["_id"]}, {"$set": {"job_ingestao_id": job["_id"]}})
    return midia


# -----------------------------------------------
# MONITOR DO CANAL
# -----------------------------------------------
def _reservar(db, momento):
    """Uma igreja por vez, e nunca a mesma em dois workers: a próxima verificação já fica marcada."""
    return db.organizacoes.find_one_and_update(
        {"canal_youtube.monitorar": True,
         "$or": [{"canal_youtube.proxima_verificacao": {"$lte": momento}},
                 {"canal_youtube.proxima_verificacao": {"$exists": False}}]},
        {"$set": {"canal_youtube.proxima_verificacao": momento + timedelta(seconds=INTERVALO_MONITOR_SEGUNDOS)}},
        projection={"canal_youtube": 1},
    )


def verificar_canal(db, organizacao_id, canal: dict) -> int:
    """
    Lê o feed e importa as lives que terminaram. Devolve quantas importações começaram.
    Na primeira volta depois de ligar, o que já tinha terminado só fica como visto: o monitor
    importa daqui para a frente, inclusive a live que já estava agendada ou no ar.
    """
    canal_id = canal.get("id") or resolver_canal(canal["handle"])
    resposta = requests.get(FEED_CANAL.format(canal_id), timeout=30)
    resposta.raise_for_status()
    vistos = list(canal.get("vistos") or [])
    primeira_volta = bool(canal.get("primeira_volta"))
    importados = 0
    for video in videos_novos(ler_feed(resposta.text), vistos):
        link = ler_link(f"https://www.youtube.com/watch?v={video['video_id']}")
        try:
            metadados = ler_metadados(link["url"])
        except ErroImportacao as erro:
            logging.warning("[%s] Monitor: o vídeo %s não abriu: %s", organizacao_id, video["video_id"], erro)
            vistos = lembrar_visto(vistos, video["video_id"])
            continue
        if precisa_esperar(metadados):
            continue   # a live está agendada ou no ar: fica para a próxima volta
        vistos = lembrar_visto(vistos, video["video_id"])
        if primeira_volta:
            continue
        if float(metadados.get("duration") or 0) < DURACAO_MINIMA_CULTO or not do_canal(metadados, {"id": canal_id}):
            continue
        existente = db.midias.find_one({"organizacao_id": organizacao_id, "importacao.id": video["video_id"],
                                        "status": {"$ne": STATUS_ERRO}}, {"_id": 1})
        if existente:
            continue
        midia = criar_importacao(db, organizacao_id, None, link)
        importados += 1
        logging.info("[%s] Monitor: a live %s terminou. Importação na fila (midia %s).", organizacao_id,
                     video["video_id"], midia["_id"])
    db.organizacoes.update_one({"_id": organizacao_id}, {"$set": {
        "canal_youtube.id": canal_id, "canal_youtube.vistos": vistos, "canal_youtube.primeira_volta": False,
        "canal_youtube.ultima_verificacao": agora(), "canal_youtube.ultimo_erro": None,
    }})
    return importados


def verificar_canais(db) -> int:
    """Chamado pelo laço do worker. Um erro numa igreja fica registrado nela e não para as outras."""
    importados = 0
    while (organizacao := _reservar(db, agora())) is not None:
        canal = organizacao.get("canal_youtube") or {}
        try:
            importados += verificar_canal(db, organizacao["_id"], canal)
        except (requests.RequestException, ErroImportacao, ErroDefinitivo, KeyError) as erro:
            logging.warning("[%s] Monitor do canal falhou: %s", organizacao["_id"], erro)
            db.organizacoes.update_one({"_id": organizacao["_id"]}, {"$set": {
                "canal_youtube.ultima_verificacao": agora(),
                "canal_youtube.ultimo_erro": str(erro)[:300] or "Não foi possível ler o canal.",
            }})
    return importados
