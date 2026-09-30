# -----------------------------------------------
# HolyCut API — formatos de entrada e saída
# -----------------------------------------------
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from core.modelos.job import STATUS_ERRO as STATUS_JOB_ERRO
from core.modelos.midia import ARQUIVOS_PUBLICOS, STATUS_ERRO, STATUS_PROCESSANDO


class CadastroEntrada(BaseModel):
    nome_igreja: str = Field(min_length=2, max_length=80)
    nome: str = Field(min_length=2, max_length=80)
    email: EmailStr
    senha: str = Field(min_length=8, max_length=128)

    @field_validator("nome_igreja", "nome", mode="before")
    @classmethod
    def limpar_espacos(cls, valor):
        return " ".join(valor.split()) if isinstance(valor, str) else valor


class EntrarEntrada(BaseModel):
    email: EmailStr
    senha: str = Field(min_length=1, max_length=128)


class UsuarioSaida(BaseModel):
    id: str
    nome: str
    email: str
    papel: str


class OrganizacaoSaida(BaseModel):
    id: str
    nome: str
    slug: str


class SessaoSaida(BaseModel):
    usuario: UsuarioSaida
    organizacao: OrganizacaoSaida


class JobCriarEntrada(BaseModel):
    tipo: Literal["teste", "diagnostico_gpu"] = "teste"
    duracao: int = Field(default=10, ge=1, le=60, description="Só para o job de teste, em segundos")
    falhar: bool = Field(default=False, description="Só para o job de teste: simula uma falha")


class JobSaida(BaseModel):
    id: str
    tipo: str
    recurso: str
    status: str
    progresso: int
    mensagem: str
    tentativas: int
    max_tentativas: int
    erro: str | None = None
    entrada: dict = {}
    saida: dict | None = None
    criado_em: datetime
    atualizado_em: datetime
    iniciado_em: datetime | None = None
    concluido_em: datetime | None = None
    disponivel_em: datetime | None = None


class ProcessamentoSaida(BaseModel):
    status: str
    progresso: int
    mensagem: str


class MidiaSaida(BaseModel):
    id: str
    nome: str
    nome_original: str
    status: str
    tamanho_total: int
    bytes_recebidos: int
    duracao: float | None = None
    video: dict | None = None
    audio: dict | None = None
    miniaturas: dict | None = None
    arquivos: list[str] = []
    erro: str | None = None
    processamento: ProcessamentoSaida | None = None
    criado_em: datetime
    atualizado_em: datetime
    enviado_em: datetime | None = None


class SilenciosSaida(BaseModel):
    intensidade: str
    limiar_db: float
    duracao_minima: float
    margem: float
    silencios: list[tuple[float, float]]
    tempo_cortado: float
    duracao_final: float


class MidiaAtualizarEntrada(BaseModel):
    nome: str = Field(min_length=1, max_length=120)

    @field_validator("nome", mode="before")
    @classmethod
    def limpar_espacos(cls, valor):
        return " ".join(valor.split()) if isinstance(valor, str) else valor


class WorkerSaida(BaseModel):
    id: str
    recursos: list[str]
    tipos: list[str]
    iniciado_em: datetime | None = None
    visto_em: datetime


class SistemaSaida(BaseModel):
    mongo: bool
    modo_ia: str
    workers: list[WorkerSaida]


def job_para_saida(doc: dict) -> JobSaida:
    return JobSaida.model_validate({**doc, "id": str(doc["_id"])})


def midia_para_saida(doc: dict, job: dict | None = None) -> MidiaSaida:
    """job: o job de ingestão, para mostrar o progresso enquanto a mídia é processada."""
    processamento = None
    status, erro = doc["status"], doc.get("erro")
    if job is not None and status == STATUS_PROCESSANDO:
        processamento = ProcessamentoSaida(status=job["status"], progresso=job.get("progresso", 0),
                                           mensagem=job.get("mensagem", ""))
        if job["status"] == STATUS_JOB_ERRO:  # o worker caiu de vez sem avisar a mídia
            status, erro = STATUS_ERRO, erro or job.get("erro")
    return MidiaSaida.model_validate({
        **doc,
        "id": str(doc["_id"]),
        "status": status,
        "erro": erro,
        "arquivos": [nome for nome in doc.get("arquivos", []) if nome in ARQUIVOS_PUBLICOS],
        "processamento": processamento,
    })


def worker_para_saida(doc: dict) -> WorkerSaida:
    return WorkerSaida.model_validate({**doc, "id": str(doc["_id"])})
