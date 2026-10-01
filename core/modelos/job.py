# -----------------------------------------------
# HolyCut — modelo de job da fila
# Funções puras: montam e calculam, sem acessar o banco.
# -----------------------------------------------
from datetime import datetime, timedelta

from core.config import ESPERAS_RETRY_MINUTOS, MAX_TENTATIVAS_JOB, TZ

STATUS_PENDENTE = "pendente"
STATUS_EXECUTANDO = "executando"
STATUS_CONCLUIDO = "concluido"
STATUS_ERRO = "erro"
STATUS_FINAIS = {STATUS_CONCLUIDO, STATUS_ERRO}

RECURSO_CPU = "cpu"
RECURSO_GPU = "gpu"

# Tipo de job → recurso que o worker precisa ter para executá-lo
TAREFAS = {
    "teste": RECURSO_CPU,
    "diagnostico_gpu": RECURSO_GPU,
    "transcricao": RECURSO_GPU,
    "limpeza_audio": RECURSO_GPU,
    "sugestao_cortes": RECURSO_GPU,
    "momentos": RECURSO_GPU,
    "renderizacao_nvenc": RECURSO_GPU,
    "enquadramento_rosto": RECURSO_CPU,
    "ingestao": RECURSO_CPU,
    "renderizacao": RECURSO_CPU,
    "preparar_musica": RECURSO_CPU,
    "capas_culto": RECURSO_CPU,
}


class ErroDefinitivo(Exception):
    """Falha que não melhora tentando de novo. O job vai direto para erro, com esta mensagem."""


def tipos_por_recursos(recursos: list[str]) -> list[str]:
    """Tipos de job que um worker com esses recursos consegue executar."""
    return [tipo for tipo, recurso in TAREFAS.items() if recurso in recursos]


def montar_job(tipo: str, organizacao_id, entrada: dict | None = None, prioridade: int = 0,
               criado_por=None, momento: datetime | None = None) -> dict:
    """Monta o documento de um job novo, pronto para inserir."""
    if tipo not in TAREFAS:
        raise ValueError(f"Tipo de job desconhecido: {tipo}")
    momento = momento or datetime.now(TZ)
    return {
        "tipo": tipo,
        "recurso": TAREFAS[tipo],
        "status": STATUS_PENDENTE,
        "prioridade": prioridade,
        "organizacao_id": organizacao_id,
        "criado_por": criado_por,
        "entrada": entrada or {},
        "saida": None,
        "erro": None,
        "progresso": 0,
        "mensagem": "Na fila",
        "tentativas": 0,
        "max_tentativas": MAX_TENTATIVAS_JOB,
        "worker_id": None,
        "lease_ate": None,
        "disponivel_em": momento,
        "criado_em": momento,
        "atualizado_em": momento,
        "iniciado_em": None,
        "concluido_em": None,
    }


def calcular_espera_retry(tentativas: int) -> timedelta:
    """Espera antes da próxima tentativa: 1 min, 5 min, 30 min e depois 30 min."""
    indice = min(max(tentativas, 1), len(ESPERAS_RETRY_MINUTOS)) - 1
    return timedelta(minutes=ESPERAS_RETRY_MINUTOS[indice])
