# -----------------------------------------------
# HolyCut — modelo de mídia (a gravação enviada pela igreja)
# Funções puras: montam e calculam, sem acessar o banco.
# -----------------------------------------------
from datetime import datetime
from pathlib import PurePosixPath

from core.config import EXTENSOES_AUDIO, EXTENSOES_VIDEO, TZ
from core.modelos.culto import ARQUIVO_BANNER, ARQUIVO_POSTER

STATUS_ENVIANDO = "enviando"        # upload em andamento
STATUS_PROCESSANDO = "processando"  # ingestão na fila ou rodando
STATUS_PRONTA = "pronta"
STATUS_ERRO = "erro"

# Arquivos gerados pela ingestão. A API só serve nomes desta lista.
ARQUIVO_PROXY_VIDEO = "proxy.mp4"
ARQUIVO_PROXY_AUDIO = "proxy.m4a"
# Áudio limpo da gravação inteira (48 kHz). Uso interno: a prévia ouve o proxy remuxado.
ARQUIVO_AUDIO_LIMPO = "audio_limpo.wav"
ARQUIVO_PROXY_LIMPO = "proxy_limpo.mp4"
ARQUIVO_AUDIO_ANALISE = "audio.wav"
ARQUIVO_FORMA_DE_ONDA = "forma_de_onda.json"
ARQUIVO_MINIATURAS = "miniaturas.jpg"
ARQUIVO_CAPA = "capa.jpg"
# Nível do áudio em dB a cada 10 ms (int8). Base do corte de silêncios. Uso interno.
ARQUIVO_NIVEIS = "niveis.bin"
NIVEIS_POR_SEGUNDO = 100
# As capas do acervo (pôster e banner) são desenhadas depois, pelo job capas_culto
ARQUIVOS_PUBLICOS = {ARQUIVO_PROXY_VIDEO, ARQUIVO_PROXY_AUDIO, ARQUIVO_PROXY_LIMPO, ARQUIVO_FORMA_DE_ONDA,
                     ARQUIVO_MINIATURAS, ARQUIVO_CAPA, ARQUIVO_POSTER, ARQUIVO_BANNER}


def extensao_aceita(nome_arquivo: str) -> str | None:
    """Extensão em minúsculas se o arquivo for vídeo ou áudio aceito, senão None."""
    extensao = PurePosixPath(nome_arquivo.replace("\\", "/")).suffix.lower()
    return extensao if extensao in EXTENSOES_VIDEO | EXTENSOES_AUDIO else None


def nome_para_exibir(nome_arquivo: str) -> str:
    """'C:/Videos/Culto 29-09.MP4' → 'Culto 29-09'."""
    nome = PurePosixPath(nome_arquivo.replace("\\", "/")).stem.strip()
    return (nome or "Gravação")[:120]


def pasta_da_midia(organizacao_id, midia_id) -> str:
    return f"org_{organizacao_id}/midias/{midia_id}"


def chave_arquivo(organizacao_id, midia_id, nome: str) -> str:
    return f"{pasta_da_midia(organizacao_id, midia_id)}/{nome}"


def montar_midia(organizacao_id, criado_por, nome_arquivo: str, tamanho_total: int,
                 tipo_mime: str = "", momento: datetime | None = None) -> dict:
    """Documento de uma mídia nova, no começo do upload."""
    extensao = extensao_aceita(nome_arquivo)
    if extensao is None:
        raise ValueError(f"Formato não aceito: {nome_arquivo}")
    momento = momento or datetime.now(TZ)
    return {
        "organizacao_id": organizacao_id,
        "criado_por": criado_por,
        "nome": nome_para_exibir(nome_arquivo),
        "nome_original": nome_arquivo[:255],
        "extensao": extensao,
        "tipo_mime": tipo_mime[:100],
        "status": STATUS_ENVIANDO,
        "tamanho_total": tamanho_total,
        "bytes_recebidos": 0,
        "original": f"original{extensao}",
        "arquivos": [],
        "duracao": None,
        "video": None,
        "audio": None,
        "miniaturas": None,
        "job_ingestao_id": None,
        "erro": None,
        "criado_em": momento,
        "atualizado_em": momento,
        "enviado_em": None,
    }
