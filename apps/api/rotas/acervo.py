# -----------------------------------------------
# HolyCut API — o acervo da igreja (a biblioteca dos cultos)
#
#   GET /api/acervo   os cultos prontos, o destaque e as fileiras, como num
#                     streaming: últimos, continuar editando, com cortes
#                     prontos, por série e por pregador
#
# Cada igreja vê só os próprios cultos. A busca do site filtra a lista
# `cultos` que vem aqui; com a IA, ela passa a entender versículo e tema.
# -----------------------------------------------
from fastapi import APIRouter, Depends

from api.dependencias import obter_db, usuario_atual
from api.esquemas import AcervoSaida, CultoResumoSaida
from api.rotas.midias import pedir_capas
from core.modelos.culto import ARQUIVO_POSTER, ficha_do_culto, montar_fileiras
from core.modelos.midia import STATUS_ENVIANDO, STATUS_PROCESSANDO, STATUS_PRONTA
from core.modelos.projeto import STATUS_EXPORTACAO_PRONTA

router = APIRouter(prefix="/api/acervo", tags=["acervo"])
LIMITE_CULTOS = 500
PROJETOS_RECENTES = 40
# Quantas capas antigas (de antes do acervo) redesenhar por visita, para não encher a fila
LIMITE_CAPAS_PENDENTES = 8


def culto_para_resumo(midia: dict, cortes: int, em_edicao: int) -> CultoResumoSaida:
    ficha = ficha_do_culto(midia)
    return CultoResumoSaida(
        id=str(midia["_id"]), titulo=midia["nome"], data=ficha["data"], pregador=ficha["pregador"],
        serie=ficha["serie"], descricao=ficha["descricao"], duracao=midia.get("duracao"),
        video=bool(midia.get("video")), capa_versao=(midia.get("capa") or {}).get("versao"),
        cortes=cortes, em_edicao=em_edicao,
    )


async def contar_por_midia(colecao, filtro: dict) -> dict:
    cursor = await colecao.aggregate([{"$match": filtro}, {"$group": {"_id": "$midia_id", "total": {"$sum": 1}}}])
    return {item["_id"]: item["total"] async for item in cursor}


@router.get("", response_model=AcervoSaida)
async def ver_acervo(usuario=Depends(usuario_atual), db=Depends(obter_db)):
    organizacao_id = usuario["organizacao_id"]
    midias = [m async for m in db.midias.find({"organizacao_id": organizacao_id, "status": STATUS_PRONTA})
              .sort("criado_em", -1).limit(LIMITE_CULTOS)]
    sem_capa = [m for m in midias if ARQUIVO_POSTER not in m.get("arquivos", [])][:LIMITE_CAPAS_PENDENTES]
    for midia in sem_capa:
        await pedir_capas(db, midia, usuario)
    cortes = await contar_por_midia(db.exportacoes, {"organizacao_id": organizacao_id,
                                                     "status": STATUS_EXPORTACAO_PRONTA})
    em_edicao = await contar_por_midia(db.projetos, {"organizacao_id": organizacao_id})
    resumos = [culto_para_resumo(m, cortes.get(m["_id"], 0), em_edicao.get(m["_id"], 0)) for m in midias]
    # Do culto mais recente para o mais antigo, pela data do culto (e pela chegada, no empate)
    resumos.sort(key=lambda c: c.data, reverse=True)

    editados = db.projetos.find({"organizacao_id": organizacao_id}, {"midia_id": 1}) \
        .sort("atualizado_em", -1).limit(PROJETOS_RECENTES)
    editados_recentemente = [str(p["midia_id"]) async for p in editados]
    fileiras = montar_fileiras([c.model_dump() for c in resumos], editados_recentemente)
    preparando = await db.midias.count_documents({"organizacao_id": organizacao_id,
                                                  "status": {"$in": [STATUS_ENVIANDO, STATUS_PROCESSANDO]}})
    return AcervoSaida(
        cultos=resumos,
        destaque=resumos[0].id if resumos else None,
        fileiras=fileiras,
        series=sorted({c.serie for c in resumos if c.serie}),
        pregadores=sorted({c.pregador for c in resumos if c.pregador}),
        preparando=preparando,
    )
