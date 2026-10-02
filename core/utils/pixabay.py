# -----------------------------------------------
# HolyCut — busca na Pixabay (foto e vídeo de apoio)
#
# A chave vai na consulta e nunca é registrada em log. O arquivo só é baixado
# de um endereço *.pixabay.com que a própria resposta trouxe.
# -----------------------------------------------
import json
from urllib import error, parse, request

from core.config import PIXABAY_API_KEY

LIMITE_IMAGEM = 8 * 1024 * 1024
LIMITE_VIDEO = 80 * 1024 * 1024
POR_PAGINA = 12


class ErroPixabay(RuntimeError):
    pass


def configurada() -> bool:
    return bool(PIXABAY_API_KEY.strip())


def url_permitida(url: str) -> bool:
    """Só https de um host da Pixabay. Recusa o resto, inclusive redirecionamento."""
    partes = parse.urlparse(url or "")
    host = (partes.hostname or "").lower()
    return partes.scheme == "https" and (host == "pixabay.com" or host.endswith(".pixabay.com"))


def _nome(hit: dict) -> str:
    tags = str(hit.get("tags") or "").split(",")
    return (tags[0].strip() or "Imagem")[:40]


def _resumo(hit: dict, tipo: str, arquivo: str, miniatura: str, duracao: int | None,
            largura: int, altura: int) -> dict | None:
    if not url_permitida(arquivo) or not url_permitida(miniatura):
        return None
    pagina = str(hit.get("pageURL") or "")
    return {
        "id": int(hit["id"]),
        "tipo": tipo,
        "nome": _nome(hit),
        "autor": str(hit.get("user") or "")[:80],
        "pagina": pagina if url_permitida(pagina) else "",
        "miniatura": miniatura,
        "duracao": duracao,
        "largura": largura,
        "altura": altura,
        "arquivo": arquivo,
    }


def resumir_imagem(hit: dict) -> dict | None:
    arquivo = hit.get("largeImageURL") or hit.get("webformatURL") or ""
    miniatura = hit.get("previewURL") or hit.get("webformatURL") or ""
    return _resumo(hit, "imagem", arquivo, miniatura, None,
                   int(hit.get("imageWidth") or hit.get("webformatWidth") or 0),
                   int(hit.get("imageHeight") or hit.get("webformatHeight") or 0))


def resumir_video(hit: dict) -> dict | None:
    videos = hit.get("videos") or {}
    # medium é 1080p (ou 720p nos antigos) e vem na conta gratuita. large pode vir vazio.
    escolhido = None
    for tamanho in ("medium", "small", "tiny"):
        item = videos.get(tamanho) or {}
        if item.get("url") and int(item.get("size") or 0) > 0:
            escolhido = item
            break
    if not escolhido:
        return None
    return _resumo(hit, "video", escolhido["url"], escolhido.get("thumbnail") or "",
                   int(hit.get("duration") or 0) or None,
                   int(escolhido.get("width") or 0), int(escolhido.get("height") or 0))


def _pedir(url: str, limite: int) -> bytes:
    if not url_permitida(url):
        raise ErroPixabay("O arquivo não veio da Pixabay.")
    pedido = request.Request(url, headers={"User-Agent": "HolyCut"})
    try:
        with request.urlopen(pedido, timeout=60) as resposta:
            if not url_permitida(resposta.geturl()):
                raise ErroPixabay("O arquivo não veio da Pixabay.")
            conteudo = bytearray()
            while pedaco := resposta.read(256 * 1024):
                conteudo += pedaco
                if len(conteudo) > limite:
                    raise ErroPixabay("O arquivo da Pixabay passou do tamanho aceito.")
            return bytes(conteudo)
    except ErroPixabay:
        raise
    except error.HTTPError as erro:
        raise ErroPixabay(f"A Pixabay respondeu {erro.code}.") from None
    except (error.URLError, TimeoutError):
        raise ErroPixabay("Não foi possível falar com a Pixabay.") from None


def _consultar(tipo: str, parametros: dict) -> dict:
    if not configurada():
        raise ErroPixabay("A busca de imagens ainda não está configurada.")
    base = "https://pixabay.com/api/videos/" if tipo == "video" else "https://pixabay.com/api/"
    consulta = {"key": PIXABAY_API_KEY, "safesearch": "true", "lang": "pt", **parametros}
    url = f"{base}?{parse.urlencode(consulta)}"
    bruto = _pedir(url, 2 * 1024 * 1024)
    try:
        return json.loads(bruto.decode())
    except json.JSONDecodeError:
        raise ErroPixabay("A Pixabay devolveu uma resposta inválida.") from None


def buscar(tipo: str, texto: str) -> list[dict]:
    """Até 12 fotos ou vídeos. A miniatura pode aparecer na busca; o arquivo, não no navegador."""
    q = " ".join(texto.split())[:100]
    if len(q) < 2:
        raise ErroPixabay("Escreva pelo menos duas letras para buscar.")
    extra = {"image_type": "photo"} if tipo == "imagem" else {}
    dados = _consultar(tipo, {"q": q, "per_page": POR_PAGINA, **extra})
    resumir = resumir_imagem if tipo == "imagem" else resumir_video
    return [item for hit in dados.get("hits") or [] if (item := resumir(hit))]


def obter(tipo: str, pixabay_id: int) -> dict:
    """Um item pelo id, com o endereço de download que a Pixabay devolveu agora."""
    dados = _consultar(tipo, {"id": str(int(pixabay_id))})
    hits = dados.get("hits") or []
    if not hits:
        raise ErroPixabay("Esse arquivo não está mais na Pixabay.")
    item = (resumir_imagem if tipo == "imagem" else resumir_video)(hits[0])
    if item is None:
        raise ErroPixabay("A Pixabay não entregou o arquivo.")
    return item


def baixar_arquivo(url: str, tipo: str) -> bytes:
    conteudo = _pedir(url, LIMITE_IMAGEM if tipo == "imagem" else LIMITE_VIDEO)
    if tipo == "video" and b"ftyp" not in conteudo[:64]:
        raise ErroPixabay("O vídeo da Pixabay não veio em MP4.")
    if not conteudo:
        raise ErroPixabay("O arquivo da Pixabay veio vazio.")
    return conteudo
