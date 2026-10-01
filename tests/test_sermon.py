# -----------------------------------------------
# HolyCut — o corte sugerido só fica se o título foi dito
# -----------------------------------------------
from core.modelos.sermon import janelas, validar_cortes

PALAVRAS = [
    {"texto": "Deus", "inicio": 10.0, "fim": 10.4},
    {"texto": "amou", "inicio": 10.4, "fim": 10.8},
    {"texto": "o", "inicio": 10.8, "fim": 11.0},
    {"texto": "mundo", "inicio": 11.0, "fim": 11.5},
    {"texto": "de", "inicio": 12.0, "fim": 12.2},
    {"texto": "tal", "inicio": 12.2, "fim": 12.5},
    {"texto": "maneira", "inicio": 12.5, "fim": 13.2},
]


def test_titulo_que_nao_foi_dito_sai_fora():
    cortes = validar_cortes([{
        "titulo": "Uma frase que ninguém disse aqui",
        "motivo": "parece forte",
        "nota": 9,
        "inicio": 10,
        "fim": 20,
    }], PALAVRAS, 60)
    assert cortes == []


def test_titulo_copiado_da_fala_entra_e_a_legenda_inventada_nao():
    cortes = validar_cortes([{
        "titulo": "Deus amou o mundo",
        "motivo": "É o centro da mensagem.",
        "nota": 8,
        "inicio": 10,
        "fim": 22,
        "legenda_post": "Hoje eu explico a teologia do amor de um jeito novo",
        "hashtags": ["#mundo", "#teologia", "#Deus"],
    }], PALAVRAS, 60)
    assert len(cortes) == 1
    assert cortes[0]["titulo"] == "Deus amou o mundo"
    assert cortes[0]["legenda_post"] == "Deus amou o mundo"
    assert cortes[0]["hashtags"] == ["#mundo", "#deus"]
    assert cortes[0]["id"] == "c01"


def test_parte_curta_demais_nao_vira_corte():
    assert validar_cortes([{
        "titulo": "Deus amou o mundo",
        "motivo": "curto",
        "nota": 7,
        "inicio": 10,
        "fim": 14,
    }], PALAVRAS, 60) == []


def test_janelas_cobrem_a_pregacao_com_sobreposicao():
    palavras = [
        {"texto": "amém", "inicio": float(segundo), "fim": float(segundo) + 0.4}
        for segundo in range(0, 1000, 2)
    ]
    grupos = janelas(palavras, segundos=480, sobreposicao=60)
    assert grupos[0][0]["inicio"] == 0
    assert grupos[0][-1]["inicio"] < 480
    assert grupos[-1][-1]["inicio"] == 998
    assert len(grupos) >= 2
