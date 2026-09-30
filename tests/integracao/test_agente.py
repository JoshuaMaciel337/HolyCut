# Agente do OBS de ponta a ponta: a API de verdade num servidor local, o agente enviando por HTTP
# como faria no PC da igreja, e as chaves de envio.
import socket
import threading
import time
import uuid

import agente.agendador_gravacoes as agente
import pytest
import requests
import uvicorn
from bson import ObjectId

from api.main import app
from core.modelos.midia import chave_arquivo
from core.utils import storage


@pytest.fixture
def servidor(db_limpo):
    with socket.socket() as livre:
        livre.bind(("127.0.0.1", 0))
        porta = livre.getsockname()[1]
    rodando = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=porta, log_level="warning"))
    thread = threading.Thread(target=rodando.run, daemon=True)
    thread.start()
    for _ in range(100):
        if rodando.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{porta}"
    rodando.should_exit = True
    thread.join(timeout=10)


def entrar(servidor, igreja="Igreja do Agente") -> requests.Session:
    sessao = requests.Session()
    resposta = sessao.post(f"{servidor}/api/auth/cadastro", timeout=10, json={
        "nome_igreja": igreja, "nome": "Pessoa", "email": f"{uuid.uuid4().hex[:8]}@exemplo.com",
        "senha": "senha-segura-1"})
    assert resposta.status_code in (200, 201), resposta.text
    return sessao


def criar_chave(servidor, sessao, nome="PC da mídia") -> dict:
    resposta = sessao.post(f"{servidor}/api/chaves-envio", json={"nome": nome}, timeout=10)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


@pytest.fixture
def pedacos_pequenos(monkeypatch):
    monkeypatch.setattr(agente, "TAMANHO_PEDACO", 4096)
    monkeypatch.setattr(agente, "ESPERA_ENTRE_TENTATIVAS", 0)


def test_chaves_de_envio(servidor):
    sessao = entrar(servidor)
    criada = criar_chave(servidor, sessao)
    assert criada["chave"].startswith("hc_") and criada["inicio"] == criada["chave"][:9]
    lista = sessao.get(f"{servidor}/api/chaves-envio", timeout=10).json()
    assert [c["id"] for c in lista] == [criada["id"]] and "chave" not in lista[0]   # a chave não volta mais

    com_chave = {"Authorization": f"Bearer {criada['chave']}"}
    conferida = requests.get(f"{servidor}/api/chaves-envio/conferir", headers=com_chave, timeout=10).json()
    assert conferida == {"igreja": "Igreja do Agente", "chave": "PC da mídia"}
    # A chave só serve para enviar: o resto do site continua pedindo login
    assert requests.get(f"{servidor}/api/midias", headers=com_chave, timeout=10).status_code == 401
    errada = {"Authorization": "Bearer hc_nao-existe"}
    assert requests.get(f"{servidor}/api/chaves-envio/conferir", headers=errada, timeout=10).status_code == 401

    # Outra igreja não vê nem revoga
    outra = entrar(servidor, igreja="Outra Igreja")
    assert outra.get(f"{servidor}/api/chaves-envio", timeout=10).json() == []
    assert outra.delete(f"{servidor}/api/chaves-envio/{criada['id']}", timeout=10).status_code == 404

    assert sessao.delete(f"{servidor}/api/chaves-envio/{criada['id']}", timeout=10).status_code == 204
    assert requests.get(f"{servidor}/api/chaves-envio/conferir", headers=com_chave, timeout=10).status_code == 401
    assert sessao.get(f"{servidor}/api/chaves-envio", timeout=10).json() == []


def test_baixar_o_agente(servidor):
    import io
    import zipfile

    sessao = entrar(servidor)
    resposta = sessao.get(f"{servidor}/api/chaves-envio/agente.zip", params={"servidor": "https://holycut.app"},
                          timeout=10)
    assert resposta.headers["content-type"] == "application/zip"
    pacote = zipfile.ZipFile(io.BytesIO(resposta.content))
    assert sorted(pacote.namelist()) == ["holycut-agente/README.md", "holycut-agente/agendador_gravacoes.py",
                                         "holycut-agente/iniciar_agente.bat", "holycut-agente/requirements.txt"]
    bat = pacote.read("holycut-agente/iniciar_agente.bat")
    assert b'agendador_gravacoes.py --servidor "https://holycut.app" %*' in bat
    assert b"\r\n" in bat and b"\n" not in bat.replace(b"\r\n", b"")     # CRLF em todas as linhas
    # Nada de comando escondido no endereço
    for malicioso in ("https://x.com\" & calc & rem", "https://x.com\n", "https://x.com/caminho"):
        assert sessao.get(f"{servidor}/api/chaves-envio/agente.zip", params={"servidor": malicioso},
                          timeout=10).status_code == 422
    assert requests.get(f"{servidor}/api/chaves-envio/agente.zip", timeout=10).status_code == 401


def test_agente_envia_so_a_gravacao_nova(servidor, db_limpo, tmp_path, pedacos_pequenos):
    sessao = entrar(servidor)
    chave = criar_chave(servidor, sessao)
    pasta = tmp_path / "obs"
    pasta.mkdir()
    (pasta / "domingo-passado.mp4").write_bytes(b"antiga" * 1000)
    configuracao = {"servidor": servidor, "chave": chave["chave"], "pasta": str(pasta), "minutos_estavel": 0}
    estado, arquivo_estado = {}, tmp_path / "estado.json"
    assert agente.conferir_pasta(configuracao, estado, arquivo_estado) == []    # primeira vez: só marca

    conteudo = bytes(range(256)) * 80        # 20 KB: cinco pedaços de 4 KB
    (pasta / "culto.mkv").write_bytes(b"mkv")
    (pasta / "culto.mp4").write_bytes(conteudo)
    assert agente.conferir_pasta(configuracao, estado, arquivo_estado) == []    # observa
    assert agente.conferir_pasta(configuracao, estado, arquivo_estado) == ["culto.mp4"]
    assert agente.conferir_pasta(configuracao, estado, arquivo_estado) == []    # não manda de novo

    midias = list(db_limpo.midias.find())
    assert len(midias) == 1
    midia = midias[0]
    assert (midia["nome_original"], midia["status"]) == ("culto.mp4", "processando")
    assert midia["tamanho_total"] == len(conteudo)
    assert midia["enviada_pela_chave"] == ObjectId(chave["id"])
    original = storage.caminho_local(chave_arquivo(midia["organizacao_id"], midia["_id"], midia["original"]))
    assert original.read_bytes() == conteudo
    assert db_limpo.jobs.find_one({"tipo": "ingestao", "entrada.midia_id": str(midia["_id"])}) is not None
    registro = estado["arquivos"][str(pasta / "culto.mp4")]
    assert registro["situacao"] == agente.ENVIADO and registro["midia_id"] == str(midia["_id"])


def test_agente_continua_de_onde_parou(servidor, db_limpo, tmp_path, pedacos_pequenos, monkeypatch):
    sessao = entrar(servidor)
    chave = criar_chave(servidor, sessao)
    pasta = tmp_path / "obs"
    pasta.mkdir()
    configuracao = {"servidor": servidor, "chave": chave["chave"], "pasta": str(pasta), "minutos_estavel": 0,
                    "enviar_existentes": True}
    conteudo = bytes(range(256)) * 64        # 16 KB: quatro pedaços
    (pasta / "culto.mp4").write_bytes(conteudo)
    estado, arquivo_estado = {}, tmp_path / "estado.json"
    agente.conferir_pasta(configuracao, estado, arquivo_estado)

    # A internet cai depois do segundo pedaço
    patch_de_verdade, enviados = requests.patch, []

    def patch_que_cai(*args, **kwargs):
        if len(enviados) >= 2:
            raise requests.ConnectionError("sem internet")
        enviados.append(1)
        return patch_de_verdade(*args, **kwargs)

    monkeypatch.setattr(agente.requests, "patch", patch_que_cai)
    assert agente.conferir_pasta(configuracao, estado, arquivo_estado) == []
    registro = estado["arquivos"][str(pasta / "culto.mp4")]
    assert registro["situacao"] == agente.ENVIANDO and registro["erro"].startswith("Sem conexão")
    assert agente.posicao_no_servidor(registro["url"], chave["chave"]) == 8192

    # A internet volta: continua do pedaço 3, sem começar de novo
    monkeypatch.setattr(agente.requests, "patch", patch_de_verdade)
    assert agente.conferir_pasta(configuracao, estado, arquivo_estado) == ["culto.mp4"]
    midia = db_limpo.midias.find_one()
    assert db_limpo.midias.count_documents({}) == 1 and midia["status"] == "processando"
    original = storage.caminho_local(chave_arquivo(midia["organizacao_id"], midia["_id"], midia["original"]))
    assert original.read_bytes() == conteudo


def test_chave_revogada_para_o_agente(servidor, tmp_path, pedacos_pequenos):
    sessao = entrar(servidor)
    chave = criar_chave(servidor, sessao)
    assert agente.conferir_chave(servidor, chave["chave"]) == "Igreja do Agente"
    sessao.delete(f"{servidor}/api/chaves-envio/{chave['id']}", timeout=10)
    with pytest.raises(agente.ErroChave):
        agente.conferir_chave(servidor, chave["chave"])

    pasta = tmp_path / "obs"
    pasta.mkdir()
    (pasta / "culto.mp4").write_bytes(b"x" * 100)
    configuracao = {"servidor": servidor, "chave": chave["chave"], "pasta": str(pasta), "minutos_estavel": 0,
                    "enviar_existentes": True}
    estado = {}
    agente.conferir_pasta(configuracao, estado, tmp_path / "estado.json")
    with pytest.raises(agente.ErroChave):
        agente.conferir_pasta(configuracao, estado, tmp_path / "estado.json")
