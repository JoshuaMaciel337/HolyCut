# -----------------------------------------------
# Tarefa "ingestao" — prepara a gravação enviada para o editor
#
#   1. ffprobe: duração, resolução, fps e áudio
#   2. uma passada do FFmpeg gera a cópia leve (proxy 720p) e o áudio de
#      análise (WAV 16 kHz mono, usado depois na transcrição e nos silêncios)
#   3. forma de onda: picos do áudio, 20 por segundo
#   4. miniaturas em uma única imagem (sprite) e a capa
# -----------------------------------------------
import json
import logging
import math
import wave
from collections.abc import Callable
from pathlib import Path

import numpy as np
from bson import ObjectId

from core.modelos.job import ErroDefinitivo
from core.modelos.midia import (
    ARQUIVO_AUDIO_ANALISE,
    ARQUIVO_CAPA,
    ARQUIVO_FORMA_DE_ONDA,
    ARQUIVO_MINIATURAS,
    ARQUIVO_PROXY_AUDIO,
    ARQUIVO_PROXY_VIDEO,
    STATUS_ERRO,
    STATUS_PROCESSANDO,
    STATUS_PRONTA,
    chave_arquivo,
)
from core.utils import storage
from core.utils.ffmpeg import ErroFFmpeg, executar_ffmpeg, resumir_sondagem, sondar
from core.utils.mongo import agora

# -----------------------------------------------
# CONFIGURAÇÕES
# -----------------------------------------------
LADO_MENOR_PROXY = 720
FPS_MAXIMO_PROXY = 30
PICOS_POR_SEGUNDO = 20
LARGURA_MINIATURA = 160
COLUNAS_MINIATURAS = 10
MIN_MINIATURAS, MAX_MINIATURAS = 10, 100
SEGUNDOS_POR_MINIATURA = 10
LARGURA_CAPA = 640

# Reduz o lado menor para 720 sem aumentar vídeos menores, sempre com dimensões pares
FILTRO_PROXY = (
    "scale=w='if(gte(iw,ih),-2,trunc(min(720,iw)/2)*2)'"
    ":h='if(gte(iw,ih),trunc(min(720,ih)/2)*2,-2)',setsar=1"
)


# -----------------------------------------------
# FUNÇÕES AUXILIARES
# -----------------------------------------------
def calcular_forma_de_onda(caminho_wav: Path, por_segundo: int = PICOS_POR_SEGUNDO) -> dict:
    """Pico de cada janela de 1/por_segundo s, em % do volume máximo possível (0 a 100)."""
    picos: list[int] = []
    with wave.open(str(caminho_wav), "rb") as wav:
        if wav.getsampwidth() != 2:
            raise ValueError("A forma de onda espera áudio PCM de 16 bits.")
        canais = wav.getnchannels()
        janela = max(wav.getframerate() // por_segundo, 1)
        frames_por_bloco = janela * por_segundo * 60  # lê 1 minuto por vez
        while dados := wav.readframes(frames_por_bloco):
            amostras = np.abs(np.frombuffer(dados, dtype="<i2").astype(np.int32))
            if canais > 1:
                amostras = amostras[: len(amostras) // canais * canais].reshape(-1, canais).max(axis=1)
            completas = len(amostras) // janela
            if completas:
                picos.extend(amostras[: completas * janela].reshape(completas, janela).max(axis=1).tolist())
            if len(amostras) % janela:
                picos.append(int(amostras[completas * janela:].max()))
    return {
        "versao": 1,
        "picos_por_segundo": por_segundo,
        "picos": [min(round(p * 100 / 32767), 100) for p in picos],
    }


def planejar_miniaturas(duracao: float) -> dict:
    """Quantas miniaturas gerar e de quanto em quanto tempo."""
    total = min(max(round(duracao / SEGUNDOS_POR_MINIATURA), MIN_MINIATURAS), MAX_MINIATURAS)
    return {
        "total": total,
        "colunas": COLUNAS_MINIATURAS,
        "linhas": math.ceil(total / COLUNAS_MINIATURAS),
        "intervalo": duracao / total,
    }


def marcar_midia_com_erro(db, job: dict, mensagem: str):
    """Chamado quando a ingestão falha de vez: a mídia mostra o erro para a igreja."""
    midia_id = (job.get("entrada") or {}).get("midia_id")
    if not midia_id:
        return
    db.midias.update_one({"_id": ObjectId(midia_id)}, {"$set": {
        "status": STATUS_ERRO, "erro": mensagem, "atualizado_em": agora(),
    }})


# -----------------------------------------------
# FUNÇÃO PRINCIPAL
# -----------------------------------------------
def executar_ingestao(db, job: dict, reportar: Callable[[int, str], None]) -> dict:
    midia_id = ObjectId(job["entrada"]["midia_id"])
    midia = db.midias.find_one({"_id": midia_id})
    if midia is None:
        raise ErroDefinitivo("A mídia foi excluída antes do processamento.")
    organizacao_id = midia["organizacao_id"]

    def caminho(nome: str) -> Path:
        return storage.caminho_local(chave_arquivo(organizacao_id, midia_id, nome))

    original = caminho(midia["original"])
    if not original.is_file():
        raise ErroDefinitivo("O arquivo enviado não foi encontrado no servidor. Envie de novo.")
    db.midias.update_one({"_id": midia_id}, {"$set": {
        "status": STATUS_PROCESSANDO, "erro": None, "atualizado_em": agora(),
    }})
    rotulo = f"[{organizacao_id}] [midia {midia_id}]"

    # 1. Leitura
    reportar(2, "Lendo o arquivo")
    try:
        resumo = resumir_sondagem(sondar(original))
    except ErroFFmpeg as e:
        raise ErroDefinitivo("O arquivo não é um vídeo ou áudio válido. Confira se ele abre no computador.") from e
    duracao, tem_video, tem_audio = resumo["duracao"], resumo["video"] is not None, resumo["audio"] is not None
    if not duracao or not (tem_video or tem_audio):
        raise ErroDefinitivo("O arquivo não tem vídeo nem áudio que dê para usar.")
    logging.info(f"{rotulo} {duracao:.0f}s, vídeo={resumo['video']}, áudio={resumo['audio']}")

    # 2. Cópia leve e áudio de análise, numa passada só
    arquivos = []
    argumentos = ["-i", str(original)]
    if tem_video:
        argumentos += ["-map", "0:v:0", "-map", "0:a:0?", "-vf", FILTRO_PROXY, "-fpsmax", str(FPS_MAXIMO_PROXY),
                       "-c:v", "libx264", "-preset", "veryfast", "-crf", "28", "-pix_fmt", "yuv420p",
                       "-g", str(FPS_MAXIMO_PROXY * 2), "-c:a", "aac", "-b:a", "128k", "-ac", "2",
                       "-movflags", "+faststart", str(caminho(ARQUIVO_PROXY_VIDEO))]
        arquivos.append(ARQUIVO_PROXY_VIDEO)
    else:
        argumentos += ["-map", "0:a:0", "-vn", "-c:a", "aac", "-b:a", "128k", "-ac", "2",
                       "-movflags", "+faststart", str(caminho(ARQUIVO_PROXY_AUDIO))]
        arquivos.append(ARQUIVO_PROXY_AUDIO)
    if tem_audio:
        argumentos += ["-map", "0:a:0", "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
                       str(caminho(ARQUIVO_AUDIO_ANALISE))]
    executar_ffmpeg(argumentos, duracao, lambda f: reportar(5 + int(f * 70), "Gerando a cópia leve do vídeo"))
    if tem_audio:
        arquivos.append(ARQUIVO_AUDIO_ANALISE)  # uso interno: a API não serve este arquivo

    # 3. Forma de onda
    if tem_audio:
        reportar(78, "Desenhando a forma de onda")
        forma = calcular_forma_de_onda(caminho(ARQUIVO_AUDIO_ANALISE))
        storage.salvar_bytes(chave_arquivo(organizacao_id, midia_id, ARQUIVO_FORMA_DE_ONDA),
                             json.dumps(forma, separators=(",", ":")).encode())
        arquivos.append(ARQUIVO_FORMA_DE_ONDA)

    # 4. Miniaturas e capa, a partir da cópia leve
    miniaturas = None
    if tem_video:
        plano = planejar_miniaturas(duracao)
        proxy = str(caminho(ARQUIVO_PROXY_VIDEO))
        executar_ffmpeg(
            ["-i", proxy, "-an", "-vf",
             f"fps={plano['total']}/{duracao:.3f},scale={LARGURA_MINIATURA}:-2,"
             f"tile={plano['colunas']}x{plano['linhas']}",
             "-frames:v", "1", "-q:v", "5", "-update", "1", str(caminho(ARQUIVO_MINIATURAS))],
            duracao, lambda f: reportar(85 + int(f * 10), "Gerando as miniaturas"),
        )
        sprite = resumir_sondagem(sondar(caminho(ARQUIVO_MINIATURAS)))["video"]
        miniaturas = {**plano, "largura": sprite["largura"] // plano["colunas"],
                      "altura": sprite["altura"] // plano["linhas"]}
        arquivos.append(ARQUIVO_MINIATURAS)

        reportar(97, "Escolhendo a capa")
        executar_ffmpeg(["-ss", f"{min(duracao * 0.1, 30):.2f}", "-i", proxy, "-frames:v", "1",
                         "-vf", f"scale={LARGURA_CAPA}:-2", "-q:v", "3", "-update", "1",
                         str(caminho(ARQUIVO_CAPA))])
        arquivos.append(ARQUIVO_CAPA)

    momento = agora()
    db.midias.update_one({"_id": midia_id}, {"$set": {
        "status": STATUS_PRONTA,
        "duracao": duracao,
        "video": resumo["video"],
        "audio": resumo["audio"],
        "arquivos": arquivos,
        "miniaturas": miniaturas,
        "erro": None,
        "processado_em": momento,
        "atualizado_em": momento,
    }})
    reportar(100, "Pronta para editar")
    return {"midia_id": str(midia_id), "duracao": duracao, "arquivos": arquivos}
