# -----------------------------------------------
# Tarefa "sugestao_cortes" — o HolySermon
#
# O Gemma, no Ollama, lê a transcrição em pedaços e devolve cortes.
# Só fica o corte cujo título é uma frase que o pregador disse.
# No fim o modelo sai da memória, para o Whisper caber na placa.
# -----------------------------------------------
import logging
from collections.abc import Callable

from bson import ObjectId

from core.modelos.job import ErroDefinitivo
from core.modelos.sermon import (
    ESQUEMA_CORTES,
    MODELO_LLM,
    janelas,
    palavras_do_documento,
    prompt_do_corte,
    texto_para_o_modelo,
    validar_cortes,
)
from core.utils.mongo import agora
from core.utils.ollama import ErroOllama, completar_json


def executar_sugestao(db, job: dict, reportar: Callable[[int, str], None]) -> dict:
    midia_id = ObjectId(job["entrada"]["midia_id"])
    organizacao_id = job["organizacao_id"]
    midia = db.midias.find_one({"_id": midia_id, "organizacao_id": organizacao_id})
    if midia is None:
        raise ErroDefinitivo("A gravação foi excluída antes da sugestão.")
    transcricao = db.transcricoes.find_one({"midia_id": midia_id, "organizacao_id": organizacao_id})
    palavras = palavras_do_documento(transcricao)
    if not palavras:
        raise ErroDefinitivo("A transcrição ainda não está pronta para sugerir cortes.")

    organizacao = db.organizacoes.find_one({"_id": organizacao_id}) or {}
    estrategia = ((organizacao.get("identidade") or {}).get("estrategia") or "")
    grupos = janelas(palavras)
    duracao = float(midia.get("duracao") or palavras[-1]["fim"])
    sistema = prompt_do_corte(estrategia)
    brutos = []
    for indice, grupo in enumerate(grupos):
        reportar(5 + int(80 * indice / max(len(grupos), 1)), "Lendo a pregação")
        ultimo = indice == len(grupos) - 1
        try:
            resposta = completar_json(sistema, texto_para_o_modelo(grupo), ESQUEMA_CORTES, descarregar=ultimo)
        except ErroOllama as erro:
            if brutos:
                logging.warning("[%s] [midia %s] Um pedaço da sugestão falhou: %s", organizacao_id, midia_id, erro)
                continue
            raise ErroDefinitivo("Não foi possível consultar o modelo de linguagem.") from erro
        brutos.extend(resposta.get("cortes") or [])

    cortes = validar_cortes(brutos, palavras, duracao)
    if not cortes:
        raise ErroDefinitivo("Nenhum corte ficou com uma frase que o pregador disse de fato.")
    documento = {
        "organizacao_id": organizacao_id,
        "midia_id": midia_id,
        "gerado_por_ia": True,
        "modelo": MODELO_LLM,
        "cortes": cortes,
        "criado_em": agora(),
    }
    db.sugestoes.replace_one({"midia_id": midia_id, "organizacao_id": organizacao_id}, documento, upsert=True)
    reportar(100, "Cortes sugeridos")
    logging.info("[%s] [midia %s] %s cortes sugeridos.", organizacao_id, midia_id, len(cortes))
    return {"midia_id": str(midia_id), "cortes": len(cortes)}
