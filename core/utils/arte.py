# -----------------------------------------------
# HolyCut — arte sobre o vídeo: logo da igreja, textos e templates
#
# Cada elemento vira uma camada PNG transparente do tamanho do vídeo.
# A mesma camada aparece na prévia do navegador e entra no vídeo final
# pelo filtro overlay do FFmpeg, então o que a igreja vê é o que sai.
# Fontes: as da marca, em brand/fontes (licença OFL, pode queimar no vídeo).
# -----------------------------------------------
import io
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, UnidentifiedImageError

from core.config import PASTA_FONTES

FONTES = {
    "display": ("Montserrat[wght].ttf", {"normal": "SemiBold", "forte": "ExtraBold"}),
    "texto": ("Inter[opsz,wght].ttf", {"normal": "Medium", "forte": "Bold"}),
    "manuscrita": ("Caveat[wght].ttf", {"normal": "Regular", "forte": "Bold"}),
}
LADO_MAXIMO_LOGO = 1024
MARGEM = 0.06            # margem das bordas, em fração da largura
LARGURA_TEXTO = 0.84     # largura máxima de um bloco de texto
MAX_LINHAS = 6

# Estilo → (família, peso, tamanho em fração da largura, caixa alta, entrelinha)
ESTILOS = {
    "destaque": ("display", "forte", 0.078, True, 1.08),
    "limpo": ("texto", "forte", 0.062, False, 1.18),
    "manuscrito": ("manuscrita", "forte", 0.13, False, 0.98),
}
POSICOES_TEXTO = {"topo": 0.14, "centro": 0.5, "base": 0.8}  # centro vertical do bloco


class ErroImagem(ValueError):
    pass


# -----------------------------------------------
# LOGO
# -----------------------------------------------
def preparar_logo(conteudo: bytes) -> bytes:
    """Valida a imagem enviada e devolve um PNG com transparência, sem bordas vazias, de até 1024 px."""
    try:
        imagem = Image.open(io.BytesIO(conteudo))
        imagem.load()
    except (UnidentifiedImageError, OSError) as e:
        raise ErroImagem("O arquivo não é uma imagem PNG, JPG ou WEBP válida.") from e
    imagem = imagem.convert("RGBA")
    caixa = imagem.getchannel("A").getbbox()
    if caixa is None:
        raise ErroImagem("A imagem está totalmente transparente.")
    imagem = imagem.crop(caixa)
    imagem.thumbnail((LADO_MAXIMO_LOGO, LADO_MAXIMO_LOGO), Image.Resampling.LANCZOS)
    saida = io.BytesIO()
    imagem.save(saida, format="PNG", optimize=True)
    return saida.getvalue()


def camada_logo(largura: int, altura: int, logo_png: bytes, posicao: str = "topo_direita",
                tamanho: float = 0.16, opacidade: float = 0.9) -> Image.Image:
    camada = Image.new("RGBA", (largura, altura), (0, 0, 0, 0))
    logo = Image.open(io.BytesIO(logo_png)).convert("RGBA")
    alvo = max(int(largura * min(max(tamanho, 0.05), 0.5)), 8)
    logo = logo.resize((alvo, max(int(logo.height * alvo / logo.width), 1)), Image.Resampling.LANCZOS)
    if opacidade < 1:
        alfa = logo.getchannel("A").point(lambda valor: int(valor * max(opacidade, 0)))
        logo.putalpha(alfa)
    margem = int(largura * MARGEM)
    x = margem if posicao.endswith("esquerda") else largura - margem - logo.width
    y = margem if posicao.startswith("topo") else altura - margem - logo.height
    camada.alpha_composite(logo, (x, y))
    return camada


# -----------------------------------------------
# TEXTO
# -----------------------------------------------
@lru_cache(maxsize=64)
def carregar_fonte(familia: str, peso: str, tamanho: int) -> ImageFont.FreeTypeFont:
    arquivo, pesos = FONTES[familia]
    # Motor de layout fixo: o worker tem a libraqm (vem com o FFmpeg) e a API não. Com motores
    # diferentes, o mesmo texto media larguras diferentes e quebrava a linha em outro lugar na
    # prévia e no vídeo final. O BASIC existe em todo lugar e atende bem o português.
    fonte = ImageFont.truetype(str(PASTA_FONTES / arquivo), tamanho, layout_engine=ImageFont.Layout.BASIC)
    fonte.set_variation_by_name(pesos[peso])
    return fonte


def quebrar_linhas(texto: str, fonte: ImageFont.FreeTypeFont, largura_maxima: int) -> list[str]:
    """Quebra por palavras para caber na largura. Respeita as quebras de linha digitadas."""
    linhas = []
    for paragrafo in texto.splitlines() or [""]:
        atual = ""
        for palavra in paragrafo.split():
            tentativa = f"{atual} {palavra}".strip()
            if fonte.getlength(tentativa) <= largura_maxima or not atual:
                atual = tentativa
            else:
                linhas.append(atual)
                atual = palavra
        linhas.append(atual)
    return [linha for linha in linhas if linha] or [""]


def _hex_para_rgb(cor: str) -> tuple[int, int, int]:
    cor = cor.lstrip("#")
    return int(cor[0:2], 16), int(cor[2:4], 16), int(cor[4:6], 16)


def camada_texto(largura: int, altura: int, texto: str, estilo: str = "destaque", posicao: str = "base",
                 cor_destaque: str = "#FF8A00", referencia: str = "", escala: float = 1.0) -> Image.Image:
    """
    Bloco de texto centralizado, com sombra suave para ler sobre qualquer imagem.
    No estilo "destaque", cada linha ganha uma faixa na cor da igreja.
    A referência (ex.: "João 3:16") sai menor, logo abaixo.
    """
    familia, peso, fracao, caixa_alta, entrelinha = ESTILOS.get(estilo, ESTILOS["destaque"])
    texto = (texto or "").strip()
    if caixa_alta:
        texto = texto.upper()
    largura_maxima = int(largura * LARGURA_TEXTO)
    tamanho = max(int(largura * fracao * min(max(escala, 0.5), 2.0)), 12)
    while True:
        fonte = carregar_fonte(familia, peso, tamanho)
        linhas = quebrar_linhas(texto, fonte, largura_maxima)
        if len(linhas) <= MAX_LINHAS or tamanho <= 16:
            break
        tamanho = int(tamanho * 0.9)

    subida, descida = fonte.getmetrics()
    altura_linha = int((subida + descida) * entrelinha)
    fonte_referencia = carregar_fonte("display", "forte", max(int(tamanho * 0.62), 12))
    altura_referencia = int(sum(fonte_referencia.getmetrics()) * 1.6) if referencia else 0
    altura_bloco = altura_linha * len(linhas) + altura_referencia
    topo = int(altura * POSICOES_TEXTO.get(posicao, 0.8) - altura_bloco / 2)
    topo = min(max(topo, int(largura * MARGEM)), altura - altura_bloco - int(largura * MARGEM))

    texto_camada = Image.new("RGBA", (largura, altura), (0, 0, 0, 0))
    desenho = ImageDraw.Draw(texto_camada)
    faixas = Image.new("RGBA", (largura, altura), (0, 0, 0, 0))
    desenho_faixas = ImageDraw.Draw(faixas)
    cor = _hex_para_rgb(cor_destaque)
    for indice, linha in enumerate(linhas):
        largura_linha = fonte.getlength(linha)
        x = (largura - largura_linha) / 2
        y = topo + indice * altura_linha
        if estilo == "destaque" and linha:
            folga = tamanho * 0.28
            desenho_faixas.rounded_rectangle(
                (x - folga, y + tamanho * 0.05, x + largura_linha + folga, y + altura_linha - tamanho * 0.02),
                radius=int(tamanho * 0.18), fill=(*cor, 235))
        desenho.text((x, y), linha, font=fonte, fill=(255, 255, 255, 255))
    if referencia:
        largura_ref = fonte_referencia.getlength(referencia)
        y = topo + len(linhas) * altura_linha + int(altura_referencia * 0.2)
        desenho.text(((largura - largura_ref) / 2, y), referencia, font=fonte_referencia, fill=(*cor, 255))

    # Sombra: a própria camada de texto, escurecida e desfocada
    sombra = Image.new("RGBA", (largura, altura), (0, 0, 0, 0))
    sombra.putalpha(texto_camada.getchannel("A").point(lambda valor: int(valor * 0.55)))
    sombra = sombra.filter(ImageFilter.GaussianBlur(radius=max(largura * 0.008, 2)))

    resultado = Image.new("RGBA", (largura, altura), (0, 0, 0, 0))
    if estilo != "destaque":
        resultado.alpha_composite(sombra)
    resultado.alpha_composite(faixas)
    resultado.alpha_composite(texto_camada)
    return resultado


def para_png(imagem: Image.Image) -> bytes:
    saida = io.BytesIO()
    imagem.save(saida, format="PNG", compress_level=6)
    return saida.getvalue()


# -----------------------------------------------
# CAPAS DO ACERVO
# -----------------------------------------------
FUNDO_ESCURO = (11, 11, 15)     # --hc-ink
MAX_LINHAS_TITULO_POSTER = 4
MAX_LINHAS_TITULO_BANNER = 3


def _cobrir(imagem: Image.Image, largura: int, altura: int) -> Image.Image:
    """Preenche o tamanho sem distorcer, cortando as sobras pelo centro (como o object-fit: cover)."""
    escala = max(largura / imagem.width, altura / imagem.height)
    tamanho = (max(round(imagem.width * escala), largura), max(round(imagem.height * escala), altura))
    nova = imagem.resize(tamanho, Image.Resampling.LANCZOS)
    x, y = (nova.width - largura) // 2, (nova.height - altura) // 2
    return nova.crop((x, y, x + largura, y + altura))


def fundo_sem_video(largura: int, altura: int, cor_destaque: str = "#FF8A00") -> Image.Image:
    """Para gravação só de áudio: fundo escuro com um brilho da cor da igreja no canto."""
    cor = np.array(_hex_para_rgb(cor_destaque), dtype=np.float32)
    ys, xs = np.mgrid[0:altura, 0:largura]
    distancia = np.hypot((xs - largura * 0.8) / largura, (ys - altura * 0.2) / altura)
    brilho = np.clip(1 - distancia / 0.9, 0, 1)[..., None] ** 2 * 0.55
    pixels = np.array(FUNDO_ESCURO, dtype=np.float32) * (1 - brilho) + cor * brilho
    return Image.fromarray(pixels.astype(np.uint8), "RGB")


def _escurecer(imagem: Image.Image, vertical: bool) -> Image.Image:
    """Degradê escuro embaixo (e à esquerda, no banner), onde o texto fica."""
    largura, altura = imagem.size
    y = np.linspace(0, 1, altura, dtype=np.float32)[:, None]
    x = np.linspace(0, 1, largura, dtype=np.float32)[None, :]
    inicio = 0.32 if vertical else 0.4
    alfa = np.clip((y - inicio) / (0.95 - inicio), 0, 1) ** 1.1 * 0.94
    if not vertical:
        alfa = np.maximum(alfa, np.clip(1 - x / 0.72, 0, 1) ** 1.2 * 0.88)
    alfa = np.maximum(alfa, 0.16)   # um véu leve em tudo, para a imagem não brigar com o texto
    pixels = np.asarray(imagem, dtype=np.float32)
    escuro = np.array(FUNDO_ESCURO, dtype=np.float32)
    resultado = pixels * (1 - alfa[..., None]) + escuro * alfa[..., None]
    return Image.fromarray(resultado.astype(np.uint8), "RGB")


def _titulo_que_cabe(titulo: str, largura_maxima: int, tamanho_inicial: int, max_linhas: int):
    tamanho = tamanho_inicial
    while True:
        fonte = carregar_fonte("display", "forte", tamanho)
        linhas = quebrar_linhas(titulo, fonte, largura_maxima)
        # Uma palavra comprida não quebra: a fonte diminui até a linha mais larga caber
        cabe = max(fonte.getlength(linha) for linha in linhas) <= largura_maxima
        if (len(linhas) <= max_linhas and cabe) or tamanho <= 18:
            break
        tamanho = int(tamanho * 0.92)
    if len(linhas) > max_linhas:
        linhas = linhas[:max_linhas]
        ultima = linhas[-1]
        while ultima and fonte.getlength(ultima + "…") > largura_maxima:
            ultima = ultima[:-1]
        linhas[-1] = ultima.rstrip() + "…"
    return fonte, linhas


def desenhar_capa(base: Image.Image | None, largura: int, altura: int, titulo: str, informacao: str = "",
                  serie: str = "", cor_destaque: str = "#FF8A00", logo_png: bytes | None = None) -> Image.Image:
    """
    Capa do culto no acervo: o quadro do vídeo (ou o fundo da cor da igreja, se não houver) com o
    título na fonte da marca. Vertical (pôster 2:3) ou horizontal (banner 16:9).
    """
    vertical = altura > largura
    fundo = _cobrir(base.convert("RGB"), largura, altura) if base is not None else fundo_sem_video(largura, altura,
                                                                                                  cor_destaque)
    imagem = _escurecer(fundo, vertical).convert("RGBA")
    # O texto vai numa camada própria, para ganhar sombra e ler sobre qualquer quadro
    camada = Image.new("RGBA", (largura, altura), (0, 0, 0, 0))
    desenho = ImageDraw.Draw(camada)
    cor = _hex_para_rgb(cor_destaque)

    margem = int(largura * 0.07) if vertical else int(altura * 0.08)
    largura_texto = largura - 2 * margem if vertical else int(largura * 0.55)
    tamanho_titulo = int(largura * 0.115) if vertical else int(altura * 0.105)
    fonte_titulo, linhas = _titulo_que_cabe((titulo or "Culto").strip(), largura_texto, tamanho_titulo,
                                            MAX_LINHAS_TITULO_POSTER if vertical else MAX_LINHAS_TITULO_BANNER)
    fonte_info = carregar_fonte("texto", "normal", max(int(tamanho_titulo * 0.36), 12))
    fonte_serie = carregar_fonte("texto", "forte", max(int(tamanho_titulo * 0.3), 11))
    subida, descida = fonte_titulo.getmetrics()
    altura_linha = int((subida + descida) * 1.02)

    # De baixo para cima: informação, título, série e a faixa na cor da igreja
    y = altura - margem
    if informacao:
        y -= sum(fonte_info.getmetrics())
        desenho.text((margem, y), informacao, font=fonte_info, fill=(255, 255, 255, 215))
        y -= int(tamanho_titulo * 0.28)
    y -= altura_linha * len(linhas)
    for indice, linha in enumerate(linhas):
        desenho.text((margem, y + indice * altura_linha), linha, font=fonte_titulo, fill=(255, 255, 255, 255))
    y -= int(tamanho_titulo * 0.2)
    if serie:
        texto_serie = serie.upper()
        while texto_serie and fonte_serie.getlength(texto_serie) > largura_texto:
            texto_serie = texto_serie[:-1]
        y -= sum(fonte_serie.getmetrics())
        desenho.text((margem, y), texto_serie, font=fonte_serie, fill=(*cor, 255))
        y -= int(tamanho_titulo * 0.18)
    espessura = max(int(tamanho_titulo * 0.08), 3)
    desenho.rounded_rectangle((margem, y - espessura, margem + int(tamanho_titulo * 0.9), y),
                              radius=espessura // 2, fill=(*cor, 255))

    sombra = Image.new("RGBA", (largura, altura), (0, 0, 0, 0))
    sombra.putalpha(camada.getchannel("A").point(lambda valor: int(valor * 0.75)))
    sombra = sombra.filter(ImageFilter.GaussianBlur(radius=max(int(tamanho_titulo * 0.12), 3)))
    imagem.alpha_composite(sombra)
    imagem.alpha_composite(camada)

    if logo_png:
        logo = Image.open(io.BytesIO(logo_png)).convert("RGBA")
        alvo_altura = int(altura * (0.07 if vertical else 0.1))
        logo = logo.resize((max(int(logo.width * alvo_altura / logo.height), 1), alvo_altura),
                           Image.Resampling.LANCZOS)
        if logo.width > largura * 0.4:
            logo = logo.resize((int(largura * 0.4), max(int(logo.height * largura * 0.4 / logo.width), 1)),
                               Image.Resampling.LANCZOS)
        imagem.alpha_composite(logo, (margem, margem))
    return imagem.convert("RGB")


LADO_MAXIMO_FUNDO_CAPA = 1920


def preparar_fundo_capa(conteudo: bytes) -> bytes:
    """Valida a imagem enviada para a capa e devolve um JPG de até 1920 px, sem transparência."""
    try:
        imagem = Image.open(io.BytesIO(conteudo))
        imagem.load()
    except (UnidentifiedImageError, OSError) as e:
        raise ErroImagem("O arquivo não é uma imagem JPG, PNG ou WEBP válida.") from e
    if imagem.mode in ("RGBA", "LA", "P"):
        fundo = Image.new("RGB", imagem.size, FUNDO_ESCURO)
        fundo.paste(imagem.convert("RGBA"), mask=imagem.convert("RGBA").getchannel("A"))
        imagem = fundo
    imagem = imagem.convert("RGB")
    imagem.thumbnail((LADO_MAXIMO_FUNDO_CAPA, LADO_MAXIMO_FUNDO_CAPA), Image.Resampling.LANCZOS)
    return para_jpeg(imagem, qualidade=90)


def para_jpeg(imagem: Image.Image, qualidade: int = 86) -> bytes:
    saida = io.BytesIO()
    imagem.convert("RGB").save(saida, format="JPEG", quality=qualidade, optimize=True, progressive=True)
    return saida.getvalue()
