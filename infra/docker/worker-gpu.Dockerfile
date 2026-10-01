# HolyCut worker de GPU — a mesma fila, com PyTorch, faster-whisper e WhisperX.
# O worker de CPU continua na imagem leve (worker.Dockerfile).
FROM python:3.11-slim-bookworm

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg gosu tzdata \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    TZ=America/Sao_Paulo \
    HF_HOME=/cache/huggingface \
    HUGGINGFACE_HUB_CACHE=/cache/huggingface \
    XDG_CACHE_HOME=/cache/huggingface

WORKDIR /app
COPY apps/worker/requirements.txt /tmp/requirements.txt
COPY apps/worker/requirements-gpu.txt /tmp/requirements-gpu.txt
# O torch com CUDA vem primeiro. O WhisperX e o DeepFilterNet não podem trocá-lo pela versão de CPU.
RUN pip install --no-cache-dir -r /tmp/requirements.txt \
 && pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cu124 torch \
 && pip install --no-cache-dir -r /tmp/requirements-gpu.txt \
 && pip install --no-cache-dir --force-reinstall --no-deps --index-url https://download.pytorch.org/whl/cu124 "torchaudio==2.6.0" \
 && python -c "import torch, torchaudio; assert torch.version.cuda, 'O PyTorch ficou sem CUDA'; import df.enhance"

COPY core /app/core
COPY apps/worker /app/worker
COPY infra/backup /app/backup
COPY brand/fontes /app/brand/fontes

RUN useradd --create-home --uid 1000 holycut \
 && mkdir -p /dados/armazenamento /dados/backups /cache/huggingface \
 && chown -R holycut /dados /cache
COPY infra/docker/entrar-como-holycut.sh /usr/local/bin/entrar-como-holycut
RUN chmod +x /usr/local/bin/entrar-como-holycut

# Sobe como root só para entregar o cache do modelo ao usuário holycut. O worker em si não fica como root.
ENTRYPOINT ["entrar-como-holycut"]
CMD ["python", "-m", "worker.worker_principal", "--automatico", "--recursos", "gpu"]
