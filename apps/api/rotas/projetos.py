# -----------------------------------------------
# HolyCut API — projetos (Reels montados a partir de uma gravação)
# -----------------------------------------------
import io
import logging
import zipfile

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pymongo import ReturnDocument
from starlette.concurrency import run_in_threadpool

from api.dependencias import obter_db, usuario_atual
from api.esquemas import (
    ExportacaoSaida,
    ExportarEntrada,
    LegendaPreviaSaida,
    ProjetoAtualizarEntrada,
    ProjetoCriarEntrada,
    ProjetoSaida,
    exportacao_para_saida,
    projeto_para_saida,
)
from api.rotas.exportacoes import apagar_exportacoes, nome_de_arquivo
from api.rotas.identidade import carregar_identidade
from api.rotas.modelos import buscar_modelo
from api.rotas.musicas import buscar_musica
from core.config import LOGO_MAX_BYTES
from core.modelos.banco import pasta_apoios
from core.modelos.fala import cortes_da_fala, fundir_cortes, palavras_para_edicao, palavras_visiveis
from core.modelos.figura import ICONES, MAX_FIGURAS, NOMES_ICONES, chave_figura, nova_figura, pasta_figuras
from core.modelos.job import montar_job
from core.modelos.legenda import COR_DOURADA, legenda_do_projeto, montar_blocos, palavras_da_transcricao
from core.modelos.midia import ARQUIVO_AUDIO_LIMPO, STATUS_PRONTA
from core.modelos.pacote_edicao import (
    PALAVRAS_POR_LEGENDA_SRT,
    clipes_da_linha_do_tempo,
    gerar_srt,
    gerar_xml,
    leia_me,
    taxa_de_quadros,
)
from core.modelos.projeto import DURACAO_MINIMA_TRECHO, montar_exportacao, montar_projeto, partes_do_projeto
from core.modelos.publicacao import textos_do_corte
from core.utils import storage
from core.utils.arte import ErroImagem, preparar_logo
from core.utils.mongo import agora
from core.utils.silencios import cortes_da_gravacao, cortes_do_projeto, partes_com_trechos

router = APIRouter(prefix="/api/projetos", tags=["projetos"])
PRIORIDADE_RENDER = 3


# -----------------------------------------------
# FUNÇÕES AUXILIARES
# -----------------------------------------------
def para_object_id(valor: str, mensagem: str) -> ObjectId:
    try:
        return ObjectId(valor)
    except (InvalidId, TypeError) as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, mensagem) from e


async def buscar_projeto(db, projeto_id: str, usuario: dict) -> dict:
    projeto = await db.projetos.find_one({"_id": para_object_id(projeto_id, "Projeto não encontrado."),
                                          "organizacao_id": usuario["organizacao_id"]})
    if projeto is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Projeto não encontrado.")
    return projeto


async def buscar_midia_do_projeto(db, midia_id, usuario: dict) -> dict:
    midia = await db.midias.find_one({"_id": midia_id, "organizacao_id": usuario["organizacao_id"]})
    if midia is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "A gravação deste projeto não existe mais.")
    return midia


# -----------------------------------------------
# ROTAS
# -----------------------------------------------
@router.post("", response_model=ProjetoSaida, status_code=status.HTTP_201_CREATED)
async def criar_projeto(dados: ProjetoCriarEntrada, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    midia = await buscar_midia_do_projeto(db, para_object_id(dados.midia_id, "Gravação não encontrada."), usuario)
    if midia["status"] != STATUS_PRONTA:
        raise HTTPException(status.HTTP_409_CONFLICT, "A gravação ainda está sendo preparada.")
    if not midia.get("video"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Para criar um Reel, a gravação precisa ter vídeo.")
    modelo = await buscar_modelo(db, dados.modelo_id, usuario) if dados.modelo_id else None
    projeto = montar_projeto(usuario["organizacao_id"], midia, usuario["_id"], dados.nome, dados.proporcao,
                             identidade=await carregar_identidade(db, usuario["organizacao_id"]),
                             tipo=dados.tipo, modelo=modelo, inicio=dados.inicio)
    projeto["_id"] = (await db.projetos.insert_one(projeto)).inserted_id
    return projeto_para_saida(projeto)


@router.get("", response_model=list[ProjetoSaida])
async def listar_projetos(midia_id: str | None = None, limite: int = Query(default=30, ge=1, le=100),
                          usuario=Depends(usuario_atual), db=Depends(obter_db)):
    filtro = {"organizacao_id": usuario["organizacao_id"]}
    if midia_id:
        filtro["midia_id"] = para_object_id(midia_id, "Gravação não encontrada.")
    cursor = db.projetos.find(filtro).sort("atualizado_em", -1).limit(limite)
    return [projeto_para_saida(p) async for p in cursor]


@router.get("/{projeto_id}", response_model=ProjetoSaida)
async def ver_projeto(projeto_id: str, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    return projeto_para_saida(await buscar_projeto(db, projeto_id, usuario))


@router.post("/{projeto_id}/publicacao", response_model=ProjetoSaida)
async def refazer_publicacao(projeto_id: str, versao: int = Query(ge=1),
                             usuario=Depends(usuario_atual), db=Depends(obter_db)):
    """Título e legenda do post a partir da fala que ficou neste corte. O que não foi dito não entra."""
    projeto = await buscar_projeto(db, projeto_id, usuario)
    transcricao = await db.transcricoes.find_one({
        "midia_id": projeto["midia_id"], "organizacao_id": usuario["organizacao_id"],
    })
    visiveis = palavras_visiveis(palavras_da_transcricao(transcricao), legenda_do_projeto(projeto))
    no_corte = [palavra for palavra in visiveis
                if any(float(parte["inicio"]) <= float(palavra["inicio"]) < float(parte["fim"])
                       for parte in projeto.get("partes") or [])]
    textos = await run_in_threadpool(textos_do_corte, no_corte)
    if textos is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            "Não há uma frase dita neste corte para virar título.")
    resultado = await db.projetos.find_one_and_update(
        {"_id": projeto["_id"], "versao": versao},
        {"$set": {
            "nome": textos["titulo"],
            "publicacao": {"legenda": textos["legenda"], "hashtags": textos["hashtags"], "gerado_por_ia": True},
            "atualizado_em": agora(),
        }, "$inc": {"versao": 1}},
        return_document=ReturnDocument.AFTER,
    )
    if resultado is None:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Este projeto foi alterado em outra aba ou por outra pessoa. Recarregue a página.")
    return projeto_para_saida(resultado)


@router.get("/{projeto_id}/legenda", response_model=LegendaPreviaSaida)
async def ver_legenda(projeto_id: str, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    """Blocos da legenda no tempo do vídeo final. A prévia e o render usam esta mesma conta."""
    projeto = await buscar_projeto(db, projeto_id, usuario)
    midia = await buscar_midia_do_projeto(db, projeto["midia_id"], usuario)
    transcricao = await db.transcricoes.find_one({
        "midia_id": projeto["midia_id"], "organizacao_id": usuario["organizacao_id"],
    })
    palavras = palavras_da_transcricao(transcricao)
    intensidade = (projeto.get("silencios") or {}).get("intensidade")
    cortes_silencio = await run_in_threadpool(cortes_da_gravacao, midia, intensidade)
    legenda = legenda_do_projeto(projeto)
    partes = partes_do_projeto(projeto)
    cortes = fundir_cortes([*cortes_silencio, *cortes_da_fala(palavras, legenda)])
    blocos = montar_blocos(palavras_visiveis(palavras, legenda), partes, cortes, legenda["palavras_por_bloco"])
    identidade = await carregar_identidade(db, usuario["organizacao_id"])
    return LegendaPreviaSaida(
        cor_destaque=identidade["cor_destaque"], cor_dourada=COR_DOURADA, tem_transcricao=bool(palavras),
        blocos=blocos, palavras=palavras_para_edicao(palavras, partes), **legenda,
    )


@router.patch("/{projeto_id}", response_model=ProjetoSaida)
async def atualizar_projeto(projeto_id: str, dados: ProjetoAtualizarEntrada,
                            usuario=Depends(usuario_atual), db=Depends(obter_db)):
    projeto = await buscar_projeto(db, projeto_id, usuario)
    campos = dados.model_dump(exclude_unset=True, exclude={"versao"})
    if dados.partes is not None:
        midia = await buscar_midia_do_projeto(db, projeto["midia_id"], usuario)
        partes = []
        for parte in dados.partes:
            fim = min(round(parte.fim, 2), round(midia["duracao"], 2))
            if fim - parte.inicio < DURACAO_MINIMA_TRECHO:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                                    "Cada parte precisa ter pelo menos 1 segundo.")
            partes.append({"id": parte.id, "inicio": round(parte.inicio, 2), "fim": fim})
        if len({parte["id"] for parte in partes}) != len(partes):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Duas partes com o mesmo identificador.")
        campos["partes"] = partes
    for texto in dados.textos or []:
        if texto.fim is not None and texto.fim <= texto.inicio:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "O texto precisa terminar depois de começar.")
    if dados.textos is not None and len({texto.id for texto in dados.textos}) != len(dados.textos):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Dois textos com o mesmo identificador.")
    if dados.figuras is not None:
        if len({figura.id for figura in dados.figuras}) != len(dados.figuras):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Duas figuras com o mesmo identificador.")
        conhecidas = {figura["id"] for figura in projeto.get("figuras") or []}
        for figura in dados.figuras:
            if figura.fim is not None and figura.fim <= figura.inicio:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                                    "A figura precisa terminar depois de começar.")
            if figura.id not in conhecidas:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "A figura não está neste projeto.")
    if dados.apoios is not None:
        if len({apoio.id for apoio in dados.apoios}) != len(dados.apoios):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                                "Dois vídeos de apoio com o mesmo identificador.")
        conhecidos = {apoio["id"] for apoio in projeto.get("apoios") or []}
        for apoio in dados.apoios:
            if apoio.fim is not None and apoio.fim <= apoio.inicio:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                                    "O vídeo de apoio precisa terminar depois de começar.")
            if apoio.id not in conhecidos:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "O vídeo de apoio não está neste projeto.")
    if dados.musica is not None and dados.musica.id is not None:
        await buscar_musica(db, dados.musica.id, usuario)
    if not campos:
        return projeto_para_saida(projeto)

    campos["atualizado_em"] = agora()
    # Projetos de antes da linha do tempo guardavam um "trecho" só; as partes substituem
    sem_trecho = {"$unset": {"trecho": ""}} if "partes" in campos else {}
    resultado = await db.projetos.find_one_and_update(
        {"_id": projeto["_id"], "versao": dados.versao},
        {"$set": campos, "$inc": {"versao": 1}, **sem_trecho},
        return_document=ReturnDocument.AFTER,
    )
    if resultado is None:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Este projeto foi alterado em outra aba ou por outra pessoa. Recarregue a página.")
    return projeto_para_saida(resultado)


@router.delete("/{projeto_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_projeto(projeto_id: str, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    projeto = await buscar_projeto(db, projeto_id, usuario)
    await apagar_exportacoes(db, {"projeto_id": projeto["_id"]})
    await run_in_threadpool(storage.remover_pasta, pasta_figuras(usuario["organizacao_id"], projeto["_id"]))
    await run_in_threadpool(storage.remover_pasta, pasta_apoios(usuario["organizacao_id"], projeto["_id"]))
    await db.projetos.delete_one({"_id": projeto["_id"]})


@router.post("/{projeto_id}/figuras", response_model=ProjetoSaida, status_code=status.HTTP_201_CREATED)
async def adicionar_figura(projeto_id: str, request: Request, versao: int = Query(ge=1),
                           icone: str | None = Query(default=None),
                           nome: str | None = Query(default=None, max_length=80),
                           usuario=Depends(usuario_atual), db=Depends(obter_db)):
    """Acrescenta um ícone pronto ou um PNG, JPG ou WEBP. A versão evita gravar por cima de outra aba."""
    if icone is not None and icone not in ICONES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Escolha cruz, bíblia, chama ou estrela.")
    projeto = await buscar_projeto(db, projeto_id, usuario)
    if len(projeto.get("figuras") or []) >= MAX_FIGURAS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Dá para colocar até 8 figuras no vídeo.")
    rotulo = (nome or "").replace("\\", "/").split("/")[-1]
    if "." in rotulo:
        rotulo = rotulo.rsplit(".", 1)[0]
    rotulo = rotulo.strip()[:40]
    figura = nova_figura(icone, rotulo or (NOMES_ICONES[icone] if icone else "Imagem"))
    chave = None
    if icone is None:
        conteudo = bytearray()
        async for pedaco in request.stream():
            conteudo += pedaco
            if len(conteudo) > LOGO_MAX_BYTES:
                raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "A imagem pode ter no máximo 5 MB.")
        if not conteudo:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Envie uma imagem PNG, JPG ou WEBP.")
        try:
            png = await run_in_threadpool(preparar_logo, bytes(conteudo))
        except ErroImagem as e:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(e)) from e
        chave = chave_figura(usuario["organizacao_id"], projeto["_id"], figura["id"])
        if not await run_in_threadpool(storage.salvar_bytes, chave, png):
            raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Não foi possível salvar a imagem.")
    resultado = await db.projetos.find_one_and_update(
        {"_id": projeto["_id"], "versao": versao},
        {"$push": {"figuras": figura}, "$inc": {"versao": 1}, "$set": {"atualizado_em": agora()}},
        return_document=ReturnDocument.AFTER,
    )
    if resultado is None:
        if chave:
            await run_in_threadpool(storage.remover, chave)
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Este projeto foi alterado em outra aba ou por outra pessoa. Recarregue a página.")
    return projeto_para_saida(resultado)


@router.post("/{projeto_id}/exportar", response_model=ExportacaoSaida, status_code=status.HTTP_201_CREATED)
async def exportar_projeto(projeto_id: str, dados: ExportarEntrada | None = None,
                           usuario=Depends(usuario_atual), db=Depends(obter_db)):
    dados = dados or ExportarEntrada()
    projeto = await buscar_projeto(db, projeto_id, usuario)
    midia = await buscar_midia_do_projeto(db, projeto["midia_id"], usuario)
    if (dados.formato == "video" and (projeto.get("audio") or {}).get("limpeza")
            and ARQUIVO_AUDIO_LIMPO not in (midia.get("arquivos") or [])):
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "A limpeza do áudio ainda está em andamento. Espere ela terminar para exportar.")
    if (projeto.get("enquadramento") or {}).get("seguir_rosto"):
        trilha = await db.rostos.find_one({"midia_id": midia["_id"], "organizacao_id": projeto["organizacao_id"]})
        if not trilha or not trilha.get("quadros"):
            raise HTTPException(status.HTTP_409_CONFLICT,
                                "O acompanhamento do rosto ainda não ficou pronto. Espere e exporte de novo.")
    exportacao = montar_exportacao(projeto, usuario["_id"], formato=dados.formato, instante=dados.instante,
                                   encoder=dados.encoder)
    exportacao["_id"] = (await db.exportacoes.insert_one(exportacao)).inserted_id
    tipo_render = "renderizacao_nvenc" if dados.formato == "video" and dados.encoder == "nvenc" else "renderizacao"
    job = montar_job(tipo_render, usuario["organizacao_id"], {"exportacao_id": str(exportacao["_id"])},
                     prioridade=PRIORIDADE_RENDER, criado_por=usuario["_id"])
    job["_id"] = (await db.jobs.insert_one(job)).inserted_id
    await db.exportacoes.update_one({"_id": exportacao["_id"]}, {"$set": {"job_id": job["_id"]}})
    logging.info(f"[{usuario['organizacao_id']}] Exportação na fila: {projeto['nome']}")
    return exportacao_para_saida({**exportacao, "job_id": job["_id"]}, job)


def montar_pacote(projeto: dict, midia: dict, palavras: list[dict]) -> tuple[str, bytes]:
    """O .zip com o XML dos cortes, o SRT da legenda e o passo a passo. Devolve o nome do arquivo e os bytes."""
    cortes = cortes_do_projeto(midia, projeto, palavras)
    partes = partes_com_trechos(projeto, cortes)
    _, _, quadros = taxa_de_quadros(midia["video"].get("fps"))
    base = nome_de_arquivo(projeto["nome"], "")
    xml = gerar_xml(projeto["nome"], midia["nome_original"], float(midia["duracao"]), midia["video"],
                    midia.get("audio"), clipes_da_linha_do_tempo(partes, quadros))
    legenda = legenda_do_projeto(projeto)
    blocos = montar_blocos(palavras_visiveis(palavras, legenda), [parte for parte, _ in partes], cortes,
                           PALAVRAS_POR_LEGENDA_SRT)
    srt = gerar_srt(blocos)
    memoria = io.BytesIO()
    with zipfile.ZipFile(memoria, "w", zipfile.ZIP_DEFLATED) as pacote:
        pacote.writestr(f"{base}.xml", xml)
        if srt:
            pacote.writestr(f"{base}.srt", srt)
        pacote.writestr("LEIA-ME.txt", leia_me(projeto["nome"], midia["nome_original"], base, bool(srt),
                                               projeto["proporcao"]))
    return f"{base}.zip", memoria.getvalue()


@router.get("/{projeto_id}/pacote-edicao")
async def baixar_pacote_edicao(projeto_id: str, usuario=Depends(usuario_atual), db=Depends(obter_db)):
    """Os cortes do projeto para o DaVinci Resolve e o Premiere Pro: XML, SRT e o passo a passo, num .zip."""
    projeto = await buscar_projeto(db, projeto_id, usuario)
    midia = await buscar_midia_do_projeto(db, projeto["midia_id"], usuario)
    if not midia.get("video") or not midia.get("duracao"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT,
                            "O pacote de edição precisa de uma gravação com vídeo.")
    transcricao = await db.transcricoes.find_one({"midia_id": midia["_id"],
                                                  "organizacao_id": usuario["organizacao_id"]})
    nome, conteudo = await run_in_threadpool(montar_pacote, projeto, midia, palavras_da_transcricao(transcricao))
    return Response(conteudo, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{nome}"', "Cache-Control": "no-store"})
