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
