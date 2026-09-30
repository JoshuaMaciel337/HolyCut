# -----------------------------------------------
# Tarefa "renderizacao" — gera o vídeo final de uma exportação
#
#   1. calcula os trechos mantidos: o trecho escolhido menos os silêncios
#   2. uma passada do FFmpeg a partir do arquivo original: seleciona os
#      trechos, enquadra, redimensiona e normaliza o áudio em -14 LUFS
#   3. capa do vídeo exportado
# A configuração vem da cópia guardada na exportação, não do projeto atual.
# -----------------------------------------------
import logging
import os
from collections.abc import Callable

import numpy as np
from bson import ObjectId

from core.modelos.job import ErroDefinitivo
from core.modelos.midia import ARQUIVO_NIVEIS, chave_arquivo
from core.modelos.projeto import (
    ARQUIVO_CAPA_EXPORTADA,
    ARQUIVO_VIDEO_EXPORTADO,
    PROPORCOES,
    STATUS_EXPORTACAO_ERRO,
    STATUS_EXPORTACAO_PRONTA,
    calcular_recorte,
    chave_exportacao,
)
from core.utils import storage
from core.utils.ffmpeg import executar_ffmpeg
from core.utils.mongo import agora
from core.utils.render import (
    FPS,
    duracao_dos_trechos,
    montar_filtro,
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


def cortes_de_silencio(midia: dict, intensidade: str | None) -> list[tuple[float, float]]:
    if not intensidade or ARQUIVO_NIVEIS not in midia.get("arquivos", []):
        return []
    caminho = storage.caminho_local(chave_arquivo(midia["organizacao_id"], midia["_id"], ARQUIVO_NIVEIS))
    niveis = np.fromfile(caminho, dtype=np.int8)
    return detectar_silencios(niveis, duracao=midia["duracao"], **INTENSIDADES[intensidade])


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
    filtro = montar_filtro(trechos, recorte, largura, altura, tem_audio=bool(midia.get("audio")),
                           normalizar=(config.get("audio") or {}).get("normalizar", True))

    def caminho(nome: str):
        return storage.caminho_local(chave_exportacao(organizacao_id, exportacao_id, nome))

    storage.salvar_bytes(chave_exportacao(organizacao_id, exportacao_id, ARQUIVO_FILTRO), filtro.encode())
    saida = caminho(ARQUIVO_VIDEO_EXPORTADO)
    argumentos = [
        "-ss", f"{inicio:.3f}", "-t", f"{fim - inicio:.3f}", "-i", str(original),
        *opcao_filtro_em_arquivo(str(caminho(ARQUIVO_FILTRO))),
        "-map", "[v]", *(["-map", "[a]"] if midia.get("audio") else []),
        "-c:v", "libx264", "-preset", PRESET_X264, "-crf", CRF_X264, "-profile:v", "high",
        "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(saida),
    ]
    executar_ffmpeg(argumentos, duracao, lambda f: reportar(5 + int(f * 88), "Renderizando o vídeo"))

    # 3. Capa
    reportar(95, "Gerando a capa")
    executar_ffmpeg(["-ss", f"{min(1.0, duracao / 2):.2f}", "-i", str(saida), "-frames:v", "1",
                     "-vf", f"scale={LARGURA_CAPA}:-2", "-q:v", "3", "-update", "1",
                     str(caminho(ARQUIVO_CAPA_EXPORTADA))])
    storage.remover(chave_exportacao(organizacao_id, exportacao_id, ARQUIVO_FILTRO))

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
