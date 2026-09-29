# HolyCut worker — fila de jobs e backup. FFmpeg incluído.
# O worker de GPU usa esta mesma imagem por enquanto. Na Fase 1 ele ganha
# uma imagem própria com PyTorch, WhisperX e CUDA.
FROM python:3.11-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg tzdata \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    TZ=America/Sao_Paulo

WORKDIR /app
COPY apps/worker/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

COPY core /app/core
COPY apps/worker /app/worker
COPY infra/backup /app/backup

RUN useradd --create-home --uid 1000 holycut && mkdir -p /dados/armazenamento /dados/backups && chown -R holycut /dados
USER holycut

CMD ["python", "-m", "worker.worker_principal", "--automatico", "--recursos", "cpu"]
