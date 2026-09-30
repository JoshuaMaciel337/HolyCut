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


Proporcao = Literal["9:16", "4:5", "1:1", "16:9"]
IntensidadeCorte = Literal["leve", "media", "forte"]
PosicaoLogo = Literal["topo_esquerda", "topo_direita", "base_esquerda", "base_direita"]
EstiloTexto = Literal["destaque", "limpo", "manuscrito"]
PosicaoTexto = Literal["topo", "centro", "base"]


class IdentidadeSaida(BaseModel):
    nome_exibicao: str
    instagram: str
    cor_destaque: str
    logo: bool
    atualizado_em: datetime | None = None


class IdentidadeAtualizarEntrada(BaseModel):
    nome_exibicao: str | None = Field(default=None, min_length=1, max_length=80)
    instagram: str | None = Field(default=None, max_length=80)
    cor_destaque: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class MarcaEntrada(BaseModel):
    logo: bool = False
    posicao: PosicaoLogo = "topo_direita"
    tamanho: float = Field(default=0.16, ge=0.06, le=0.4)
    opacidade: float = Field(default=0.9, ge=0.2, le=1)


class TextoEntrada(BaseModel):
    id: str = Field(min_length=1, max_length=20)
    tipo: Literal["titulo", "frase", "versiculo"] = "titulo"
    texto: str = Field(default="", max_length=280)
    referencia: str = Field(default="", max_length=40)
    estilo: EstiloTexto = "destaque"
    posicao: PosicaoTexto = "base"
    inicio: float = Field(default=0, ge=0, description="Segundos no vídeo final")
    fim: float | None = Field(default=None, gt=0, description="None: até o fim do vídeo")
    tamanho: float = Field(default=1.0, ge=0.5, le=2.0, description="Escala da fonte")


class FundoEntrada(BaseModel):
    escurecer: float = Field(default=0.0, ge=0, le=0.8)
    desfoque: float = Field(default=0, ge=0, le=30)


class CamadaEntrada(BaseModel):
    """Uma camada para a prévia: o logo da igreja ou um texto, do tamanho da moldura."""
    largura: int = Field(ge=90, le=1920)
    altura: int = Field(ge=90, le=1920)
    tipo: Literal["logo", "texto"]
    marca: MarcaEntrada | None = None
    texto: TextoEntrada | None = None


class TrechoEntrada(BaseModel):
    inicio: float = Field(ge=0)
    fim: float = Field(gt=0)


class SilenciosProjetoEntrada(BaseModel):
    intensidade: IntensidadeCorte | None = None


class EnquadramentoEntrada(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    zoom: float = Field(ge=1, le=3)


class AudioProjetoEntrada(BaseModel):
    normalizar: bool = True


class ProjetoCriarEntrada(BaseModel):
    midia_id: str
    nome: str | None = Field(default=None, max_length=120)
    proporcao: Proporcao = "9:16"
    tipo: Literal["reel", "story"] = "reel"
    modelo_id: str | None = Field(default=None, max_length=40)
    inicio: float = Field(default=0, ge=0, description="Story: de onde começam os 15 s")


class ProjetoAtualizarEntrada(BaseModel):
    versao: int = Field(description="Versão que a tela editou. Se o projeto mudou depois, a API responde 409.")
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    proporcao: Proporcao | None = None
    trecho: TrechoEntrada | None = None
    silencios: SilenciosProjetoEntrada | None = None
    enquadramento: EnquadramentoEntrada | None = None
    audio: AudioProjetoEntrada | None = None
    marca: MarcaEntrada | None = None
    textos: list[TextoEntrada] | None = Field(default=None, max_length=6)
    fundo: FundoEntrada | None = None


class ProjetoSaida(BaseModel):
    id: str
    midia_id: str
    nome: str
    tipo: str
    proporcao: str
    trecho: TrechoEntrada
    silencios: SilenciosProjetoEntrada
    enquadramento: EnquadramentoEntrada
    audio: AudioProjetoEntrada
    marca: MarcaEntrada = MarcaEntrada()
    textos: list[TextoEntrada] = []
    fundo: FundoEntrada = FundoEntrada()
    modelo_id: str | None = None
    versao: int
    criado_em: datetime
    atualizado_em: datetime


class ExportarEntrada(BaseModel):
    formato: Literal["video", "imagem"] = "video"
    instante: float = Field(default=0, ge=0, description="Imagem: segundos do vídeo final")


class ModeloSaida(BaseModel):
    id: str
    nome: str
    descricao: str = ""
    pronto: bool = Field(description="Modelo que vem com o HolyCut (não pode ser apagado)")
    fundo: FundoEntrada = FundoEntrada()
    marca: MarcaEntrada = MarcaEntrada()
    textos: list[TextoEntrada] = []


class ModeloCriarEntrada(BaseModel):
    nome: str = Field(min_length=1, max_length=60)
    projeto_id: str


class ExportacaoSaida(BaseModel):
    id: str
    projeto_id: str
    midia_id: str
    nome: str
    formato: str = "video"
    instante: float = 0
    status: str
    processamento: ProcessamentoSaida | None = None
    duracao: float | None = None
    tamanho: int | None = None
    largura: int
    altura: int
    arquivos: list[str] = []
    erro: str | None = None
    criado_em: datetime
    concluido_em: datetime | None = None


def projeto_para_saida(doc: dict) -> ProjetoSaida:
    return ProjetoSaida.model_validate({**doc, "id": str(doc["_id"]), "midia_id": str(doc["midia_id"])})


def exportacao_para_saida(doc: dict, job: dict | None = None) -> ExportacaoSaida:
    processamento, status, erro = None, doc["status"], doc.get("erro")
    if job is not None and status == "processando":
        processamento = ProcessamentoSaida(status=job["status"], progresso=job.get("progresso", 0),
                                           mensagem=job.get("mensagem", ""))
        if job["status"] == STATUS_JOB_ERRO:
            status, erro = "erro", erro or job.get("erro")
    return ExportacaoSaida.model_validate({
        **doc, "id": str(doc["_id"]), "projeto_id": str(doc["projeto_id"]), "midia_id": str(doc["midia_id"]),
        "status": status, "erro": erro, "processamento": processamento,
    })


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
