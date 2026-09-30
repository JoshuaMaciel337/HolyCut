# -----------------------------------------------
# HolyCut — o culto no acervo da igreja
#
# Um culto é uma gravação com a sua ficha: data, pregador, série e
# descrição. O título é o próprio nome da gravação. As capas (pôster 2:3
# para as fileiras e banner 16:9 para o destaque) são desenhadas pelo
# worker a partir de um quadro do vídeo ou de uma imagem enviada.
# Funções puras: montam e calculam, sem acessar o banco.
# -----------------------------------------------
from datetime import date, datetime

from core.config import TZ

ARQUIVO_POSTER = "poster.jpg"
ARQUIVO_BANNER = "banner.jpg"
ARQUIVO_FUNDO_CAPA = "fundo_capa.jpg"   # imagem enviada pela igreja para a capa (uso interno)
TAMANHO_POSTER = (600, 900)
TAMANHO_BANNER = (1280, 720)
CAPA_IMAGEM_MAX_BYTES = 10 * 1024 * 1024

FICHA_PADRAO = {"data": None, "pregador": "", "serie": "", "descricao": ""}
LIMITE_FILEIRA = 20
MINIMO_CULTOS_POR_PREGADOR = 2


def data_do_envio(midia: dict) -> str:
    momento = midia.get("enviado_em") or midia.get("criado_em") or datetime.now(TZ)
    return momento.astimezone(TZ).date().isoformat()


def ficha_do_culto(midia: dict) -> dict:
    """A ficha salva, completada: sem data, vale o dia em que a gravação chegou."""
    ficha = {**FICHA_PADRAO, **(midia.get("ficha") or {})}
    ficha["data"] = ficha["data"] or data_do_envio(midia)
    return ficha


def formatar_data(data_iso: str) -> str:
    """'2026-08-15' → '15/08/2026'."""
    try:
        return date.fromisoformat(data_iso).strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return ""


def linha_de_informacao(ficha: dict) -> str:
    """O que vai embaixo do título na capa: 'Pr. Joelson Moura · 15/08/2026'."""
    return " · ".join(parte for parte in (ficha.get("pregador", "").strip(), formatar_data(ficha.get("data"))) if parte)


def montar_fileiras(cultos: list[dict], editados_recentemente: list[str]) -> list[dict]:
    """
    Fileiras do acervo, como num streaming. `cultos` já vem do mais novo para o mais antigo, cada um
    com id, serie, pregador e cortes (quantos vídeos prontos). `editados_recentemente` são ids de
    cultos com projeto mexido por último, do mais recente para o mais antigo.
    """
    fileiras = [{"id": "recentes", "titulo": "Últimos cultos", "ids": [c["id"] for c in cultos[:LIMITE_FILEIRA]]}]
    por_id = {c["id"]: c for c in cultos}
    editando = [i for i in dict.fromkeys(editados_recentemente) if i in por_id][:LIMITE_FILEIRA]
    if editando:
        fileiras.append({"id": "editando", "titulo": "Continuar editando", "ids": editando})
    com_cortes = [c["id"] for c in cultos if c.get("cortes")][:LIMITE_FILEIRA]
    if com_cortes:
        fileiras.append({"id": "cortes", "titulo": "Com cortes prontos", "ids": com_cortes})

    series: dict[str, list[str]] = {}
    pregadores: dict[str, list[str]] = {}
    for culto in cultos:
        if culto.get("serie"):
            series.setdefault(culto["serie"], []).append(culto["id"])
        if culto.get("pregador"):
            pregadores.setdefault(culto["pregador"], []).append(culto["id"])
    # As séries e os pregadores aparecem na ordem do culto mais recente de cada um
    for serie, ids in series.items():
        fileiras.append({"id": f"serie:{serie}", "titulo": f"Série: {serie}", "ids": ids[:LIMITE_FILEIRA]})
    for pregador, ids in pregadores.items():
        if len(ids) >= MINIMO_CULTOS_POR_PREGADOR:
            fileiras.append({"id": f"pregador:{pregador}", "titulo": pregador, "ids": ids[:LIMITE_FILEIRA]})
    return fileiras
