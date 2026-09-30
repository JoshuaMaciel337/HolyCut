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
from core.utils.cores import filtro_ffmpeg

FPS = 30
TAXA_AUDIO = 48000
AMOSTRAS_POR_QUADRO = TAXA_AUDIO // FPS
QUADROS_MINIMOS_POR_TRECHO = 2
LUFS_ALVO = -14            # padrão de volume das redes sociais
PICO_MAXIMO_DB = -1.5
FADE_ENTRADA = 0.05
FADE_SAIDA = 0.08
# Música abaixando sob a fala (sidechaincompress): começa a agir com a voz acima de ~-34 dBFS
LIMIAR_FALA = 0.02
RAZAO_ABAIXAR = 10
ATAQUE_MS = 15
SOLTURA_MS = 400


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


def _enquadrar(recorte: dict, largura: int, altura: int, fundo: dict | None, cor: dict | None = None) -> str:
    """
    Recorta, redimensiona, aplica o filtro de cor e o fundo (desfoque e escurecimento), antes das
    camadas de arte. É a mesma ordem da prévia: filtro de cor, blur e preto translúcido por cima.
    """
    cadeia = (f"crop={recorte['largura']}:{recorte['altura']}:{recorte['x']}:{recorte['y']},"
              f"scale={largura}:{altura}:flags=lanczos,setsar=1")
    fundo, cor = fundo or {}, cor or {}
    desfoque, escurecer = float(fundo.get("desfoque") or 0), float(fundo.get("escurecer") or 0)
    filtro_cor = filtro_ffmpeg(cor.get("filtro") or "natural", float(cor.get("intensidade", 1.0)))
    if desfoque <= 0 and escurecer <= 0 and not filtro_cor:
        return cadeia
    # Em RGB, como o navegador faz na prévia. O drawbox escurecia no espaço YUV e tirava a
    # saturação: o amarelo virava bege (medido comparando com a prévia).
    cadeia += ",format=gbrp"
    if filtro_cor:
        cadeia += f",{filtro_cor}"
    if desfoque > 0:
        cadeia += f",gblur=sigma={desfoque:.1f}"
    if escurecer > 0:
        fator = 1 - escurecer
        cadeia += f",colorchannelmixer=rr={fator:.3f}:gg={fator:.3f}:bb={fator:.3f}"
    return cadeia


def _sobrepor(camadas: list[tuple[float, float]] | None, duracao: float | None, primeira_entrada: int = 1) -> str:
    """
    Encadeia um overlay por camada a partir de [base0] e termina em [v]. Sem duração: imagem parada.
    A primeira camada é a entrada primeira_entrada do FFmpeg, e as outras vêm em seguida.
    """
    if not camadas:
        return ",format=yuv420p[v]"
    grafo, anterior = "[base0]", "base0"
    for indice, (inicio, fim) in enumerate(camadas, start=1):
        saida = "v" if indice == len(camadas) else f"base{indice}"
        entrada = primeira_entrada + indice - 1
        quando = f":enable='between(t,{inicio:.3f},{min(fim, duracao):.3f})'" if duracao is not None else ""
        grafo += f";\n[{anterior}][{entrada}:v]overlay=0:0{quando}{',format=yuv420p' if saida == 'v' else ''}[{saida}]"
        anterior = saida
    return grafo


def _selecionar_video(entrada: int, trechos: list[tuple[float, float]]) -> str:
    return f"[{entrada}:v]setpts=PTS-STARTPTS,fps={FPS},select='{expressao_selecao(trechos)}',setpts=N/{FPS}/TB"


def _selecionar_audio(entrada: int, trechos: list[tuple[float, float]]) -> str:
    return (f"[{entrada}:a]asetpts=PTS-STARTPTS,aresample={TAXA_AUDIO},asetnsamples=n={AMOSTRAS_POR_QUADRO}:p=0,"
            f"aselect='{expressao_selecao(trechos)}',asetpts=N/SR/TB")


def montar_filtro(partes: list[list[tuple[float, float]]], recorte: dict, largura: int, altura: int,
                  tem_audio: bool, normalizar: bool = True,
                  camadas: list[tuple[float, float]] | None = None, fundo: dict | None = None,
                  cor: dict | None = None, musica: dict | None = None) -> str:
    """
    Grafo de filtros completo, com as saídas [v] e [a].
    partes: os trechos mantidos de cada parte do vídeo, na ordem final. A parte k é a entrada k do
    FFmpeg (a gravação aberta de novo, a partir do início daquela parte). Com mais de uma parte, elas
    se emendam com concat. Cada parte tem vídeo e áudio com a mesma duração, em quadros inteiros,
    então a sincronia não escorrega nas emendas.
    camadas: (início, fim) de cada imagem PNG sobreposta, no tempo do vídeo final. As camadas vêm
    logo depois das partes nas entradas do FFmpeg.
    musica: {"entrada": índice da faixa no FFmpeg, "volume": 0 a 1, "abaixar_na_fala": bool}.
    """
    duracao = round(sum(duracao_dos_trechos(trechos) for trechos in partes), 3)
    grafo = []
    if len(partes) == 1:
        fonte_video = f"{_selecionar_video(0, partes[0])},"
        voz = _selecionar_audio(0, partes[0])
    else:
        emenda = ""
        for indice, trechos in enumerate(partes):
            grafo.append(f"{_selecionar_video(indice, trechos)}[p{indice}v]")
            emenda += f"[p{indice}v]"
            if tem_audio:
                grafo.append(f"{_selecionar_audio(indice, trechos)}[p{indice}a]")
                emenda += f"[p{indice}a]"
        grafo.append(f"{emenda}concat=n={len(partes)}:v=1:a={1 if tem_audio else 0}[pv]{'[pa]' if tem_audio else ''}")
        fonte_video, voz = "[pv]", "[pa]anull"
    grafo.append(f"{fonte_video}{_enquadrar(recorte, largura, altura, fundo, cor)}"
                 f"{_sobrepor(camadas, duracao, primeira_entrada=len(partes))}")
    if not tem_audio and not musica:
        return ";\n".join(grafo)

    acabamento = f"loudnorm=I={LUFS_ALVO}:TP={PICO_MAXIMO_DB}:LRA=11,aresample={TAXA_AUDIO}," if normalizar else ""
    acabamento += (f"afade=t=in:d={FADE_ENTRADA},"
                   f"afade=t=out:st={max(duracao - FADE_SAIDA, 0):.3f}:d={FADE_SAIDA}[a]")
    if not musica:
        return ";\n".join([*grafo, f"{voz},{acabamento}"])

    faixa = (f"[{musica['entrada']}:a]aresample={TAXA_AUDIO},aformat=channel_layouts=stereo,"
             f"atrim=0:{duracao:.3f},asetpts=PTS-STARTPTS,volume={float(musica['volume']):.3f}")
    if not tem_audio:
        return ";\n".join([*grafo, f"{faixa},{acabamento}"])
    if musica.get("abaixar_na_fala", True):
        # A voz vira a "chave" do compressor: quando alguém fala, a música abaixa sozinha
        grafo += [f"{voz},aformat=channel_layouts=stereo,asplit=2[voz][chave]", f"{faixa}[musica0]",
                  f"[musica0][chave]sidechaincompress=threshold={LIMIAR_FALA}:ratio={RAZAO_ABAIXAR}"
                  f":attack={ATAQUE_MS}:release={SOLTURA_MS}[musica]"]
    else:
        grafo += [f"{voz},aformat=channel_layouts=stereo[voz]", f"{faixa}[musica]"]
    grafo.append(f"[voz][musica]amix=inputs=2:duration=first:normalize=0,{acabamento}")
    return ";\n".join(grafo)


def montar_filtro_imagem(recorte: dict, largura: int, altura: int, quantidade_camadas: int = 0,
                         fundo: dict | None = None, cor: dict | None = None) -> str:
    """Um quadro só (exportação em imagem): enquadra, aplica cor e fundo e sobrepõe as camadas."""
    camadas = [(0.0, 0.0)] * quantidade_camadas
    return f"[0:v]{_enquadrar(recorte, largura, altura, fundo, cor)}{_sobrepor(camadas, None)}"


def localizar_no_video(partes: list[list[tuple[float, float]]], posicao_final: float) -> tuple[int, float]:
    """(índice da parte, instante relativo ao início dela) de um ponto do vídeo final."""
    acumulado = 0.0
    for indice, trechos in enumerate(partes):
        duracao = duracao_dos_trechos(trechos)
        if posicao_final < acumulado + duracao or indice == len(partes) - 1:
            return indice, instante_na_gravacao(trechos, posicao_final - acumulado)
        acumulado += duracao
    return 0, 0.0


def instante_na_gravacao(trechos: list[tuple[float, float]], posicao_final: float) -> float:
    """
    Converte um ponto do vídeo final (já sem os cortes) no ponto correspondente da gravação,
    relativo ao início do trecho escolhido.
    """
    acumulado = 0.0
    for inicio, fim in trechos:
        if posicao_final < acumulado + (fim - inicio):
            return inicio + max(posicao_final - acumulado, 0.0)
        acumulado += fim - inicio
    return max(trechos[-1][1] - 1 / FPS, 0.0) if trechos else 0.0


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
