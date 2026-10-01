# -----------------------------------------------
# HolyCut — rosto, versículo e momentos
# -----------------------------------------------
from core.modelos.momentos import montar_momentos, picos_de_energia
from core.modelos.rosto import aplicar_enfases, instante_no_final, quadro_em, suavizar
from core.modelos.versiculo import detectar_versiculos


def test_rosto_segura_o_ultimo_quadro_e_afina():
    quadros = suavizar([(0.0, 0.2, 0.3), (1.0, 0.21, 0.3), (2.0, 0.8, 0.4)])
    assert len(quadros) == 2
    assert quadro_em(quadros, 1.5)["x"] == quadros[0]["x"]
    assert quadro_em(quadros, 2.0)["x"] == quadros[1]["x"]


def test_zoom_so_no_pico():
    quadros = aplicar_enfases([{"t": 1.0, "x": 0.5, "y": 0.5, "zoom": 1.0},
                               {"t": 5.0, "x": 0.5, "y": 0.5, "zoom": 1.0}], [(4.5, 6.0)])
    assert quadros[0]["zoom"] == 1.0
    assert quadros[1]["zoom"] == 1.25


def test_instante_cortado_nao_entra_no_video_final():
    assert instante_no_final([(0.0, 10.0)], [[(0.0, 2.0), (4.0, 6.0)]], 5.0) == 3.0
    assert instante_no_final([(0.0, 10.0)], [[(0.0, 2.0), (4.0, 6.0)]], 3.0) is None


def test_versiculo_dito_entra_e_o_incompleto_nao():
    palavras = [
        {"texto": "João", "inicio": 1.0, "fim": 1.3},
        {"texto": "três", "inicio": 1.3, "fim": 1.6},
        {"texto": "dezesseis", "inicio": 1.6, "fim": 2.2},
        {"texto": "Salmos", "inicio": 8.0, "fim": 8.4},
    ]
    achados = detectar_versiculos(palavras)
    assert len(achados) == 1
    assert achados[0]["referencia"] == "João 3:16"
    assert "João" in achados[0]["citacao"]


def test_pico_de_energia_junta_vizinhos():
    niveis = [-40] * 500 + [-8] * 400 + [-40] * 500
    picos = picos_de_energia(niveis)
    assert picos
    assert picos[0][0] >= 4
    momentos = montar_momentos(picos, [picos[0][0] + 0.2], {picos[0][0] + 0.2: {"assunto": "pregador", "nota": 8}})
    assert momentos[0]["assunto"] == "pregador"
    assert montar_momentos(picos, [], {0.0: {"assunto": "inventado", "nota": 9}})[0].get("assunto") is None
