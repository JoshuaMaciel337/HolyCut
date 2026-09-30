# Acervo da igreja pela API: ficha do culto, capas na fila e fileiras, contra um MongoDB de verdade
import io
import uuid
from datetime import timedelta

import pytest
from bson import ObjectId
from fastapi.testclient import TestClient
from PIL import Image

from api.main import app
from core.modelos.culto import ARQUIVO_FUNDO_CAPA
from core.modelos.midia import chave_arquivo, montar_midia
from core.modelos.projeto import montar_exportacao, montar_projeto
from core.utils import storage
from core.utils.mongo import agora


@pytest.fixture
def cliente(db_limpo):
    with TestClient(app) as cliente:
        entrar(cliente)
        yield cliente


def entrar(cliente, igreja="Igreja do Acervo"):
    return cliente.post("/api/auth/cadastro", json={
        "nome_igreja": igreja, "nome": "Pessoa", "email": f"{uuid.uuid4().hex[:8]}@exemplo.com",
        "senha": "senha-segura-1"}).json()


def organizacao(cliente) -> ObjectId:
    return ObjectId(cliente.get("/api/auth/eu").json()["organizacao"]["id"])


def criar_culto(db, organizacao_id, nome, ficha=None, status="pronta", com_video=True, dias_atras=0):
    midia = montar_midia(organizacao_id, None, f"{nome}.mp4", 10)
    midia.update({"nome": nome, "status": status, "duracao": 3600.0, "enviado_em": agora() - timedelta(days=dias_atras),
                  "video": {"largura": 1920, "altura": 1080} if com_video else None,
                  "audio": {"canais": 2, "taxa": 48000}})
    if ficha:
        midia["ficha"] = ficha
    return db.midias.insert_one(midia).inserted_id


def jobs_de_capa(db, midia_id) -> int:
    return db.jobs.count_documents({"tipo": "capas_culto", "entrada.midia_id": str(midia_id)})


def test_ficha_do_culto_e_capas_na_fila(cliente, db_limpo):
    midia_id = criar_culto(db_limpo, organizacao(cliente), "Culto de domingo")
    rota = f"/api/midias/{midia_id}"
    inicial = cliente.get(rota).json()
    assert inicial["ficha"]["pregador"] == "" and len(inicial["ficha"]["data"]) == 10
    assert jobs_de_capa(db_limpo, midia_id) == 1              # a visita pede as capas das gravações antigas

    ficha = {"data": "2026-08-15", "pregador": "  Pr.  Joelson Moura ", "serie": "Romanos", "descricao": "Rm 12"}
    salvo = cliente.patch(rota, json={"nome": "Inconformados no altar", "ficha": ficha})
    assert salvo.status_code == 200
    corpo = salvo.json()
    assert corpo["nome"] == "Inconformados no altar"
    assert corpo["ficha"] == {"data": "2026-08-15", "pregador": "Pr. Joelson Moura", "serie": "Romanos",
                              "descricao": "Rm 12"}
    assert jobs_de_capa(db_limpo, midia_id) == 1              # já tem um esperando: o patch não enfileira outro
    cliente.patch(rota, json={"nome": "Inconformados no altar!"})
    assert jobs_de_capa(db_limpo, midia_id) == 1
    assert cliente.patch(rota, json={"ficha": {"data": "15/08/2026"}}).status_code == 422

    # Gravação ainda preparando: a ingestão desenha as capas quando terminar
    preparando = criar_culto(db_limpo, organizacao(cliente), "Chegando", status="processando")
    cliente.patch(f"/api/midias/{preparando}", json={"ficha": {"pregador": "Pr. Ana"}})
    assert jobs_de_capa(db_limpo, preparando) == 0


def test_escolher_o_fundo_da_capa(cliente, db_limpo):
    organizacao_id = organizacao(cliente)
    midia_id = criar_culto(db_limpo, organizacao_id, "Culto")
    rota = f"/api/midias/{midia_id}/capa"
    corpo = cliente.post(rota, json={"instante": 125.5}).json()
    assert corpo["capa_personalizada"] is False
    assert db_limpo.midias.find_one({"_id": midia_id})["capa"]["instante"] == 125.5

    assert cliente.put(f"{rota}/imagem", content=b"nao e imagem").status_code == 422
    png = io.BytesIO()
    Image.new("RGB", (800, 600), (40, 80, 160)).save(png, format="PNG")
    enviada = cliente.put(f"{rota}/imagem", content=png.getvalue())
    assert enviada.status_code == 200 and enviada.json()["capa_personalizada"] is True
    arquivo = storage.caminho_local(chave_arquivo(organizacao_id, midia_id, ARQUIVO_FUNDO_CAPA))
    assert arquivo.is_file() and Image.open(arquivo).format == "JPEG"

    removida = cliente.delete(f"{rota}/imagem").json()
    assert removida["capa_personalizada"] is False and not arquivo.exists()

    so_audio = criar_culto(db_limpo, organizacao_id, "Podcast", com_video=False)
    assert cliente.post(f"/api/midias/{so_audio}/capa", json={"instante": 3}).status_code == 422


def test_acervo_com_fileiras(cliente, db_limpo):
    organizacao_id = organizacao(cliente)
    antigo = criar_culto(db_limpo, organizacao_id, "Família 1",
                         {"data": "2026-07-05", "pregador": "Pr. Ana", "serie": "Família"})
    meio = criar_culto(db_limpo, organizacao_id, "Romanos 12",
                       {"data": "2026-08-15", "pregador": "Pr. Ana", "serie": "Romanos"})
    novo = criar_culto(db_limpo, organizacao_id, "Culto de missões", {"data": "2026-09-27", "pregador": "Pr. Bruno"})
    criar_culto(db_limpo, organizacao_id, "Chegando", status="processando")

    # Um corte pronto do culto de agosto e um Reel em edição do culto de julho
    midia_meio = db_limpo.midias.find_one({"_id": meio})
    projeto = {**montar_projeto(organizacao_id, midia_meio, None), "atualizado_em": agora()}
    projeto["_id"] = db_limpo.projetos.insert_one(projeto).inserted_id
    exportacao = montar_exportacao(projeto, None)
    exportacao["status"] = "pronta"
    db_limpo.exportacoes.insert_one(exportacao)
    db_limpo.projetos.insert_one({**montar_projeto(organizacao_id, db_limpo.midias.find_one({"_id": antigo}), None),
                                  "atualizado_em": agora() + timedelta(minutes=1)})

    acervo = cliente.get("/api/acervo").json()
    assert [c["titulo"] for c in acervo["cultos"]] == ["Culto de missões", "Romanos 12", "Família 1"]
    assert acervo["destaque"] == str(novo)
    assert acervo["preparando"] == 1
    fileiras = {f["id"]: f["ids"] for f in acervo["fileiras"]}
    assert fileiras["recentes"] == [str(novo), str(meio), str(antigo)]
    assert fileiras["editando"] == [str(antigo), str(meio)]    # o projeto mexido por último vem primeiro
    assert fileiras["cortes"] == [str(meio)]
    assert fileiras["serie:Romanos"] == [str(meio)] and fileiras["serie:Família"] == [str(antigo)]
    assert fileiras["pregador:Pr. Ana"] == [str(meio), str(antigo)]
    assert "pregador:Pr. Bruno" not in fileiras
    resumo = next(c for c in acervo["cultos"] if c["id"] == str(meio))
    assert (resumo["cortes"], resumo["em_edicao"], resumo["serie"]) == (1, 1, "Romanos")
    assert acervo["series"] == ["Família", "Romanos"] and acervo["pregadores"] == ["Pr. Ana", "Pr. Bruno"]

    # Os cortes de um culto, de todos os projetos dele
    assert len(cliente.get(f"/api/exportacoes?midia_id={meio}").json()) == 1
    assert cliente.get(f"/api/exportacoes?midia_id={antigo}").json() == []

    # Cada igreja vê só o próprio acervo
    cliente.post("/api/auth/sair")
    entrar(cliente, igreja="Outra Igreja")
    vazio = cliente.get("/api/acervo").json()
    assert vazio["cultos"] == [] and vazio["destaque"] is None and vazio["fileiras"][0]["ids"] == []
    assert cliente.patch(f"/api/midias/{novo}", json={"nome": "invasão"}).status_code == 404
