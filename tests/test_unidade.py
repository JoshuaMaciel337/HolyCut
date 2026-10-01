# Testes que não precisam de banco
import asyncio
from datetime import datetime, timedelta

import pytest

from api.rotas.eventos import eventos
from api.seguranca import (
    LimitadorTentativas,
    criar_token,
    gerar_hash_senha,
    gerar_slug,
    ler_token,
    verificar_senha,
)
from backup.agendador_backup import PREFIXO, remover_backups_antigos
from core.config import TZ
from core.modelos.job import (
    STATUS_PENDENTE,
    calcular_espera_retry,
    montar_job,
    tipos_por_recursos,
)
from core.utils.storage import caminho_local, existe, remover, salvar_bytes


# -----------------------------------------------
# JOB
# -----------------------------------------------
def test_montar_job_preenche_campos_da_fila():
    momento = datetime(2026, 9, 29, 10, 0, tzinfo=TZ)
    job = montar_job("teste", "org1", {"duracao": 3}, momento=momento)
    assert job["status"] == STATUS_PENDENTE
    assert job["recurso"] == "cpu"
    assert job["tentativas"] == 0
    assert job["disponivel_em"] == momento
    assert job["entrada"] == {"duracao": 3}


def test_montar_job_recusa_tipo_desconhecido():
    with pytest.raises(ValueError):
        montar_job("nao_existe", "org1")


def test_espera_retry_cresce_e_para_no_maximo():
    assert calcular_espera_retry(1) == timedelta(minutes=1)
    assert calcular_espera_retry(2) == timedelta(minutes=5)
    assert calcular_espera_retry(3) == timedelta(minutes=30)
    assert calcular_espera_retry(9) == timedelta(minutes=30)


def test_tipos_por_recursos():
    assert tipos_por_recursos(["cpu"]) == [
        "teste", "enquadramento_rosto", "ingestao", "renderizacao", "preparar_musica", "capas_culto",
    ]
    assert tipos_por_recursos(["gpu"]) == [
        "diagnostico_gpu", "transcricao", "limpeza_audio", "sugestao_cortes", "momentos", "renderizacao_nvenc",
    ]
    assert set(tipos_por_recursos(["cpu", "gpu"])) == {
        "teste", "diagnostico_gpu", "transcricao", "limpeza_audio", "sugestao_cortes", "momentos",
        "renderizacao_nvenc", "enquadramento_rosto", "ingestao", "renderizacao", "preparar_musica", "capas_culto",
    }


# -----------------------------------------------
# SEGURANÇA
# -----------------------------------------------
def test_hash_de_senha():
    hash_salvo = gerar_hash_senha("senha-forte-123")
    assert verificar_senha(hash_salvo, "senha-forte-123")
    assert not verificar_senha(hash_salvo, "outra-senha")
    assert not verificar_senha("hash-invalido", "senha-forte-123")


def test_token_de_sessao():
    token = criar_token("usuario1", "org1")
    assert ler_token(token)["sub"] == "usuario1"
    assert ler_token(token + "x") is None
    vencido = criar_token("usuario1", "org1", momento=datetime.now(TZ) - timedelta(days=30))
    assert ler_token(vencido) is None


def test_limitador_bloqueia_depois_do_maximo():
    limitador = LimitadorTentativas(maximo=3, janela_minutos=15)
    for _ in range(3):
        assert not limitador.bloqueado("ip|email")
        limitador.registrar_falha("ip|email")
    assert limitador.bloqueado("ip|email")
    assert not limitador.bloqueado("outro|email")
    limitador.limpar("ip|email")
    assert not limitador.bloqueado("ip|email")


@pytest.mark.parametrize(("nome", "esperado"), [
    ("Igreja Batista da Graça", "igreja-batista-da-graca"),
    ("  Comunidade  Ágape!! ", "comunidade-agape"),
    ("???", "igreja"),
])
def test_gerar_slug(nome, esperado):
    assert gerar_slug(nome) == esperado


# -----------------------------------------------
# EVENTOS AO VIVO
# -----------------------------------------------
def test_eventos_comecam_com_pronto():
    # O painel usa o "pronto" para saber se o fluxo chega ou se precisa consultar a API.
    # Lê só os dois primeiros blocos: antes deles o gerador não toca no banco.
    async def primeiros_blocos():
        resposta = await eventos(request=None, usuario={"organizacao_id": "org1"}, db=None)
        gerador = resposta.body_iterator
        blocos = [await anext(gerador), await anext(gerador)]
        await gerador.aclose()
        return resposta.media_type, blocos

    media_type, blocos = asyncio.run(primeiros_blocos())
    assert media_type == "text/event-stream"
    assert blocos == ["retry: 3000\n\n", "event: pronto\ndata: {}\n\n"]


# -----------------------------------------------
# ARMAZENAMENTO
# -----------------------------------------------
@pytest.mark.parametrize("chave", ["../fora.txt", "/absoluto.txt", "a/../../b", ""])
def test_storage_recusa_chaves_perigosas(chave, tmp_path):
    with pytest.raises(ValueError):
        caminho_local(chave, tmp_path)


def test_storage_salva_e_remove(tmp_path):
    assert salvar_bytes("org1/midias/teste.bin", b"abc", tmp_path)
    assert existe("org1/midias/teste.bin", tmp_path)
    assert (tmp_path / "org1" / "midias" / "teste.bin").read_bytes() == b"abc"
    assert remover("org1/midias/teste.bin", tmp_path)
    assert not existe("org1/midias/teste.bin", tmp_path)


# -----------------------------------------------
# BACKUP
# -----------------------------------------------
def test_remover_backups_antigos_so_apaga_pastas_do_backup(tmp_path):
    agora = datetime(2026, 9, 29, 3, 0, tzinfo=TZ)
    antigo = tmp_path / f"{PREFIXO}01-09-2026_03-00"
    recente = tmp_path / f"{PREFIXO}28-09-2026_03-00"
    outra = tmp_path / "fotos_da_igreja"
    for pasta in (antigo, recente, outra):
        pasta.mkdir()

    assert remover_backups_antigos(tmp_path, retencao_dias=14, momento=agora) == 1
    assert not antigo.exists()
    assert recente.exists()
    assert outra.exists()
