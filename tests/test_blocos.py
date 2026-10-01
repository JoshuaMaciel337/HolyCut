# Blocos do culto: música e fala pelo áudio e pelas palavras, os nomes e a pregação principal
import numpy as np
import pytest

from core.modelos.blocos import (
    classificar_janelas,
    conferir_pregacao,
    janelas_do_audio,
    montar_blocos,
    nome_pelas_palavras,
    palavras_da_pregacao,
    partes_da_fala,
    pregacao_principal,
    suavizar,
    texto_do_bloco,
    trechos_do_culto,
)

LOUVOR = "Santo santo santo é o Senhor digno de louvor"
AVISOS = "Os avisos desta semana a agenda do retiro e as inscrições estão abertas na secretaria"
OFERTA = "Agora é o momento da oferta e do dízimo pelo pix ou pelo envelope"
PREGACAO = "A graça de Deus nos alcança e transforma a nossa vida inteira"
DURACAO = 1500.0


def falar(inicio: float, fim: float, texto: str, passo: float = 0.5, duracao: float = 0.25) -> list[dict]:
    """Palavras seguidas, repetindo o texto, uma a cada passo."""
    base = texto.split()
    palavras, instante, indice = [], inicio, 0
    while instante < fim:
        palavras.append({"texto": base[indice % len(base)], "inicio": round(instante, 2),
                         "fim": round(instante + duracao, 2)})
        instante += passo
        indice += 1
    return palavras


def palavras_do_culto() -> list[dict]:
    """Louvor 0-5 min, avisos e oferta 5-9 min (com uma pausa entre eles), louvor 9-12 min e pregação."""
    return (falar(0, 300, LOUVOR, passo=2.0, duracao=0.8)
            + falar(300, 418, AVISOS)
            + falar(422, 540, OFERTA)
            + falar(540, 720, LOUVOR, passo=2.0, duracao=0.8)
            + falar(725, 1490, PREGACAO))


def niveis_do_culto() -> np.ndarray:
    """10 ms por valor. A música soa contínua; a fala cai 30 dB entre as sílabas."""
    niveis = np.full(int(DURACAO * 100), -10, dtype=np.int8)
    fala = np.array([-15] * 25 + [-45] * 10, dtype=np.int8)
    for inicio, fim in ((300, 540), (720, 1500)):
        trecho = np.resize(fala, (fim - inicio) * 100)
        niveis[inicio * 100:fim * 100] = trecho
    return niveis


def test_audio_separa_musica_continua_da_fala_com_pausas():
    janelas = janelas_do_audio(niveis_do_culto())
    assert len(janelas) == 150
    assert janelas[0] == {"ativo": True, "quedas": 0.0}
    assert janelas[40]["quedas"] == pytest.approx(10 / 35, abs=0.01)
    silencio = janelas_do_audio(np.full(1000, -70, dtype=np.int8))
    assert silencio[0]["ativo"] is False


def test_janelas_e_suavizacao():
    rotulos = classificar_janelas(DURACAO, janelas_do_audio(niveis_do_culto()), palavras_do_culto())
    assert rotulos[0] == "musica" and rotulos[35] == "fala" and rotulos[100] == "fala"
    # Uma janela fora do lugar não parte o bloco, e a indefinida segue o vizinho
    assert suavizar(["fala", "fala", "musica", "fala", "fala"]) == ["fala"] * 5
    assert suavizar(["musica", "musica", "indefinido", "indefinido", "indefinido", "indefinido", "indefinido"]) == \
        ["musica"] * 7


@pytest.mark.parametrize("com_audio", [True, False])
def test_trechos_do_culto(com_audio):
    audio = janelas_do_audio(niveis_do_culto()) if com_audio else []
    # Sem o niveis.bin, a palavra cantada (esticada e espaçada) ainda separa o louvor
    assert trechos_do_culto(DURACAO, audio, palavras_do_culto()) == [
        (0.0, 300.0, "musica"), (300.0, 540.0, "fala"), (540.0, 720.0, "musica"), (720.0, 1500.0, "fala"),
    ]


def test_fala_se_divide_na_pausa_longa():
    palavras = palavras_do_culto()
    # O corte fica no meio da pausa: a última palavra dos avisos acaba em 417,75 s e a oferta começa em 422 s
    assert partes_da_fala(300.0, 540.0, palavras) == [(300.0, 419.88), (419.88, 540.0)]
    # Uma pausa que deixaria uma parte com menos de 1,5 min não separa nada
    curta = falar(0, 60, AVISOS) + falar(64, 300, PREGACAO)
    assert partes_da_fala(0.0, 300.0, curta) == [(0.0, 300.0)]


def test_nomes_pelas_palavras_chave():
    palavras = palavras_do_culto()
    assert nome_pelas_palavras([p for p in palavras if 300 <= p["inicio"] < 420], 120) == "avisos"
    assert nome_pelas_palavras([p for p in palavras if 420 <= p["inicio"] < 540], 120) == "oferta"
    assert nome_pelas_palavras(falar(0, 60, PREGACAO), 600) == "pregacao"   # 10 min seguidos de fala
    assert nome_pelas_palavras(falar(0, 60, "Que bom ter vocês aqui hoje conosco"), 120) == "outro"


def test_blocos_e_pregacao_principal():
    palavras = palavras_do_culto()
    trechos = trechos_do_culto(DURACAO, janelas_do_audio(niveis_do_culto()), palavras)
    partes = [parte for inicio, fim, rotulo in trechos if rotulo == "fala"
              for parte in partes_da_fala(inicio, fim, palavras)]
    nomes = [nome_pelas_palavras([p for p in palavras if a <= p["inicio"] < b], b - a) for a, b in partes]
    blocos = montar_blocos(trechos, partes, nomes, palavras)
    assert [(b["inicio"], b["fim"], b["tipo"]) for b in blocos] == [
        (0.0, 300.0, "louvor"), (300.0, 419.88, "avisos"), (419.88, 540.0, "oferta"),
        (540.0, 720.0, "louvor"), (720.0, 1500.0, "pregacao"),
    ]
    assert blocos[1]["frase"].startswith("Os avisos desta semana")
    # Do começo da primeira palavra ao fim da última, com folga, dentro do bloco
    assert pregacao_principal(blocos, palavras) == {"inicio": 724.5, "fim": 1490.75}


def test_parte_curta_entre_dois_blocos_iguais():
    palavras = falar(0, 60, "Que bom ter vocês aqui")
    trechos = [(0.0, 300.0, "musica"), (300.0, 400.0, "fala"), (400.0, 700.0, "musica")]
    # A fala solta do ministro entre duas músicas é louvor
    assert [b["tipo"] for b in montar_blocos(trechos, [(300.0, 400.0)], ["outro"], palavras)] == ["louvor"]
    # A oferta entre duas músicas fica com o próprio nome
    assert [b["tipo"] for b in montar_blocos(trechos, [(300.0, 400.0)], ["oferta"], palavras)] == \
        ["louvor", "oferta", "louvor"]
    # A oração no meio da pregação continua pregação
    trechos = [(0.0, 900.0, "fala")]
    partes = [(0.0, 400.0), (400.0, 520.0), (520.0, 900.0)]
    blocos = montar_blocos(trechos, partes, ["pregacao", "oracao", "pregacao"], palavras)
    assert [(b["inicio"], b["fim"], b["tipo"]) for b in blocos] == [(0.0, 900.0, "pregacao")]


def test_sem_pregacao_nomeada_vale_a_fala_mais_longa():
    blocos = [{"inicio": 0.0, "fim": 700.0, "tipo": "louvor"}, {"inicio": 700.0, "fim": 1400.0, "tipo": "outro"},
              {"inicio": 1400.0, "fim": 1500.0, "tipo": "avisos"}]
    assert pregacao_principal(blocos, []) == {"inicio": 700.0, "fim": 1400.0}
    curtos = [{"inicio": 0.0, "fim": 300.0, "tipo": "outro"}]
    assert pregacao_principal(curtos, []) is None


def test_marcacao_da_pessoa_e_palavras_da_pregacao():
    assert conferir_pregacao(-3, 5000, 1500) == {"inicio": 0.0, "fim": 1500.0}
    with pytest.raises(ValueError, match="30 segundos"):
        conferir_pregacao(100, 120, 1500)
    with pytest.raises(ValueError):
        conferir_pregacao(1490, 1600, 1500)   # cortado no fim da gravação, sobram 10 s
    palavras = palavras_do_culto()
    so_a_mensagem = palavras_da_pregacao(palavras, {"inicio": 720, "fim": 1500})
    assert so_a_mensagem[0]["inicio"] == 725 and len(so_a_mensagem) < len(palavras)
    assert palavras_da_pregacao(palavras, None) is palavras
    assert palavras_da_pregacao(palavras, {"inicio": 0, "fim": 5}) is palavras   # quase nada dentro: fica tudo


def test_texto_para_o_modelo_tem_a_posicao_no_culto():
    texto = texto_do_bloco(palavras_do_culto(), 300.0, 420.0, 3900.0)
    assert texto.startswith("Começa em 5 min de um culto de 1h05 e dura 2 min.")
    assert "Começo: Os avisos desta semana" in texto and "Fim:" in texto
