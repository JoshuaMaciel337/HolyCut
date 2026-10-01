# -----------------------------------------------
# HolyCut — detecção de silêncios
#
# Trabalha sobre os níveis em dB a cada 10 ms gerados na ingestão
# (niveis.bin). Um trecho é silêncio quando todos os seus 10 ms ficam
# abaixo do limiar por pelo menos a duração mínima. É o mesmo critério do
# silencedetect do FFmpeg, só que já calculado, então mudar a intensidade
# custa milissegundos.
#
# O corte deixa uma margem antes e depois da fala, para o vídeo não
# ficar "picotado".
# -----------------------------------------------
import numpy as np

from core.modelos.midia import ARQUIVO_NIVEIS, NIVEIS_POR_SEGUNDO, chave_arquivo
from core.utils import storage

MARGEM_PADRAO = 0.12   # segundos preservados de cada lado da fala
CORTE_MINIMO = 0.1     # silêncio que sobra menor que isso não vale o corte

INTENSIDADES = {
    "leve": {"limiar_db": -40, "duracao_minima": 1.0},
    "media": {"limiar_db": -35, "duracao_minima": 0.6},
    "forte": {"limiar_db": -30, "duracao_minima": 0.35},
}


def detectar_silencios(niveis_db: np.ndarray, limiar_db: float, duracao_minima: float,
                       margem: float = MARGEM_PADRAO, duracao: float | None = None,
                       por_segundo: int = NIVEIS_POR_SEGUNDO) -> list[tuple[float, float]]:
    """Trechos a cortar, em segundos, já descontada a margem ao redor da fala."""
    total = len(niveis_db)
    if total == 0:
        return []
    duracao = duracao if duracao is not None else total / por_segundo
    silencioso = (niveis_db.astype(np.int16) < limiar_db).astype(np.int8)
    bordas = np.diff(np.concatenate(([0], silencioso, [0])))
    inicios, fins = np.flatnonzero(bordas == 1), np.flatnonzero(bordas == -1)

    trechos = []
    for inicio, fim in zip(inicios.tolist(), fins.tolist(), strict=True):
        if (fim - inicio) / por_segundo < duracao_minima:
            continue
        # No começo e no fim do arquivo não há fala do outro lado para proteger
        corte_inicio = 0.0 if inicio == 0 else inicio / por_segundo + margem
        corte_fim = duracao if fim == total else min(fim / por_segundo - margem, duracao)
        if corte_fim - corte_inicio >= CORTE_MINIMO:
            trechos.append((round(corte_inicio, 2), round(corte_fim, 2)))
    return trechos


def trechos_mantidos(duracao: float, cortes: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """O complemento dos cortes: o que fica no vídeo."""
    mantidos, posicao = [], 0.0
    for inicio, fim in sorted(cortes):
        if inicio > posicao:
            mantidos.append((round(posicao, 2), round(inicio, 2)))
        posicao = max(posicao, fim)
    if posicao < duracao:
        mantidos.append((round(posicao, 2), round(duracao, 2)))
    return mantidos


def tempo_cortado(cortes: list[tuple[float, float]]) -> float:
    return round(sum(fim - inicio for inicio, fim in cortes), 2)


def cortes_da_gravacao(midia: dict, intensidade: str | None) -> list[tuple[float, float]]:
    """Os cortes que o render tira, lidos do niveis.bin da ingestão. Sem análise, não corta nada."""
    if not intensidade or intensidade not in INTENSIDADES:
        return []
    if ARQUIVO_NIVEIS not in (midia.get("arquivos") or []):
        return []
    caminho = storage.caminho_local(chave_arquivo(midia["organizacao_id"], midia["_id"], ARQUIVO_NIVEIS))
    if not caminho.is_file():
        return []
    niveis = np.fromfile(caminho, dtype=np.int8)
    return detectar_silencios(niveis, duracao=float(midia["duracao"]), **INTENSIDADES[intensidade])
