# -----------------------------------------------
# HolyCut — pacote para o DaVinci Resolve e o Adobe Premiere Pro
#
# O XML (formato do Final Cut Pro 7, "xmeml" versão 5, que os dois
# importam) leva os cortes do projeto: cada trecho que fica no vídeo vira
# um clipe na linha do tempo, apontando para a gravação original. Como o
# arquivo é a gravação inteira, toda ponta tem folga: dá para esticar
# qualquer corte no editor. O SRT leva a legenda no tempo do vídeo final.
# Não vão no XML: o enquadramento, os textos, a marca, a música, a cor e
# a legenda gravada no vídeo. A linha do tempo vem no tamanho da gravação.
# Funções puras: montam texto, sem acessar o banco.
# -----------------------------------------------
import xml.etree.ElementTree as ET
from urllib.parse import quote

from core.modelos.transcricao import tempo_srt

PALAVRAS_POR_LEGENDA_SRT = 8
TAXA_AUDIO_PADRAO = 48000


def taxa_de_quadros(fps: float | None) -> tuple[int, bool, float]:
    """(timebase, ntsc, quadros por segundo de verdade). 29,97 é 30 com ntsc; sem fps, 30."""
    if not fps or fps <= 0:
        return 30, False, 30.0
    base = max(round(fps), 1)
    ntsc = abs(fps - base * 1000 / 1001) < abs(fps - base)
    return base, ntsc, base * 1000 / 1001 if ntsc else float(base)


def clipes_da_linha_do_tempo(partes: list[tuple[dict, list[tuple[float, float]]]], quadros: float) -> list[dict]:
    """
    Um clipe por trecho que fica, em quadros: onde entra na linha do tempo (start e end) e de onde
    sai na gravação (in e out). A posição vem do tempo acumulado, então centenas de cortes não
    escorregam; o clipe dura na gravação o mesmo que na linha do tempo.
    """
    clipes, cursor = [], 0.0
    for parte, trechos in partes:
        for relativo_a, relativo_b in trechos:
            start = round(cursor * quadros)
            cursor += relativo_b - relativo_a
            end = round(cursor * quadros)
            if end <= start:
                continue
            entrada = round((parte["inicio"] + relativo_a) * quadros)
            clipes.append({"start": start, "end": end, "in": entrada, "out": entrada + end - start})
    return clipes


def _no(pai: ET.Element, tag: str, texto: str | int | None = None, **atributos) -> ET.Element:
    elemento = ET.SubElement(pai, tag, atributos)
    if texto is not None:
        elemento.text = str(texto)
    return elemento


def _taxa(pai: ET.Element, base: int, ntsc: bool) -> None:
    taxa = _no(pai, "rate")
    _no(taxa, "timebase", base)
    _no(taxa, "ntsc", "TRUE" if ntsc else "FALSE")


def _timecode(pai: ET.Element, base: int, ntsc: bool) -> None:
    timecode = _no(pai, "timecode")
    _taxa(timecode, base, ntsc)
    _no(timecode, "string", "00:00:00:00")
    _no(timecode, "frame", 0)
    _no(timecode, "displayformat", "NDF")


def gerar_xml(nome: str, arquivo: str, duracao: float, video: dict, audio: dict | None, clipes: list[dict]) -> str:
    """A linha do tempo com os cortes, para importar no DaVinci (Importar > Timeline) ou no Premiere (Importar)."""
    base, ntsc, quadros = taxa_de_quadros(video.get("fps"))
    total_fonte = max(round(duracao * quadros), max((clipe["out"] for clipe in clipes), default=0))
    canais = min(int((audio or {}).get("canais") or 0), 2)
    taxa_audio = int((audio or {}).get("taxa") or TAXA_AUDIO_PADRAO)

    raiz = ET.Element("xmeml", version="5")
    sequencia = _no(raiz, "sequence", id="sequencia-1")
    _no(sequencia, "name", nome)
    _no(sequencia, "duration", clipes[-1]["end"] if clipes else 0)
    _taxa(sequencia, base, ntsc)
    _timecode(sequencia, base, ntsc)
    midia = _no(sequencia, "media")

    def caracteristicas(pai: ET.Element) -> None:
        amostra = _no(pai, "samplecharacteristics")
        _taxa(amostra, base, ntsc)
        _no(amostra, "width", video["largura"])
        _no(amostra, "height", video["altura"])
        _no(amostra, "pixelaspectratio", "square")

    def arquivo_completo(pai: ET.Element) -> None:
        """A gravação é descrita uma vez, no primeiro clipe. Os outros só apontam para ela."""
        elemento = _no(pai, "file", id="arquivo-1")
        _no(elemento, "name", arquivo)
        _no(elemento, "pathurl", "file://localhost/" + quote(arquivo))
        _taxa(elemento, base, ntsc)
        _no(elemento, "duration", total_fonte)
        _timecode(elemento, base, ntsc)
        midia_arquivo = _no(elemento, "media")
        caracteristicas(_no(midia_arquivo, "video"))
        if canais:
            som = _no(midia_arquivo, "audio")
            amostra = _no(som, "samplecharacteristics")
            _no(amostra, "depth", 16)
            _no(amostra, "samplerate", taxa_audio)
            _no(som, "channelcount", canais)

    def ligar(clipitem: ET.Element, indice: int) -> None:
        """Vídeo e áudio do mesmo trecho andam juntos no editor."""
        itens = [(f"video-{indice}", "video", 1)] + [(f"audio-{faixa}-{indice}", "audio", faixa)
                                                     for faixa in range(1, canais + 1)]
        for referencia, tipo, faixa in itens:
            link = _no(clipitem, "link")
            _no(link, "linkclipref", referencia)
            _no(link, "mediatype", tipo)
            _no(link, "trackindex", faixa)
            _no(link, "clipindex", indice)

    def clipe(faixa_xml: ET.Element, identificador: str, indice: int, dados: dict, faixa_audio: int | None) -> None:
        item = _no(faixa_xml, "clipitem", id=identificador)
        _no(item, "name", arquivo)
        _no(item, "enabled", "TRUE")
        _no(item, "duration", total_fonte)
        _taxa(item, base, ntsc)
        for campo in ("start", "end", "in", "out"):
            _no(item, campo, dados[campo])
        if identificador == "video-1":
            arquivo_completo(item)
        else:
            _no(item, "file", id="arquivo-1")
        if faixa_audio is not None:
            origem = _no(item, "sourcetrack")
            _no(origem, "mediatype", "audio")
            _no(origem, "trackindex", faixa_audio)
        ligar(item, indice)

    imagem = _no(midia, "video")
    caracteristicas(_no(imagem, "format"))
    faixa_video = _no(imagem, "track")
    for indice, dados in enumerate(clipes, start=1):
        clipe(faixa_video, f"video-{indice}", indice, dados, None)

    if canais:
        som = _no(midia, "audio")
        _no(som, "numOutputChannels", 2)
        formato = _no(_no(som, "format"), "samplecharacteristics")
        _no(formato, "depth", 16)
        _no(formato, "samplerate", taxa_audio)
        for faixa in range(1, canais + 1):
            faixa_audio = _no(som, "track")
            for indice, dados in enumerate(clipes, start=1):
                clipe(faixa_audio, f"audio-{faixa}-{indice}", indice, dados, faixa)

    ET.indent(raiz, space="  ")
    corpo = ET.tostring(raiz, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n{corpo}\n'


def gerar_srt(blocos: list[dict]) -> str:
    """Os blocos da legenda (já no tempo do vídeo final) num SRT."""
    itens = []
    for bloco in blocos:
        texto = " ".join(palavra["texto"] for palavra in bloco["palavras"]).strip()
        if texto:
            itens.append(f"{len(itens) + 1}\n{tempo_srt(bloco['inicio'])} --> {tempo_srt(bloco['fim'])}\n{texto}")
    return "\n\n".join(itens) + ("\n" if itens else "")


def leia_me(nome: str, arquivo: str, base: str, tem_legenda: bool, proporcao: str) -> str:
    """O passo a passo que vai junto no .zip."""
    linhas = [
        f"Pacote de edição: {nome}",
        "",
        "O que vem aqui:",
        f"- {base}.xml: os cortes do HolyCut numa linha do tempo, para o DaVinci Resolve e o Adobe Premiere Pro.",
    ]
    if tem_legenda:
        linhas.append(f"- {base}.srt: a legenda, no tempo do vídeo final.")
    linhas += [
        "",
        "Como abrir:",
        f"1. Deixe a gravação original ({arquivo}) numa pasta do computador. É o arquivo que saiu do OBS,",
        "   ou baixe pelo HolyCut, na aba Gravação do culto.",
        "2. DaVinci Resolve: Arquivo > Importar > Timeline (File > Import > Timeline) e escolha o .xml.",
        "   Quando ele pedir, aponte a pasta da gravação.",
        "   Premiere Pro: Arquivo > Importar e escolha o .xml. Se a mídia aparecer offline, clique com o",
        "   botão direito no clipe > Vincular mídia e escolha a gravação.",
    ]
    if tem_legenda:
        linhas.append("3. A legenda: importe o .srt e arraste para a linha do tempo.")
    linhas += [
        "",
        "Folga: cada clipe aponta para a gravação inteira, então dá para esticar qualquer corte para os dois lados.",
        "",
        f"Não vão no XML: o enquadramento (o projeto é {proporcao}; a linha do tempo vem no tamanho da gravação),",
        "os textos, a marca, a música, a cor e a legenda gravada no vídeo.",
        "",
        "Gravação em .mkv que o Premiere não abre: no OBS, Arquivo > Remux gravações gera um .mp4 sem perder",
        "qualidade. Depois, vincule a mídia ao .mp4.",
    ]
    return "\n".join(linhas) + "\n"
