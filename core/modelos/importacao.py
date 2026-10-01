# -----------------------------------------------
# HolyCut — importar pelo link do YouTube ou do Google Drive, e o monitor do canal
#
# Só vídeos da própria igreja:
#   - do YouTube, só os do canal cadastrado em Envio automático (o worker
#     confere o canal nos dados do vídeo antes de baixar);
#   - do Drive não dá para saber o dono, então a pessoa confirma que o
#     vídeo é da igreja.
# O monitor lê o feed RSS público do canal (sem chave de API e sem custo)
# e importa a live quando ela termina. Vídeo curto (Shorts, cortes) fica.
# Funções puras: leem e decidem, sem acessar o banco nem a rede.
# -----------------------------------------------
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import parse_qs, urlparse

from core.config import TZ
from core.modelos.job import montar_job
from core.modelos.midia import PRIORIDADE_INGESTAO, STATUS_PROCESSANDO, montar_midia

ORIGENS = ("youtube", "drive")
DURACAO_MINIMA_CULTO = 20 * 60      # o monitor ignora vídeo com menos de 20 min
ESPERA_LIVE_MINUTOS = 10            # live no ar: tenta de novo daqui a 10 min
MAXIMO_ESPERAS_LIVE = 48            # 8 h esperando a live acabar
MAXIMO_VISTOS = 200
FEED_CANAL = "https://www.youtube.com/feeds/videos.xml?channel_id={}"
# Até 1080p, vídeo e áudio juntos num .mp4. É o tamanho que o render usa.
FORMATO_DOWNLOAD = "bv*[height<=1080]+ba/b[height<=1080]/bv*+ba/b"
SITUACOES_ESPERAR = {"is_live", "is_upcoming", "post_live"}

_ID_VIDEO = re.compile(r"^[A-Za-z0-9_-]{11}$")
_ID_DRIVE = re.compile(r"^[A-Za-z0-9_-]{20,}$")
_ID_CANAL = re.compile(r"^UC[A-Za-z0-9_-]{22}$")
_HANDLE = re.compile(r"^@[A-Za-z0-9._-]{3,30}$")
_ATOM = "{http://www.w3.org/2005/Atom}"
_YT = "{http://www.youtube.com/xml/schemas/2015}"


def ler_link(url: str) -> dict | None:
    """O vídeo por trás do link: {"origem", "id", "url"} com a url canônica, ou None se não é YouTube nem Drive."""
    texto = (url or "").strip()
    if not re.match(r"^https?://", texto):
        texto = f"https://{texto}"
    partes = urlparse(texto)
    host = (partes.hostname or "").lower().removeprefix("www.").removeprefix("m.")
    caminho = [pedaco for pedaco in partes.path.split("/") if pedaco]
    consulta = parse_qs(partes.query)
    if host in ("youtube.com", "music.youtube.com", "youtu.be"):
        candidato = None
        if host == "youtu.be" and caminho:
            candidato = caminho[0]
        elif caminho[:1] == ["watch"]:
            candidato = (consulta.get("v") or [""])[0]
        elif len(caminho) >= 2 and caminho[0] in ("live", "shorts", "embed", "v"):
            candidato = caminho[1]
        if candidato and _ID_VIDEO.fullmatch(candidato):
            return {"origem": "youtube", "id": candidato, "url": f"https://www.youtube.com/watch?v={candidato}"}
        return None
    if host in ("drive.google.com", "docs.google.com"):
        candidato = None
        if len(caminho) >= 3 and caminho[0] == "file" and caminho[1] == "d":
            candidato = caminho[2]
        elif consulta.get("id"):
            candidato = consulta["id"][0]
        if candidato and _ID_DRIVE.fullmatch(candidato):
            return {"origem": "drive", "id": candidato, "url": f"https://drive.google.com/file/d/{candidato}/view"}
    return None


def normalizar_canal(texto: str) -> dict:
    """'@igrejaviva', 'youtube.com/@IgrejaViva' ou o id 'UC...' (Studio > Configurações > Canal)."""
    valor = (texto or "").strip()
    valor = re.sub(r"^(https?://)?(www\.|m\.)?youtube\.com/", "", valor).split("?")[0].strip("/")
    if valor.startswith("channel/"):
        valor = valor.removeprefix("channel/").split("/")[0]
    else:
        valor = valor.split("/")[0]
    if _ID_CANAL.fullmatch(valor):
        return {"id": valor, "handle": None}
    if not valor.startswith("@"):
        valor = f"@{valor}"
    if _HANDLE.fullmatch(valor):
        return {"id": None, "handle": valor.lower()}
    raise ValueError("Não reconheci o canal. Cole o @ do canal (como @igrejaviva) ou o endereço dele.")


def do_canal(metadados: dict, canal: dict | None) -> bool:
    """O vídeo é do canal cadastrado? Confere pelo id e, se só há o @, pelo @."""
    if not canal:
        return False
    if canal.get("id") and metadados.get("channel_id") == canal["id"]:
        return True
    handle = (canal.get("handle") or "").lower()
    if not handle:
        return False
    do_video = str(metadados.get("uploader_id") or "").lower()
    endereco = str(metadados.get("channel_url") or metadados.get("uploader_url") or "").lower()
    return do_video == handle or endereco.rstrip("/").endswith(f"/{handle}")


def precisa_esperar(metadados: dict) -> bool:
    """A live ainda está no ar (ou o YouTube ainda prepara o vídeo dela)."""
    return metadados.get("live_status") in SITUACOES_ESPERAR or bool(metadados.get("is_live"))


def data_do_video(metadados: dict) -> str | None:
    """O dia em que a live aconteceu (ou o vídeo foi publicado), no fuso de São Paulo, como 2026-09-28."""
    for campo in ("release_timestamp", "timestamp"):
        valor = metadados.get(campo)
        if isinstance(valor, (int, float)) and valor > 0:
            return datetime.fromtimestamp(valor, TZ).date().isoformat()
    bruto = str(metadados.get("upload_date") or "")
    if re.fullmatch(r"\d{8}", bruto):
        return f"{bruto[:4]}-{bruto[4:6]}-{bruto[6:]}"
    return None


def titulo_do_video(metadados: dict, padrao: str = "Culto") -> str:
    titulo = " ".join(str(metadados.get("title") or "").split())
    return titulo[:120] or padrao


def nome_de_arquivo_do_video(titulo: str, extensao: str) -> str:
    """O título vira nome de arquivo: é o que o XML do DaVinci e do Premiere procura."""
    base = re.sub(r'[\\/:*?"<>|]+', " ", titulo)
    base = " ".join(base.split())[:120].strip(" .") or "culto"
    return f"{base}{extensao}"


def ler_feed(texto: str) -> list[dict]:
    """Os vídeos do feed RSS do canal: id, título e quando foi publicado."""
    try:
        raiz = ET.fromstring(texto)
    except ET.ParseError:
        return []
    videos = []
    for entrada in raiz.findall(f"{_ATOM}entry"):
        video_id = (entrada.findtext(f"{_YT}videoId") or "").strip()
        publicado = (entrada.findtext(f"{_ATOM}published") or "").strip()
        if not _ID_VIDEO.fullmatch(video_id):
            continue
        try:
            momento = datetime.fromisoformat(publicado)
        except ValueError:
            continue
        videos.append({"video_id": video_id, "titulo": (entrada.findtext(f"{_ATOM}title") or "").strip(),
                       "publicado": momento})
    return videos


def videos_novos(videos: list[dict], vistos: list[str]) -> list[dict]:
    """
    O que o monitor ainda não olhou, do mais antigo ao mais novo. A data do feed não serve de
    filtro: a live agendada com dias de antecedência entra no feed com a data do agendamento.
    """
    ja_vistos = set(vistos)
    novos = [video for video in videos if video["video_id"] not in ja_vistos]
    return sorted(novos, key=lambda video: video["publicado"])


def lembrar_visto(vistos: list[str], video_id: str) -> list[str]:
    return ([item for item in vistos if item != video_id] + [video_id])[-MAXIMO_VISTOS:]


def montar_importacao(organizacao_id, criado_por, link: dict, momento: datetime | None = None) -> tuple[dict, dict]:
    """
    A gravação nova, ainda sem arquivo, e o job que baixa o vídeo. O job entra no lugar da ingestão
    (job_ingestao_id), então o cartão do culto mostra o download; depois ele enfileira a ingestão.
    Quem insere preenche entrada.midia_id e job_ingestao_id com os ids gerados.
    """
    midia = montar_midia(organizacao_id, criado_por, f"{link['origem']}-{link['id']}.mp4", 0, momento=momento)
    midia.update({"status": STATUS_PROCESSANDO,
                  "nome": "Importando do YouTube" if link["origem"] == "youtube" else "Importando do Google Drive",
                  "importacao": dict(link)})
    job = montar_job("importar_link", organizacao_id, {"midia_id": "", **link}, prioridade=PRIORIDADE_INGESTAO,
                     criado_por=criado_por, momento=momento)
    return midia, job
