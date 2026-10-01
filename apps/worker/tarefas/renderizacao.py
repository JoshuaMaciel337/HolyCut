# -----------------------------------------------
# Tarefa "renderizacao" — gera o vídeo final (ou a imagem) de uma exportação
#
#   1. calcula os trechos mantidos de cada parte: a parte menos os silêncios
#   2. uma passada do FFmpeg a partir do arquivo original, aberto uma vez por
#      parte: seleciona os trechos, emenda as partes na ordem escolhida,
#      enquadra, aplica cor e fundo, sobrepõe logo e textos, queima a legenda,
#      mistura a música e normaliza o áudio em -14 LUFS
#   3. capa do vídeo exportado
# No formato "imagem", sai um quadro só em JPG, com as camadas daquele instante.
# A configuração vem da cópia guardada na exportação, não do projeto atual.
# -----------------------------------------------
import logging
import os
from collections.abc import Callable

from bson import ObjectId
from bson.errors import InvalidId
from PIL import Image

from core.modelos.fala import palavras_visiveis
from core.modelos.identidade import chave_logo, identidade_padrao
from core.modelos.job import ErroDefinitivo
from core.modelos.legenda import gerar_ass, legenda_do_projeto, montar_blocos, palavras_da_transcricao
from core.modelos.midia import ARQUIVO_AUDIO_LIMPO, chave_arquivo
from core.modelos.musica import ARQUIVO_MUSICA, MUSICA_DO_PROJETO_PADRAO, chave_musica
from core.modelos.musica import STATUS_PRONTA as STATUS_MUSICA_PRONTA
from core.modelos.projeto import (
    ARQUIVO_CAPA_EXPORTADA,
    ARQUIVO_IMAGEM_EXPORTADA,
    ARQUIVO_VIDEO_EXPORTADO,
    PROPORCOES,
    STATUS_EXPORTACAO_ERRO,
    STATUS_EXPORTACAO_PRONTA,
    calcular_recorte,
    chave_exportacao,
)
from core.modelos.rosto import comandos_de_recorte, instante_no_final
from core.utils import storage
from core.utils.arte import camada_logo, camada_texto, para_png
from core.utils.ffmpeg import ErroFFmpeg, executar_ffmpeg
from core.utils.mongo import agora
from core.utils.render import (
    FPS,
    duracao_dos_trechos,
    localizar_no_video,
    montar_filtro,
    montar_filtro_imagem,
    opcao_filtro_em_arquivo,
)
from core.utils.silencios import cortes_do_projeto, partes_com_trechos

# -----------------------------------------------
# CONFIGURAÇÕES
# -----------------------------------------------
# "medium" dá o melhor equilíbrio entre qualidade e tempo na CPU. No Nitro,
# o NVENC da GPU entra depois como opção.
PRESET_X264 = os.environ.get("RENDER_PRESET", "medium")
CRF_X264 = os.environ.get("RENDER_CRF", "20")
ARQUIVO_FILTRO = "filtro.txt"
ARQUIVO_LEGENDA = "legenda.ass"
LARGURA_CAPA = 540


# -----------------------------------------------
# FUNÇÕES AUXILIARES
# -----------------------------------------------
def marcar_exportacao_com_erro(db, job: dict, mensagem: str):
    exportacao_id = (job.get("entrada") or {}).get("exportacao_id")
    if exportacao_id:
        db.exportacoes.update_one({"_id": ObjectId(exportacao_id)}, {"$set": {
            "status": STATUS_EXPORTACAO_ERRO, "erro": mensagem, "atualizado_em": agora(),
        }})


def desenhar_camadas(db, organizacao_id, config: dict, largura: int, altura: int,
                     duracao: float) -> list[tuple[Image.Image, float, float]]:
    """(imagem, início, fim) do logo e de cada texto, no tempo do vídeo final."""
    organizacao = db.organizacoes.find_one({"_id": organizacao_id}, {"nome": 1, "identidade": 1}) or {}
    identidade = {**identidade_padrao(organizacao.get("nome", "")), **(organizacao.get("identidade") or {})}
    camadas = []
    marca = config.get("marca") or {}
    if marca.get("logo"):
        logo = storage.caminho_local(chave_logo(organizacao_id))
        if logo.is_file():
            camadas.append((camada_logo(largura, altura, logo.read_bytes(), marca.get("posicao", "topo_direita"),
                                        marca.get("tamanho", 0.16), marca.get("opacidade", 0.9)), 0.0, duracao))
        else:
            logging.warning(f"[{organizacao_id}] O projeto pede o logo, mas a igreja não tem logo enviado.")
    for texto in config.get("textos") or []:
        inicio_texto = min(float(texto.get("inicio") or 0), duracao)
        fim_texto = min(float(texto.get("fim") or duracao), duracao)
        if not (texto.get("texto") or "").strip() or fim_texto <= inicio_texto:
            continue
        imagem = camada_texto(largura, altura, texto["texto"], texto.get("estilo", "destaque"),
                              texto.get("posicao", "base"), identidade["cor_destaque"], texto.get("referencia", ""),
                              float(texto.get("tamanho") or 1.0))
        camadas.append((imagem, inicio_texto, fim_texto))
    return camadas


def musica_do_projeto(db, organizacao_id, escolha: dict | None):
    """(arquivo, ajustes) da faixa escolhida, ou None se não houver música ou ela não estiver pronta."""
    if not escolha or not escolha.get("id"):
        return None
    try:
        musica = db.musicas.find_one({"_id": ObjectId(escolha["id"]), "organizacao_id": organizacao_id})
    except InvalidId:
        musica = None
    caminho = (storage.caminho_local(chave_musica(organizacao_id, musica["_id"], ARQUIVO_MUSICA))
               if musica and musica.get("status") == STATUS_MUSICA_PRONTA else None)
    if caminho is None or not caminho.is_file():
        logging.warning(f"[{organizacao_id}] A música {escolha['id']} não está pronta. O vídeo sai sem ela.")
        return None
    ajustes = {**MUSICA_DO_PROJETO_PADRAO, **escolha}
    ajustes["inicio"] = min(max(float(ajustes["inicio"] or 0), 0.0), max(float(musica.get("duracao") or 0) - 1, 0.0))
    return caminho, ajustes


def preparar_legenda(db, organizacao_id, exportacao_id, midia: dict, config: dict, partes: list,
                     cortes: list, largura: int, altura: int) -> str | None:
    """
    Grava o ASS da exportação e devolve o caminho local, ou None se a legenda está
    desligada ou a gravação ainda não tem palavras. O texto é o da transcrição, sem correção.
    """
    legenda = legenda_do_projeto(config)
    if not legenda["ativa"]:
        return None
    transcricao = db.transcricoes.find_one({"midia_id": midia["_id"], "organizacao_id": organizacao_id})
    palavras = palavras_da_transcricao(transcricao)
    if not palavras:
        return None
    blocos = montar_blocos(palavras_visiveis(palavras, legenda), [parte for parte, _ in partes], cortes,
                           legenda["palavras_por_bloco"])
    if not blocos:
        return None
    organizacao = db.organizacoes.find_one({"_id": organizacao_id}, {"nome": 1, "identidade": 1}) or {}
    identidade = {**identidade_padrao(organizacao.get("nome", "")), **(organizacao.get("identidade") or {})}
    texto = gerar_ass(blocos, legenda["preset"], identidade["cor_destaque"], largura, altura, legenda["posicao"])
    chave = chave_exportacao(organizacao_id, exportacao_id, ARQUIVO_LEGENDA)
    storage.salvar_bytes(chave, texto.encode("utf-8"))
    logging.info(f"[{organizacao_id}] [exportacao {exportacao_id}] Legenda {legenda['preset']}: {len(blocos)} blocos.")
    return str(storage.caminho_local(chave))


def exportar_imagem(db, exportacao: dict, config: dict, original, partes: list, duracao: float, recorte: dict,
                    largura: int, altura: int, caminho, reportar: Callable[[int, str], None]) -> dict:
    """Um quadro do vídeo final em JPG, com o fundo e as camadas visíveis naquele instante."""
    organizacao_id, exportacao_id = exportacao["organizacao_id"], exportacao["_id"]
    posicao = min(float(exportacao.get("instante") or 0), max(duracao - 1 / FPS, 0.0))
    indice, relativo = localizar_no_video([trechos for _, trechos in partes], posicao)
    origem = partes[indice][0]["inicio"] + relativo

    reportar(10, "Desenhando o logo e os textos")
    visiveis = [imagem for imagem, inicio, fim in desenhar_camadas(db, organizacao_id, config, largura, altura, duracao)
                if inicio <= posicao < fim]
    entradas = []
    for indice, imagem in enumerate(visiveis):
        nome = f"camada_{indice}.png"
        storage.salvar_bytes(chave_exportacao(organizacao_id, exportacao_id, nome), para_png(imagem))
        entradas += ["-i", str(caminho(nome))]
    filtro = montar_filtro_imagem(recorte, largura, altura, len(visiveis), config.get("fundo"), config.get("cor"))
    storage.salvar_bytes(chave_exportacao(organizacao_id, exportacao_id, ARQUIVO_FILTRO), filtro.encode())

    reportar(40, "Gerando a imagem")
    saida = caminho(ARQUIVO_IMAGEM_EXPORTADA)
    executar_ffmpeg(["-ss", f"{origem:.3f}", "-i", str(original), *entradas,
                     *opcao_filtro_em_arquivo(str(caminho(ARQUIVO_FILTRO))),
                     "-map", "[v]", "-frames:v", "1", "-q:v", "2", "-update", "1", str(saida)])
    with Image.open(saida) as imagem:
        capa = imagem.copy()
    capa.thumbnail((LARGURA_CAPA, LARGURA_CAPA * 4))
    capa.save(caminho(ARQUIVO_CAPA_EXPORTADA), quality=85)
    for nome in [ARQUIVO_FILTRO, *(f"camada_{indice}.png" for indice in range(len(visiveis)))]:
        storage.remover(chave_exportacao(organizacao_id, exportacao_id, nome))

    momento = agora()
    tamanho = saida.stat().st_size
    db.exportacoes.update_one({"_id": exportacao_id}, {"$set": {
        "status": STATUS_EXPORTACAO_PRONTA,
        "arquivos": [ARQUIVO_IMAGEM_EXPORTADA, ARQUIVO_CAPA_EXPORTADA],
        "duracao": None,
        "instante": posicao,
        "tamanho": tamanho,
        "erro": None,
        "concluido_em": momento,
        "atualizado_em": momento,
    }})
    reportar(100, "Pronta para postar")
    return {"exportacao_id": str(exportacao_id), "formato": "imagem", "tamanho": tamanho}


# -----------------------------------------------
# FUNÇÃO PRINCIPAL
# -----------------------------------------------
def extrair_capa(video, destino, instante: float):
    """Um quadro do vídeo final, em JPG de 540 px de largura. Serve à exportação e à troca de capa."""
    executar_ffmpeg(["-ss", f"{instante:.2f}", "-i", str(video), "-frames:v", "1",
                     "-vf", f"scale={LARGURA_CAPA}:-2", "-q:v", "3", "-update", "1", str(destino)])

def executar_renderizacao(db, job: dict, reportar: Callable[[int, str], None]) -> dict:
    exportacao_id = ObjectId(job["entrada"]["exportacao_id"])
    exportacao = db.exportacoes.find_one({"_id": exportacao_id})
    if exportacao is None:
        raise ErroDefinitivo("A exportação foi excluída antes de ficar pronta.")
    midia = db.midias.find_one({"_id": exportacao["midia_id"]})
    if midia is None:
        raise ErroDefinitivo("A gravação deste projeto foi excluída.")
    if not midia.get("video"):
        raise ErroDefinitivo("Esta gravação não tem vídeo para exportar.")
    original = storage.caminho_local(chave_arquivo(midia["organizacao_id"], midia["_id"], midia["original"]))
    if not original.is_file():
        raise ErroDefinitivo("O arquivo original da gravação não foi encontrado no servidor.")

    organizacao_id = exportacao["organizacao_id"]
    rotulo = f"[{organizacao_id}] [exportacao {exportacao_id}]"
    config = exportacao["configuracao"]

    # 1. Trechos mantidos de cada parte (silêncio, vício ou palavra apagada saem do vídeo)
    reportar(2, "Calculando os cortes")
    transcricao = db.transcricoes.find_one({"midia_id": midia["_id"], "organizacao_id": organizacao_id})
    cortes = cortes_do_projeto(midia, config, palavras_da_transcricao(transcricao))
    partes = partes_com_trechos(config, cortes)
    if not partes:
        raise ErroDefinitivo("O vídeo ficou vazio depois dos cortes.")
    grupos = [trechos for _, trechos in partes]
    duracao = round(sum(duracao_dos_trechos(trechos) for trechos in grupos), 3)
    escolhido = sum(parte["fim"] - parte["inicio"] for parte, _ in partes)
    total_trechos = sum(len(trechos) for trechos in grupos)
    logging.info(f"{rotulo} {len(partes)} partes, {total_trechos} trechos, "
                 f"{duracao:.1f}s de {escolhido:.1f}s escolhidos.")

    # 2. Vídeo final
    largura, altura = PROPORCOES[config["proporcao"]]
    enquadramento = config["enquadramento"]
    recorte = calcular_recorte(midia["video"]["largura"], midia["video"]["altura"], config["proporcao"],
                               enquadramento["x"], enquadramento["y"], enquadramento["zoom"])
    mapeados_rosto = []
    if enquadramento.get("seguir_rosto"):
        trilha = db.rostos.find_one({"midia_id": midia["_id"], "organizacao_id": organizacao_id}) or {}
        partes_abs = [(parte["inicio"], parte["fim"]) for parte, _ in partes]
        for quadro in trilha.get("quadros") or []:
            saida_t = instante_no_final(partes_abs, grupos, quadro["t"])
            if saida_t is None:
                continue
            mapeados_rosto.append((saida_t, calcular_recorte(
                midia["video"]["largura"], midia["video"]["altura"], config["proporcao"],
                quadro["x"], quadro["y"], quadro.get("zoom") or 1.0,
            )))
        if not mapeados_rosto:
            raise ErroDefinitivo("O acompanhamento do rosto ainda não ficou pronto. Espere e exporte de novo.")
        mapeados_rosto.sort()
        recorte = mapeados_rosto[0][1]

    def caminho(nome: str):
        return storage.caminho_local(chave_exportacao(organizacao_id, exportacao_id, nome))

    if exportacao.get("formato") == "imagem":
        if mapeados_rosto:
            posicao = float(exportacao.get("instante") or 0)
            vigentes = [item for item in mapeados_rosto if item[0] <= posicao]
            recorte = (vigentes[-1] if vigentes else mapeados_rosto[0])[1]
        return exportar_imagem(db, exportacao, config, original, partes, duracao, recorte, largura, altura,
                               caminho, reportar)

    # Logo e textos: uma imagem PNG por camada, sobreposta só no intervalo dela
    reportar(4, "Desenhando o logo e os textos")
    camadas = desenhar_camadas(db, organizacao_id, config, largura, altura, duracao)
    entradas_camadas = []
    for indice, (imagem, _inicio, _fim) in enumerate(camadas):
        nome = f"camada_{indice}.png"
        storage.salvar_bytes(chave_exportacao(organizacao_id, exportacao_id, nome), para_png(imagem))
        entradas_camadas += ["-loop", "1", "-framerate", str(FPS), "-t", f"{duracao:.3f}", "-i", str(caminho(nome))]

    # Música da biblioteca, em loop a partir do ponto escolhido, depois das camadas nas entradas do FFmpeg
    faixa = musica_do_projeto(db, organizacao_id, config.get("musica"))
    entradas_musica, musica = [], None
    if faixa:
        caminho_faixa, ajustes = faixa
        entradas_musica = ["-stream_loop", "-1", "-ss", f"{ajustes['inicio']:.3f}", "-i", str(caminho_faixa)]
        musica = {"entrada": len(partes) + len(camadas), "volume": ajustes["volume"],
                  "abaixar_na_fala": ajustes["abaixar_na_fala"]}
    # A faixa limpa entra depois da música. As camadas continuam no índice len(partes).
    entradas_limpo, audio_limpo = [], None
    if (config.get("audio") or {}).get("limpeza"):
        if ARQUIVO_AUDIO_LIMPO not in (midia.get("arquivos") or []):
            raise ErroDefinitivo("A limpeza do áudio ainda não ficou pronta. Espere ela terminar e exporte de novo.")
        caminho_wav = storage.caminho_local(chave_arquivo(organizacao_id, midia["_id"], ARQUIVO_AUDIO_LIMPO))
        if not caminho_wav.is_file():
            raise ErroDefinitivo("O áudio limpo não foi encontrado no servidor.")
        entradas_limpo = ["-i", str(caminho_wav)]
        indice_wav = len(partes) + len(camadas) + (1 if musica else 0)
        audio_limpo = (indice_wav, [(parte["inicio"], parte["fim"]) for parte, _ in partes])
    tem_voz = bool(midia.get("audio")) or audio_limpo is not None
    tem_saida_de_audio = tem_voz or musica is not None

    reportar(4, "Preparando a legenda")
    caminho_legenda = preparar_legenda(db, organizacao_id, exportacao_id, midia, config, partes, cortes,
                                       largura, altura)
    comandos_rosto = None
    if mapeados_rosto:
        storage.salvar_bytes(chave_exportacao(organizacao_id, exportacao_id, "rosto.txt"),
                             comandos_de_recorte(mapeados_rosto).encode())
        comandos_rosto = str(caminho("rosto.txt"))
    filtro = montar_filtro(grupos, recorte, largura, altura, tem_audio=tem_voz,
                           normalizar=(config.get("audio") or {}).get("normalizar", True),
                           camadas=[(inicio_camada, fim_camada) for _, inicio_camada, fim_camada in camadas],
                           fundo=config.get("fundo"), cor=config.get("cor"), musica=musica, legenda=caminho_legenda,
                           audio_limpo=audio_limpo, comandos_rosto=comandos_rosto)
    storage.salvar_bytes(chave_exportacao(organizacao_id, exportacao_id, ARQUIVO_FILTRO), filtro.encode())
    saida = caminho(ARQUIVO_VIDEO_EXPORTADO)
    # A gravação entra uma vez por parte, já a partir do início dela
    entradas_partes = []
    for parte, _ in partes:
        entradas_partes += ["-ss", f"{parte['inicio']:.3f}", "-t", f"{parte['fim'] - parte['inicio']:.3f}",
                            "-i", str(original)]
    argumentos = [
        *entradas_partes,
        *entradas_camadas,
        *entradas_musica,
        *entradas_limpo,
        *opcao_filtro_em_arquivo(str(caminho(ARQUIVO_FILTRO))),
        "-map", "[v]", *(["-map", "[a]"] if tem_saida_de_audio else []),
        *(["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", CRF_X264, "-profile:v", "high"]
          if exportacao.get("encoder") == "nvenc"
          else ["-c:v", "libx264", "-preset", PRESET_X264, "-crf", CRF_X264, "-profile:v", "high"]),
        "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(saida),
    ]
    try:
        executar_ffmpeg(argumentos, duracao, lambda f: reportar(5 + int(f * 88), "Renderizando o vídeo"))
    except ErroFFmpeg as erro:
        if exportacao.get("encoder") == "nvenc":
            raise ErroDefinitivo(
                "A placa de vídeo não conseguiu codificar este vídeo. Exporte pelo processador."
            ) from erro
        raise

    # 3. Capa
    reportar(95, "Gerando a capa")
    extrair_capa(saida, caminho(ARQUIVO_CAPA_EXPORTADA), min(1.0, duracao / 2))
    temporarios = [ARQUIVO_FILTRO, *(f"camada_{indice}.png" for indice in range(len(camadas)))]
    if caminho_legenda:
        temporarios.append(ARQUIVO_LEGENDA)
    if comandos_rosto:
        temporarios.append("rosto.txt")
    for nome in temporarios:
        storage.remover(chave_exportacao(organizacao_id, exportacao_id, nome))

    momento = agora()
    tamanho = saida.stat().st_size
    db.exportacoes.update_one({"_id": exportacao_id}, {"$set": {
        "status": STATUS_EXPORTACAO_PRONTA,
        "arquivos": [ARQUIVO_VIDEO_EXPORTADO, ARQUIVO_CAPA_EXPORTADA],
        "duracao": duracao,
        "tamanho": tamanho,
        "trechos": total_trechos,
        "partes": len(partes),
        "erro": None,
        "concluido_em": momento,
        "atualizado_em": momento,
    }})
    reportar(100, "Pronto para postar")
    return {"exportacao_id": str(exportacao_id), "duracao": duracao, "tamanho": tamanho}
