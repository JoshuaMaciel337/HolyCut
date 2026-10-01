# HolyCut worker — fila de jobs e backup. FFmpeg incluído.
# O worker de GPU usa infra/docker/worker-gpu.Dockerfile (PyTorch, WhisperX e CUDA).
FROM python:3.11-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg tzdata libglib2.0-0 libgl1 \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    TZ=America/Sao_Paulo

WORKDIR /app
COPY apps/worker/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
 && pip install --no-cache-dir mediapipe \
 && mkdir -p /app/modelos \
 && python -c "import urllib.request; urllib.request.urlretrieve('https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite', '/app/modelos/blaze_face_short_range.tflite')"

COPY core /app/core
COPY apps/worker /app/worker
COPY infra/backup /app/backup
# Fontes da marca, para desenhar textos e templates (licença OFL)
COPY brand/fontes /app/brand/fontes

RUN useradd --create-home --uid 1000 holycut && mkdir -p /dados/armazenamento /dados/backups && chown -R holycut /dados
USER holycut

CMD ["python", "-m", "worker.worker_principal", "--automatico", "--recursos", "cpu"]
