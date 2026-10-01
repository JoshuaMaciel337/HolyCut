# -----------------------------------------------
# Tarefa "enquadramento_rosto" — MediaPipe na CPU
# A placa fica livre para o Whisper e para o modelo de linguagem.
# -----------------------------------------------
import logging
import subprocess
from collections.abc import Callable

from bson import ObjectId

from core.config import FFMPEG
from core.modelos.job import ErroDefinitivo
from core.modelos.midia import ARQUIVO_NIVEIS, ARQUIVO_PROXY_VIDEO, NIVEIS_POR_SEGUNDO, chave_arquivo
from core.modelos.momentos import picos_de_energia
from core.modelos.rosto import aplicar_enfases, suavizar
from core.utils import storage
from core.utils.ffmpeg import ErroFFmpeg
from core.utils.mongo import agora

MODELO_ROSTO = "/app/modelos/blaze_face_short_range.tflite"
LARGURA = 320


def _altura_par(largura: int, altura: int) -> int:
    valor = max(int(round(altura * LARGURA / max(largura, 1))), 2)
    return valor if valor % 2 == 0 else valor + 1


def _amostras(caminho, largura_video: int, altura_video: int, reportar) -> list[tuple[float, float, float]]:
    import mediapipe as mp
    import numpy as np

    altura = _altura_par(largura_video, altura_video)
    quadro_bytes = LARGURA * altura * 3
    opcoes = mp.tasks.vision.FaceDetectorOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=MODELO_ROSTO),
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
    )
    processo = subprocess.Popen(
        [FFMPEG, "-hide_banner", "-loglevel", "error", "-i", str(caminho),
         "-vf", f"fps=1,scale={LARGURA}:{altura}", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    amostras = []
    ultimo = (0.5, 0.45)
    segundo = 0
    try:
        with mp.tasks.vision.FaceDetector.create_from_options(opcoes) as detector:
            while True:
                bruto = processo.stdout.read(quadro_bytes)
                if len(bruto) < quadro_bytes:
                    break
                imagem = np.frombuffer(bruto, dtype=np.uint8).reshape((altura, LARGURA, 3)).copy()
                resultado = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=imagem))
                if resultado.detections:
                    caixa = max(resultado.detections,
                                key=lambda item: item.bounding_box.width * item.bounding_box.height)
                    caixa = caixa.bounding_box
                    ultimo = ((caixa.origin_x + caixa.width / 2) / LARGURA,
                              (caixa.origin_y + caixa.height / 2) / altura)
                amostras.append((float(segundo), ultimo[0], ultimo[1]))
                segundo += 1
                if segundo % 30 == 0:
                    reportar(min(90, 10 + segundo // 30), "Seguindo o rosto")
    finally:
        if processo.stdout:
            processo.stdout.close()
        processo.wait(timeout=30)
    if processo.returncode not in (0, None):
        raise ErroFFmpeg(f"Não foi possível ler os quadros para o rosto (código {processo.returncode}).")
    return amostras


def executar_rosto(db, job: dict, reportar: Callable[[int, str], None]) -> dict:
    midia_id = ObjectId(job["entrada"]["midia_id"])
    organizacao_id = job["organizacao_id"]
    midia = db.midias.find_one({"_id": midia_id, "organizacao_id": organizacao_id})
    if midia is None or not midia.get("video"):
        raise ErroDefinitivo("Esta gravação não tem vídeo para reenquadrar.")
    proxy = storage.caminho_local(chave_arquivo(organizacao_id, midia_id, ARQUIVO_PROXY_VIDEO))
    if not proxy.is_file():
        raise ErroDefinitivo("O vídeo de prévia não foi encontrado no servidor.")
    video = midia["video"]
    reportar(5, "Lendo o vídeo")
    try:
        amostras = _amostras(proxy, int(video["largura"]), int(video["altura"]), reportar)
    except ErroFFmpeg as erro:
        raise ErroDefinitivo("Não foi possível seguir o rosto neste vídeo.") from erro
    quadros = suavizar(amostras)
    niveis = storage.caminho_local(chave_arquivo(organizacao_id, midia_id, ARQUIVO_NIVEIS))
    if niveis.is_file():
        import numpy as np
        picos = [(inicio, fim) for inicio, fim, _ in picos_de_energia(np.fromfile(niveis, dtype=np.int8).tolist(),
                                                                     NIVEIS_POR_SEGUNDO)]
        quadros = aplicar_enfases(quadros, picos)
    db.rostos.replace_one(
        {"midia_id": midia_id, "organizacao_id": organizacao_id},
        {"organizacao_id": organizacao_id, "midia_id": midia_id, "quadros": quadros, "criado_em": agora()},
        upsert=True,
    )
    reportar(100, "Rosto marcado")
    logging.info("[%s] [midia %s] %s quadros de rosto.", organizacao_id, midia_id, len(quadros))
    return {"midia_id": str(midia_id), "quadros": len(quadros)}
