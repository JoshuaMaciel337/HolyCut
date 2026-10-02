# Efeitos não mudam o filtro quando estão desligados, e o texto do post só fica se foi dito.
from core.modelos.efeitos import amplitude_tremor, ganho_brilho
from core.modelos.projeto import calcular_recorte, montar_projeto
from core.modelos.publicacao import textos_do_corte
from core.modelos.rosto import caixa_contorno
from core.utils.render import montar_filtro
from core.utils.sons import sintetizar


def test_sem_efeito_o_filtro_nao_muda():
    recorte = calcular_recorte(1920, 1080, "9:16")
    base = montar_filtro([[(0.0, 4.0)]], recorte, 1080, 1920, tem_audio=True)
    efeitos = {"brilho": 0, "tremor": 0, "transicao": "corte", "zoom": None, "som": {"id": "nenhum", "inicio": 0}}
    assert montar_filtro([[(0.0, 4.0)]], recorte, 1080, 1920, tem_audio=True, efeitos=efeitos) == base
    assert ganho_brilho(0) == 1
    assert amplitude_tremor(1080, 0) == 0


def test_brilho_tremor_zoom_e_transicao_entram_no_filtro():
    recorte = calcular_recorte(1920, 1080, "9:16")
    com = montar_filtro(
        [[(0.0, 2.0)], [(0.0, 2.0)]], recorte, 1080, 1920, tem_audio=True,
        efeitos={"brilho": 0.2, "tremor": 1, "transicao": "escurecer",
                 "zoom": {"inicio": 0.5, "fim": 1.5, "nivel": 1.2}, "som": {"id": "nenhum", "inicio": 0}},
        som={"entrada": 4, "inicio": 0.4},
    )
    assert "colorchannelmixer=rr=1.200:gg=1.200:bb=1.200" in com
    assert "sin(2*PI*7*t)" in com and "sin(2*PI*11*t)" in com
    assert "fade=t=out" in com and "fade=t=in" in com
    assert "enable='between(t,0.500,1.500)'" in com
    assert "adelay=400|400" in com


def test_projeto_novo_nasce_sem_efeito():
    projeto = montar_projeto("org1", {"_id": "m1", "nome": "Culto", "duracao": 30}, "u1")
    assert projeto["efeitos"]["transicao"] == "corte"
    assert projeto["efeitos"]["luz"] == 0
    assert projeto["efeitos"]["contorno"] is False
    assert projeto["efeitos"]["som"]["id"] == "nenhum"


def test_luz_fusao_desfoque_e_contorno_entram_no_filtro():
    recorte = calcular_recorte(1920, 1080, "9:16")
    partes = [[(0.0, 2.0)], [(0.0, 2.0)]]
    luz = montar_filtro(partes, recorte, 1080, 1920, tem_audio=True, efeitos={"luz": 0.4, "transicao": "corte"})
    assert "gblur=sigma=18" in luz
    assert "blend=all_mode=screen:all_opacity=0.40" in luz
    assert "xfade" not in luz

    desfoque = montar_filtro(partes, recorte, 1080, 1920, tem_audio=True, efeitos={"transicao": "desfoque"})
    assert "gblur=sigma=14" in desfoque
    assert "blend=all_expr='if(gt(gt(T,1.800),0),B,A)'" in desfoque
    assert "fade=t=in:st=0" not in desfoque
    assert "concat=n=2" in desfoque

    fusao = montar_filtro(partes, recorte, 1080, 1920, tem_audio=True, efeitos={"transicao": "fusao"})
    assert "gblur=sigma=14" in fusao and "fade=t=in" in fusao and "afade=t=in" in fusao

    base = montar_filtro([[(0.0, 4.0)]], recorte, 1080, 1920, tem_audio=True)
    sem_caixa = montar_filtro(
        [[(0.0, 4.0)]], recorte, 1080, 1920, tem_audio=True,
        efeitos={"luz": 0, "contorno": True, "transicao": "desfoque"},
    )
    assert sem_caixa == base
    com_caixa = montar_filtro(
        [[(0.0, 4.0)]], recorte, 1080, 1920, tem_audio=True,
        caixa_contorno=(100, 200, 300, 400),
        comandos_contorno=r"C:\dados\contorno.txt",
    )
    assert "drawbox=x=100:y=200:w=300:h=400:t=6:color=white@0.9" in com_caixa
    assert "sendcmd=filename=C\\:/dados/contorno.txt" in com_caixa


def test_contorno_fica_no_centro_quando_o_rosto_esta_no_centro():
    recorte = calcular_recorte(1920, 1080, "9:16", 0.5, 0.5, 1)
    x = (recorte["x"] + recorte["largura"] / 2) / 1920
    y = (recorte["y"] + recorte["altura"] / 2) / 1080
    esquerda, topo, largura, altura = caixa_contorno(x, y, recorte, 1080, 1920, 1920, 1080)
    assert abs(esquerda + largura / 2 - 540) <= 1
    assert abs(topo + altura / 2 - 960) <= 1
    assert largura % 2 == 0 and altura % 2 == 0


def test_som_sintetizado_e_wav():
    assert sintetizar("toque").startswith(b"RIFF")
    assert sintetizar("sopro").startswith(b"RIFF")


def test_titulo_do_corte_e_uma_frase_dita(monkeypatch):
    monkeypatch.setattr("core.modelos.publicacao.MODO_IA", "simulado")
    palavras = [{"texto": t, "inicio": i, "fim": i + 0.4} for i, t in enumerate("a luz entra pela janela".split())]
    textos = textos_do_corte(palavras)
    assert textos["titulo"] == "a luz entra pela janela"
    assert textos_do_corte([{"texto": "amém", "inicio": 0, "fim": 0.2}]) is None


def test_parafrase_do_modelo_e_descartada(monkeypatch):
    monkeypatch.setattr("core.modelos.publicacao.MODO_IA", "real")
    monkeypatch.setattr(
        "core.modelos.publicacao.completar_json",
        lambda *args, **kwargs: {
            "usar": True,
            "titulo": "uma frase inventada agora",
            "legenda_post": "outra",
            "hashtags": ["luz"],
        },
    )
    fala = "a luz entra pela janela da igreja"
    palavras = [{"texto": t, "inicio": i, "fim": i + 0.4} for i, t in enumerate(fala.split())]
    assert textos_do_corte(palavras) is None
