# -----------------------------------------------
# Tarefa "teste" — simula um pipeline completo para validar a fila,
# o heartbeat e o progresso ao vivo no navegador, sem precisar de IA.
# -----------------------------------------------
import time
from collections.abc import Callable

DURACAO_PADRAO_SEGUNDOS = 10
DURACAO_MAXIMA_SEGUNDOS = 60
TOTAL_PASSOS = 20

ETAPAS = [
    "Preparando arquivos",
    "Extraindo áudio (simulado)",
    "Transcrevendo (simulado)",
    "Escolhendo os melhores trechos (simulado)",
    "Renderizando vídeo (simulado)",
]


def executar_teste(_db, job: dict, reportar: Callable[[int, str], None]) -> dict:
    """Avança o progresso em passos. Com entrada.falhar=True, falha no meio de propósito."""
    entrada = job.get("entrada") or {}
    duracao = min(max(float(entrada.get("duracao", DURACAO_PADRAO_SEGUNDOS)), 1), DURACAO_MAXIMA_SEGUNDOS)
    falhar = bool(entrada.get("falhar", False))

    for passo in range(1, TOTAL_PASSOS + 1):
        time.sleep(duracao / TOTAL_PASSOS)
        progresso = round(passo * 100 / TOTAL_PASSOS)
        etapa = ETAPAS[min((passo - 1) * len(ETAPAS) // TOTAL_PASSOS, len(ETAPAS) - 1)]
        if falhar and progresso >= 50:
            raise RuntimeError("Falha simulada no meio do pipeline de teste.")
        reportar(progresso, etapa)

    return {"mensagem": "Pipeline de teste concluído.", "duracao_segundos": duracao}
