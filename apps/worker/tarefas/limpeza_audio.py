# -----------------------------------------------
# Tarefa "limpeza_audio" — tira ruído de ar-condicionado e eco da nave
#
# DeepFilterNet3, um modelo por vez. A faixa limpa cobre a gravação inteira,
# no mesmo tempo do original, para o corte e a prévia continuarem alinhados.
# O modelo sai da memória no fim, para o Whisper caber nos 8 GB.
# -----------------------------------------------
import logging
import os
from collections.abc import Callable
from pathlib import Path

from bson import ObjectId

from core.modelos.job import ErroDefinitivo
from core.modelos.midia import (
    ARQUIVO_AUDIO_LIMPO,
    ARQUIVO_PROXY_LIMPO,
    ARQUIVO_PROXY_VIDEO,
    chave_arquivo,
)
from core.utils import storage
from core.utils.ffmpeg import ErroFFmpeg, executar_ffmpeg, sondar
from core.utils.limpeza import SOBREPOSICAO_SEGUNDOS, TOLERANCIA_DURACAO_SEGUNDOS, fatias
from core.utils.mongo import agora
from worker.tarefas.transcricao import esvaziar_memoria_da_gpu


def _duracao(caminho: Path) -> float:
    info = sondar(caminho)
    try:
        return float(info.get("format", {}).get("duration") or 0)
    except (TypeError, ValueError):
        return 0.0


def _limpar_amostras(audio, model, estado, reportar: Callable[[int, str], None]):
    """Limpa em pedaços e mistura a sobreposição. O tensor de entrada fica na CPU."""
    import torch

    taxa = estado.sr()
    if audio.dim() == 1:
        audio = audio.unsqueeze(0)
    if audio.shape[0] > 1:
        audio = audio.mean(dim=0, keepdim=True)
    total = int(audio.shape[1])
    pedacos = fatias(total, taxa)
    saida = torch.zeros(1, total)
    peso = torch.zeros(1, total)
    sobreposicao = int(taxa * SOBREPOSICAO_SEGUNDOS)
    from df.enhance import enhance

    for indice, (inicio, fim) in enumerate(pedacos):
        limpo = enhance(model, estado, audio[:, inicio:fim])
        while limpo.dim() > 2:
            limpo = limpo.squeeze(0)
        if limpo.dim() == 1:
            limpo = limpo.unsqueeze(0)
        limpo = limpo.detach().float().cpu()
        n = fim - inicio
        if limpo.shape[-1] > n:
            limpo = limpo[:, :n]
        elif limpo.shape[-1] < n:
            limpo = torch.nn.functional.pad(limpo, (0, n - limpo.shape[-1]))
        w = torch.ones(1, n)
        if inicio > 0 and n > sobreposicao:
            w[:, :sobreposicao] = torch.linspace(0, 1, sobreposicao)
        if fim < total and n > sobreposicao:
            w[:, -sobreposicao:] = torch.linspace(1, 0, sobreposicao)
        saida[:, inicio:fim] += limpo * w
        peso[:, inicio:fim] += w
        reportar(10 + int(75 * (indice + 1) / max(len(pedacos), 1)), "Limpando o áudio")
    return saida / peso.clamp(min=1e-6)


def _gerar_faixa(origem: Path, destino: Path, reportar: Callable[[int, str], None]) -> None:
    import torch
    import torchaudio
    from df.enhance import init_df

    if not torch.cuda.is_available():
        raise ErroDefinitivo("A limpeza de áudio precisa da placa de vídeo, e ela não está disponível.")
    reportar(8, "Carregando o modelo")
    model = None
    estado = None
    parcial = destino.with_name("audio_limpo.parcial.wav")
    try:
        # Esta versão do pacote devolve modelo, estado e sufixo. O estado carrega a taxa.
        model, estado, _ = init_df(post_filter=False, log_level="INFO", log_file=None)
        dispositivo = next(model.parameters()).device
        if dispositivo.type != "cuda":
            raise ErroDefinitivo("A limpeza de áudio precisa da placa de vídeo, e ela não está disponível.")
        audio, taxa = torchaudio.load(str(origem))
        if taxa != estado.sr():
            audio = torchaudio.functional.resample(audio, taxa, estado.sr())
        limpo = _limpar_amostras(audio, model, estado, reportar)
        destino.parent.mkdir(parents=True, exist_ok=True)
        torchaudio.save(str(parcial), limpo, estado.sr(), encoding="PCM_S", bits_per_sample=16)
        os.replace(parcial, destino)
    finally:
        del model, estado
        esvaziar_memoria_da_gpu()
        parcial.unlink(missing_ok=True)


def _remixar_previa(proxy: Path, faixa: Path, destino: Path, duracao: float,
                    reportar: Callable[[int, str], None]) -> None:
    """Vídeo do proxy, sem reencodar, com o áudio limpo. A linha do tempo não muda."""
    parcial = destino.with_name("proxy_limpo.parcial.mp4")
    executar_ffmpeg([
        "-i", str(proxy), "-i", str(faixa),
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
        "-shortest", "-movflags", "+faststart", str(parcial),
    ], duracao, lambda fracao: reportar(88 + int(fracao * 10), "Preparando a prévia"))
    os.replace(parcial, destino)


def executar_limpeza_audio(db, job: dict, reportar: Callable[[int, str], None]) -> dict:
    midia_id = ObjectId(job["entrada"]["midia_id"])
    organizacao_id = job["organizacao_id"]
    midia = db.midias.find_one({"_id": midia_id, "organizacao_id": organizacao_id})
    if midia is None:
        raise ErroDefinitivo("A gravação foi excluída antes da limpeza.")
    if not midia.get("audio"):
        raise ErroDefinitivo("Esta gravação não tem áudio para limpar.")
    original = storage.caminho_local(chave_arquivo(organizacao_id, midia_id, midia["original"]))
    if not original.is_file():
        raise ErroDefinitivo("O arquivo original da gravação não foi encontrado no servidor.")

    destino = storage.caminho_local(chave_arquivo(organizacao_id, midia_id, ARQUIVO_AUDIO_LIMPO))
    bruto = destino.with_name("audio_48k.wav")
    esperada = float(midia.get("duracao") or 0)
    try:
        if not destino.is_file() or abs(_duracao(destino) - esperada) > TOLERANCIA_DURACAO_SEGUNDOS:
            reportar(2, "Separando o áudio")
            executar_ffmpeg([
                "-i", str(original), "-vn", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(bruto),
            ], esperada or None, lambda fracao: reportar(2 + int(fracao * 6), "Separando o áudio"))
            _gerar_faixa(bruto, destino, reportar)
        duracao = _duracao(destino)
        if abs(duracao - esperada) > TOLERANCIA_DURACAO_SEGUNDOS:
            destino.unlink(missing_ok=True)
            raise ErroDefinitivo("O áudio limpo ficou com duração diferente da gravação.")

        nomes = [ARQUIVO_AUDIO_LIMPO]
        proxy = storage.caminho_local(chave_arquivo(organizacao_id, midia_id, ARQUIVO_PROXY_VIDEO))
        if ARQUIVO_PROXY_VIDEO in (midia.get("arquivos") or []) and proxy.is_file():
            previa = storage.caminho_local(chave_arquivo(organizacao_id, midia_id, ARQUIVO_PROXY_LIMPO))
            reportar(88, "Preparando a prévia")
            _remixar_previa(proxy, destino, previa, duracao, reportar)
            nomes.append(ARQUIVO_PROXY_LIMPO)

        db.midias.update_one(
            {"_id": midia_id, "organizacao_id": organizacao_id},
            {"$addToSet": {"arquivos": {"$each": nomes}}, "$set": {"atualizado_em": agora()}},
        )
        reportar(100, "Áudio limpo")
        logging.info("[%s] [midia %s] Limpeza de áudio pronta (%.1f s).", organizacao_id, midia_id, duracao)
        return {"midia_id": str(midia_id), "arquivos": nomes}
    except ErroDefinitivo:
        raise
    except ErroFFmpeg as erro:
        logging.error("[%s] [midia %s] Falha ao preparar o áudio limpo: %s", organizacao_id, midia_id, erro)
        raise ErroDefinitivo("Não foi possível preparar o áudio limpo.") from erro
    finally:
        bruto.unlink(missing_ok=True)
        esvaziar_memoria_da_gpu()
