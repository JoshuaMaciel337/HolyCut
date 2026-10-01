from collections.abc import Callable
from dataclasses import dataclass

from worker.tarefas.blocos import executar_blocos
from worker.tarefas.capas import executar_capas_culto
from worker.tarefas.diagnostico_gpu import executar_diagnostico_gpu
from worker.tarefas.estudo import executar_estudo
from worker.tarefas.importacao import executar_importacao
from worker.tarefas.ingestao import executar_ingestao, marcar_midia_com_erro
from worker.tarefas.limpeza_audio import executar_limpeza_audio
from worker.tarefas.momentos import executar_momentos
from worker.tarefas.preparar_musica import executar_preparar_musica, marcar_musica_com_erro
from worker.tarefas.renderizacao import executar_renderizacao, marcar_exportacao_com_erro
from worker.tarefas.rosto import executar_rosto
from worker.tarefas.sugestao import executar_sugestao
from worker.tarefas.teste import executar_teste
from worker.tarefas.transcricao import executar_transcricao


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
    "transcricao": Tarefa(executar_transcricao),
    "limpeza_audio": Tarefa(executar_limpeza_audio),
    "sugestao_cortes": Tarefa(executar_sugestao),
    "momentos": Tarefa(executar_momentos),
    "renderizacao_nvenc": Tarefa(executar_renderizacao, ao_falhar=marcar_exportacao_com_erro),
    "enquadramento_rosto": Tarefa(executar_rosto),
    "ingestao": Tarefa(executar_ingestao, ao_falhar=marcar_midia_com_erro),
    "renderizacao": Tarefa(executar_renderizacao, ao_falhar=marcar_exportacao_com_erro),
    "preparar_musica": Tarefa(executar_preparar_musica, ao_falhar=marcar_musica_com_erro),
    "capas_culto": Tarefa(executar_capas_culto),
    "estudo_culto": Tarefa(executar_estudo),
    "blocos_culto": Tarefa(executar_blocos),
    "importar_link": Tarefa(executar_importacao, ao_falhar=marcar_midia_com_erro),
}
