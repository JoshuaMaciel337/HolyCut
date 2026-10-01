# -----------------------------------------------
# HolyCut — gerador do brand kit
#
# Gera símbolo, logos, ícones do app, favicon e design tokens a partir
# das definições deste arquivo. Rodar de novo sempre que mudar cor ou forma.
#
#   python brand/gerar_brand_kit.py
#   python brand/gerar_brand_kit.py --so-tokens   (só as cores, sem logos nem navegador)
#
# Dependências: fonttools, Pillow (brand/requirements.txt)
# PNGs são renderizados pelo Edge ou Chrome em modo headless.
# -----------------------------------------------

# -----------------------------------------------
# IMPORTS — stdlib primeiro, depois terceiros
# -----------------------------------------------
import argparse
import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from PIL import Image

# -----------------------------------------------
# CONFIGURAÇÕES
# -----------------------------------------------
PASTA_BRAND = Path(__file__).resolve().parent
PASTA_FONTES = PASTA_BRAND / "fontes"
PASTA_LOGO = PASTA_BRAND / "logo"
PASTA_ICONE = PASTA_BRAND / "app-icon"
PASTA_TOKENS = PASTA_BRAND / "tokens"

FONTE_MONTSERRAT = PASTA_FONTES / "Montserrat[wght].ttf"

NAVEGADORES = [
    os.environ.get("HOLYCUT_NAVEGADOR", ""),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
]
TIMEOUT_RENDER_SEGUNDOS = 60

SLOGAN = ["TRANSFORME MOMENTOS", "EM HISTÓRIAS."]

# Paleta oficial — kit v2 (outubro de 2026): pretos neutros, sem o azulado do v1,
# e o roxo #A855F7 dos elementos de IA. O cinza do texto secundário é um pouco mais
# claro que o #888B93 do kit, para passar com folga no contraste (7:1 no fundo).
CORES = {
    "ink": "#070709",
    "surface": "#0F0F13",
    "surface_2": "#17171C",
    "border": "#25252D",
    "white": "#FFFFFF",
    "text": "#F5F5F7",
    "muted": "#9C9EA8",
    "yellow": "#FFD24D",
    "orange": "#FF8A00",
    "coral": "#FF6A3D",
    "red": "#FF6B6B",
    "violet": "#A855F7",
    "magenta": "#F05BFF",
    "cyan": "#43D9FF",
}
# Tema claro: off-white entre o branco e o bege do FeedChurch, como o fundo do Cut.Pro.
# Só muda o que precisa: os acentos escurecem para o texto colorido passar no contraste
# (4,5:1 no fundo), e o degradê da marca troca o amarelo, que some no claro.
CORES_CLARO = {
    "ink": "#F8F6F2",
    "surface": "#FFFFFF",
    "surface_2": "#F1EEE8",
    "border": "#E3DFD7",
    "text": "#17171B",
    "muted": "#5C5C66",
    "yellow": "#A16207",
    "orange": "#C2570C",
    "coral": "#C2410C",
    "red": "#DC2626",
    "violet": "#9333EA",
    "magenta": "#C026D3",
    "cyan": "#0E7490",
}
GRADIENTES_CLARO = {
    "marca": ["#FF8A00", "#E2500C"],
    "brand": ["#FF8A00", "#E2500C", "#C026D3", "#9333EA"],
}
# A dobra do símbolo fica com o vermelho do kit v1: o logo não muda com a paleta da interface
COR_DOBRA = "#FF5A36"

GRADIENTES = {
    # Símbolo e "Cut" do logo: quente, como no styleboard
    "marca": ["#FFD24D", "#FF8A00"],
    # Versão do "Cut" para fundo claro: o amarelo perde contraste no branco
    "marca-claro": ["#FF9A1F", "#FF5A36"],
    "perna": ["#FF6A3D", "#FF8A00", "#FFC43D"],
    # Destaques gerais e ilustrações
    "brand": ["#FFD24D", "#FF8A00", "#F05BFF", "#A855F7"],
    # Elementos de IA
    "ia": ["#A855F7", "#F05BFF"],
    # Botões principais, como o "Comece agora" do mockup
    "cta": ["#A855F7", "#FF8A00"],
}

# -----------------------------------------------
# GEOMETRIA DO SÍMBOLO
# Coordenadas desenhadas sobre o styleboard. Os cantos são
# arredondados por um contorno da mesma cor com junção redonda.
# -----------------------------------------------
RAIO_CANTO = 18
HASTE_ESQUERDA = "8,64 97,8 97,452 8,452"
TRAVESSA = "97,213 204,213 97,285"
PLAY = "238,18 343,90 238,182"
DOBRA = "288,172 334,134 334,176"
PERNA_DIREITA = "190,286 332,208 332,400 238,452 238,300"
# Limites visuais do símbolo já com o arredondamento
MARCA_X0, MARCA_Y0, MARCA_X1, MARCA_Y1 = -1, -1, 352, 461
MARCA_L = MARCA_X1 - MARCA_X0
MARCA_A = MARCA_Y1 - MARCA_Y0

# Proporções do logo horizontal, medidas no styleboard
PROPORCAO_ALTURA_MAIUSCULA = 0.55   # altura da maiúscula / altura do símbolo
PROPORCAO_ESPACO = 0.33             # espaço entre símbolo e texto / largura do símbolo
PROPORCAO_MARGEM = 0.14             # margem em volta / altura do símbolo
PROPORCAO_SLOGAN = 0.17             # maiúscula do slogan / maiúscula do nome
ESPACAMENTO_SLOGAN_EM = 0.34        # espaçamento entre letras do slogan
AJUSTE_Y_C_EM = -0.02               # aproximação manual entre "y" e "C"

# -----------------------------------------------
# LOGGING
# -----------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)

# -----------------------------------------------
# FUNÇÕES AUXILIARES — FONTE
# -----------------------------------------------
_cache_fontes: dict[int, TTFont] = {}


def carregar_fonte(peso: int) -> TTFont:
    """Instancia a Montserrat variável no peso pedido."""
    if peso not in _cache_fontes:
        fonte = TTFont(FONTE_MONTSERRAT)
        _cache_fontes[peso] = instancer.instantiateVariableFont(fonte, {"wght": peso})
    return _cache_fontes[peso]


def medir_maiuscula(fonte: TTFont) -> float:
    """Altura da maiúscula em unidades da fonte, como fração do em."""
    return fonte["OS/2"].sCapHeight / fonte["head"].unitsPerEm


def texto_para_path(fonte: TTFont, texto: str, tamanho: float, x: float, y_base: float,
                    espacamento: float = 0.0, ajustes: dict | None = None) -> tuple[str, float]:
    """Converte texto em contorno SVG. Retorna (d do path, largura ocupada)."""
    escala = tamanho / fonte["head"].unitsPerEm
    cmap = fonte.getBestCmap()
    glifos = fonte.getGlyphSet()
    metricas = fonte["hmtx"]
    comandos, cursor, anterior = [], x, ""

    for caractere in texto:
        if ajustes and anterior + caractere in ajustes:
            cursor += ajustes[anterior + caractere] * tamanho
        nome = cmap.get(ord(caractere))
        if nome is None:
            logging.warning(f"Caractere sem glifo na fonte: {caractere!r}")
            continue
        caneta = SVGPathPen(glifos)
        glifos[nome].draw(TransformPen(caneta, (escala, 0, 0, -escala, cursor, y_base)))
        comandos.append(caneta.getCommands())
        cursor += metricas[nome][0] * escala + espacamento
        anterior = caractere

    largura = cursor - x - (espacamento if texto else 0)
    return " ".join(c for c in comandos if c), largura


def arredondar(d: str) -> str:
    """Reduz casas decimais dos paths para arquivos menores."""
    return re.sub(r"-?\d+\.\d+", lambda m: f"{float(m.group()):.1f}".rstrip("0").rstrip("."), d)

# -----------------------------------------------
# FUNÇÕES AUXILIARES — SVG
# -----------------------------------------------


def gradiente_linear(id_: str, cores: list[str], x1, y1, x2, y2) -> str:
    """Gera um linearGradient em coordenadas absolutas."""
    passos = len(cores) - 1
    paradas = "".join(
        f'<stop offset="{i / passos:.2f}" stop-color="{cor}"/>' for i, cor in enumerate(cores)
    )
    return (f'<linearGradient id="{id_}" gradientUnits="userSpaceOnUse" '
            f'x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">{paradas}</linearGradient>')


def desenhar_simbolo(modo: str, prefixo: str = "hc") -> tuple[str, str]:
    """
    Retorna (defs, grupo) do símbolo em coordenadas locais.
    modo: 'escuro' (branco + laranja), 'claro' (ink + laranja),
          'branco', 'preto' ou 'ink' (uma cor só).
    """
    if modo in ("branco", "preto", "ink"):
        cor = {"branco": CORES["white"], "preto": CORES["ink"], "ink": CORES["ink"]}[modo]
        base = perna = dobra = cor
        defs = ""
    else:
        base = CORES["white"] if modo == "escuro" else CORES["ink"]
        perna, dobra = f"url(#{prefixo}-perna)", COR_DOBRA
        defs = gradiente_linear(f"{prefixo}-perna", GRADIENTES["perna"], 332, 208, 238, 452)

    def forma(pontos: str, cor: str, raio: int = RAIO_CANTO) -> str:
        return (f'<polygon points="{pontos}" fill="{cor}" stroke="{cor}" '
                f'stroke-width="{raio}" stroke-linejoin="round"/>')

    grupo = "".join([
        forma(HASTE_ESQUERDA, base),
        forma(TRAVESSA, base),
        forma(PLAY, base),
        forma(DOBRA, dobra, raio=8),
        forma(PERNA_DIREITA, perna),
    ])
    return defs, grupo


def envolver_svg(largura: float, altura: float, conteudo: str, defs: str = "",
                 x0: float = 0, y0: float = 0, titulo: str = "HolyCut") -> str:
    """Monta o documento SVG final."""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0:.1f} {y0:.1f} {largura:.1f} {altura:.1f}" '
            f'role="img" aria-label="{titulo}"><title>{titulo}</title>'
            f'<defs>{defs}</defs>{conteudo}</svg>\n')


def salvar(caminho: Path, conteudo: str):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(conteudo, encoding="utf-8")
    logging.info(f"Gerado: {caminho.relative_to(PASTA_BRAND)}")

# -----------------------------------------------
# FUNÇÕES AUXILIARES — RENDERIZAÇÃO PNG
# -----------------------------------------------


def encontrar_navegador() -> str | None:
    for caminho in NAVEGADORES:
        if caminho and Path(caminho).exists():
            return caminho
    return None


def renderizar_png(svg: Path, png: Path, largura: int, navegador: str | None) -> bool:
    """Renderiza um SVG em PNG com fundo transparente via navegador headless."""
    if not navegador:
        return False
    texto = svg.read_text(encoding="utf-8")
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', texto).group(1).split()]
    altura = round(largura * vb[3] / vb[2])
    dimensionado = texto.replace("<svg ", f'<svg width="{largura}" height="{altura}" ', 1)

    with tempfile.TemporaryDirectory() as pasta:
        temporario = Path(pasta) / "render.svg"
        temporario.write_text(dimensionado, encoding="utf-8")
        png.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                [navegador, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                 "--default-background-color=00000000", f"--window-size={largura},{altura}",
                 f"--screenshot={png}", temporario.as_uri()],
                capture_output=True, timeout=TIMEOUT_RENDER_SEGUNDOS, check=True,
            )
        except Exception as e:
            logging.error(f"Falha ao renderizar {svg.name}: {e}")
            return False
    logging.info(f"Renderizado: {png.relative_to(PASTA_BRAND)} ({largura}x{altura})")
    return True

# -----------------------------------------------
# FUNÇÕES PRINCIPAIS — LOGOS
# -----------------------------------------------


def gerar_simbolos() -> list[Path]:
    """Símbolo sozinho em todas as variações."""
    margem = MARCA_A * PROPORCAO_MARGEM
    lado = MARCA_A + 2 * margem
    x0 = MARCA_X0 + MARCA_L / 2 - lado / 2
    y0 = MARCA_Y0 - margem
    arquivos = []
    for modo, nome in [("escuro", "simbolo"), ("claro", "simbolo-fundo-claro"),
                       ("branco", "simbolo-branco"), ("preto", "simbolo-preto")]:
        defs, grupo = desenhar_simbolo(modo)
        caminho = PASTA_LOGO / f"holycut-{nome}.svg"
        salvar(caminho, envolver_svg(lado, lado, grupo, defs, x0, y0))
        arquivos.append(caminho)
    return arquivos


def montar_logo_horizontal(modo: str, com_slogan: bool = False) -> str:
    """Símbolo + nome, opcionalmente com o slogan embaixo do nome."""
    fonte_nome = carregar_fonte(700)
    altura_maiuscula = MARCA_A * PROPORCAO_ALTURA_MAIUSCULA
    tamanho = altura_maiuscula / medir_maiuscula(fonte_nome)
    centro_y = MARCA_Y0 + MARCA_A / 2
    base_y = centro_y + altura_maiuscula / 2
    x_texto = MARCA_X1 + MARCA_L * PROPORCAO_ESPACO

    d_holy, l_holy = texto_para_path(fonte_nome, "Holy", tamanho, x_texto, base_y)
    x_cut = x_texto + l_holy + AJUSTE_Y_C_EM * tamanho
    d_cut, l_cut = texto_para_path(fonte_nome, "Cut", tamanho, x_cut, base_y)
    x_fim = x_cut + l_cut

    defs, grupo = desenhar_simbolo(modo)
    if modo in ("branco", "preto"):
        cor_holy = cor_cut = CORES["white"] if modo == "branco" else CORES["ink"]
    else:
        cor_holy = CORES["white"] if modo == "escuro" else CORES["ink"]
        cor_cut = "url(#hc-cut)"
        gradiente_cut = GRADIENTES["marca"] if modo == "escuro" else GRADIENTES["marca-claro"]
        defs += gradiente_linear("hc-cut", gradiente_cut,
                                 round(x_cut), round(base_y - altura_maiuscula),
                                 round(x_fim), round(base_y))

    conteudo = (grupo
                + f'<path d="{arredondar(d_holy)}" fill="{cor_holy}"/>'
                + f'<path d="{arredondar(d_cut)}" fill="{cor_cut}"/>')
    y_fim = MARCA_Y1

    if com_slogan:
        fonte_slogan = carregar_fonte(500)
        maiuscula_slogan = altura_maiuscula * PROPORCAO_SLOGAN
        tamanho_slogan = maiuscula_slogan / medir_maiuscula(fonte_slogan)
        espacamento = ESPACAMENTO_SLOGAN_EM * tamanho_slogan
        centro_x = (x_texto + x_fim) / 2
        cor_slogan = cor_holy if modo in ("branco", "preto") else (
            CORES["text"] if modo == "escuro" else CORES["surface_2"])
        linha_y = base_y + maiuscula_slogan * 3.2
        for linha in SLOGAN:
            _, largura = texto_para_path(fonte_slogan, linha, tamanho_slogan, 0, 0, espacamento)
            d, _ = texto_para_path(fonte_slogan, linha, tamanho_slogan,
                                   centro_x - largura / 2, linha_y, espacamento)
            conteudo += f'<path d="{arredondar(d)}" fill="{cor_slogan}"/>'
            y_fim = max(y_fim, linha_y)
            linha_y += maiuscula_slogan * 2.3

    margem = MARCA_A * PROPORCAO_MARGEM
    x0, y0 = MARCA_X0 - margem, MARCA_Y0 - margem
    return envolver_svg(x_fim + margem - x0, y_fim + margem - y0, conteudo, defs, x0, y0)


def gerar_logos_horizontais() -> list[Path]:
    arquivos = []
    for modo, sufixo in [("escuro", ""), ("claro", "-fundo-claro"),
                         ("branco", "-branco"), ("preto", "-preto")]:
        for com_slogan in (False, True):
            nome = f"holycut-horizontal{'-slogan' if com_slogan else ''}{sufixo}.svg"
            caminho = PASTA_LOGO / nome
            salvar(caminho, montar_logo_horizontal(modo, com_slogan))
            arquivos.append(caminho)
    return arquivos

# -----------------------------------------------
# FUNÇÕES PRINCIPAIS — ÍCONES DO APP
# -----------------------------------------------


def montar_icone(fundo: str, modo_simbolo: str, arredondado: bool = True,
                 ocupacao: float = 0.56) -> str:
    """Ícone quadrado 1024. ocupacao = altura do símbolo / lado do ícone."""
    lado = 1024
    escala = lado * ocupacao / MARCA_A
    tx = (lado - MARCA_L * escala) / 2 - MARCA_X0 * escala
    ty = (lado - MARCA_A * escala) / 2 - MARCA_Y0 * escala
    defs, grupo = desenhar_simbolo(modo_simbolo, prefixo="ic")

    if fundo == "escuro":
        defs += gradiente_linear("ic-fundo", ["#171226", CORES["ink"]], lado, 0, 0, lado)
        preenchimento = "url(#ic-fundo)"
    elif fundo == "gradiente":
        defs += gradiente_linear("ic-fundo", ["#FFD24D", "#FF8A00", "#7B61FF"], 0, 0, lado, lado)
        preenchimento = "url(#ic-fundo)"
    else:
        preenchimento = CORES["white"]

    raio = 230 if arredondado else 0
    conteudo = (f'<rect width="{lado}" height="{lado}" rx="{raio}" fill="{preenchimento}"/>'
                f'<g transform="translate({tx:.1f} {ty:.1f}) scale({escala:.4f})">{grupo}</g>')
    return envolver_svg(lado, lado, conteudo, defs, titulo="HolyCut")


def gerar_icones() -> dict[str, Path]:
    variacoes = {
        "icone-escuro": ("escuro", "escuro", True, 0.56),
        "icone-claro": ("claro", "claro", True, 0.56),
        "icone-gradiente": ("gradiente", "ink", True, 0.56),
        # PWA maskable e Apple: quadrado cheio, símbolo dentro da zona segura
        "icone-maskable": ("escuro", "escuro", False, 0.46),
        "favicon": ("escuro", "escuro", True, 0.64),
    }
    arquivos = {}
    for nome, (fundo, simbolo, arredondado, ocupacao) in variacoes.items():
        caminho = PASTA_ICONE / f"{nome}.svg"
        salvar(caminho, montar_icone(fundo, simbolo, arredondado, ocupacao))
        arquivos[nome] = caminho
    return arquivos

# -----------------------------------------------
# FUNÇÕES PRINCIPAIS — TOKENS
# -----------------------------------------------


def css_gradiente(cores: list[str], angulo: int = 135) -> str:
    passos = len(cores) - 1
    paradas = ", ".join(f"{cor} {round(i * 100 / passos)}%" for i, cor in enumerate(cores))
    return f"linear-gradient({angulo}deg, {paradas})"


def gerar_tokens():
    tipografia = {
        "display": "'Montserrat', system-ui, sans-serif",
        "body": "'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif",
        "script": "'Caveat', cursive",
    }
    raios = {"sm": 8, "md": 14, "lg": 22, "pill": 999}
    sombras = {
        "soft": "0 10px 30px rgba(0,0,0,.28)",
        "glow-violet": "0 0 28px rgba(168,85,247,.35)",
        "glow-orange": "0 0 28px rgba(255,138,0,.30)",
    }

    linhas = ["/* HolyCut Design Tokens — gerado por brand/gerar_brand_kit.py, não editar à mão */",
              ":root {"]
    linhas += [f"  --hc-{nome.replace('_', '-')}: {valor};" for nome, valor in CORES.items()]
    linhas.append("")
    linhas += [f"  --hc-gradient-{nome}: {css_gradiente(cores)};" for nome, cores in GRADIENTES.items()]
    linhas.append("")
    linhas += [f"  --hc-font-{nome}: {valor};" for nome, valor in tipografia.items()]
    linhas.append("")
    linhas += [f"  --hc-radius-{nome}: {valor}px;" for nome, valor in raios.items()]
    linhas.append("")
    linhas += [f"  --hc-shadow-{nome}: {valor};" for nome, valor in sombras.items()]
    linhas.append("}")
    linhas += ["", "/* Tema claro: o site põe data-tema=\"claro\" no <html> */", ':root[data-tema="claro"] {']
    linhas += [f"  --hc-{nome.replace('_', '-')}: {valor};" for nome, valor in CORES_CLARO.items()]
    linhas += [f"  --hc-gradient-{nome}: {css_gradiente(cores)};" for nome, cores in GRADIENTES_CLARO.items()]
    linhas.append("  --hc-shadow-soft: 0 10px 30px rgba(23,23,27,.08);")
    linhas.append("}")
    salvar(PASTA_TOKENS / "design-tokens.css", "\n".join(linhas) + "\n")

    salvar(PASTA_TOKENS / "cores.json", json.dumps({
        "cores": CORES,
        "gradientes": GRADIENTES,
        "tema_claro": {"cores": CORES_CLARO, "gradientes": GRADIENTES_CLARO},
        "tipografia": {
            "display": {"familia": "Montserrat", "pesos": [600, 700]},
            "body": {"familia": "Inter", "pesos": [400, 500, 600, 700]},
            "script": {"familia": "Caveat", "pesos": [500, 700]},
        },
        "raios": raios,
        "sombras": sombras,
    }, indent=2, ensure_ascii=False) + "\n")

# -----------------------------------------------
# FUNÇÕES PRINCIPAIS — PNG E FAVICON
# -----------------------------------------------


def gerar_pngs(simbolos: list[Path], horizontais: list[Path], icones: dict[str, Path]):
    navegador = encontrar_navegador()
    if not navegador:
        logging.warning("Edge/Chrome não encontrado — PNGs não gerados. Defina HOLYCUT_NAVEGADOR.")
        return

    pasta_png = PASTA_LOGO / "png"
    for svg in simbolos:
        renderizar_png(svg, pasta_png / f"{svg.stem}-1024.png", 1024, navegador)
    for svg in horizontais:
        renderizar_png(svg, pasta_png / f"{svg.stem}-1600.png", 1600, navegador)

    for nome in ("icone-escuro", "icone-claro", "icone-gradiente"):
        renderizar_png(icones[nome], PASTA_ICONE / f"{nome}-1024.png", 1024, navegador)

    # Tamanhos usados pelo PWA, iOS e navegador
    base_maskable = PASTA_ICONE / "icone-maskable-512.png"
    if renderizar_png(icones["icone-maskable"], base_maskable, 512, navegador):
        maskable = Image.open(base_maskable)
        maskable.resize((192, 192), Image.LANCZOS).save(PASTA_ICONE / "icone-maskable-192.png")
        maskable.resize((180, 180), Image.LANCZOS).save(PASTA_ICONE / "apple-touch-icon.png")

    base_escuro = PASTA_ICONE / "icone-escuro-512.png"
    if renderizar_png(icones["icone-escuro"], base_escuro, 512, navegador):
        Image.open(base_escuro).resize((192, 192), Image.LANCZOS).save(PASTA_ICONE / "icone-escuro-192.png")

    base_favicon = PASTA_ICONE / "favicon-256.png"
    if renderizar_png(icones["favicon"], base_favicon, 256, navegador):
        Image.open(base_favicon).save(PASTA_ICONE / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
        base_favicon.unlink()
        logging.info("Gerado: app-icon/favicon.ico (16, 32, 48)")

# -----------------------------------------------
# EXECUÇÃO
# -----------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Gera o brand kit do HolyCut")
    parser.add_argument("--so-tokens", action="store_true",
                        help="Gera só os tokens de cor, sem redesenhar os logos e sem abrir o navegador")
    args = parser.parse_args()
    if args.so_tokens:
        gerar_tokens()
        logging.info("Tokens gerados.")
        return
    if not FONTE_MONTSERRAT.exists():
        logging.error(f"Fonte não encontrada: {FONTE_MONTSERRAT}")
        return
    simbolos = gerar_simbolos()
    horizontais = gerar_logos_horizontais()
    icones = gerar_icones()
    gerar_tokens()
    gerar_pngs(simbolos, horizontais, icones)
    logging.info("Brand kit gerado.")


if __name__ == "__main__":
    main()
