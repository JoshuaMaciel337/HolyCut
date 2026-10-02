# -----------------------------------------------
# HolyCut — configurações compartilhadas por API e workers
# Tudo que muda entre máquinas vem de variável de ambiente.
# -----------------------------------------------
import os
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/Sao_Paulo")
VERSAO = "0.1.0"

PASTA_RAIZ = Path(__file__).resolve().parent.parent

# -----------------------------------------------
# BANCO
# -----------------------------------------------
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017/?directConnection=true")  # TODO: .env
DATABASE_NAME = os.environ.get("DATABASE_NAME", "holycut")

# -----------------------------------------------
# ARMAZENAMENTO DE ARQUIVOS
# -----------------------------------------------
PASTA_ARMAZENAMENTO = Path(os.environ.get("PASTA_ARMAZENAMENTO", PASTA_RAIZ / "armazenamento"))

# -----------------------------------------------
# UPLOAD (protocolo tus)
# -----------------------------------------------
UPLOAD_MAX_BYTES = int(float(os.environ.get("UPLOAD_MAX_GB", "20")) * 1024**3)
# Um envio que deixaria menos que isso livre no disco é recusado.
# Disco cheio derruba o Mongo e o Docker no meio do trabalho.
ESPACO_MINIMO_LIVRE_BYTES = int(float(os.environ.get("ESPACO_MINIMO_LIVRE_GB", "2")) * 1024**3)
EXTENSOES_VIDEO = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm", ".mts", ".m2ts", ".ts"}
EXTENSOES_AUDIO = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}

# -----------------------------------------------
# FFMPEG
# -----------------------------------------------
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
FFPROBE = os.environ.get("FFPROBE", "ffprobe")

# -----------------------------------------------
# ARTE (logo, textos e templates desenhados com Pillow)
# -----------------------------------------------
PASTA_FONTES = Path(os.environ.get("PASTA_FONTES", PASTA_RAIZ / "brand" / "fontes"))
LOGO_MAX_BYTES = 5 * 1024 * 1024

# -----------------------------------------------
# SESSÃO
# -----------------------------------------------
# TODO: .env — o valor padrão só serve para desenvolvimento local
JWT_SEGREDO = os.environ.get("JWT_SEGREDO") or "dev-apenas-para-desenvolvimento-local-troque-no-env"
JWT_ALGORITMO = "HS256"
SESSAO_DIAS = int(os.environ.get("SESSAO_DIAS", "7"))
COOKIE_NOME = "holycut_sessao"
COOKIE_SEGURO = os.environ.get("COOKIE_SEGURO", "false").lower() == "true"

# Limite de tentativas de login por IP + e-mail
MAX_TENTATIVAS_LOGIN = 5
JANELA_TENTATIVAS_MINUTOS = 15

# -----------------------------------------------
# FILA DE JOBS
# -----------------------------------------------
LEASE_MINUTOS = 5                 # posse do job sem heartbeat antes de voltar para a fila
HEARTBEAT_SEGUNDOS = 30           # frequência de renovação da posse
MAX_TENTATIVAS_JOB = 3
ESPERAS_RETRY_MINUTOS = [1, 5, 30]
INTERVALO_BUSCA_SEGUNDOS = 2      # espera do worker quando a fila está vazia
INTERVALO_LIMPEZA_SEGUNDOS = 60   # frequência da recuperação de jobs com posse vencida
# Cada quanto o monitor lê o feed do canal do YouTube de cada igreja
INTERVALO_MONITOR_SEGUNDOS = int(os.environ.get("INTERVALO_MONITOR_SEGUNDOS", "600"))

# -----------------------------------------------
# IA
# -----------------------------------------------
MODO_IA = os.environ.get("MODO_IA", "simulado")  # "simulado" ou "real"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODELO = os.environ.get("OLLAMA_MODELO", "gemma3:4b")
# Busca de imagens de apoio. Vazia: a tela avisa que a busca não está configurada.
PIXABAY_API_KEY = os.environ.get("PIXABAY_API_KEY", "")
