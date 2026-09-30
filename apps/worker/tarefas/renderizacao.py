# -----------------------------------------------
# Tarefa "renderizacao" — gera o vídeo final (ou a imagem) de uma exportação
#
#   1. calcula os trechos mantidos: o trecho escolhido menos os silêncios
#   2. uma passada do FFmpeg a partir do arquivo original: seleciona os
#      trechos, enquadra, aplica o fundo, sobrepõe logo e textos e normaliza
#      o áudio em -14 LUFS
#   3. capa do vídeo exportado
# No formato "imagem", sai um quadro só em JPG, com as camadas daquele instante.
# A configuração vem da cópia guardada na exportação, não do projeto atual.
# -----------------------------------------------
import logging
import os
from collections.abc import Callable

import numpy as np
from bson import ObjectId
from bson.errors import InvalidId
from PIL import Image

from core.modelos.identidade import chave_logo, identidade_padrao
from core.modelos.job import ErroDefinitivo
from core.modelos.midia import ARQUIVO_NIVEIS, chave_arquivo
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
from core.utils import storage
from core.utils.arte import camada_logo, camada_texto, para_png
from core.utils.ffmpeg import executar_ffmpeg
from core.utils.mongo import agora
from core.utils.render import (
    FPS,
    duracao_dos_trechos,
    instante_na_gravacao,
    montar_filtro,
    montar_filtro_imagem,
    opcao_filtro_em_arquivo,
    planejar_trechos,
)
from core.utils.silencios import INTENSIDADES, detectar_silencios

# -----------------------------------------------
# CONFIGURAÇÕES
# -----------------------------------------------
# "medium" dá o melhor equilíbrio entre qualidade e tempo na CPU. No Nitro,
# o NVENC da GPU entra depois como opção.
PRESET_X264 = os.environ.get("RENDER_PRESET", "medium")
CRF_X264 = os.environ.get("RENDER_CRF", "20")
ARQUIVO_FILTRO = "filtro.txt"
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


def cortes_de_silencio(midia: dict, intensidade: str | None) -> list[tuple[float, float]]:
    if not intensidade or ARQUIVO_NIVEIS not in midia.get("arquivos", []):
        return []
    caminho = storage.caminho_local(chave_arquivo(midia["organizacao_id"], midia["_id"], ARQUIVO_NIVEIS))
    niveis = np.fromfile(caminho, dtype=np.int8)
    return detectar_silencios(niveis, duracao=midia["duracao"], **INTENSIDADES[intensidade])


def exportar_imagem(db, exportacao: dict, config: dict, original, trechos, duracao: float, recorte: dict,
                    largura: int, altura: int, caminho, reportar: Callable[[int, str], None]) -> dict:
    """Um quadro do vídeo final em JPG, com o fundo e as camadas visíveis naquele instante."""
    organizacao_id, exportacao_id = exportacao["organizacao_id"], exportacao["_id"]
    posicao = min(float(exportacao.get("instante") or 0), max(duracao - 1 / FPS, 0.0))
    origem = config["trecho"]["inicio"] + instante_na_gravacao(trechos, posicao)

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

    # 1. Trechos mantidos
    reportar(2, "Calculando os cortes")
    inicio, fim = config["trecho"]["inicio"], config["trecho"]["fim"]
    cortes = cortes_de_silencio(midia, (config.get("silencios") or {}).get("intensidade"))
    trechos = planejar_trechos(inicio, fim, cortes)
    if not trechos:
        raise ErroDefinitivo("O trecho escolhido ficou vazio depois do corte de silêncios.")
    duracao = duracao_dos_trechos(trechos)
    logging.info(f"{rotulo} {len(trechos)} trechos, {duracao:.1f}s de {fim - inicio:.1f}s escolhidos.")

    # 2. Vídeo final
    largura, altura = PROPORCOES[config["proporcao"]]
    enquadramento = config["enquadramento"]
    recorte = calcular_recorte(midia["video"]["largura"], midia["video"]["altura"], config["proporcao"],
                               enquadramento["x"], enquadramento["y"], enquadramento["zoom"])

    def caminho(nome: str):
        return storage.caminho_local(chave_exportacao(organizacao_id, exportacao_id, nome))

    if exportacao.get("formato") == "imagem":
        return exportar_imagem(db, exportacao, config, original, trechos, duracao, recorte, largura, altura,
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
        musica = {"entrada": 1 + len(camadas), "volume": ajustes["volume"],
                  "abaixar_na_fala": ajustes["abaixar_na_fala"]}
    tem_saida_de_audio = bool(midia.get("audio")) or musica is not None

    filtro = montar_filtro(trechos, recorte, largura, altura, tem_audio=bool(midia.get("audio")),
                           normalizar=(config.get("audio") or {}).get("normalizar", True),
                           camadas=[(inicio_camada, fim_camada) for _, inicio_camada, fim_camada in camadas],
                           fundo=config.get("fundo"), cor=config.get("cor"), musica=musica)
    storage.salvar_bytes(chave_exportacao(organizacao_id, exportacao_id, ARQUIVO_FILTRO), filtro.encode())
    saida = caminho(ARQUIVO_VIDEO_EXPORTADO)
    argumentos = [
        "-ss", f"{inicio:.3f}", "-t", f"{fim - inicio:.3f}", "-i", str(original),
        *entradas_camadas,
        *entradas_musica,
        *opcao_filtro_em_arquivo(str(caminho(ARQUIVO_FILTRO))),
        "-map", "[v]", *(["-map", "[a]"] if tem_saida_de_audio else []),
        "-c:v", "libx264", "-preset", PRESET_X264, "-crf", CRF_X264, "-profile:v", "high",
        "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(saida),
    ]
    executar_ffmpeg(argumentos, duracao, lambda f: reportar(5 + int(f * 88), "Renderizando o vídeo"))

    # 3. Capa
    reportar(95, "Gerando a capa")
    executar_ffmpeg(["-ss", f"{min(1.0, duracao / 2):.2f}", "-i", str(saida), "-frames:v", "1",
                     "-vf", f"scale={LARGURA_CAPA}:-2", "-q:v", "3", "-update", "1",
                     str(caminho(ARQUIVO_CAPA_EXPORTADA))])
    for nome in [ARQUIVO_FILTRO, *(f"camada_{indice}.png" for indice in range(len(camadas)))]:
        storage.remover(chave_exportacao(organizacao_id, exportacao_id, nome))

    momento = agora()
    tamanho = saida.stat().st_size
    db.exportacoes.update_one({"_id": exportacao_id}, {"$set": {
        "status": STATUS_EXPORTACAO_PRONTA,
        "arquivos": [ARQUIVO_VIDEO_EXPORTADO, ARQUIVO_CAPA_EXPORTADA],
        "duracao": duracao,
        "tamanho": tamanho,
        "trechos": len(trechos),
        "erro": None,
        "concluido_em": momento,
        "atualizado_em": momento,
    }})
    reportar(100, "Pronto para postar")
    return {"exportacao_id": str(exportacao_id), "duracao": duracao, "tamanho": tamanho}
