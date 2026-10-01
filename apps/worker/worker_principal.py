# -----------------------------------------------
# HolyCut — worker da fila de jobs
#
#   python -m worker.worker_principal --automatico --recursos cpu
#   python -m worker.worker_principal --agora          (processa o que houver e encerra)
#
# Rode com a pasta "apps" e a raiz do projeto no PYTHONPATH (o Docker já faz isso).
# -----------------------------------------------

# -----------------------------------------------
# IMPORTS — stdlib primeiro, depois terceiros
# -----------------------------------------------
import argparse
import logging
import os
import signal
import socket
import threading
import time
import traceback
import uuid

from core.config import (
    HEARTBEAT_SEGUNDOS,
    INTERVALO_BUSCA_SEGUNDOS,
    INTERVALO_LIMPEZA_SEGUNDOS,
    INTERVALO_MONITOR_SEGUNDOS,
    MODO_IA,
)
from core.modelos.job import STATUS_ERRO, ErroDefinitivo, tipos_por_recursos
from core.utils.fila import (
    atualizar_progresso,
    concluir_job,
    falhar_job,
    liberar_jobs_expirados,
    pegar_proximo_job,
    registrar_worker,
    renovar_lease,
)
from core.utils.mongo import agora, conectar, criar_indices
from worker.tarefas import REGISTRO
from worker.tarefas.importacao import verificar_canais

# -----------------------------------------------
# CONFIGURAÇÕES
# -----------------------------------------------
RECURSOS_PADRAO = os.environ.get("WORKER_RECURSOS", "cpu")
ESPERA_RECONEXAO_SEGUNDOS = 10
INTERVALO_MINIMO_PROGRESSO_SEGUNDOS = 0.5   # evita gravar progresso no banco a cada milissegundo
INTERVALO_SINAL_DE_VIDA_SEGUNDOS = 15

# -----------------------------------------------
# LOGGING
# -----------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)

_parar = threading.Event()


# -----------------------------------------------
# FUNÇÕES AUXILIARES
# -----------------------------------------------
def pedir_parada(_sinal, _frame):
    logging.info("Sinal de parada recebido. O job atual termina e o worker encerra.")
    _parar.set()


def manter_posse(db, job_id, worker_id: str, fim: threading.Event):
    """Heartbeat: renova a posse do job até a tarefa terminar."""
    while not fim.wait(HEARTBEAT_SEGUNDOS):
        if not renovar_lease(db, job_id, worker_id):
            logging.warning(f"[{worker_id}] Posse do job {job_id} perdida. Outro worker pode reprocessá-lo.")
            return


def enviar_sinal_de_vida(db, worker_id: str, recursos: list[str], tipos: list[str]):
    """Mantém o worker marcado como online, inclusive durante jobs longos."""
    iniciado_em = agora()
    while not _parar.is_set():
        registrar_worker(db, worker_id, recursos, tipos, iniciado_em)
        _parar.wait(INTERVALO_SINAL_DE_VIDA_SEGUNDOS)


def criar_reportador(db, job_id, worker_id: str):
    """Função que a tarefa chama para informar progresso, com limite de frequência."""
    ultimo = {"momento": 0.0}

    def reportar(progresso: int, mensagem: str = ""):
        instante = time.monotonic()
        if progresso < 100 and instante - ultimo["momento"] < INTERVALO_MINIMO_PROGRESSO_SEGUNDOS:
            return
        ultimo["momento"] = instante
        atualizar_progresso(db, job_id, worker_id, progresso, mensagem)

    return reportar


# -----------------------------------------------
# FUNÇÕES PRINCIPAIS
# -----------------------------------------------
def processar_job(db, job: dict, worker_id: str) -> str:
    """Executa um job e grava o resultado. Nunca deixa exceção escapar."""
    rotulo = f"[{worker_id}] [{job['tipo']} {job['_id']}]"
    tarefa = REGISTRO.get(job["tipo"])
    if tarefa is None:
        logging.error(f"{rotulo} Tipo sem implementação neste worker.")
        return falhar_job(db, job, worker_id, "Tipo de job sem implementação no worker.", definitivo=True) or "erro"

    fim = threading.Event()
    threading.Thread(target=manter_posse, args=(db, job["_id"], worker_id, fim), daemon=True).start()
    inicio = time.monotonic()
    try:
        saida = tarefa.executar(db, job, criar_reportador(db, job["_id"], worker_id))
        if not concluir_job(db, job["_id"], worker_id, saida):
            logging.warning(f"{rotulo} Terminou, mas a posse já tinha sido perdida. Resultado descartado.")
            return "descartado"
        logging.info(f"{rotulo} Concluído em {time.monotonic() - inicio:.1f}s.")
        return "concluido"
    except Exception as e:
        definitivo = isinstance(e, ErroDefinitivo)
        mensagem = str(e) if definitivo else f"{type(e).__name__}: {e}"
        logging.error(f"{rotulo} Falhou{' (sem nova tentativa)' if definitivo else ''}: {e}")
        logging.debug(traceback.format_exc())
        status = falhar_job(db, job, worker_id, mensagem, definitivo=definitivo)
        if status:
            logging.info(f"{rotulo} Status após a falha: {status}.")
        if status == STATUS_ERRO and tarefa.ao_falhar:
            try:
                tarefa.ao_falhar(db, job, mensagem)
            except Exception as erro_aviso:
                logging.error(f"{rotulo} Erro ao registrar a falha definitiva: {erro_aviso}")
        return status or "erro"
    finally:
        fim.set()


def executar_loop(db, tipos: list[str], worker_id: str, somente_disponiveis: bool = False):
    """Loop principal. Erros de um ciclo são registrados e o loop continua."""
    ultima_limpeza = ultimo_monitor = 0.0
    # O monitor do canal do YouTube roda nos workers que importam (os de CPU), não na fila:
    # um job a cada 10 min por igreja esconderia o que importa na lista de atividades
    monitorar = "importar_link" in tipos and not somente_disponiveis
    while not _parar.is_set():
        try:
            if time.monotonic() - ultima_limpeza >= INTERVALO_LIMPEZA_SEGUNDOS:
                liberar_jobs_expirados(db)
                ultima_limpeza = time.monotonic()
            if monitorar and time.monotonic() - ultimo_monitor >= min(INTERVALO_MONITOR_SEGUNDOS, 60):
                ultimo_monitor = time.monotonic()
                verificar_canais(db)

            job = pegar_proximo_job(db, tipos, worker_id)
            if job is None:
                if somente_disponiveis:
                    logging.info(f"[{worker_id}] Fila vazia. Encerrando (--agora).")
                    return
                _parar.wait(INTERVALO_BUSCA_SEGUNDOS)
                continue

            logging.info(f"[{worker_id}] Job {job['tipo']} {job['_id']} "
                         f"(tentativa {job['tentativas']}/{job['max_tentativas']}).")
            processar_job(db, job, worker_id)
        except Exception as e:
            logging.error(f"[{worker_id}] Erro no ciclo do worker: {e}")
            _parar.wait(ESPERA_RECONEXAO_SEGUNDOS)
    logging.info(f"[{worker_id}] Worker encerrado.")


# -----------------------------------------------
# EXECUÇÃO
# -----------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Worker da fila de jobs do HolyCut")
    parser.add_argument("--recursos", default=RECURSOS_PADRAO, help="cpu, gpu ou cpu,gpu")
    parser.add_argument("--automatico", action="store_true",
                        help="Roda sem parar e tenta reconectar ao Mongo se ele cair")
    parser.add_argument("--agora", action="store_true", help="Processa os jobs disponíveis e encerra")
    parser.add_argument("--id", default=None, help="Identificador do worker nos logs e no banco")
    args = parser.parse_args()

    recursos = [r.strip() for r in args.recursos.split(",") if r.strip()]
    tipos = [tipo for tipo in tipos_por_recursos(recursos) if tipo in REGISTRO]
    worker_id = args.id or f"{socket.gethostname()}-{'+'.join(recursos)}-{uuid.uuid4().hex[:6]}"

    signal.signal(signal.SIGINT, pedir_parada)
    signal.signal(signal.SIGTERM, pedir_parada)

    if not tipos:
        logging.error(f"[{worker_id}] Nenhum tipo de job para os recursos {recursos}.")
        return
    logging.info(f"[{worker_id}] Worker iniciado. Recursos: {recursos}. Tipos: {tipos}. Modo IA: {MODO_IA}.")

    db = None
    while not _parar.is_set():
        db = conectar()
        if db is not None:
            break
        if not args.automatico:
            return
        logging.info(f"[{worker_id}] Nova tentativa de conexão em {ESPERA_RECONEXAO_SEGUNDOS}s.")
        _parar.wait(ESPERA_RECONEXAO_SEGUNDOS)
    if db is None:
        return

    criar_indices(db)
    threading.Thread(target=enviar_sinal_de_vida, args=(db, worker_id, recursos, tipos), daemon=True).start()
    executar_loop(db, tipos, worker_id, somente_disponiveis=args.agora)
    _parar.set()
    try:
        db["workers"].delete_one({"_id": worker_id})
    except Exception as e:
        logging.error(f"[{worker_id}] Erro ao remover o registro do worker: {e}")


if __name__ == "__main__":
    main()
