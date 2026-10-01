# -----------------------------------------------
# HolyCut — transcrição da gravação
# Funções puras: montam o documento, o SRT e o TXT, sem acessar o banco.
# O português do pregador fica como foi falado. Nada aqui "corrige" a fala.
# -----------------------------------------------
from datetime import datetime

from core.config import TZ

MODELO = "large-v3-turbo"
IDIOMA = "pt"

# Nomes como são ditos no púlpito. Ajudam o Whisper a não trocar "João" por uma palavra parecida.
LIVROS = (
    "Gênesis", "Êxodo", "Levítico", "Números", "Deuteronômio", "Josué", "Juízes", "Rute",
    "Samuel", "Reis", "Crônicas", "Esdras", "Neemias", "Ester", "Jó", "Salmos", "Provérbios",
    "Eclesiastes", "Cantares", "Isaías", "Jeremias", "Lamentações", "Ezequiel", "Daniel",
    "Oseias", "Joel", "Amós", "Obadias", "Jonas", "Miqueias", "Naum", "Habacuque", "Sofonias",
    "Ageu", "Zacarias", "Malaquias", "Mateus", "Marcos", "Lucas", "João", "Atos", "Romanos",
    "Coríntios", "Gálatas", "Efésios", "Filipenses", "Colossenses", "Tessalonicenses",
    "Timóteo", "Tito", "Filemom", "Hebreus", "Tiago", "Pedro", "Judas", "Apocalipse",
)


def deve_transcrever(modo_ia: str, tem_audio: bool) -> bool:
    """A transcrição só entra na fila no servidor com IA de verdade e quando há áudio."""
    return modo_ia == "real" and tem_audio


def _limpar(texto: str) -> str:
    return " ".join((texto or "").split())


def dicas_da_igreja(nome_igreja: str = "", pregador: str = "") -> dict:
    """
    Contexto para o Whisper: o nome da igreja, o do pregador e os livros bíblicos.
    O initial_prompt situa o áudio. As hotwords puxam esses nomes na hora de ouvir.
    """
    nomes = []
    for valor in (nome_igreja, pregador):
        limpo = _limpar(valor)[:80]
        if limpo and limpo not in nomes:
            nomes.append(limpo)
    frase = "Culto em português do Brasil. A fala fica como foi dita, sem corrigir o português."
    if nomes:
        frase += " " + ". ".join(nomes) + "."
    return {
        "initial_prompt": frase[:500],
        "hotwords": ", ".join([*nomes, *LIVROS])[:1000],
    }


def _tempo(valor) -> float | None:
    if valor is None:
        return None
    return round(float(valor), 3)


def montar_segmentos(brutos: list[dict]) -> list[dict]:
    """Segmentos do Whisper, com id estável em cada palavra, na ordem em que foram ouvidas."""
    segmentos = []
    numero_palavra = 0
    for bruto in brutos:
        palavras = []
        for palavra in bruto.get("palavras") or []:
            escrito = _limpar(palavra.get("texto") or "")
            inicio, fim = _tempo(palavra.get("inicio")), _tempo(palavra.get("fim"))
            if not escrito or inicio is None or fim is None:
                continue
            numero_palavra += 1
            item = {
                "id": f"w{numero_palavra:06d}",
                "texto": escrito,
                "inicio": inicio,
                "fim": max(fim, inicio),
            }
            if palavra.get("confianca") is not None:
                item["confianca"] = round(min(1.0, max(0.0, float(palavra["confianca"]))), 3)
            palavras.append(item)

        texto = _limpar(bruto.get("texto") or "") or " ".join(palavra["texto"] for palavra in palavras)
        if not texto:
            continue
        inicio = _tempo(bruto.get("inicio"))
        fim = _tempo(bruto.get("fim"))
        if inicio is None:
            inicio = palavras[0]["inicio"] if palavras else 0.0
        if fim is None:
            fim = palavras[-1]["fim"] if palavras else inicio
        segmentos.append({
            "id": f"s{len(segmentos) + 1:04d}",
            "inicio": inicio,
            "fim": max(fim, inicio),
            "texto": texto,
            "palavras": palavras,
        })
    return segmentos


def montar_transcricao(organizacao_id, midia_id, segmentos: list[dict], duracao: float | None,
                       momento: datetime | None = None, idioma: str = IDIOMA, modelo: str = MODELO) -> dict:
    """Documento da coleção transcricoes. A transcrição original; edições futuras ficam por cima."""
    momento = momento or datetime.now(TZ)
    palavras = sum(len(segmento["palavras"]) for segmento in segmentos)
    return {
        "organizacao_id": organizacao_id,
        "midia_id": midia_id,
        "idioma": idioma,
        "modelo": modelo,
        "gerado_por_ia": True,
        "segmentos": segmentos,
        "contagem_palavras": palavras,
        "duracao": duracao,
        "criado_em": momento,
        "atualizado_em": momento,
    }


def tempo_srt(segundos: float) -> str:
    """Segundos → 00:01:02,345, o formato do arquivo SRT."""
    total_ms = int(round(max(0.0, segundos) * 1000))
    horas, resto = divmod(total_ms, 3_600_000)
    minutos, resto = divmod(resto, 60_000)
    segs, milissegundos = divmod(resto, 1000)
    return f"{horas:02d}:{minutos:02d}:{segs:02d},{milissegundos:03d}"


def exportar_srt(segmentos: list[dict]) -> str:
    blocos = []
    for segmento in segmentos:
        if not _limpar(segmento.get("texto") or ""):
            continue
        blocos.append(
            f"{len(blocos) + 1}\n{tempo_srt(segmento['inicio'])} --> {tempo_srt(segmento['fim'])}\n{segmento['texto']}"
        )
    return "\n\n".join(blocos) + ("\n" if blocos else "")


def exportar_txt(segmentos: list[dict]) -> str:
    """Uma linha por trecho, com o instante, para achar a fala na gravação."""
    linhas = []
    for segmento in segmentos:
        texto = _limpar(segmento.get("texto") or "")
        if not texto:
            continue
        linhas.append(f"{tempo_srt(segmento['inicio']).replace(',', '.')} {texto}")
    return "\n".join(linhas) + ("\n" if linhas else "")
