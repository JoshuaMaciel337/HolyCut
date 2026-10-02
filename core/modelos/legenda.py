# -----------------------------------------------
# HolyCut — legendas animadas a partir da transcrição
#
# Os blocos (quais palavras aparecem juntas, em que instante do vídeo final
# e qual delas é o destaque) são calculados aqui. A prévia e o arquivo ASS
# do render leem esses mesmos blocos: o navegador só pinta, o libass só queima.
# A fala entra como foi transcrita. Este módulo não corrige o português.
# -----------------------------------------------
import re

from core.modelos.fala import VICIOS, edicoes_validas, ids_validos
from core.utils.render import planejar_trechos

PRESETS = ("clean", "karaoke", "destaque", "digno", "flutuante")
POSICOES = ("base", "centro")
COR_DOURADA = "#FFD24D"   # o dourado do preset Digno; os outros usam a cor da igreja
PALAVRAS_PADRAO = 3
PAUSA_NOVO_BLOCO = 0.45   # um intervalo maior que isso entre palavras abre outro bloco
# A palavra flutuante sobe esta fração da moldura e some nas pontas do tempo dela.
SUBIDA_FLUTUANTE = 0.04
ENTRADA_FLUTUANTE = 0.15
SAIDA_FLUTUANTE = 0.20
LEGENDA_PADRAO = {
    "ativa": True, "preset": "destaque", "palavras_por_bloco": PALAVRAS_PADRAO, "posicao": "base",
    "vicios": None, "edicoes": {}, "apagadas": [], "mantidas": [],
}


def _fracao(valor) -> float | None:
    try:
        return min(max(float(valor), 0.0), 1.0) if valor is not None else None
    except (TypeError, ValueError):
        return None


def _limitado(valor, minimo: float, maximo: float, padrao: float) -> float:
    try:
        return min(max(float(valor), minimo), maximo) if valor is not None else padrao
    except (TypeError, ValueError):
        return padrao


def legenda_do_projeto(doc: dict) -> dict:
    """Estilo salvo no projeto, com as correções e os cortes da fala. Projeto antigo usa o padrão."""
    bruta = doc.get("legenda")
    if not isinstance(bruta, dict):
        bruta = {}
    try:
        quantidade = int(bruta.get("palavras_por_bloco") or PALAVRAS_PADRAO)
    except (TypeError, ValueError):
        quantidade = PALAVRAS_PADRAO
    vicios = bruta.get("vicios")
    return {
        "ativa": bool(bruta.get("ativa", True)),
        "preset": bruta.get("preset") if bruta.get("preset") in PRESETS else "destaque",
        "palavras_por_bloco": min(max(quantidade, 1), 8),
        "posicao": bruta.get("posicao") if bruta.get("posicao") in POSICOES else "base",
        # Arrastada na prévia: o centro do bloco (0 a 1). Sem ela, vale a posição pronta.
        "x": _fracao(bruta.get("x")),
        "y": _fracao(bruta.get("y")),
        "escala": _limitado(bruta.get("escala"), 0.6, 2.0, 1.0),
        "vicios": vicios if vicios in VICIOS else None,
        "edicoes": edicoes_validas(bruta.get("edicoes")),
        "apagadas": ids_validos(bruta.get("apagadas")),
        "mantidas": ids_validos(bruta.get("mantidas")),
    }


def palavras_da_transcricao(doc: dict | None) -> list[dict]:
    """Palavras com tempo, na ordem em que foram ditas. Sem texto ou sem tempo, ficam de fora."""
    if not doc:
        return []
    palavras = []
    for segmento in doc.get("segmentos") or []:
        for palavra in segmento.get("palavras") or []:
            texto = str(palavra.get("texto") or "").replace("\n", " ").strip()
            if not texto:
                continue
            try:
                inicio, fim = float(palavra["inicio"]), float(palavra["fim"])
            except (KeyError, TypeError, ValueError):
                continue
            if fim <= inicio:
                continue
            palavras.append({
                "id": str(palavra.get("id") or ""),
                "texto": texto,
                "inicio": inicio,
                "fim": fim,
                "segmento": str(segmento.get("id") or ""),
            })
    palavras.sort(key=lambda item: (item["inicio"], item["fim"]))
    return palavras


def _instante(segundos: float) -> float:
    """Centesimos de segundo: é a precisão do ASS, e a prévia usa a mesma grade."""
    return round(max(segundos, 0.0), 2)


def _no_video(palavras: list[dict], partes: list[dict], cortes: list[tuple[float, float]]) -> list[dict]:
    """
    Leva cada palavra do tempo da gravação para o tempo do vídeo final.
    Uma palavra some se o meio dela cai num silêncio cortado ou fora das partes.
    A mesma frase repetida na linha do tempo aparece de novo, no instante em que entra.
    """
    mapeadas, cursor = [], 0.0
    for parte in partes:
        for relativo_a, relativo_b in planejar_trechos(parte["inicio"], parte["fim"], cortes):
            absoluto_a, absoluto_b = parte["inicio"] + relativo_a, parte["inicio"] + relativo_b
            duracao = relativo_b - relativo_a
            dentro = []
            for palavra in palavras:
                meio = (palavra["inicio"] + palavra["fim"]) / 2
                if not (absoluto_a <= meio < absoluto_b):
                    continue
                inicio = cursor + max(palavra["inicio"] - absoluto_a, 0.0)
                fim = cursor + min(palavra["fim"] - absoluto_a, duracao)
                inicio, fim = _instante(inicio), _instante(fim)
                if fim - inicio < 0.02:
                    continue
                dentro.append({**palavra, "inicio": inicio, "fim": fim})
            dentro.sort(key=lambda item: (item["inicio"], item["fim"]))
            mapeadas.extend(dentro)
            cursor += duracao
    return mapeadas


def _tamanho_util(texto: str) -> int:
    return len(re.sub(r"[^\w]", "", texto, flags=re.UNICODE))


def _fechar_bloco(grupo: list[dict]) -> dict:
    """A palavra em destaque é a mais longa do bloco (com pelo menos 4 letras, se houver)."""
    indice = max(range(len(grupo)), key=lambda i: (_tamanho_util(grupo[i]["texto"]) >= 4,
                                                   _tamanho_util(grupo[i]["texto"]), i))
    return {
        "inicio": grupo[0]["inicio"],
        "fim": grupo[-1]["fim"],
        "palavras": [{**palavra, "destaque": i == indice} for i, palavra in enumerate(grupo)],
    }


def montar_blocos(palavras: list[dict], partes: list[dict], cortes: list[tuple[float, float]],
                  palavras_por_bloco: int = PALAVRAS_PADRAO) -> list[dict]:
    """Blocos de legenda no tempo do vídeo final. Uma pausa longa também abre um bloco novo."""
    quantidade = min(max(int(palavras_por_bloco or PALAVRAS_PADRAO), 1), 8)
    blocos, atual = [], []
    for palavra in _no_video(palavras, partes, cortes):
        pausa = atual and palavra["inicio"] - atual[-1]["fim"] > PAUSA_NOVO_BLOCO
        if atual and (pausa or len(atual) >= quantidade):
            blocos.append(_fechar_bloco(atual))
            atual = []
        atual.append(palavra)
    if atual:
        blocos.append(_fechar_bloco(atual))
    return blocos


def cor_ass(cor: str) -> str:
    """#RRGGBB → &H00BBGGRR&, a cor do ASS. Cor inválida vira o laranja da marca."""
    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", cor or ""):
        cor = "#FF8A00"
    vermelho, verde, azul = int(cor[1:3], 16), int(cor[3:5], 16), int(cor[5:7], 16)
    return f"&H00{azul:02X}{verde:02X}{vermelho:02X}&"


def tempo_ass(segundos: float) -> str:
    """Segundos → H:MM:SS.cs, o tempo de um evento ASS."""
    centesimos = int(round(max(segundos, 0.0) * 100))
    horas, resto = divmod(centesimos, 360_000)
    minutos, resto = divmod(resto, 6_000)
    segs, cs = divmod(resto, 100)
    return f"{horas}:{minutos:02d}:{segs:02d}.{cs:02d}"


def _escapar(texto: str) -> str:
    return texto.replace("\\", "").replace("{", "").replace("}", "").replace("\n", " ").replace("\r", "")


def _colorir(palavras: list[dict], indice_aceso: int | None, cor_igreja: str, preset: str, tamanho: int) -> str:
    pedacos = []
    for indice, palavra in enumerate(palavras):
        if indice:
            pedacos.append(" ")
        texto = _escapar(palavra["texto"])
        acesa = indice == indice_aceso if preset == "karaoke" else bool(palavra.get("destaque"))
        if preset == "clean" or not acesa:
            pedacos.append(texto)
        elif preset == "digno":
            pedacos.append(f"{{\\fnCaveat\\fs{int(tamanho * 1.35)}\\c{cor_ass(COR_DOURADA)}}}{texto}{{\\r}}")
        else:
            pedacos.append(f"{{\\c{cor_ass(cor_igreja)}}}{texto}{{\\r}}")
    return "".join(pedacos)


def _evento(inicio: float, fim: float, texto: str) -> str:
    if fim <= inicio:
        fim = inicio + 0.01
    return f"Dialogue: 0,{tempo_ass(inicio)},{tempo_ass(fim)},Legenda,,0,0,0,,{texto}"


def _evento_flutuante(palavra: dict, cor: str, tamanho: int, largura: int, altura: int,
                      posicao: str, x: float | None, y: float | None) -> str:
    """Uma palavra só, grande, subindo e sumindo. O brilho é o contorno borrado."""
    centro_x = int(round((0.5 if x is None else x) * largura))
    if y is None:
        centro_y = int(round((0.5 if posicao == "centro" else 0.78) * altura))
    else:
        centro_y = int(round(y * altura))
    subida = int(round(altura * SUBIDA_FLUTUANTE))
    duracao = max(float(palavra["fim"]) - float(palavra["inicio"]), 0.08)
    entra = int(round(min(duracao * ENTRADA_FLUTUANTE, 0.25) * 1000))
    sai = int(round(min(duracao * SAIDA_FLUTUANTE, 0.3) * 1000))
    estilo = (f"{{\\an5\\move({centro_x},{centro_y + subida},{centro_x},{centro_y - subida})"
              f"\\fad({entra},{sai})\\fs{int(tamanho * 1.8)}\\blur3\\bord2\\3c{cor_ass(cor)}}}")
    return _evento(palavra["inicio"], palavra["fim"], estilo + _escapar(palavra["texto"]))


def _eventos_do_bloco(bloco: dict, preset: str, cor_igreja: str, tamanho: int,
                      largura: int = 1080, altura: int = 1920, posicao: str = "base",
                      x: float | None = None, y: float | None = None) -> list[str]:
    palavras = bloco["palavras"]
    if preset == "flutuante":
        return [_evento_flutuante(palavra, cor_igreja, tamanho, largura, altura, posicao, x, y)
                for palavra in palavras]
    if preset != "karaoke":
        return [_evento(bloco["inicio"], bloco["fim"], _colorir(palavras, None, cor_igreja, preset, tamanho))]
    eventos = []
    for indice, palavra in enumerate(palavras):
        fim = palavras[indice + 1]["inicio"] if indice + 1 < len(palavras) else bloco["fim"]
        eventos.append(_evento(bloco["inicio"] if indice == 0 else palavra["inicio"], max(fim, palavra["fim"]),
                               _colorir(palavras, indice, cor_igreja, preset, tamanho)))
    return eventos


def gerar_ass(blocos: list[dict], preset: str, cor_destaque: str, largura: int, altura: int,
              posicao: str = "base", x: float | None = None, y: float | None = None, escala: float = 1.0) -> str:
    """
    Arquivo ASS queimado no vídeo. Clean é o bloco inteiro em branco; Karaokê acende só a
    palavra do momento; Destaque pinta a mais longa na cor da igreja; Digno escreve essa
    palavra em Caveat, dourada. Flutuante mostra uma palavra por vez, grande, subindo, com um brilho.
    As fontes são as da marca, em /app/brand/fontes.
    """
    if not blocos:
        return ""
    preset = preset if preset in PRESETS else "destaque"
    posicao = posicao if posicao in POSICOES else "base"
    tamanho = max(int(round(altura * 0.038 * min(max(escala, 0.6), 2.0))), 28)
    contorno = max(int(round(altura * 0.003)), 2)
    margem = int(round(altura * 0.12)) if posicao == "base" else 0
    alinhamento = 2 if posicao == "base" else 5
    estilo = (f"Style: Legenda,Montserrat,{tamanho},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,"
              f"-1,0,0,0,100,100,0,0,1,{contorno},0,{alinhamento},80,80,{margem},1")
    eventos = [evento for bloco in blocos
               for evento in _eventos_do_bloco(
                   bloco, preset, cor_destaque, tamanho, largura, altura, posicao, x, y)]
    if preset != "flutuante" and (x is not None or y is not None):
        # Arrastada na prévia: cada linha vai centrada no ponto escolhido (\an5\pos), como na prévia
        centro_x = int(round((0.5 if x is None else x) * largura))
        centro_y = int(round((0.5 if y is None else y) * altura))
        ponto = "{\\an5\\pos(" + f"{centro_x},{centro_y}" + ")}"
        eventos = [evento.replace(",,0,0,0,,", ",,0,0,0,," + ponto, 1) for evento in eventos]
    formato = ("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
               "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
               "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding")
    return "\n".join([
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {int(largura)}",
        f"PlayResY: {int(altura)}",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        formato,
        estilo,
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        *eventos,
        "",
    ])
