# Legendas: o tempo das palavras no vídeo final e o ASS que o render queima
from core.modelos.legenda import (
    COR_DOURADA,
    cor_ass,
    gerar_ass,
    legenda_do_projeto,
    montar_blocos,
    palavras_da_transcricao,
)
from core.modelos.projeto import montar_exportacao, montar_projeto
from core.utils.render import PASTA_FONTES_LEGENDA, montar_filtro

MIDIA = {"_id": "m1", "nome": "Culto", "duracao": 30.0}
RECORTE = {"x": 0, "y": 0, "largura": 1080, "altura": 1920}


def _palavras(*tempos):
    return [
        {"id": f"w{i}", "texto": texto, "inicio": inicio, "fim": fim}
        for i, (texto, inicio, fim) in enumerate(tempos)
    ]


def test_projeto_antigo_sem_legenda_usa_o_padrao():
    assert legenda_do_projeto({})["preset"] == "destaque"
    assert legenda_do_projeto({})["vicios"] is None
    assert legenda_do_projeto({})["apagadas"] == []
    ajustada = legenda_do_projeto({"legenda": {"ativa": False, "preset": "inexistente", "posicao": "lado"}})
    assert ajustada["ativa"] is False
    assert ajustada["preset"] == "destaque"
    assert ajustada["posicao"] == "base"


def test_projeto_novo_guarda_a_legenda_na_exportacao():
    projeto = {**montar_projeto("org1", MIDIA, "u1"), "_id": "p1"}
    assert projeto["legenda"]["preset"] == "destaque"
    assert montar_exportacao(projeto, "u1")["configuracao"]["legenda"]["ativa"] is True


def test_palavra_no_silencio_sai_e_o_tempo_anda():
    palavras = _palavras(("antes", 0.4, 0.8), ("corte", 2.4, 2.8), ("depois", 5.0, 5.4))
    partes = [{"id": "p1", "inicio": 0.0, "fim": 8.0}]
    blocos = montar_blocos(palavras, partes, [(2.0, 4.0)], 3)
    textos = [palavra["texto"] for bloco in blocos for palavra in bloco["palavras"]]
    assert textos == ["antes", "depois"]
    depois = blocos[-1]["palavras"][-1]
    assert depois["inicio"] < 5.0


def test_parte_repetida_repete_a_palavra():
    palavras = _palavras(("paz", 0.2, 0.8))
    partes = [{"id": "a", "inicio": 0.0, "fim": 2.0}, {"id": "b", "inicio": 0.0, "fim": 2.0}]
    blocos = montar_blocos(palavras, partes, [], 3)
    ditas = [palavra for bloco in blocos for palavra in bloco["palavras"] if palavra["texto"] == "paz"]
    assert len(ditas) == 2
    assert ditas[1]["inicio"] > ditas[0]["fim"]


def test_pausa_e_quantidade_abrem_bloco_novo():
    seguidas = _palavras(*[(f"p{i}", i * 0.3, i * 0.3 + 0.2) for i in range(5)])
    blocos = montar_blocos(seguidas, [{"inicio": 0.0, "fim": 10.0}], [], 3)
    assert [len(bloco["palavras"]) for bloco in blocos] == [3, 2]

    com_pausa = _palavras(("oi", 0.1, 0.4), ("tarde", 2.0, 2.5))
    separados = montar_blocos(com_pausa, [{"inicio": 0.0, "fim": 10.0}], [], 3)
    assert len(separados) == 2


def test_destaque_e_a_palavra_mais_longa():
    palavras = _palavras(("A", 0.1, 0.3), ("paz", 0.3, 0.6), ("Deus", 0.6, 1.0))
    bloco = montar_blocos(palavras, [{"inicio": 0.0, "fim": 5.0}], [], 3)[0]
    assert [palavra["texto"] for palavra in bloco["palavras"] if palavra["destaque"]] == ["Deus"]


def test_transcricao_ignora_palavra_sem_tempo():
    doc = {"segmentos": [{"palavras": [
        {"id": "w1", "texto": "paz", "inicio": 0.1, "fim": 0.4},
        {"id": "w2", "texto": " ", "inicio": 0.4, "fim": 0.5},
        {"texto": "sem tempo"},
    ]}]}
    assert [palavra["texto"] for palavra in palavras_da_transcricao(doc)] == ["paz"]
    assert palavras_da_transcricao(None) == []


def test_ass_digno_karaoke_e_clean():
    palavras = _palavras(("A", 0.0, 0.3), ("paz", 0.3, 0.8))
    blocos = montar_blocos(palavras, [{"inicio": 0.0, "fim": 2.0}], [], 3)
    digno = gerar_ass(blocos, "digno", "#FF8A00", 1080, 1920, "base")
    assert "Caveat" in digno
    assert cor_ass(COR_DOURADA) in digno
    assert "PlayResY: 1920" in digno
    assert digno.count("Dialogue:") == 1

    karaoke = gerar_ass(blocos, "karaoke", "#FF8A00", 1080, 1920, "centro")
    assert karaoke.count("Dialogue:") == 2
    assert cor_ass("#FF8A00") in karaoke
    estilo = next(linha for linha in karaoke.splitlines() if linha.startswith("Style:"))
    assert estilo.endswith("0,5,80,80,0,1")   # alinhamento central, sem margem de baixo

    clean = gerar_ass(blocos, "clean", "#FF8A00", 1080, 1920)
    assert "\\c" not in clean
    assert "A paz" in clean
    assert gerar_ass([], "clean", "#FF8A00", 1080, 1920) == ""


def test_filtro_queima_a_legenda_depois_do_video():
    filtro = montar_filtro([[(0.0, 2.0)]], RECORTE, 1080, 1920, tem_audio=True,
                           legenda="/dados/org/exportacoes/e1/legenda.ass")
    assert f"subtitles=/dados/org/exportacoes/e1/legenda.ass:fontsdir={PASTA_FONTES_LEGENDA}[v]" in filtro
    assert filtro.strip().endswith("[v]") or filtro.strip().endswith("[a]")
    assert "[vleg]subtitles=" in filtro
    sem = montar_filtro([[(0.0, 2.0)]], RECORTE, 1080, 1920, tem_audio=False)
    assert "subtitles=" not in sem
