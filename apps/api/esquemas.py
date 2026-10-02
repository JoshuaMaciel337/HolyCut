# -----------------------------------------------
# HolyCut API — formatos de entrada e saída
# -----------------------------------------------
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from core.modelos.aprovacao import expirada
from core.modelos.culto import ficha_do_culto
from core.modelos.fala import conferir_edicoes, conferir_ids
from core.modelos.job import STATUS_ERRO as STATUS_JOB_ERRO
from core.modelos.legenda import legenda_do_projeto
from core.modelos.midia import ARQUIVOS_PUBLICOS, STATUS_ERRO, STATUS_PROCESSANDO
from core.modelos.projeto import MAXIMO_PARTES, partes_do_projeto


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


class FichaCultoEntrada(BaseModel):
    data: date | None = Field(default=None, description="Dia do culto")
    pregador: str = Field(default="", max_length=80)
    serie: str = Field(default="", max_length=80, description="Série de mensagens, se houver")
    descricao: str = Field(default="", max_length=500)

    @field_validator("pregador", "serie", "descricao", mode="before")
    @classmethod
    def limpar_espacos(cls, valor):
        return " ".join(valor.split()) if isinstance(valor, str) else valor


class FichaCultoSaida(BaseModel):
    data: str
    pregador: str = ""
    serie: str = ""
    descricao: str = ""


class PregacaoSaida(BaseModel):
    """Onde a mensagem começa e termina. A marcação da pessoa nunca é trocada pela da IA."""
    inicio: float
    fim: float
    origem: Literal["ia", "pessoa"]


class PregacaoEntrada(BaseModel):
    inicio: float = Field(ge=0)
    fim: float = Field(gt=0)


class ImportarEntrada(BaseModel):
    url: str = Field(min_length=8, max_length=500, description="Link de um vídeo do YouTube ou de um arquivo do Drive")
    confirmo_que_e_da_igreja: bool = Field(default=False, description="Exigido para o Drive, que não diz de quem é")


class CanalYoutubeEntrada(BaseModel):
    canal: str = Field(min_length=2, max_length=200, description="O @ do canal, o endereço dele ou o id UC...")
    monitorar: bool = False


class CanalYoutubeSaida(BaseModel):
    configurado: bool
    canal: str = ""
    id: str | None = None
    handle: str | None = None
    monitorar: bool = False
    ultima_verificacao: datetime | None = None
    ultimo_erro: str | None = None


class ImportacaoSaida(BaseModel):
    origem: Literal["youtube", "drive"]
    url: str
    titulo: str = ""


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
    ficha: FichaCultoSaida
    pregacao: PregacaoSaida | None = None
    importacao: ImportacaoSaida | None = None
    capa_versao: int | None = None
    capa_personalizada: bool = False
    erro: str | None = None
    processamento: ProcessamentoSaida | None = None
    criado_em: datetime
    atualizado_em: datetime
    enviado_em: datetime | None = None


class CultoResumoSaida(BaseModel):
    """Um culto nas fileiras do acervo."""
    id: str
    titulo: str
    data: str
    pregador: str = ""
    serie: str = ""
    descricao: str = ""
    duracao: float | None = None
    video: bool
    capa_versao: int | None = Field(description="Muda quando as capas são redesenhadas")
    cortes: int = Field(description="Vídeos e imagens prontos deste culto")
    em_edicao: int = Field(description="Reels e Stories criados a partir deste culto")


class FileiraSaida(BaseModel):
    id: str
    titulo: str
    ids: list[str]


class AcervoSaida(BaseModel):
    cultos: list[CultoResumoSaida]
    destaque: str | None
    fileiras: list[FileiraSaida]
    series: list[str]
    pregadores: list[str]
    preparando: int = Field(description="Gravações que ainda estão chegando ou sendo preparadas")


class CapaEntrada(BaseModel):
    instante: float = Field(ge=0, description="Segundo da gravação usado como fundo da capa")


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
LicencaMusica = Literal["propria", "dominio_publico", "cc_by", "licenciada"]


class IdentidadeSaida(BaseModel):
    nome_exibicao: str
    instagram: str
    cor_destaque: str
    logo: bool
    estrategia: str = ""
    atualizado_em: datetime | None = None


class IdentidadeAtualizarEntrada(BaseModel):
    nome_exibicao: str | None = Field(default=None, min_length=1, max_length=80)
    instagram: str | None = Field(default=None, max_length=80)
    cor_destaque: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    estrategia: str | None = Field(default=None, max_length=400)


class MarcaEntrada(BaseModel):
    logo: bool = False
    posicao: PosicaoLogo = "topo_direita"
    tamanho: float = Field(default=0.16, ge=0.06, le=0.4)
    opacidade: float = Field(default=0.9, ge=0.2, le=1)
    x: float | None = Field(default=None, ge=0, le=1, description="Centro arrastado na prévia; None usa a posição")
    y: float | None = Field(default=None, ge=0, le=1)
    rotacao: float = Field(default=0, ge=-180, le=180, description="Graus, no sentido do relógio")


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
    x: float | None = Field(default=None, ge=0, le=1, description="Centro arrastado na prévia; None usa a posição")
    y: float | None = Field(default=None, ge=0, le=1)
    rotacao: float = Field(default=0, ge=-180, le=180, description="Graus, no sentido do relógio")


class FiguraEntrada(BaseModel):
    """PNG da igreja ou um ícone desenhado pelo HolyCut, no tempo do vídeo final."""
    id: str = Field(pattern=r"^[0-9a-f]{8}$")
    nome: str = Field(default="Imagem", max_length=40)
    icone: Literal["cruz", "biblia", "chama", "estrela"] | None = None
    inicio: float = Field(default=0, ge=0)
    fim: float | None = Field(default=None, gt=0)
    tamanho: float = Field(default=0.28, ge=0.08, le=0.8, description="Largura em fração da moldura")
    opacidade: float = Field(default=1, ge=0.2, le=1)
    x: float | None = Field(default=None, ge=0, le=1)
    y: float | None = Field(default=None, ge=0, le=1)
    rotacao: float = Field(default=0, ge=-180, le=180)
    credito: str = Field(default="", max_length=120, description="Autor e a Pixabay, quando a imagem veio de lá")


class ApoioEntrada(BaseModel):
    """Vídeo da Pixabay que cobre o quadro num intervalo. O som continua o da pregação."""
    id: str = Field(pattern=r"^[0-9a-f]{8}$")
    nome: str = Field(default="Vídeo", max_length=40)
    credito: str = Field(default="", max_length=120)
    inicio: float = Field(default=0, ge=0)
    fim: float | None = Field(default=None, gt=0)
    pixabay_id: int = Field(ge=1)


class BuscaBancoEntrada(BaseModel):
    frase: str = Field(min_length=2, max_length=240)


class UsarBancoEntrada(BaseModel):
    versao: int = Field(ge=1)
    tipo: Literal["imagem", "video"]
    pixabay_id: int = Field(ge=1)
    inicio: float = Field(default=0, ge=0)


class ResultadoBancoSaida(BaseModel):
    id: int
    tipo: Literal["imagem", "video"]
    nome: str
    autor: str
    pagina: str
    miniatura: str
    duracao: int | None = None


class SugestaoBancoSaida(BaseModel):
    usar: bool
    consulta: str
    tipo: Literal["imagem", "video"]


class FundoEntrada(BaseModel):
    escurecer: float = Field(default=0.0, ge=0, le=0.8)
    desfoque: float = Field(default=0, ge=0, le=30)


class CorEntrada(BaseModel):
    filtro: Literal["natural", "quente", "frio", "cinema", "pb", "vivo"] = "natural"
    intensidade: float = Field(default=1.0, ge=0, le=1)


class MusicaProjetoEntrada(BaseModel):
    id: str | None = Field(default=None, max_length=24, description="None: sem música")
    volume: float = Field(default=0.25, ge=0, le=1)
    abaixar_na_fala: bool = True
    inicio: float = Field(default=0, ge=0, description="Segundo da música em que o vídeo começa")


class MusicaCriarEntrada(BaseModel):
    titulo: str = Field(min_length=1, max_length=120)
    artista: str = Field(default="", max_length=120)
    licenca: LicencaMusica
    atribuicao: str = Field(default="", max_length=300, description="Obrigatória na CC BY")
    fonte: str = Field(default="", max_length=300, description="Onde a música foi obtida")


class MusicaAtualizarEntrada(BaseModel):
    titulo: str | None = Field(default=None, min_length=1, max_length=120)
    artista: str | None = Field(default=None, max_length=120)
    licenca: LicencaMusica | None = None
    atribuicao: str | None = Field(default=None, max_length=300)
    fonte: str | None = Field(default=None, max_length=300)


class MusicaSaida(BaseModel):
    id: str
    titulo: str
    artista: str
    licenca: str
    licenca_nome: str
    atribuicao: str
    fonte: str
    status: str
    duracao: float | None = None
    erro: str | None = None
    criado_em: datetime


class ChaveEnvioCriarEntrada(BaseModel):
    nome: str = Field(min_length=1, max_length=60, description="Onde a chave vai ser usada, ex.: PC da mídia")


class ChaveEnvioSaida(BaseModel):
    id: str
    nome: str
    inicio: str = Field(description="Começo da chave, para reconhecer na lista")
    criado_em: datetime
    ultimo_uso_em: datetime | None = None


class ChaveEnvioCriadaSaida(ChaveEnvioSaida):
    chave: str = Field(description="A chave inteira. Só aparece nesta resposta.")


class ChaveEnvioConferirSaida(BaseModel):
    igreja: str
    chave: str | None = Field(description="Nome da chave, quando a conexão é por chave")


class FiltroSaida(BaseModel):
    id: str
    nome: str
    operacoes: list[dict] = Field(description="Na intensidade máxima: matriz 3x3 ou contraste")


class CamadaEntrada(BaseModel):
    """Uma camada para a prévia: o logo, um texto ou uma figura, do tamanho da moldura."""
    largura: int = Field(ge=90, le=1920)
    altura: int = Field(ge=90, le=1920)
    tipo: Literal["logo", "texto", "figura"]
    marca: MarcaEntrada | None = None
    texto: TextoEntrada | None = None
    figura: FiguraEntrada | None = None
    projeto_id: str | None = Field(default=None, max_length=24, description="Para carregar o PNG enviado")


class ParteEntrada(BaseModel):
    """Uma parte da gravação que entra no vídeo. As partes seguem a ordem da lista."""
    id: str = Field(min_length=1, max_length=20)
    inicio: float = Field(ge=0)
    fim: float = Field(gt=0)


class SilenciosProjetoEntrada(BaseModel):
    intensidade: IntensidadeCorte | None = None


class EnquadramentoEntrada(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    zoom: float = Field(ge=1, le=3)
    seguir_rosto: bool = False
    rotacao: float = Field(default=0, ge=-180, le=180, description="Graus, no sentido do relógio")


class AudioProjetoEntrada(BaseModel):
    normalizar: bool = True
    # Desligada por padrão: a exportação antiga continua com o áudio original.
    limpeza: bool = False


class ProjetoCriarEntrada(BaseModel):
    midia_id: str
    nome: str | None = Field(default=None, max_length=120)
    proporcao: Proporcao = "9:16"
    tipo: Literal["reel", "story"] = "reel"
    modelo_id: str | None = Field(default=None, max_length=40)
    inicio: float = Field(default=0, ge=0, description="Story: de onde começam os 15 s")


class LegendaEntrada(BaseModel):
    ativa: bool = True
    preset: Literal["clean", "karaoke", "destaque", "digno", "flutuante"] = "destaque"
    palavras_por_bloco: int = Field(default=3, ge=1, le=8)
    posicao: Literal["base", "centro"] = "base"
    x: float | None = Field(default=None, ge=0, le=1, description="Centro arrastado na prévia")
    y: float | None = Field(default=None, ge=0, le=1)
    escala: float = Field(default=1.0, ge=0.6, le=2.0, description="Tamanho da letra")
    vicios: Literal["leve", "media", "forte"] | None = None
    edicoes: dict[str, str] = Field(default_factory=dict)
    apagadas: list[str] = Field(default_factory=list)
    mantidas: list[str] = Field(default_factory=list)

    @field_validator("edicoes")
    @classmethod
    def limpar_edicoes(cls, valor: dict) -> dict:
        return conferir_edicoes(valor)

    @field_validator("apagadas", "mantidas")
    @classmethod
    def limpar_ids(cls, valor: list) -> list:
        return conferir_ids(valor)


class PalavraLegendaSaida(BaseModel):
    id: str = ""
    texto: str
    inicio: float
    fim: float
    destaque: bool = False


class BlocoLegendaSaida(BaseModel):
    inicio: float
    fim: float
    palavras: list[PalavraLegendaSaida]


class PalavraFalaSaida(BaseModel):
    id: str
    texto: str
    inicio: float
    fim: float
    vicio: Literal["leve", "media", "forte"] | None = None
    segmento: str = ""


class LegendaPreviaSaida(BaseModel):
    ativa: bool
    preset: Literal["clean", "karaoke", "destaque", "digno", "flutuante"]
    posicao: Literal["base", "centro"]
    palavras_por_bloco: int
    cor_destaque: str
    cor_dourada: str
    tem_transcricao: bool
    blocos: list[BlocoLegendaSaida]
    palavras: list[PalavraFalaSaida] = []


class ZoomEfeitoEntrada(BaseModel):
    inicio: float = Field(default=0, ge=0)
    fim: float | None = Field(default=None, gt=0)
    nivel: float = Field(default=1, ge=1, le=1.35)


class SomEfeitoEntrada(BaseModel):
    id: Literal["nenhum", "sopro", "toque"] = "nenhum"
    inicio: float = Field(default=0, ge=0)


class EfeitosEntrada(BaseModel):
    brilho: float = Field(default=0, ge=-0.3, le=0.3)
    tremor: float = Field(default=0, ge=0, le=1)
    luz: float = Field(default=0, ge=0, le=0.8)
    contorno: bool = False
    transicao: Literal["corte", "escurecer", "fusao", "desfoque"] = "corte"
    zoom: ZoomEfeitoEntrada | None = None
    som: SomEfeitoEntrada = SomEfeitoEntrada()


class ProjetoAtualizarEntrada(BaseModel):
    versao: int = Field(description="Versão que a tela editou. Se o projeto mudou depois, a API responde 409.")
    nome: str | None = Field(default=None, min_length=1, max_length=120)
    proporcao: Proporcao | None = None
    partes: list[ParteEntrada] | None = Field(default=None, min_length=1, max_length=MAXIMO_PARTES)
    silencios: SilenciosProjetoEntrada | None = None
    enquadramento: EnquadramentoEntrada | None = None
    audio: AudioProjetoEntrada | None = None
    marca: MarcaEntrada | None = None
    textos: list[TextoEntrada] | None = Field(default=None, max_length=6)
    figuras: list[FiguraEntrada] | None = Field(default=None, max_length=8)
    apoios: list[ApoioEntrada] | None = Field(default=None, max_length=4)
    fundo: FundoEntrada | None = None
    cor: CorEntrada | None = None
    musica: MusicaProjetoEntrada | None = None
    efeitos: EfeitosEntrada | None = None
    legenda: LegendaEntrada | None = None


class PublicacaoSaida(BaseModel):
    legenda: str = ""
    hashtags: list[str] = []
    gerado_por_ia: bool = True


class ProjetoSaida(BaseModel):
    id: str
    midia_id: str
    nome: str
    tipo: str
    proporcao: str
    partes: list[ParteEntrada]
    silencios: SilenciosProjetoEntrada
    enquadramento: EnquadramentoEntrada
    audio: AudioProjetoEntrada
    marca: MarcaEntrada = MarcaEntrada()
    textos: list[TextoEntrada] = []
    figuras: list[FiguraEntrada] = []
    apoios: list[ApoioEntrada] = []
    fundo: FundoEntrada = FundoEntrada()
    cor: CorEntrada = CorEntrada()
    musica: MusicaProjetoEntrada = MusicaProjetoEntrada()
    efeitos: EfeitosEntrada = EfeitosEntrada()
    legenda: LegendaEntrada = LegendaEntrada()
    modelo_id: str | None = None
    publicacao: PublicacaoSaida | None = None
    versao: int
    criado_em: datetime
    atualizado_em: datetime


class ExportarEntrada(BaseModel):
    formato: Literal["video", "imagem"] = "video"
    instante: float = Field(default=0, ge=0, description="Imagem: segundos do vídeo final")
    encoder: Literal["cpu", "nvenc"] = "cpu"


class ModeloSaida(BaseModel):
    id: str
    nome: str
    descricao: str = ""
    pronto: bool = Field(description="Modelo que vem com o HolyCut (não pode ser apagado)")
    fundo: FundoEntrada = FundoEntrada()
    cor: CorEntrada = CorEntrada()
    marca: MarcaEntrada = MarcaEntrada()
    textos: list[TextoEntrada] = []


class ModeloCriarEntrada(BaseModel):
    nome: str = Field(min_length=1, max_length=60)
    projeto_id: str


class AprovacaoSaida(BaseModel):
    status: Literal["pendente", "aprovado", "ajustes"]
    para: str = ""
    pedido_em: datetime
    expira_em: datetime
    expirada: bool = Field(description="Pedido sem resposta que passou da validade")
    respondido_por: str | None = None
    comentario: str | None = None
    respondido_em: datetime | None = None


class AprovacaoCriarEntrada(BaseModel):
    para: str = Field(default="", max_length=60, description="Quem vai aprovar, ex.: Pr. João")


class AprovacaoCriadaSaida(BaseModel):
    token: str = Field(description="Vai no link /aprovar/{token}. Só aparece nesta resposta.")
    aprovacao: AprovacaoSaida


class AprovacaoPublicaSaida(BaseModel):
    """O que a pessoa que aprova vê pelo link, sem conta."""
    igreja: str
    nome: str
    formato: str
    duracao: float | None = None
    largura: int
    altura: int
    arquivos: list[str]
    aprovacao: AprovacaoSaida


class AprovacaoRespostaEntrada(BaseModel):
    decisao: Literal["aprovado", "ajustes"]
    nome: str = Field(min_length=1, max_length=60)
    comentario: str = Field(default="", max_length=500)


def aprovacao_para_saida(aprovacao: dict | None) -> AprovacaoSaida | None:
    if not aprovacao:
        return None
    return AprovacaoSaida.model_validate({**aprovacao, "expirada": expirada(aprovacao)})


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
    aprovacao: AprovacaoSaida | None = None
    capa_versao: int = Field(default=0, description="Muda quando a capa é trocada, para o navegador buscar a nova")


class CapaExportacaoEntrada(BaseModel):
    instante: float = Field(ge=0, description="Segundo do vídeo exportado de onde sai a capa")


class LinkCelularSaida(BaseModel):
    caminho: str = Field(description="Junte ao endereço do site: é o que vai no QR code")
    expira_em: datetime


def projeto_para_saida(doc: dict) -> ProjetoSaida:
    return ProjetoSaida.model_validate({**doc, "id": str(doc["_id"]), "midia_id": str(doc["midia_id"]),
                                        "partes": partes_do_projeto(doc), "legenda": legenda_do_projeto(doc)})


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
        "aprovacao": aprovacao_para_saida(doc.get("aprovacao")),
    })


class MidiaAtualizarEntrada(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=120, description="O título do culto")
    ficha: FichaCultoEntrada | None = None

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


class PalavraTranscricaoSaida(BaseModel):
    id: str
    texto: str
    inicio: float
    fim: float
    confianca: float | None = None


class SegmentoTranscricaoSaida(BaseModel):
    id: str
    inicio: float
    fim: float
    texto: str
    palavras: list[PalavraTranscricaoSaida] = []


class ParteSugestaoSaida(BaseModel):
    inicio: float
    fim: float


class CorteSugestaoSaida(BaseModel):
    id: str
    titulo: str
    motivo: str
    nota: float
    partes: list[ParteSugestaoSaida]
    legenda_post: str = ""
    hashtags: list[str] = []


class SugestoesSaida(BaseModel):
    status: str
    progresso: int = 0
    mensagem: str = ""
    erro: str | None = None
    gerado_por_ia: bool = False
    cortes: list[CorteSugestaoSaida] = []


class LimpezaSaida(BaseModel):
    status: str
    progresso: int = 0
    mensagem: str = ""
    erro: str | None = None


class VersiculoSaida(BaseModel):
    referencia: str
    citacao: str
    inicio: float
    fim: float


class TranscricaoSaida(BaseModel):
    status: str
    progresso: int = 0
    mensagem: str = ""
    erro: str | None = None
    gerado_por_ia: bool = False
    idioma: str | None = None
    modelo: str | None = None
    segmentos: list[SegmentoTranscricaoSaida] = []
    versiculos: list[VersiculoSaida] = []


class QuadroRostoSaida(BaseModel):
    t: float
    x: float
    y: float
    zoom: float = 1


class RostoSaida(BaseModel):
    status: str
    progresso: int = 0
    mensagem: str = ""
    erro: str | None = None
    quadros: list[QuadroRostoSaida] = []


class MomentoSaida(BaseModel):
    inicio: float
    fim: float
    energia: float
    nota: float | None = None
    assunto: str | None = None


class MomentosSaida(BaseModel):
    status: str
    progresso: int = 0
    mensagem: str = ""
    erro: str | None = None
    gerado_por_ia: bool = False
    momentos: list[MomentoSaida] = []
    cenas: list[float] = []


class TrechoDitoSaida(BaseModel):
    """Uma frase como o pregador disse, com o momento da gravação."""
    texto: str
    inicio: float
    fim: float | None = None


class PerguntaEstudoSaida(BaseModel):
    pergunta: str
    base: TrechoDitoSaida


class VersiculoChaveSaida(BaseModel):
    referencia: str
    inicio: float
    citacao: str = ""
    vezes: int = 1


class EstudoSaida(BaseModel):
    status: str
    progresso: int = 0
    mensagem: str = ""
    erro: str | None = None
    gerado_por_ia: bool = False
    resumo: list[TrechoDitoSaida] = []
    temas: list[str] = []
    personagens: list[str] = []
    versiculos_chave: list[VersiculoChaveSaida] = []
    perguntas: list[PerguntaEstudoSaida] = []
    aplicacoes: list[TrechoDitoSaida] = []
    oracao: str = ""


class BlocoSaida(BaseModel):
    """Um bloco do culto. A frase é o começo do que foi dito nele, para reconhecer o trecho."""
    inicio: float
    fim: float
    tipo: Literal["louvor", "oracao", "avisos", "oferta", "ceia", "pregacao", "outro"]
    frase: str = ""


class TrechoSaida(BaseModel):
    inicio: float
    fim: float


class BlocosSaida(BaseModel):
    status: str
    progresso: int = 0
    mensagem: str = ""
    erro: str | None = None
    gerado_por_ia: bool = False
    nomes_pelo_modelo: bool = Field(default=False, description="Falso quando os nomes vieram só das palavras-chave")
    blocos: list[BlocoSaida] = []
    pregacao: TrechoSaida | None = Field(default=None, description="A pregação que a análise encontrou")


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
    capa = doc.get("capa") or {}
    return MidiaSaida.model_validate({
        **doc,
        "ficha": ficha_do_culto(doc),
        "capa_versao": capa.get("versao"),
        "capa_personalizada": bool(capa.get("personalizada")),
        "id": str(doc["_id"]),
        "status": status,
        "erro": erro,
        "arquivos": [nome for nome in doc.get("arquivos", []) if nome in ARQUIVOS_PUBLICOS],
        "processamento": processamento,
    })


def worker_para_saida(doc: dict) -> WorkerSaida:
    return WorkerSaida.model_validate({**doc, "id": str(doc["_id"])})
