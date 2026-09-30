# -----------------------------------------------
# Tarefa "diagnostico_gpu" — confirma, de dentro do container, que a
# GPU NVIDIA e o Ollama estão acessíveis. Roda no worker de GPU do Nitro 5.
# -----------------------------------------------
import logging
import shutil
import subprocess
from collections.abc import Callable

import requests

from core.config import OLLAMA_URL

TIMEOUT_SEGUNDOS = 30


def consultar_gpus() -> list[dict]:
    """Lista as GPUs vistas pelo nvidia-smi. Lança erro se não houver GPU."""
    if not shutil.which("nvidia-smi"):
        raise RuntimeError("nvidia-smi não encontrado: o container não recebeu a GPU. "
                           "Confira o NVIDIA Container Toolkit e o perfil gpu do compose.")
    resultado = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"],
        capture_output=True, text=True, timeout=TIMEOUT_SEGUNDOS, check=True,
    )
    gpus = []
    for linha in resultado.stdout.strip().splitlines():
        nome, memoria, driver = [parte.strip() for parte in linha.split(",")]
        gpus.append({"nome": nome, "memoria": memoria, "driver": driver})
    return gpus


def consultar_ollama() -> dict | None:
    """Versão e modelos instalados no Ollama, ou None se não responder."""
    try:
        versao = requests.get(f"{OLLAMA_URL}/api/version", timeout=TIMEOUT_SEGUNDOS)
        versao.raise_for_status()
        modelos = requests.get(f"{OLLAMA_URL}/api/tags", timeout=TIMEOUT_SEGUNDOS)
        modelos.raise_for_status()
        return {
            "versao": versao.json().get("version"),
            "modelos": [m.get("name") for m in modelos.json().get("models", [])],
        }
    except Exception as e:
        logging.warning(f"Ollama não respondeu em {OLLAMA_URL}: {e}")
        return None


def executar_diagnostico_gpu(_db, job: dict, reportar: Callable[[int, str], None]) -> dict:
    reportar(10, "Consultando a GPU")
    gpus = consultar_gpus()
    reportar(60, "Consultando o Ollama")
    ollama = consultar_ollama()
    reportar(100, "Diagnóstico pronto")
    return {"gpus": gpus, "ollama": ollama}
