from worker.tarefas.diagnostico_gpu import executar_diagnostico_gpu
from worker.tarefas.teste import executar_teste

# Tipo de job → função que executa. Os tipos e recursos ficam em core/modelos/job.py.
REGISTRO = {
    "teste": executar_teste,
    "diagnostico_gpu": executar_diagnostico_gpu,
}
