# -----------------------------------------------
# Tarefa "estudo_culto" — o HolyStudy
#
# O Gemma, no Ollama, lê a transcrição em pedaços e propõe as frases
# centrais, os temas, os personagens, as perguntas para o grupo e as
# aplicações. Tudo é conferido contra a fala (core/modelos/estudo.py):
# o que o pregador não disse é omitido. Com a pregação marcada, só ela
# é lida. No fim o modelo sai da memória.
# -----------------------------------------------
import logging
from collections.abc import Callable

from bson import ObjectId

from core.modelos.blocos import palavras_da_pregacao
from core.modelos.estudo import ESQUEMA_ESTUDO, estudo_vazio, montar_estudo, prompt_do_estudo
from core.modelos.job import ErroDefinitivo
from core.modelos.sermon import MODELO_LLM, janelas, palavras_do_documento, texto_para_o_modelo
from core.utils.mongo import agora
from core.utils.ollama import ErroOllama, completar_json


def executar_estudo(db, job: dict, reportar: Callable[[int, str], None]) -> dict:
    midia_id = ObjectId(job["entrada"]["midia_id"])
    organizacao_id = job["organizacao_id"]
    midia = db.midias.find_one({"_id": midia_id, "organizacao_id": organizacao_id}, {"pregacao": 1})
    if midia is None:
        raise ErroDefinitivo("A gravação foi excluída antes do estudo.")
    transcricao = db.transcricoes.find_one({"midia_id": midia_id, "organizacao_id": organizacao_id})
    palavras = palavras_da_pregacao(palavras_do_documento(transcricao), midia.get("pregacao"))
    if not palavras:
        raise ErroDefinitivo("A transcrição ainda não está pronta para o estudo.")
    comeco, final = palavras[0]["inicio"], palavras[-1]["fim"]
    versiculos = [item for item in (transcricao or {}).get("versiculos") or []
                  if comeco <= float(item.get("inicio") or 0) <= final]

    grupos = janelas(palavras)
    sistema = prompt_do_estudo()
    respostas = []
    for indice, grupo in enumerate(grupos):
        reportar(5 + int(85 * indice / max(len(grupos), 1)), "Lendo a pregação")
        try:
            respostas.append(completar_json(sistema, texto_para_o_modelo(grupo), ESQUEMA_ESTUDO,
                                            descarregar=indice == len(grupos) - 1))
        except ErroOllama as erro:
            if respostas:
                logging.warning("[%s] [midia %s] Um pedaço do estudo falhou: %s", organizacao_id, midia_id, erro)
                continue
            raise ErroDefinitivo("Não foi possível consultar o modelo de linguagem.") from erro

    estudo = montar_estudo(respostas, palavras, versiculos)
    if estudo_vazio(estudo):
        raise ErroDefinitivo("Nada do estudo ficou com frases que o pregador disse de fato.")
    documento = {"organizacao_id": organizacao_id, "midia_id": midia_id, "gerado_por_ia": True,
                 "modelo": MODELO_LLM, **estudo, "criado_em": agora()}
    db.estudos.replace_one({"midia_id": midia_id, "organizacao_id": organizacao_id}, documento, upsert=True)
    reportar(100, "Estudo pronto")
    logging.info("[%s] [midia %s] Estudo pronto: %s frases, %s perguntas.", organizacao_id, midia_id,
                 len(estudo["resumo"]), len(estudo["perguntas"]))
    return {"midia_id": str(midia_id), "frases": len(estudo["resumo"]), "perguntas": len(estudo["perguntas"])}
