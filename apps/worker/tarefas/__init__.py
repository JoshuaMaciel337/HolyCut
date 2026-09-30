from collections.abc import Callable
from dataclasses import dataclass

from worker.tarefas.diagnostico_gpu import executar_diagnostico_gpu
from worker.tarefas.ingestao import executar_ingestao, marcar_midia_com_erro
from worker.tarefas.teste import executar_teste


@dataclass(frozen=True)
class Tarefa:
    # executar(db, job, reportar) -> saída do job
    executar: Callable
    # ao_falhar(db, job, mensagem): chamado quando o job vai para erro sem mais tentativas
    ao_falhar: Callable | None = None


# Tipo de job → tarefa. Os tipos e recursos ficam em core/modelos/job.py.
REGISTRO = {
    "teste": Tarefa(executar_teste),
    "diagnostico_gpu": Tarefa(executar_diagnostico_gpu),
    "ingestao": Tarefa(executar_ingestao, ao_falhar=marcar_midia_com_erro),
}
