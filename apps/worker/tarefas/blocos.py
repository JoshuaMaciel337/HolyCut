# -----------------------------------------------
# Tarefa "blocos_culto" — louvor, oração, avisos, oferta, ceia e pregação
#
# As fronteiras saem dos níveis do áudio e das palavras da transcrição
# (core/modelos/blocos.py). O Gemma só dá nome a cada parte falada, numa
# lista fechada; se o Ollama não responder, ficam os nomes pelas
# palavras-chave. A pregação principal vai para a gravação, a não ser
# que a pessoa já tenha marcado a dela.
# -----------------------------------------------
import logging
from collections.abc import Callable

from bson import ObjectId

from core.modelos.blocos import (
    ESQUEMA_BLOCO,
    TIPOS_FALADOS,
    janelas_do_audio,
    montar_blocos,
    nome_pelas_palavras,
    palavras_entre,
    partes_da_fala,
    pregacao_principal,
    prompt_do_bloco,
    texto_do_bloco,
    trechos_do_culto,
)
from core.modelos.job import ErroDefinitivo
from core.modelos.midia import ARQUIVO_NIVEIS, NIVEIS_POR_SEGUNDO, chave_arquivo
from core.modelos.sermon import MODELO_LLM, palavras_do_documento
from core.utils import storage
from core.utils.mongo import agora
from core.utils.ollama import ErroOllama, completar_json


def _audio(organizacao_id, midia_id) -> list[dict]:
    caminho = storage.caminho_local(chave_arquivo(organizacao_id, midia_id, ARQUIVO_NIVEIS))
    if not caminho.is_file():
        return []
    import numpy as np
    return janelas_do_audio(np.fromfile(caminho, dtype=np.int8), NIVEIS_POR_SEGUNDO)


def _nomes(partes: list[tuple[float, float]], palavras: list[dict], duracao: float, reportar) -> tuple[list[str], bool]:
    """Os nomes pelas palavras-chave, trocados pelo do modelo quando ele responde dentro da lista."""
    nomes = [nome_pelas_palavras(palavras_entre(palavras, inicio, fim), fim - inicio) for inicio, fim in partes]
    usou_modelo = False
    for indice, (inicio, fim) in enumerate(partes):
        reportar(30 + int(60 * indice / max(len(partes), 1)), "Dando nome aos blocos")
        try:
            resposta = completar_json(prompt_do_bloco(), texto_do_bloco(palavras, inicio, fim, duracao),
                                      ESQUEMA_BLOCO, descarregar=indice == len(partes) - 1)
        except ErroOllama as erro:
            # Sem o modelo, cada parte esperaria o tempo limite inteiro. Ficam as palavras-chave.
            logging.warning("Os nomes dos blocos ficam pelas palavras-chave: %s", erro)
            break
        if resposta.get("tipo") in TIPOS_FALADOS:
            nomes[indice] = resposta["tipo"]
            usou_modelo = True
    return nomes, usou_modelo


def executar_blocos(db, job: dict, reportar: Callable[[int, str], None]) -> dict:
    midia_id = ObjectId(job["entrada"]["midia_id"])
    organizacao_id = job["organizacao_id"]
    midia = db.midias.find_one({"_id": midia_id, "organizacao_id": organizacao_id})
    if midia is None:
        raise ErroDefinitivo("A gravação foi excluída antes dos blocos.")
    transcricao = db.transcricoes.find_one({"midia_id": midia_id, "organizacao_id": organizacao_id})
    palavras = palavras_do_documento(transcricao)
    if not palavras:
        raise ErroDefinitivo("A transcrição ainda não está pronta para os blocos.")

    duracao = float(midia.get("duracao") or palavras[-1]["fim"])
    reportar(10, "Separando música e fala")
    trechos = trechos_do_culto(duracao, _audio(organizacao_id, midia_id), palavras)
    partes = [parte for inicio, fim, rotulo in trechos if rotulo == "fala"
              for parte in partes_da_fala(inicio, fim, palavras)]
    nomes, usou_modelo = _nomes(partes, palavras, duracao, reportar)
    blocos = montar_blocos(trechos, partes, nomes, palavras)
    pregacao = pregacao_principal(blocos, palavras)

    db.blocos.replace_one(
        {"midia_id": midia_id, "organizacao_id": organizacao_id},
        {"organizacao_id": organizacao_id, "midia_id": midia_id, "gerado_por_ia": True,
         "modelo": MODELO_LLM if usou_modelo else None, "blocos": blocos, "pregacao": pregacao, "criado_em": agora()},
        upsert=True,
    )
    if pregacao:
        # A marcação da pessoa vale mais que a da IA e nunca é trocada
        db.midias.update_one(
            {"_id": midia_id, "pregacao.origem": {"$ne": "pessoa"}},
            {"$set": {"pregacao": {**pregacao, "origem": "ia"}, "atualizado_em": agora()}},
        )
    reportar(100, "Blocos prontos")
    logging.info("[%s] [midia %s] %s blocos; pregação: %s.", organizacao_id, midia_id, len(blocos),
                 f"{pregacao['inicio']:.0f}s a {pregacao['fim']:.0f}s" if pregacao else "não encontrada")
    return {"midia_id": str(midia_id), "blocos": len(blocos), "pregacao": bool(pregacao)}
