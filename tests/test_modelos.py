# Modelos de Story, fundo e exportação em imagem: funções puras
import pytest

from core.modelos.modelos_story import MODELOS_PADRAO, aplicar_modelo, modelo_padrao, montar_modelo_da_igreja
from core.modelos.projeto import montar_exportacao, montar_projeto
from core.utils.arte import camada_texto
from core.utils.render import instante_na_gravacao, montar_filtro, montar_filtro_imagem

MIDIA = {"_id": "m1", "nome": "Culto de domingo", "duracao": 120.0}
IDENTIDADE = {"nome_exibicao": "Igreja Viva", "instagram": "@igrejaviva", "cor_destaque": "#7B61FF", "logo": True}


def test_tres_modelos_prontos():
    assert [m["id"] for m in MODELOS_PADRAO] == ["culto-de-hoje", "frase-da-pregacao", "versiculo"]
    assert modelo_padrao("nao-existe") is None
    copia = modelo_padrao("versiculo")
    copia["textos"][0]["texto"] = "mudou"
    assert modelo_padrao("versiculo")["textos"][0]["texto"] != "mudou"   # cópia, não o original


def test_aplicar_modelo_preenche_o_instagram_e_respeita_o_logo():
    visual = aplicar_modelo(modelo_padrao("culto-de-hoje"), IDENTIDADE)
    assert [t["texto"] for t in visual["textos"]] == ["Culto de hoje", "Domingo · 19h", "@igrejaviva"]
    assert visual["marca"]["logo"] is True
    assert visual["fundo"] == {"escurecer": 0.35, "desfoque": 0}

    sem_logo_nem_arroba = aplicar_modelo(modelo_padrao("culto-de-hoje"), {"instagram": "", "logo": False})
    assert sem_logo_nem_arroba["marca"]["logo"] is False
    assert len(sem_logo_nem_arroba["textos"]) == 2    # o texto só com {instagram} vazio sai


def test_projeto_story_a_partir_do_modelo():
    projeto = montar_projeto("org1", MIDIA, "u1", tipo="story", modelo=modelo_padrao("versiculo"),
                             identidade=IDENTIDADE, inicio=30.456)
    assert projeto["nome"] == "Story · Culto de domingo"
    assert projeto["tipo"] == "story"
    assert projeto["modelo_id"] == "versiculo"
    assert projeto["proporcao"] == "9:16"
    assert projeto["trecho"] == {"inicio": 30.46, "fim": 45.46}
    assert projeto["silencios"] == {"intensidade": None}
    assert projeto["fundo"] == {"escurecer": 0.45, "desfoque": 14}
    assert projeto["textos"][0]["referencia"] == "Filipenses 4:13"


def test_story_no_fim_da_gravacao_nao_passa_da_duracao():
    projeto = montar_projeto("org1", MIDIA, "u1", tipo="story", inicio=118.0)
    assert projeto["trecho"] == {"inicio": 118.0, "fim": 120.0}
    assert projeto["fundo"] == {"escurecer": 0.0, "desfoque": 0}
    with pytest.raises(ValueError):
        montar_projeto("org1", MIDIA, "u1", tipo="carrossel")


def test_reel_continua_igual():
    projeto = montar_projeto("org1", MIDIA, "u1", identidade=IDENTIDADE)
    assert projeto["tipo"] == "reel" and projeto["modelo_id"] is None
    assert projeto["trecho"] == {"inicio": 0.0, "fim": 120.0}
    assert projeto["silencios"] == {"intensidade": "media"}
    assert projeto["marca"]["logo"] is True


def test_modelo_da_igreja_guarda_o_visual_do_projeto():
    projeto = {**montar_projeto("org1", MIDIA, "u1", tipo="story", modelo=modelo_padrao("culto-de-hoje"),
                                identidade=IDENTIDADE), "_id": "p1"}
    modelo = montar_modelo_da_igreja("org1", projeto, "Nosso culto de domingo", "u1")
    assert modelo["nome"] == "Nosso culto de domingo"
    assert modelo["textos"][2]["texto"] == "@igrejaviva"
    projeto["textos"][0]["texto"] = "mudou depois"
    assert modelo["textos"][0]["texto"] == "Culto de hoje"


def test_exportacao_em_imagem():
    projeto = {**montar_projeto("org1", MIDIA, "u1"), "_id": "p1"}
    exportacao = montar_exportacao(projeto, "u1", formato="imagem", instante=12.5)
    assert (exportacao["formato"], exportacao["instante"]) == ("imagem", 12.5)
    assert exportacao["configuracao"]["fundo"] == {"escurecer": 0.0, "desfoque": 0}
    assert montar_exportacao(projeto, "u1")["formato"] == "video"
    with pytest.raises(ValueError):
        montar_exportacao(projeto, "u1", formato="gif")


# -----------------------------------------------
# RENDER
# -----------------------------------------------
RECORTE = {"x": 0, "y": 0, "largura": 1080, "altura": 1920}


def test_fundo_desfocado_e_escurecido_antes_das_camadas():
    filtro = montar_filtro([(0.0, 5.0)], RECORTE, 1080, 1920, tem_audio=False, camadas=[(0.0, 5.0)],
                           fundo={"escurecer": 0.45, "desfoque": 14})
    video = filtro.split(";\n")[0]
    assert video.endswith("scale=1080:1920:flags=lanczos,setsar=1,format=gbrp,gblur=sigma=14.0,"
                          "colorchannelmixer=rr=0.550:gg=0.550:bb=0.550[base0]")
    sem_fundo = montar_filtro([(0.0, 5.0)], RECORTE, 1080, 1920, tem_audio=False)
    assert "gblur" not in sem_fundo and "colorchannelmixer" not in sem_fundo and "gbrp" not in sem_fundo


def test_filtro_de_imagem():
    filtro = montar_filtro_imagem(RECORTE, 1080, 1920, quantidade_camadas=2, fundo={"escurecer": 0.3})
    linhas = filtro.split(";\n")
    assert linhas[0].startswith("[0:v]crop=1080:1920:0:0,scale=1080:1920")
    assert "select" not in filtro and "enable" not in filtro
    assert linhas[-1] == "[base1][2:v]overlay=0:0,format=yuv420p[v]"
    assert montar_filtro_imagem(RECORTE, 1080, 1920).endswith("setsar=1,format=yuv420p[v]")


def test_instante_do_video_final_na_gravacao():
    trechos = [(0.0, 2.0), (3.0, 6.0), (8.0, 10.0)]   # 2 + 3 + 2 = 7 s de vídeo final
    assert instante_na_gravacao(trechos, 0.5) == 0.5
    assert instante_na_gravacao(trechos, 2.5) == 3.5    # já no segundo trecho, depois do corte
    assert instante_na_gravacao(trechos, 6.0) == 9.0
    assert instante_na_gravacao(trechos, 99) == pytest.approx(10 - 1 / 30)


def test_tamanho_do_texto():
    normal = camada_texto(1080, 1920, "Ele é digno", "limpo", "centro").getchannel("A").getbbox()
    maior = camada_texto(1080, 1920, "Ele é digno", "limpo", "centro", escala=1.6).getchannel("A").getbbox()
    assert (maior[2] - maior[0]) > (normal[2] - normal[0]) * 1.4
