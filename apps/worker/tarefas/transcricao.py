# -----------------------------------------------
# Tarefa "transcricao" — a fala da gravação, em português, com o tempo de cada palavra
#
# faster-whisper (large-v3-turbo, int8, cerca de 3 GB) ouve o áudio de análise.
# O WhisperX alinha o tempo de cada palavra e é descarregado em seguida:
# com 8 GB de VRAM cabe um modelo por vez.
# O texto não é corrigido. O que o pregador disse fica como ele disse.
# -----------------------------------------------
import gc
import logging
import tempfile
from collections.abc import Callable
from pathlib import Path

from bson import ObjectId

from core.config import MODO_IA
from core.modelos.culto import ficha_do_culto
from core.modelos.job import ErroDefinitivo
from core.modelos.midia import ARQUIVO_AUDIO_ANALISE, chave_arquivo
from core.modelos.sermon import palavras_do_documento
from core.modelos.transcricao import (
    MODELO,
    com_deslocamento,
    dicas_da_igreja,
    fatias_de,
    montar_segmentos,
    montar_transcricao,
)
from core.modelos.versiculo import detectar_versiculos
from core.utils import storage
from core.utils.fila import (
    enfileirar_blocos,
    enfileirar_estudo,
    enfileirar_momentos,
    enfileirar_rosto,
    enfileirar_sugestao,
)
from core.utils.mongo import agora


# -----------------------------------------------
# FUNÇÕES AUXILIARES
# -----------------------------------------------
def esvaziar_memoria_da_gpu():
    """Solta o modelo antes de carregar o próximo. Sem isso os 8 GB não chegam para os dois."""
    gc.collect()
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except Exception:
        logging.debug("Não foi possível esvaziar a memória da GPU.", exc_info=True)


def _palavras_do_faster(segmento) -> list[dict]:
    palavras = []
    for palavra in segmento.words or []:
        palavras.append({
            "texto": palavra.word or "",
            "inicio": palavra.start,
            "fim": palavra.end,
            "confianca": palavra.probability,
        })
    return palavras


def _ouvir_arquivo(modelo, caminho, dicas: dict, inicio: float, duracao: float,
                   reportar: Callable[[int, str], None]) -> tuple[list[dict], str]:
    """Ouve uma fatia. Os tempos voltam relativos ao começo dela."""
    segmentos, info = modelo.transcribe(
        str(caminho),
        language="pt",
        vad_filter=True,
        word_timestamps=True,
        condition_on_previous_text=False,
        initial_prompt=dicas["initial_prompt"],
        hotwords=dicas["hotwords"] or None,
        beam_size=5,
    )
    brutos = []
    for segmento in segmentos:
        brutos.append({
            "texto": segmento.text or "",
            "inicio": segmento.start,
            "fim": segmento.end,
            "palavras": _palavras_do_faster(segmento),
        })
        if duracao:
            absoluto = inicio + (segmento.end or 0)
            reportar(min(68, 10 + int(58 * absoluto / duracao)), "Transcrevendo")
    return brutos, info.language or "pt"


def _extrair_fatia(origem, destino: Path, inicio: float, fim: float) -> None:
    from core.utils.ffmpeg import ErroFFmpeg, executar_ffmpeg

    try:
        executar_ffmpeg([
            "-ss", f"{inicio:.3f}", "-to", f"{fim:.3f}", "-i", str(origem),
            "-c", "copy", str(destino),
        ])
    except ErroFFmpeg as erro:
        raise ErroDefinitivo("Não foi possível separar um trecho do áudio para transcrever.") from erro


def _juntar(pecas: list[tuple[float, list[dict]]]) -> list[dict]:
    todos = []
    for inicio, brutos in pecas:
        todos.extend(com_deslocamento(brutos, inicio))
    return todos


def transcrever(caminho, dicas: dict, duracao: float | None,
                reportar: Callable[[int, str], None]) -> tuple[list[dict], str]:
    """Ouve o WAV em fatias de 10 min. O modelo sai da memória no fim, antes do alinhamento."""
    import ctranslate2
    from faster_whisper import WhisperModel

    if ctranslate2.get_cuda_device_count() < 1:
        raise ErroDefinitivo("A GPU não está disponível para a transcrição. Rode o diagnóstico da GPU.")

    fatias = fatias_de(duracao or 0)
    reportar(5, "Carregando o modelo de transcrição")
    modelo = WhisperModel(MODELO, device="cuda", compute_type="int8")
    pecas: list[tuple[float, list[dict]]] = []
    idioma = "pt"
    try:
        with tempfile.TemporaryDirectory(prefix="holycut-fala-") as pasta:
            for indice, (inicio, fim) in enumerate(fatias):
                reportar(
                    8 + int(4 * indice / max(len(fatias), 1)),
                    f"Transcrevendo o trecho {indice + 1} de {len(fatias)}",
                )
                logging.info("Transcrevendo o trecho %s de %s (%.0f–%.0f s).", indice + 1, len(fatias), inicio, fim)
                if len(fatias) == 1:
                    arquivo = caminho
                else:
                    arquivo = Path(pasta) / f"fatia-{indice:02d}.wav"
                    _extrair_fatia(caminho, arquivo, inicio, fim)
                brutos, idioma = _ouvir_arquivo(modelo, arquivo, dicas, inicio, duracao or fim, reportar)
                pecas.append((inicio, brutos))
    finally:
        del modelo
        esvaziar_memoria_da_gpu()
    return _juntar(pecas), idioma


def _segmentos_alinhados(resultado: dict) -> list[dict]:
    alinhados = []
    for segmento in resultado.get("segments") or []:
        palavras = []
        for palavra in segmento.get("words") or []:
            palavras.append({
                "texto": palavra.get("word") or "",
                "inicio": palavra.get("start"),
                "fim": palavra.get("end"),
                "confianca": palavra.get("score"),
            })
        alinhados.append({
            "texto": segmento.get("text") or "",
            "inicio": segmento.get("start"),
            "fim": segmento.get("end"),
            "palavras": palavras,
        })
    return alinhados


def alinhar_palavras(brutos: list[dict], caminho, reportar: Callable[[int, str], None],
                     duracao: float | None = None) -> list[dict]:
    """Tempo de cada palavra pelo WhisperX, também em fatias. O modelo é descarregado no fim."""
    import whisperx

    fatias = fatias_de(duracao or 0)
    if len(fatias) <= 1:
        reportar(72, "Alinhando o tempo de cada palavra")
        audio = whisperx.load_audio(str(caminho))
        modelo, metadados = whisperx.load_align_model(language_code="pt", device="cuda")
        try:
            return _segmentos_alinhados(whisperx.align(
                [{"text": segmento["texto"], "start": segmento["inicio"], "end": segmento["fim"]}
                 for segmento in brutos],
                modelo, metadados, audio, "cuda", return_char_alignments=False,
            ))
        finally:
            del modelo
            esvaziar_memoria_da_gpu()

    reportar(72, "Alinhando o tempo de cada palavra")
    modelo, metadados = whisperx.load_align_model(language_code="pt", device="cuda")
    try:
        with tempfile.TemporaryDirectory(prefix="holycut-alinha-") as pasta:
            alinhados = []
            for indice, (inicio, fim) in enumerate(fatias):
                da_fatia = [segmento for segmento in brutos if inicio <= (segmento.get("inicio") or 0) < fim]
                if not da_fatia:
                    continue
                arquivo = Path(pasta) / f"fatia-{indice:02d}.wav"
                _extrair_fatia(caminho, arquivo, inicio, fim)
                duracao_fatia = fim - inicio
                relativos = []
                for segmento in com_deslocamento(da_fatia, -inicio):
                    fim_relativo = min(segmento["fim"], duracao_fatia)
                    if fim_relativo <= (segmento["inicio"] or 0):
                        continue
                    palavras = [palavra for palavra in segmento["palavras"]
                                if palavra.get("inicio") is None or palavra["inicio"] < duracao_fatia]
                    relativos.append({**segmento, "fim": fim_relativo, "palavras": palavras})
                if not relativos:
                    continue
                audio = whisperx.load_audio(str(arquivo))
                resultado = whisperx.align(
                    [{"text": segmento["texto"], "start": segmento["inicio"], "end": segmento["fim"]}
                     for segmento in relativos],
                    modelo, metadados, audio, "cuda", return_char_alignments=False,
                )
                alinhados.extend(com_deslocamento(_segmentos_alinhados(resultado), inicio))
                reportar(72 + int(22 * (indice + 1) / len(fatias)), "Alinhando o tempo de cada palavra")
            return alinhados
    finally:
        del modelo
        esvaziar_memoria_da_gpu()


# -----------------------------------------------
# FUNÇÃO PRINCIPAL
# -----------------------------------------------
def executar_transcricao(db, job: dict, reportar: Callable[[int, str], None]) -> dict:
    midia_id = ObjectId(job["entrada"]["midia_id"])
    midia = db.midias.find_one({"_id": midia_id})
    if midia is None:
        raise ErroDefinitivo("A mídia foi excluída antes da transcrição.")
    if not midia.get("audio"):
        raise ErroDefinitivo("Esta gravação não tem áudio para transcrever.")
    if ARQUIVO_AUDIO_ANALISE not in (midia.get("arquivos") or []):
        raise ErroDefinitivo("O áudio de análise ainda não foi gerado. Envie a gravação de novo.")

    organizacao_id = midia["organizacao_id"]
    caminho = storage.caminho_local(chave_arquivo(organizacao_id, midia_id, ARQUIVO_AUDIO_ANALISE))
    if not caminho.is_file():
        raise ErroDefinitivo("O áudio de análise não foi encontrado no servidor.")

    organizacao = db.organizacoes.find_one({"_id": organizacao_id}) or {}
    identidade = organizacao.get("identidade") or {}
    ficha = ficha_do_culto(midia)
    nome_igreja = identidade.get("nome_exibicao") or organizacao.get("nome") or ""
    dicas = dicas_da_igreja(nome_igreja, ficha.get("pregador") or "")
    duracao = midia.get("duracao") or 0
    rotulo = f"[{organizacao_id}] [midia {midia_id}]"

    brutos, idioma = transcrever(caminho, dicas, duracao, reportar)
    try:
        brutos = alinhar_palavras(brutos, caminho, reportar, duracao)
    except Exception as e:
        logging.warning(f"{rotulo} O alinhamento por palavra falhou. Fica o tempo do Whisper: {e}")

    segmentos = montar_segmentos(brutos)
    documento = montar_transcricao(organizacao_id, midia_id, segmentos, midia.get("duracao"), agora(), idioma=idioma)
    documento["versiculos"] = detectar_versiculos(palavras_do_documento(documento))
    db.transcricoes.replace_one({"midia_id": midia_id}, documento, upsert=True)
    palavras = sum(len(segmento["palavras"]) for segmento in segmentos)
    logging.info(f"{rotulo} Transcrição pronta: {len(segmentos)} trechos, {palavras} palavras, "
                 f"{len(documento['versiculos'])} versículos.")
    if palavras and MODO_IA == "real":
        # Os blocos vêm primeiro: com a pregação marcada, os cortes e o estudo leem só a mensagem
        enfileirar_blocos(db, organizacao_id, str(midia_id))
        enfileirar_sugestao(db, organizacao_id, str(midia_id))
        enfileirar_estudo(db, organizacao_id, str(midia_id))
        enfileirar_momentos(db, organizacao_id, str(midia_id))
        if midia.get("video"):
            enfileirar_rosto(db, organizacao_id, str(midia_id))
    reportar(100, "Transcrição pronta")
    return {"midia_id": str(midia_id), "segmentos": len(segmentos), "palavras": palavras}
