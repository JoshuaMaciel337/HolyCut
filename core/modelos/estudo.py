# -----------------------------------------------
# HolyCut — HolyStudy: o estudo da pregação, a partir da fala real
#
# O modelo de linguagem só propõe; o que fica é conferido contra a
# transcrição. Fiel ao que foi pregado (CLAUDE.md):
#   - o resumo são frases que o pregador disse, com o tempo de cada uma;
#   - tema e personagem só entram se a palavra aparece na fala;
#   - cada pergunta para o grupo precisa se apoiar numa frase dita;
#   - "para viver nesta semana" são frases de aplicação do próprio pastor;
#   - os versículos-chave vêm da detecção de referências ditas;
#   - a oração não é escrita pela IA: o guia só convida o grupo a orar.
# O que não passa na conferência é omitido, nunca reescrito.
# Funções puras: montam e conferem, sem acessar o banco.
# -----------------------------------------------
from collections import Counter

from core.modelos.sermon import token

MINIMO_PALAVRAS_FRASE = 6
MAXIMO_PALAVRAS_FRASE = 45
MAXIMO_FRASES_RESUMO = 6
MAXIMO_TEMAS = 6
MAXIMO_PERSONAGENS = 8
MAXIMO_VERSICULOS_CHAVE = 5
MAXIMO_PERGUNTAS = 5
MAXIMO_APLICACOES = 4
TAMANHO_PERGUNTA = (15, 220)
CONVITE_ORACAO = ("Encerrem o encontro orando juntos pelo que a mensagem pediu, "
                  "com as palavras do próprio grupo.")

# Nomes que podem aparecer como "personagens bíblicos" (grafia brasileira mais comum)
PERSONAGENS_BIBLICOS = (
    "Adão", "Eva", "Caim", "Abel", "Sete", "Enoque", "Noé", "Abraão", "Sara", "Agar", "Ismael", "Isaque", "Rebeca",
    "Esaú", "Jacó", "Raquel", "Lia", "José", "Judá", "Benjamim", "Moisés", "Arão", "Miriã", "Josué", "Calebe",
    "Raabe", "Débora", "Gideão", "Sansão", "Dalila", "Rute", "Noemi", "Boaz", "Ana", "Eli", "Samuel", "Saul",
    "Jônatas", "Davi", "Golias", "Bate-Seba", "Natã", "Absalão", "Salomão", "Elias", "Eliseu", "Jezabel", "Acabe",
    "Naamã", "Ezequias", "Josias", "Isaías", "Jeremias", "Ezequiel", "Daniel", "Sadraque", "Mesaque", "Abede-Nego",
    "Nabucodonosor", "Ester", "Mardoqueu", "Neemias", "Esdras", "Jó", "Jonas", "Oseias", "Joel", "Amós", "Miqueias",
    "Habacuque", "Ageu", "Zacarias", "Malaquias", "Maria", "Jesus", "Cristo", "João", "Pedro", "Simão", "André",
    "Tiago", "Filipe", "Bartolomeu", "Tomé", "Mateus", "Judas", "Marcos", "Lucas", "Paulo", "Saulo", "Barnabé",
    "Silas", "Timóteo", "Tito", "Filemom", "Onésimo", "Estêvão", "Lázaro", "Marta", "Nicodemos", "Zaqueu",
    "Bartimeu", "Pilatos", "Herodes", "Caifás", "Barrabás", "Cornélio", "Lídia", "Priscila", "Áquila", "Apolo",
    "Ananias", "Safira", "Isabel", "Simeão", "Melquisedeque", "Ló", "Labão", "Faraó", "Balaão", "Gamaliel",
)
_PERSONAGENS = {token(nome): nome for nome in PERSONAGENS_BIBLICOS}


# -----------------------------------------------
# CONFERÊNCIA CONTRA A TRANSCRIÇÃO
# -----------------------------------------------
class BuscaNaFala:
    """Acha uma frase na transcrição palavra por palavra (sem acento, pontuação e caixa)."""

    def __init__(self, palavras: list[dict]):
        self.palavras = palavras
        self.tokens = [token(palavra["texto"]) for palavra in palavras]
        self.conhecidos = {item for item in self.tokens if item}
        self._posicoes: dict[str, list[int]] = {}
        for indice, item in enumerate(self.tokens):
            if item:
                self._posicoes.setdefault(item, []).append(indice)

    def frase(self, texto: str, minimo: int = MINIMO_PALAVRAS_FRASE,
              maximo: int = MAXIMO_PALAVRAS_FRASE) -> dict | None:
        """A frase como foi dita, com início e fim, ou None se não foi dita assim."""
        alvo = [item for item in (token(pedaço) for pedaço in str(texto or "").split()) if item]
        if not minimo <= len(alvo) <= maximo:
            return None
        for inicio in self._posicoes.get(alvo[0], []):
            if self.tokens[inicio:inicio + len(alvo)] == alvo:
                trecho = self.palavras[inicio:inicio + len(alvo)]
                return {"texto": " ".join(palavra["texto"] for palavra in trecho),
                        "inicio": round(float(trecho[0]["inicio"]), 2), "fim": round(float(trecho[-1]["fim"]), 2)}
        return None

    def foi_dita(self, palavra: str) -> bool:
        return token(palavra) in self.conhecidos


def temas_validos(brutos, busca: BuscaNaFala) -> list[str]:
    """Temas de uma a três palavras; cada palavra com significado (4 letras ou mais) tem de aparecer na fala."""
    saida = []
    for bruto in brutos or []:
        tema = " ".join(str(bruto or "").split())
        palavras = tema.split()
        significativas = [palavra for palavra in palavras if len(token(palavra)) >= 4]
        if not 1 <= len(palavras) <= 3 or not significativas:
            continue
        if not all(busca.foi_dita(palavra) for palavra in significativas):
            continue
        tema = tema[:1].upper() + tema[1:]
        if tema.lower() not in (item.lower() for item in saida):
            saida.append(tema)
    return saida


def personagens_validos(brutos, busca: BuscaNaFala) -> list[str]:
    """Só nomes bíblicos conhecidos que o pregador falou."""
    saida = []
    for bruto in brutos or []:
        nome = _PERSONAGENS.get(token(str(bruto or "")))
        if nome and busca.foi_dita(nome) and nome not in saida:
            saida.append(nome)
    return saida


def versiculos_chave(versiculos: list[dict]) -> list[dict]:
    """As referências mais citadas, na ordem em que apareceram pela primeira vez no empate."""
    vezes = Counter(item["referencia"] for item in versiculos)
    primeira = {}
    for item in versiculos:
        primeira.setdefault(item["referencia"], item)
    ordem = sorted(primeira.values(), key=lambda item: (-vezes[item["referencia"]], item["inicio"]))
    return [{"referencia": item["referencia"], "inicio": item["inicio"], "citacao": item.get("citacao", ""),
             "vezes": vezes[item["referencia"]]} for item in ordem[:MAXIMO_VERSICULOS_CHAVE]]


def _pergunta_valida(bruta, busca: BuscaNaFala) -> dict | None:
    if not isinstance(bruta, dict):
        return None
    pergunta = " ".join(str(bruta.get("pergunta") or "").split())
    base = busca.frase(bruta.get("frase_base") or "")
    if base is None or not pergunta.endswith("?") or not TAMANHO_PERGUNTA[0] <= len(pergunta) <= TAMANHO_PERGUNTA[1]:
        return None
    return {"pergunta": pergunta, "base": base}


# -----------------------------------------------
# MONTAGEM DO ESTUDO
# -----------------------------------------------
def _sem_repetir(itens: list[dict]) -> list[dict]:
    vistos, saida = set(), []
    for item in itens:
        chave = token(item["texto"])
        if chave not in vistos:
            vistos.add(chave)
            saida.append(item)
    return saida


def montar_estudo(respostas: list[dict], palavras: list[dict], versiculos: list[dict]) -> dict:
    """
    Junta as respostas do modelo (uma por pedaço da pregação) num estudo só, conferido contra a fala.
    `versiculos` é a lista já detectada na transcrição.
    """
    busca = BuscaNaFala(palavras)
    centrais, temas, personagens, aplicacoes = [], Counter(), Counter(), []
    perguntas_por_pedaco: list[list[dict]] = []
    for resposta in respostas:
        if not isinstance(resposta, dict):
            continue
        for item in resposta.get("frases_centrais") or []:
            frase = busca.frase(item.get("frase") if isinstance(item, dict) else item)
            if frase is None:
                continue
            importancia = item.get("importancia", 5) if isinstance(item, dict) else 5
            try:
                frase["importancia"] = min(max(float(importancia), 0.0), 10.0)
            except (TypeError, ValueError):
                frase["importancia"] = 5.0
            centrais.append(frase)
        temas.update(temas_validos(resposta.get("temas"), busca))
        personagens.update(personagens_validos(resposta.get("personagens"), busca))
        for item in resposta.get("aplicacoes") or []:
            frase = busca.frase(item)
            if frase is not None:
                aplicacoes.append(frase)
        validas = (_pergunta_valida(bruta, busca) for bruta in resposta.get("perguntas") or [])
        perguntas_por_pedaco.append([pergunta for pergunta in validas if pergunta])

    # Resumo: as frases mais importantes, de volta na ordem em que foram pregadas
    centrais = _sem_repetir(sorted(centrais, key=lambda item: -item["importancia"]))[:MAXIMO_FRASES_RESUMO]
    resumo = [{"texto": item["texto"], "inicio": item["inicio"], "fim": item["fim"]}
              for item in sorted(centrais, key=lambda item: item["inicio"])]
    # Perguntas: uma de cada pedaço por vez, para o guia cobrir a pregação inteira
    perguntas, vistas = [], set()
    while len(perguntas) < MAXIMO_PERGUNTAS and any(perguntas_por_pedaco):
        for grupo in perguntas_por_pedaco:
            if grupo and len(perguntas) < MAXIMO_PERGUNTAS:
                pergunta = grupo.pop(0)
                if pergunta["pergunta"].lower() not in vistas:
                    vistas.add(pergunta["pergunta"].lower())
                    perguntas.append(pergunta)
    return {
        "resumo": resumo,
        "temas": [tema for tema, _ in temas.most_common(MAXIMO_TEMAS)],
        "personagens": [nome for nome, _ in personagens.most_common(MAXIMO_PERSONAGENS)],
        "versiculos_chave": versiculos_chave(versiculos),
        "perguntas": sorted(perguntas, key=lambda item: item["base"]["inicio"]),
        "aplicacoes": sorted(_sem_repetir(aplicacoes)[:MAXIMO_APLICACOES], key=lambda item: item["inicio"]),
        "oracao": CONVITE_ORACAO,
    }


def estudo_vazio(estudo: dict) -> bool:
    return not estudo["resumo"] and not estudo["perguntas"]


# -----------------------------------------------
# PEDIDO AO MODELO
# -----------------------------------------------
ESQUEMA_ESTUDO = {
    "type": "object",
    "properties": {
        "frases_centrais": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"frase": {"type": "string"}, "importancia": {"type": "number"}},
                "required": ["frase", "importancia"],
            },
        },
        "temas": {"type": "array", "items": {"type": "string"}},
        "personagens": {"type": "array", "items": {"type": "string"}},
        "perguntas": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"pergunta": {"type": "string"}, "frase_base": {"type": "string"}},
                "required": ["pergunta", "frase_base"],
            },
        },
        "aplicacoes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["frases_centrais", "temas", "personagens", "perguntas", "aplicacoes"],
}


def prompt_do_estudo() -> str:
    return (
        "Você prepara um guia de estudo para grupos pequenos a partir de um trecho de pregação já transcrito. "
        "Regra principal: não invente nada e não reescreva o pregador. "
        "Em frases_centrais, copie da transcrição, palavra por palavra, de 1 a 3 frases (de 6 a 40 palavras) "
        "que carregam a ideia principal deste trecho, com importância de 0 a 10. "
        "Em temas, de 1 a 3 temas curtos, usando palavras que aparecem na fala. "
        "Em personagens, só nomes de personagens bíblicos que o pregador citou. "
        "Em perguntas, de 1 a 2 perguntas abertas para o grupo conversar, terminando com ponto de interrogação; "
        "em frase_base, copie palavra por palavra a frase da transcrição em que a pergunta se apoia. "
        "Em aplicacoes, copie palavra por palavra as frases em que o pregador diz o que fazer na prática; "
        "se ele não disse, deixe vazio. Não corrija o português."
    )
