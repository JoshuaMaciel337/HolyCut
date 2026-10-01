# O que sai do vídeo quando a pessoa apaga uma palavra ou liga os vícios de fala
import pytest

from core.modelos.fala import (
    conferir_edicoes,
    conferir_ids,
    cortes_da_fala,
    fundir_cortes,
    nivel_do_vicio,
    palavra_cortada,
    palavras_visiveis,
    texto_exibido,
)
from core.modelos.legenda import legenda_do_projeto, montar_blocos

PALAVRAS = [
    {"id": "w000001", "texto": "A", "inicio": 0.2, "fim": 0.4, "segmento": "s0001"},
    {"id": "w000002", "texto": "né,", "inicio": 0.5, "fim": 0.8, "segmento": "s0001"},
    {"id": "w000003", "texto": "paz", "inicio": 1.0, "fim": 1.4, "segmento": "s0001"},
]


def _legenda(**campos):
    return legenda_do_projeto({"legenda": campos})


def test_vicio_respeita_a_intensidade_e_nao_corta_a_mensagem():
    assert nivel_do_vicio("Né,") == "leve"
    assert nivel_do_vicio("tipo") == "media"
    assert nivel_do_vicio("então") == "forte"
    for texto in ("Jesus", "amém", "é", "Deus", "paz"):
        assert nivel_do_vicio(texto) is None

    leve = _legenda(vicios="leve")
    assert palavra_cortada(PALAVRAS[1], leve) is True
    assert palavra_cortada({"id": "w000004", "texto": "tipo"}, leve) is False
    assert palavra_cortada({"id": "w000005", "texto": "então"}, _legenda(vicios="media")) is False
    assert palavra_cortada({"id": "w000005", "texto": "então"}, _legenda(vicios="forte")) is True
    assert palavra_cortada({"id": "w000006", "texto": "Jesus"}, _legenda(vicios="forte")) is False


def test_corrigir_mantem_o_som_e_apagar_tira():
    corrigida = _legenda(vicios="leve", edicoes={"w000002": "não"})
    assert palavra_cortada(PALAVRAS[1], corrigida) is False
    assert texto_exibido(PALAVRAS[1], corrigida) == "não"

    mantida = _legenda(vicios="leve", mantidas=["w000002"])
    assert palavra_cortada(PALAVRAS[1], mantida) is False

    apagada = _legenda(apagadas=["w000002"], edicoes={"w000002": "não"})
    assert palavra_cortada(PALAVRAS[1], apagada) is True
    assert [palavra["texto"] for palavra in palavras_visiveis(PALAVRAS, _legenda(edicoes={"w000003": "Paz"}))] == [
        "A", "né,", "Paz",
    ]


def test_corte_da_fala_anda_o_tempo_da_legenda():
    legenda = _legenda(apagadas=["w000002"])
    assert cortes_da_fala(PALAVRAS, legenda) == [(0.5, 0.8)]
    blocos = montar_blocos(palavras_visiveis(PALAVRAS, legenda), [{"inicio": 0.0, "fim": 5.0}],
                           cortes_da_fala(PALAVRAS, legenda), 4)
    textos = [palavra["texto"] for bloco in blocos for palavra in bloco["palavras"]]
    assert textos == ["A", "paz"]
    paz = blocos[-1]["palavras"][-1]
    assert paz["inicio"] < 1.0


def test_cortes_perto_viram_um_so():
    assert fundir_cortes([(1.0, 1.2), (0.0, 0.2), (0.25, 0.4)]) == [(0.0, 0.4), (1.0, 1.2)]


def test_id_invalido_nao_entra_e_a_api_recusa():
    legenda = legenda_do_projeto({"legenda": {"apagadas": ["w000001", "ruim", "w000001"], "edicoes": {"x": "oi"}}})
    assert legenda["apagadas"] == ["w000001"]
    assert legenda["edicoes"] == {}
    with pytest.raises(ValueError):
        conferir_ids(["palavra"])
    with pytest.raises(ValueError):
        conferir_edicoes({"w000001": "   "})
