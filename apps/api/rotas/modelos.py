# -----------------------------------------------
# HolyCut API — modelos de Story e Reel (os que vêm prontos e os da igreja)
# -----------------------------------------------
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencias import obter_db, usuario_atual
from api.esquemas import ModeloCriarEntrada, ModeloSaida
from core.modelos.modelos_story import IDS_PADRAO, MODELOS_PADRAO, modelo_padrao, montar_modelo_da_igreja

router = APIRouter(prefix="/api/modelos", tags=["modelos"])
LIMITE_MODELOS_DA_IGREJA = 50


def modelo_para_saida(modelo: dict, pronto: bool) -> ModeloSaida:
    return ModeloSaida.model_validate({**modelo, "id": str(modelo.get("id") or modelo["_id"]), "pronto": pronto})


async def buscar_modelo(db, modelo_id: str, usuario: dict) -> dict:
    """Um modelo pronto (pelo id) ou um da própria igreja (pelo _id)."""
    if modelo_id in IDS_PADRAO:
        return modelo_padrao(modelo_id)
    try:
        modelo = await db.modelos.find_one({"_id": ObjectId(modelo_id), "organizacao_id": usuario["organizacao_id"]})
    except InvalidId:
        modelo = None
    if modelo is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Modelo não encontrado.")
    return modelo


@router.get("", response_model=list[ModeloSaida])
async def listar_modelos(usuario=Depends(usuario_atual), db=Depends(obter_db)):
    """Primeiro os modelos da igreja, dos mais novos para os mais antigos; depois os que vêm prontos."""
    cursor = db.modelos.find({"organizacao_id": usuario["organizacao_id"]}).sort("criado_em", -1)
    da_igreja = [modelo_para_saida(m, pronto=False) async for m in cursor.limit(LIMITE_MODELOS_DA_IGREJA)]
    return da_igreja + [modelo_para_saida(m, pronto=True) for m in MODELOS_PADRAO]


@router.post("", response_model=ModeloSaida, status_code=status.HTTP_201_CREATED)
async def salvar_modelo(dados: ModeloCriarEntrada, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    """Guarda o visual de um projeto (fundo, logo e textos) como modelo da igreja."""
    try:
        projeto = await db.projetos.find_one({"_id": ObjectId(dados.projeto_id),
                                              "organizacao_id": usuario["organizacao_id"]})
    except InvalidId:
        projeto = None
    if projeto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Projeto não encontrado.")
    if await db.modelos.count_documents({"organizacao_id": usuario["organizacao_id"]}) >= LIMITE_MODELOS_DA_IGREJA:
        raise HTTPException(status.HTTP_409_CONFLICT, "A igreja já tem 50 modelos. Apague algum para salvar outro.")
    modelo = montar_modelo_da_igreja(usuario["organizacao_id"], projeto, " ".join(dados.nome.split()), usuario["_id"])
    modelo["_id"] = (await db.modelos.insert_one(modelo)).inserted_id
    return modelo_para_saida(modelo, pronto=False)


@router.delete("/{modelo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def apagar_modelo(modelo_id: str, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    if modelo_id in IDS_PADRAO:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Os modelos que vêm com o HolyCut não podem ser apagados.")
    modelo = await buscar_modelo(db, modelo_id, usuario)
    await db.modelos.delete_one({"_id": modelo["_id"]})
