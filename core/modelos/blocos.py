# -----------------------------------------------
# HolyCut — os blocos do culto: louvor, oração, avisos, oferta, ceia e pregação
#
# As fronteiras saem do áudio e das palavras ditas, não do modelo:
#   - o culto é lido em janelas de 10 s. A janela é fala quando as palavras
#     vêm densas e curtas; é música quando a palavra se estica (cantada)
#     ou quando o áudio soa contínuo, sem as pausas que a fala tem;
#   - a fala se divide nas pausas longas, e cada pedaço ganha um nome:
#     primeiro pelas palavras-chave e pela duração, depois pelo modelo,
#     que só escolhe numa lista fechada.
# A pregação principal é o bloco de pregação mais longo, com o começo e o
# fim presos às palavras ditas. A marcação da pessoa nunca é trocada pela IA.
# Os limiares são o ponto de partida: calibrar com cultos reais no Nitro.
# Funções puras: montam e conferem, sem acessar o banco.
# -----------------------------------------------
import math
from collections import Counter

import numpy as np

from core.modelos.sermon import token

TIPOS_BLOCO = {
    "louvor": "Louvor",
    "oracao": "Oração",
    "avisos": "Avisos",
    "oferta": "Oferta",
    "ceia": "Santa Ceia",
    "pregacao": "Pregação",
    "outro": "Outro",
}
TIPOS_FALADOS = ("oracao", "avisos", "oferta", "ceia", "pregacao", "outro")

JANELA = 10.0                 # segundos por janela de análise
NIVEL_ATIVO_DB = -40          # abaixo disso a janela inteira é silêncio
QUEDA_DB = 12                 # quanto o áudio cai abaixo do pico da janela numa pausa da fala
QUEDAS_MUSICA = 0.12          # a música soa contínua: menos de 12% da janela em queda
DENSIDADE_FALA = 1.3          # palavras por segundo
PALAVRA_CANTADA = 0.45        # segundos: cantada, a palavra se estica
VIZINHANCA = 2                # janelas de cada lado na suavização (50 s ao todo)
BLOCO_MINIMO = 60.0           # trecho de música, fala ou silêncio mais curto que isso some no vizinho
PAUSA_DE_TROCA = 3.0          # segundos sem palavra que podem separar duas partes faladas
PARTE_MINIMA = 90.0           # parte falada mais curta que isso junta com a anterior
PARTE_LONGA = 480.0           # 8 min seguidos de fala, pelas palavras-chave, já é pregação
SANDUICHE_MAXIMO = 180.0      # parte curta entre duas do mesmo tipo vira desse tipo
PREGACAO_MINIMA = 600.0       # sem bloco chamado pregação, a fala mais longa vira, se tiver 10 min
FOLGA_INICIO = 0.5
FOLGA_FIM = 1.0
PREGACAO_MANUAL_MINIMA = 30.0
PALAVRAS_DA_FRASE = 14
PISTA_MINIMA = 0.01           # 1 palavra-chave a cada 100 palavras

# Palavras que denunciam o tipo de uma parte falada, sem acento e em minúsculas
PISTAS = {
    "oferta": {"oferta", "ofertas", "ofertar", "ofertando", "dizimo", "dizimos", "dizimar", "dizimista",
               "contribuir", "contribuicao", "semear", "semeadura", "pix", "envelope", "envelopes", "generosidade",
               "maquininha", "cartao"},
    "avisos": {"aviso", "avisos", "agenda", "programacao", "inscricao", "inscricoes", "inscreva", "evento", "eventos",
               "retiro", "acampamento", "congresso", "conferencia", "encontro", "secretaria", "recado", "recados",
               "horario", "horarios"},
    "ceia": {"ceia", "calice", "pao", "partiu", "memoria", "elementos"},
    "oracao": {"oremos", "orar", "oracao", "oramos", "amem", "senhor", "pai", "clamamos", "abencoa", "abencoe",
               "agradecemos", "obrigado", "intercedemos", "santo", "gloria"},
}


# -----------------------------------------------
# MÚSICA OU FALA, JANELA POR JANELA
# -----------------------------------------------
def janelas_do_audio(niveis, por_segundo: int = 100, janela: float = JANELA) -> list[dict]:
    """Para cada janela: se há som e quanto dela cai bem abaixo do pico (as pausas da fala)."""
    niveis = np.asarray(niveis, dtype=np.int16)
    tamanho = max(int(por_segundo * janela), 1)
    resultado = []
    for comeco in range(0, len(niveis), tamanho):
        trecho = niveis[comeco:comeco + tamanho]
        topo = float(np.percentile(trecho, 90))
        resultado.append({"ativo": topo > NIVEL_ATIVO_DB, "quedas": float(np.mean(trecho < topo - QUEDA_DB))})
    return resultado


def _rotulo(audio: dict | None, densidade: float, duracao_media: float) -> str:
    if densidade >= DENSIDADE_FALA and duracao_media < PALAVRA_CANTADA:
        return "fala"
    if densidade > 0 and duracao_media >= PALAVRA_CANTADA:
        return "musica"
    if audio is None:
        return "fala" if densidade > 0 else "indefinido"
    if not audio["ativo"]:
        return "fala" if densidade > 0 else "silencio"
    if audio["quedas"] < QUEDAS_MUSICA:
        return "musica"
    return "fala" if densidade > 0 else "indefinido"


def classificar_janelas(duracao: float, audio: list[dict], palavras: list[dict], janela: float = JANELA) -> list[str]:
    """Um rótulo por janela: fala, musica, silencio ou indefinido (som com pausas e sem palavra)."""
    total = max(math.ceil(duracao / janela), 1)
    contagem, soma = [0] * total, [0.0] * total
    for palavra in palavras:
        indice = int(palavra["inicio"] // janela)
        if 0 <= indice < total:
            contagem[indice] += 1
            soma[indice] += min(palavra["fim"] - palavra["inicio"], 2.0)
    return [
        _rotulo(audio[indice] if indice < len(audio) else None, contagem[indice] / janela,
                soma[indice] / contagem[indice] if contagem[indice] else 0.0)
        for indice in range(total)
    ]


def suavizar(rotulos: list[str], vizinhanca: int = VIZINHANCA) -> list[str]:
    """Voto da vizinhança, para uma janela fora do lugar não partir um bloco. Indefinido segue o vizinho."""
    suaves = []
    for indice, rotulo in enumerate(rotulos):
        perto = rotulos[max(indice - vizinhanca, 0):indice + vizinhanca + 1]
        vizinhos = [item for item in perto if item != "indefinido"]
        if not vizinhos:
            suaves.append(rotulo)
            continue
        contagem = Counter(vizinhos)
        mais_comum, vezes = contagem.most_common(1)[0]
        suaves.append(mais_comum if vezes > contagem.get(rotulo, 0) else rotulo)
    for indice, rotulo in enumerate(suaves):
        if rotulo == "indefinido":
            anterior = next((item for item in reversed(suaves[:indice]) if item != "indefinido"), None)
            seguinte = next((item for item in suaves[indice + 1:] if item != "indefinido"), None)
            suaves[indice] = anterior or seguinte or "musica"
    return suaves


def _absorver_curtos(trechos: list[list], minimo: float) -> list[list]:
    """O trecho curto some no vizinho mais longo, até todos terem o mínimo (ou sobrar um só)."""
    trechos = [list(item) for item in trechos]
    while len(trechos) > 1:
        curtos = [indice for indice, (inicio, fim, _) in enumerate(trechos) if fim - inicio < minimo]
        if not curtos:
            break
        indice = min(curtos, key=lambda posicao: trechos[posicao][1] - trechos[posicao][0])
        antes = trechos[indice - 1] if indice > 0 else None
        depois = trechos[indice + 1] if indice + 1 < len(trechos) else None
        if antes and (not depois or antes[1] - antes[0] >= depois[1] - depois[0]):
            antes[1] = trechos[indice][1]
        else:
            depois[0] = trechos[indice][0]
        del trechos[indice]
        trechos = _juntar_iguais(trechos)
    return trechos


def _juntar_iguais(trechos: list[list]) -> list[list]:
    juntos: list[list] = []
    for trecho in trechos:
        if juntos and juntos[-1][2] == trecho[2]:
            juntos[-1][1] = trecho[1]
        else:
            juntos.append(list(trecho))
    return juntos


def trechos_do_culto(duracao: float, audio: list[dict], palavras: list[dict],
                     janela: float = JANELA) -> list[tuple[float, float, str]]:
    """O culto inteiro em trechos seguidos de musica, fala ou silencio, cada um com pelo menos 1 min."""
    if duracao <= 0:
        return []
    rotulos = suavizar(classificar_janelas(duracao, audio, palavras, janela))
    trechos = _juntar_iguais([[indice * janela, min((indice + 1) * janela, duracao), rotulo]
                              for indice, rotulo in enumerate(rotulos)])
    return [(round(inicio, 2), round(fim, 2), rotulo)
            for inicio, fim, rotulo in _absorver_curtos(trechos, BLOCO_MINIMO)]


# -----------------------------------------------
# A FALA EM PARTES, CADA UMA COM UM NOME
# -----------------------------------------------
def partes_da_fala(inicio: float, fim: float, palavras: list[dict]) -> list[tuple[float, float]]:
    """Divide um trecho falado nas pausas longas. Parte curta demais junta com a vizinha."""
    dentro = [palavra for palavra in palavras if inicio <= palavra["inicio"] < fim]
    cortes = [round((anterior["fim"] + atual["inicio"]) / 2, 2)
              for anterior, atual in zip(dentro, dentro[1:], strict=False)
              if atual["inicio"] - anterior["fim"] >= PAUSA_DE_TROCA]
    limites = [inicio, *cortes, fim]
    partes = [[limites[indice], limites[indice + 1], "fala"] for indice in range(len(limites) - 1)]
    return [(round(comeco, 2), round(final, 2)) for comeco, final, _ in _absorver_curtos(partes, PARTE_MINIMA)]


def palavras_entre(palavras: list[dict], inicio: float, fim: float) -> list[dict]:
    return [palavra for palavra in palavras if inicio <= palavra["inicio"] < fim]


def nome_pelas_palavras(palavras: list[dict], duracao: float) -> str:
    """O nome sem o modelo: fala longa é pregação; a curta vai pela palavra-chave mais frequente."""
    if duracao >= PARTE_LONGA:
        return "pregacao"
    tokens = [token(palavra["texto"]) for palavra in palavras]
    total = max(len(tokens), 1)
    pontos = {tipo: sum(1 for item in tokens if item in pistas) / total for tipo, pistas in PISTAS.items()}
    tipo, valor = max(pontos.items(), key=lambda par: par[1])
    return tipo if valor >= PISTA_MINIMA else "outro"


def _engolido(meio: str, volta: str) -> bool:
    return meio == "outro" or volta == "pregacao" or (meio == "oracao" and volta == "louvor")


def _frase_inicial(palavras: list[dict]) -> str:
    return " ".join(palavra["texto"] for palavra in palavras[:PALAVRAS_DA_FRASE])


def montar_blocos(trechos: list[tuple[float, float, str]], partes: list[tuple[float, float]],
                  nomes: list[str], palavras: list[dict]) -> list[dict]:
    """
    Junta a música (louvor), as partes faladas já com nome e os silêncios longos (outro).
    Uma parte curta entre duas do mesmo tipo pode virar desse tipo: a fala solta do
    ministro e a oração entre duas músicas são louvor; o que está no meio da pregação
    continua pregação. Avisos, oferta e ceia entre duas músicas ficam com o próprio nome.
    """
    brutos = []
    nomes_por_parte = dict(zip(partes, nomes, strict=True))
    for inicio, fim, rotulo in trechos:
        if rotulo == "fala":
            brutos += [[comeco, final, nomes_por_parte.get((comeco, final), "outro")]
                       for comeco, final in partes if inicio <= comeco < fim]
        else:
            brutos.append([inicio, fim, "louvor" if rotulo == "musica" else "outro"])
    brutos.sort(key=lambda item: item[0])
    for indice in range(1, len(brutos) - 1):
        inicio, fim, meio = brutos[indice]
        volta = brutos[indice - 1][2]
        if fim - inicio <= SANDUICHE_MAXIMO and volta == brutos[indice + 1][2] and _engolido(meio, volta):
            brutos[indice][2] = volta
    return [
        {"inicio": round(inicio, 2), "fim": round(fim, 2), "tipo": tipo,
         "frase": _frase_inicial(palavras_entre(palavras, inicio, fim))}
        for inicio, fim, tipo in _juntar_iguais(brutos)
    ]


def pregacao_principal(blocos: list[dict], palavras: list[dict]) -> dict | None:
    """O bloco de pregação mais longo, do começo da primeira palavra ao fim da última, com folga."""
    candidatos = [bloco for bloco in blocos if bloco["tipo"] == "pregacao"]
    if not candidatos:
        candidatos = [bloco for bloco in blocos if bloco["tipo"] != "louvor"
                      and bloco["fim"] - bloco["inicio"] >= PREGACAO_MINIMA]
    if not candidatos:
        return None
    bloco = max(candidatos, key=lambda item: item["fim"] - item["inicio"])
    ditas = palavras_entre(palavras, bloco["inicio"], bloco["fim"])
    if not ditas:
        return {"inicio": bloco["inicio"], "fim": bloco["fim"]}
    return {"inicio": round(max(bloco["inicio"], ditas[0]["inicio"] - FOLGA_INICIO), 2),
            "fim": round(min(bloco["fim"], ditas[-1]["fim"] + FOLGA_FIM), 2)}


def conferir_pregacao(inicio: float, fim: float, duracao: float) -> dict:
    """A marcação feita pela pessoa. Recusa o que não cabe na gravação."""
    inicio, fim = round(max(float(inicio), 0.0), 2), round(min(float(fim), float(duracao)), 2)
    if fim - inicio < PREGACAO_MANUAL_MINIMA:
        raise ValueError("A pregação precisa ter pelo menos 30 segundos, dentro da gravação.")
    return {"inicio": inicio, "fim": fim}


def palavras_da_pregacao(palavras: list[dict], pregacao: dict | None, minimo: int = 200) -> list[dict]:
    """Só o que foi dito na pregação marcada. Se quase nada cair dentro, fica a fala inteira."""
    if not pregacao:
        return palavras
    dentro = palavras_entre(palavras, float(pregacao["inicio"]), float(pregacao["fim"]))
    return dentro if len(dentro) >= minimo else palavras


# -----------------------------------------------
# O MODELO SÓ ESCOLHE O NOME, NUMA LISTA FECHADA
# -----------------------------------------------
ESQUEMA_BLOCO = {
    "type": "object",
    "properties": {"tipo": {"type": "string", "enum": list(TIPOS_FALADOS)}},
    "required": ["tipo"],
}


def prompt_do_bloco() -> str:
    return (
        "Você classifica um trecho falado de um culto evangélico. Responda só o tipo, uma destas opções: "
        "oracao (alguém ora a Deus), avisos (agenda, eventos e recados da igreja), "
        "oferta (dízimos, ofertas e contribuição), ceia (Santa Ceia), "
        "pregacao (a mensagem bíblica, em geral longa), "
        "outro (boas-vindas, testemunho, apresentação ou qualquer outra coisa). "
        "Se não tiver certeza, responda outro."
    )


def _minutos(segundos: float) -> str:
    total = int(segundos // 60)
    return f"{total // 60}h{total % 60:02d}" if total >= 60 else f"{total} min"


def texto_do_bloco(palavras: list[dict], inicio: float, fim: float, duracao_culto: float) -> str:
    """O começo e o fim da parte, com a posição dela no culto. A fala vai sem correção."""
    ditas = palavras_entre(palavras, inicio, fim)
    comeco = " ".join(palavra["texto"] for palavra in ditas[:120])
    final = " ".join(palavra["texto"] for palavra in ditas[120:][-60:])
    linhas = [f"Começa em {_minutos(inicio)} de um culto de {_minutos(duracao_culto)} e dura {_minutos(fim - inicio)}.",
              f"Começo: {comeco}"]
    if final:
        linhas.append(f"Fim: {final}")
    return "\n".join(linhas)
