# -----------------------------------------------
# HolyCut — planejamento da renderização com FFmpeg
#
# Os trechos mantidos saem de uma leitura só do arquivo, com os filtros
# select (vídeo) e aselect (áudio). Montar cada trecho separado estouraria a
# memória numa pregação com centenas de cortes.
#
# Para o áudio não sair de sincronia com o vídeo depois de muitos cortes:
#   - os cortes são alinhados aos quadros de 1/30 s
#   - o áudio vai para 48 kHz em blocos de 1600 amostras, ou seja, um bloco
#     de áudio por quadro de vídeo. Os dois filtros escolhem as mesmas fatias.
# Os cortes caem dentro do silêncio (há margem para a fala), então emendar
# o áudio ali não faz estalo.
# -----------------------------------------------
import re
import subprocess
from functools import lru_cache

from core.config import FFMPEG

FPS = 30
TAXA_AUDIO = 48000
AMOSTRAS_POR_QUADRO = TAXA_AUDIO // FPS
QUADROS_MINIMOS_POR_TRECHO = 2
LUFS_ALVO = -14            # padrão de volume das redes sociais
PICO_MAXIMO_DB = -1.5
FADE_ENTRADA = 0.05
FADE_SAIDA = 0.08


def alinhar(segundos: float) -> float:
    """Arredonda para o quadro de 1/30 s mais próximo."""
    return round(segundos * FPS) / FPS


def planejar_trechos(inicio: float, fim: float, cortes: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """
    Trechos que ficam no vídeo, entre inicio e fim, já sem os cortes.
    Tempos relativos ao inicio (é de onde o FFmpeg começa a ler) e alinhados aos quadros.
    """
    trechos, posicao = [], inicio
    for corte_inicio, corte_fim in sorted(cortes):
        if corte_fim <= inicio or corte_inicio >= fim:
            continue
        if corte_inicio > posicao:
            trechos.append((posicao, corte_inicio))
        posicao = max(posicao, corte_fim)
    if posicao < fim:
        trechos.append((posicao, fim))

    alinhados = []
    for a, b in trechos:
        a, b = alinhar(a - inicio), alinhar(b - inicio)
        if round((b - a) * FPS) >= QUADROS_MINIMOS_POR_TRECHO:
            alinhados.append((a, b))
    return alinhados


def duracao_dos_trechos(trechos: list[tuple[float, float]]) -> float:
    return round(sum(b - a for a, b in trechos), 3)


def expressao_selecao(trechos: list[tuple[float, float]]) -> str:
    """
    1 para os quadros dentro de algum trecho, 0 fora. Cada quadro começa num múltiplo de 1/30 s,
    então os limites ficam meio quadro antes: nenhum quadro cai exatamente na fronteira, e o
    arredondamento das casas decimais não tira nem acrescenta quadros nas emendas.
    """
    meio = 0.5 / FPS
    return "+".join(f"gte(t,{a - meio:.4f})*lt(t,{b - meio:.4f})" for a, b in trechos)


def montar_filtro(trechos: list[tuple[float, float]], recorte: dict, largura: int, altura: int,
                  tem_audio: bool, normalizar: bool = True) -> str:
    """Grafo de filtros completo, com as saídas [v] e [a]."""
    selecao = expressao_selecao(trechos)
    video = (
        f"[0:v]setpts=PTS-STARTPTS,fps={FPS},select='{selecao}',setpts=N/{FPS}/TB,"
        f"crop={recorte['largura']}:{recorte['altura']}:{recorte['x']}:{recorte['y']},"
        f"scale={largura}:{altura}:flags=lanczos,setsar=1,format=yuv420p[v]"
    )
    if not tem_audio:
        return video
    duracao = duracao_dos_trechos(trechos)
    audio = (
        f"[0:a]asetpts=PTS-STARTPTS,aresample={TAXA_AUDIO},asetnsamples=n={AMOSTRAS_POR_QUADRO}:p=0,"
        f"aselect='{selecao}',asetpts=N/SR/TB"
    )
    if normalizar:
        audio += f",loudnorm=I={LUFS_ALVO}:TP={PICO_MAXIMO_DB}:LRA=11,aresample={TAXA_AUDIO}"
    audio += (f",afade=t=in:d={FADE_ENTRADA},"
              f"afade=t=out:st={max(duracao - FADE_SAIDA, 0):.3f}:d={FADE_SAIDA}[a]")
    return f"{video};\n{audio}"


@lru_cache(maxsize=1)
def versao_principal_ffmpeg() -> int:
    saida = subprocess.run([FFMPEG, "-version"], capture_output=True, text=True, timeout=30).stdout
    encontrada = re.search(r"ffmpeg version n?(\d+)", saida)
    return int(encontrada.group(1)) if encontrada else 0


def opcao_filtro_em_arquivo(caminho: str) -> list[str]:
    """O FFmpeg 7 lê opções de arquivo com '-/opção'. O 6 só tinha -filter_complex_script."""
    if versao_principal_ffmpeg() >= 7:
        return ["-/filter_complex", caminho]
    return ["-filter_complex_script", caminho]
