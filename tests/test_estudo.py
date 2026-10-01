# HolyStudy: o estudo só fica com o que o pregador disse (funções puras, sem modelo de verdade)
from core.modelos.estudo import (
    CONVITE_ORACAO,
    BuscaNaFala,
    estudo_vazio,
    montar_estudo,
    personagens_validos,
    temas_validos,
    versiculos_chave,
)

FALA = (
    "Irmãos, abram a Bíblia em Romanos doze. Não se conformem com este século, mas transformem-se pela "
    "renovação da vossa mente. Davi não venceu Golias com a força dele, venceu com a fé no Senhor. "
    "A graça de Deus nos alcança antes de nós sabermos orar. Esta semana, procure alguém que você "
    "precisa perdoar e dê o primeiro passo. A oração muda quem ora."
)


def palavras_da_fala(texto=FALA, passo=0.5):
    return [{"texto": palavra, "inicio": round(i * passo, 2), "fim": round(i * passo + 0.4, 2)}
            for i, palavra in enumerate(texto.split())]


def test_busca_ignora_acento_pontuacao_e_caixa():
    busca = BuscaNaFala(palavras_da_fala())
    achada = busca.frase("nao se conformem com este seculo mas transformem-se")
    assert achada["texto"] == "Não se conformem com este século, mas transformem-se"
    assert achada["inicio"] == 3.5 and achada["fim"] > achada["inicio"]   # "Não" é a 8ª palavra, a 0,5 s cada
    assert busca.frase("não se conformem com este mundo, mas transformem-se") is None   # o pregador disse "século"
    assert busca.frase("a oração muda") is None                                         # curta demais
    assert busca.foi_dita("GRAÇA") and not busca.foi_dita("misericórdia")


def test_temas_e_personagens_so_do_que_foi_dito():
    busca = BuscaNaFala(palavras_da_fala())
    assert temas_validos(["graça", "Renovação da mente", "misericórdia", "fé e obras", "", "x" * 3], busca) == [
        "Graça", "Renovação da mente"]                     # "misericórdia" e "obras" não foram ditas
    sugeridos = ["Davi", "Golias", "davi", "Moisés", "Pastor João", "Graça"]
    assert personagens_validos(sugeridos, busca) == ["Davi", "Golias"]   # Moisés não foi citado


def test_versiculos_chave_pelos_mais_citados():
    versiculos = [{"referencia": "João 3:16", "inicio": 50, "citacao": "João três dezesseis"},
                  {"referencia": "Romanos 12:2", "inicio": 10, "citacao": "Romanos doze dois"},
                  {"referencia": "Romanos 12:2", "inicio": 90, "citacao": "Romanos doze dois"}]
    chave = versiculos_chave(versiculos)
    assert [(item["referencia"], item["vezes"], item["inicio"]) for item in chave] == [
        ("Romanos 12:2", 2, 10), ("João 3:16", 1, 50)]


def test_montar_estudo_descarta_o_que_foi_inventado():
    palavras = palavras_da_fala()
    respostas = [
        {
            "frases_centrais": [
                {"frase": "Não se conformem com este século, mas transformem-se pela renovação da vossa mente",
                 "importancia": 9},
                # Inventada: o pregador não disse
                {"frase": "Deus quer que você seja próspero e feliz em tudo o que fizer", "importancia": 10},
            ],
            "temas": ["Renovação", "Prosperidade"],
            "personagens": ["Paulo"],                                     # não foi dito
            "perguntas": [
                {"pergunta": "O que significa não se conformar com este século hoje?",
                 "frase_base": "Não se conformem com este século, mas transformem-se"},
                # Sem base: o pregador não disse esta frase
                {"pergunta": "Como prosperar mais?", "frase_base": "Deus quer que você seja próspero e feliz"},
                # Não é pergunta (sem ponto de interrogação)
                {"pergunta": "Fale sobre a mente", "frase_base": "transformem-se pela renovação da vossa mente"},
            ],
            "aplicacoes": ["Esta semana, procure alguém que você precisa perdoar e dê o primeiro passo",
                           "Doe o dízimo para a igreja todo mês sem falta"],  # inventada
        },
        {
            "frases_centrais": [
                {"frase": "Davi não venceu Golias com a força dele, venceu com a fé no Senhor", "importancia": 7},
                {"frase": "Não se conformem com este século, mas transformem-se pela renovação da vossa mente",
                 "importancia": 8},  # repetida em outro pedaço
            ],
            "temas": ["fé", "Renovação"],
            "personagens": ["Davi", "Golias"],
            "perguntas": [{"pergunta": "Em que situação você confiou na própria força em vez de confiar em Deus?",
                           "frase_base": "Davi não venceu Golias com a força dele"}],
            "aplicacoes": [],
        },
        "resposta quebrada",
    ]
    versiculos = [{"referencia": "Romanos 12:2", "inicio": 2.5, "citacao": "Romanos doze"}]
    estudo = montar_estudo(respostas, palavras, versiculos)

    # Na ordem da pregação, sem a frase inventada e sem repetir a que veio de dois pedaços
    assert [frase["texto"][:13] for frase in estudo["resumo"]] == ["Não se confor", "Davi não venc"]
    assert all("próspero" not in frase["texto"] for frase in estudo["resumo"])
    assert estudo["temas"][0] == "Renovação" and "Prosperidade" not in estudo["temas"]
    assert estudo["personagens"] == ["Davi", "Golias"]
    assert [pergunta["pergunta"][:10] for pergunta in estudo["perguntas"]] == ["O que sign", "Em que sit"]
    assert estudo["perguntas"][0]["base"]["texto"].startswith("Não se conformem")
    assert [item["texto"][:10] for item in estudo["aplicacoes"]] == ["Esta seman"]
    assert estudo["versiculos_chave"][0]["referencia"] == "Romanos 12:2"
    assert estudo["oracao"] == CONVITE_ORACAO                      # a oração não é escrita pela IA
    assert not estudo_vazio(estudo)


def test_estudo_sem_nada_dito_fica_vazio():
    estudo = montar_estudo([{"frases_centrais": [{"frase": "uma frase que ninguém disse no culto", "importancia": 9}],
                             "temas": [], "personagens": [], "perguntas": [], "aplicacoes": []}],
                           palavras_da_fala(), [])
    assert estudo_vazio(estudo)
