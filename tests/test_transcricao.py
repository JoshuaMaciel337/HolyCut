# A transcrição monta o documento, o SRT e o TXT sem modelo e sem banco.
from datetime import datetime

from core.config import TZ
from core.modelos.job import tipos_por_recursos
from core.modelos.transcricao import (
    deve_transcrever,
    dicas_da_igreja,
    exportar_srt,
    exportar_txt,
    montar_segmentos,
    montar_transcricao,
    tempo_srt,
)


def test_so_transcreve_com_ia_real_e_audio():
    assert deve_transcrever("real", True)
    assert not deve_transcrever("simulado", True)
    assert not deve_transcrever("real", False)


def test_dicas_trazem_igreja_pregador_e_livros():
    dicas = dicas_da_igreja("  Igreja Viva  ", "Pr. João")
    assert "Igreja Viva" in dicas["initial_prompt"]
    assert "Pr. João" in dicas["initial_prompt"]
    assert "sem corrigir o português" in dicas["initial_prompt"]
    assert "Igreja Viva" in dicas["hotwords"]
    assert "Apocalipse" in dicas["hotwords"]
    assert "Gênesis" in dicas["hotwords"]


def test_segmentos_ganham_id_e_ignoram_palavra_sem_tempo():
    segmentos = montar_segmentos([
        {
            "texto": "  A paz   do Senhor ",
            "inicio": 1.23456,
            "fim": 3,
            "palavras": [
                {"texto": " A ", "inicio": 1.2, "fim": 1.4, "confianca": 0.91234},
                {"texto": "paz", "inicio": None, "fim": 1.8, "confianca": 0.2},
                {"texto": "do", "inicio": 1.8, "fim": 2.0, "confianca": 1.4},
            ],
        },
        {"texto": "   ", "inicio": 4, "fim": 5, "palavras": []},
    ])
    assert len(segmentos) == 1
    assert segmentos[0]["id"] == "s0001"
    assert segmentos[0]["texto"] == "A paz do Senhor"
    assert segmentos[0]["inicio"] == 1.235
    assert [p["id"] for p in segmentos[0]["palavras"]] == ["w000001", "w000002"]
    assert segmentos[0]["palavras"][0]["confianca"] == 0.912
    assert segmentos[0]["palavras"][1]["confianca"] == 1.0


def test_srt_e_txt_usam_o_tempo_do_trecho():
    segmentos = montar_segmentos([{"texto": "A paz", "inicio": 65.5, "fim": 67, "palavras": []}])
    assert tempo_srt(65.5) == "00:01:05,500"
    assert exportar_srt(segmentos) == "1\n00:01:05,500 --> 00:01:07,000\nA paz\n"
    assert exportar_txt(segmentos) == "00:01:05.500 A paz\n"


def test_documento_marca_que_foi_gerado_por_ia():
    momento = datetime(2026, 9, 30, 21, 0, tzinfo=TZ)
    segmentos = montar_segmentos([{"texto": "Amém", "inicio": 0, "fim": 1, "palavras": [
        {"texto": "Amém", "inicio": 0, "fim": 1, "confianca": 0.8},
    ]}])
    doc = montar_transcricao("org", "mid", segmentos, 12, momento)
    assert doc["gerado_por_ia"] is True
    assert doc["idioma"] == "pt"
    assert doc["modelo"] == "large-v3-turbo"
    assert doc["contagem_palavras"] == 1
    assert doc["criado_em"] == momento


def test_transcricao_e_job_de_gpu():
    assert "transcricao" in tipos_por_recursos(["gpu"])
    assert "transcricao" not in tipos_por_recursos(["cpu"])


def test_gravacao_longa_e_ouvida_em_fatias_de_dez_minutos():
    from core.modelos.transcricao import TAMANHO_FATIA, com_deslocamento, fatias_de

    assert fatias_de(90) == [(0.0, 90.0)]
    fatias = fatias_de(9537.381)
    assert fatias[0] == (0.0, TAMANHO_FATIA)
    assert fatias[-1][1] == 9537.381
    assert len(fatias) == 16
    assert all(fim - inicio <= TAMANHO_FATIA + 0.001 for inicio, fim in fatias)
    deslocado = com_deslocamento(
        [{"texto": "paz", "inicio": 1.0, "fim": 2.0, "palavras": [{"texto": "paz", "inicio": 1.0, "fim": 2.0}]}],
        600,
    )
    assert deslocado[0]["inicio"] == 601.0
    assert deslocado[0]["palavras"][0]["fim"] == 602.0
