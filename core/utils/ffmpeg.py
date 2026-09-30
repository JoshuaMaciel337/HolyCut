# -----------------------------------------------
# HolyCut — execução do FFmpeg e do ffprobe
# -----------------------------------------------
import json
import logging
import subprocess
import threading
from collections import deque
from collections.abc import Callable
from pathlib import Path

from core.config import FFMPEG, FFPROBE

TIMEOUT_FFPROBE_SEGUNDOS = 60
LINHAS_ERRO_GUARDADAS = 15


class ErroFFmpeg(RuntimeError):
    pass


def sondar(caminho: Path) -> dict:
    """Metadados do arquivo pelo ffprobe (formato e streams)."""
    resultado = subprocess.run(
        [FFPROBE, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(caminho)],
        capture_output=True, text=True, timeout=TIMEOUT_FFPROBE_SEGUNDOS,
    )
    if resultado.returncode != 0:
        raise ErroFFmpeg(f"O arquivo não pôde ser lido como vídeo ou áudio: {resultado.stderr.strip()[-300:]}")
    return json.loads(resultado.stdout or "{}")


def _fracao(valor: str) -> float | None:
    """'30000/1001' → 29.97. None se inválido."""
    numerador, _, denominador = valor.partition("/")
    try:
        divisor = float(denominador) if denominador else 1.0
        return round(float(numerador) / divisor, 3) if divisor else None
    except ValueError:
        return None


def resumir_sondagem(sondagem: dict) -> dict:
    """Extrai duração e as características do primeiro vídeo e do primeiro áudio."""
    streams = sondagem.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"
                  and not (s.get("disposition") or {}).get("attached_pic")), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    duracao = float((sondagem.get("format") or {}).get("duration") or 0) or None

    resumo = {"duracao": duracao, "video": None, "audio": None}
    if video:
        largura, altura = int(video.get("width") or 0), int(video.get("height") or 0)
        rotacao = _rotacao(video)
        if rotacao in (90, 270):
            largura, altura = altura, largura
        resumo["video"] = {
            "codec": video.get("codec_name"),
            "largura": largura,
            "altura": altura,
            "fps": _fracao(video.get("avg_frame_rate") or "") or _fracao(video.get("r_frame_rate") or ""),
            "rotacao": rotacao,
        }
    if audio:
        resumo["audio"] = {
            "codec": audio.get("codec_name"),
            "canais": int(audio.get("channels") or 0),
            "taxa": int(audio.get("sample_rate") or 0),
        }
    return resumo


def _rotacao(video: dict) -> int:
    """Rotação gravada pelo celular, em graus positivos (0, 90, 180 ou 270)."""
    rotacao = (video.get("tags") or {}).get("rotate")
    for dado in video.get("side_data_list") or []:
        if "rotation" in dado:
            rotacao = dado["rotation"]
    try:
        return int(float(rotacao or 0)) % 360
    except (TypeError, ValueError):
        return 0


def ler_progresso(linha: str) -> float | None:
    """Segundos já processados, a partir de uma linha do -progress do FFmpeg."""
    chave, _, valor = linha.strip().partition("=")
    if chave in ("out_time_us", "out_time_ms") and valor.isdigit():
        return int(valor) / 1_000_000  # as duas chaves vêm em microssegundos
    return None


def executar_ffmpeg(argumentos: list[str], duracao: float | None = None,
                    reportar: Callable[[float], None] | None = None) -> None:
    """
    Roda o FFmpeg com os argumentos dados. Se houver duração e reportar,
    chama reportar(fração de 0 a 1) conforme o arquivo avança.
    Lança ErroFFmpeg com o final da saída de erro se o comando falhar.
    """
    comando = [FFMPEG, "-hide_banner", "-nostdin", "-y", "-progress", "pipe:1", "-nostats", *argumentos]
    logging.debug("FFmpeg: " + " ".join(comando))
    processo = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, encoding="utf-8", errors="replace")
    ultimas_linhas: deque[str] = deque(maxlen=LINHAS_ERRO_GUARDADAS)

    def guardar_erros():
        for linha in processo.stderr:
            if linha.strip():
                ultimas_linhas.append(linha.rstrip())

    leitor = threading.Thread(target=guardar_erros, daemon=True)
    leitor.start()
    for linha in processo.stdout:
        segundos = ler_progresso(linha)
        if segundos is not None and duracao and reportar:
            reportar(min(max(segundos / duracao, 0.0), 1.0))
    codigo = processo.wait()
    leitor.join(timeout=5)
    if codigo != 0:
        raise ErroFFmpeg(f"FFmpeg terminou com código {codigo}: " + " | ".join(ultimas_linhas)[-600:])
