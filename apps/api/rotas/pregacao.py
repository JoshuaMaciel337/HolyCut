# -----------------------------------------------
# HolyCut API — a pregação do culto
#
# A pessoa marca onde a mensagem começa e termina (ou confere a marcação
# que os blocos do culto fizeram) e cria o vídeo 16:9 só da mensagem,
# sem louvor nem avisos. Funciona sem a IA: a marcação pode ser à mão.
# -----------------------------------------------
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencias import obter_db, usuario_atual
from api.esquemas import MidiaSaida, PregacaoEntrada, ProjetoSaida, projeto_para_saida
from api.rotas.identidade import carregar_identidade
from api.rotas.midias import buscar_midia, para_saida
from core.modelos.blocos import conferir_pregacao
from core.modelos.projeto import montar_projeto
from core.utils.mongo import agora

router = APIRouter(prefix="/api/midias", tags=["pregacao"])


@router.put("/{midia_id}/pregacao", response_model=MidiaSaida)
async def marcar_pregacao(midia_id: str, dados: PregacaoEntrada, db=Depends(obter_db),
                          usuario: dict = Depends(usuario_atual)):
    """A marcação da pessoa. Depois dela, a análise dos blocos não mexe mais na pregação."""
    midia = await buscar_midia(db, midia_id, usuario)
    if not midia.get("duracao"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Espere a gravação terminar de ser preparada.")
    try:
        trecho = conferir_pregacao(dados.inicio, dados.fim, midia["duracao"])
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from e
    pregacao = {**trecho, "origem": "pessoa"}
    await db.midias.update_one({"_id": midia["_id"]}, {"$set": {"pregacao": pregacao, "atualizado_em": agora()}})
    return (await para_saida(db, [{**midia, "pregacao": pregacao}]))[0]


@router.delete("/{midia_id}/pregacao", response_model=MidiaSaida)
async def desmarcar_pregacao(midia_id: str, db=Depends(obter_db), usuario: dict = Depends(usuario_atual)):
    midia = await buscar_midia(db, midia_id, usuario)
    await db.midias.update_one({"_id": midia["_id"]}, {"$unset": {"pregacao": ""}, "$set": {"atualizado_em": agora()}})
    return (await para_saida(db, [{chave: valor for chave, valor in midia.items() if chave != "pregacao"}]))[0]


@router.post("/{midia_id}/pregacao/projeto", response_model=ProjetoSaida, status_code=status.HTTP_201_CREATED)
async def criar_video_da_mensagem(midia_id: str, db=Depends(obter_db), usuario: dict = Depends(usuario_atual)):
    """Um projeto 16:9 com a pregação inteira, que abre no editor para exportar."""
    midia = await buscar_midia(db, midia_id, usuario)
    if not midia.get("video"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            "Para o vídeo da mensagem, a gravação precisa ter vídeo.")
    pregacao = midia.get("pregacao")
    if not pregacao:
        raise HTTPException(status.HTTP_409_CONFLICT, "Marque onde a pregação começa e termina primeiro.")
    projeto = montar_projeto(usuario["organizacao_id"], midia, usuario["_id"], tipo="mensagem",
                             inicio=pregacao["inicio"], fim=pregacao["fim"],
                             identidade=await carregar_identidade(db, usuario["organizacao_id"]))
    projeto["_id"] = (await db.projetos.insert_one(projeto)).inserted_id
    return projeto_para_saida(projeto)
