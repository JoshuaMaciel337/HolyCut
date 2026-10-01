# -----------------------------------------------
# HolyCut — pedaços da limpeza de áudio
#
# O DeepFilterNet roda em trechos de 30 s, com meio segundo de sobreposição,
# para uma pregação inteira não ir de uma vez para a memória da GPU.
# -----------------------------------------------

TAMANHO_SEGUNDOS = 30.0
SOBREPOSICAO_SEGUNDOS = 0.5
# A faixa limpa tem de cobrir a gravação. Acima disso o job falha, em vez de
# entregar um áudio mais curto que o vídeo.
TOLERANCIA_DURACAO_SEGUNDOS = 0.5


def fatias(total_amostras: int, taxa: int, tamanho_segundos: float = TAMANHO_SEGUNDOS,
           sobreposicao_segundos: float = SOBREPOSICAO_SEGUNDOS) -> list[tuple[int, int]]:
    """Intervalos [início, fim) em amostras. Os vizinhos se sobrepõem meio segundo."""
    if total_amostras <= 0 or taxa <= 0:
        return []
    tamanho = max(int(taxa * tamanho_segundos), 1)
    if total_amostras <= tamanho:
        return [(0, total_amostras)]
    passo = max(tamanho - int(taxa * sobreposicao_segundos), 1)
    resultado = []
    inicio = 0
    while inicio < total_amostras:
        fim = min(inicio + tamanho, total_amostras)
        resultado.append((inicio, fim))
        if fim >= total_amostras:
            break
        inicio += passo
    return resultado
