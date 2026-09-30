# -----------------------------------------------
# HolyCut — modelos (templates) de Story e de Reel
#
# Um modelo é só configuração: fundo, logo e textos. Os três primeiros vêm
# prontos com o HolyCut; a igreja pode salvar os seus a partir de um projeto.
# Nos textos, {igreja} e {instagram} viram o nome e o @ de Sua Identidade.
# Funções puras: montam e aplicam, sem acessar o banco.
# -----------------------------------------------
import copy
from datetime import datetime

from core.config import TZ

DURACAO_PADRAO_STORY = 15.0

MODELOS_PADRAO = [
    {
        "id": "culto-de-hoje",
        "nome": "Culto de hoje",
        "descricao": "Convite com o título em letra manuscrita, o horário em destaque e o @ da igreja.",
        "fundo": {"escurecer": 0.35, "desfoque": 0},
        "marca": {"logo": True, "posicao": "base_direita", "tamanho": 0.18, "opacidade": 0.95},
        "textos": [
            {"id": "titulo", "tipo": "titulo", "texto": "Culto de hoje", "referencia": "", "estilo": "manuscrito",
             "posicao": "topo", "tamanho": 1.1, "inicio": 0, "fim": None},
            {"id": "horario", "tipo": "frase", "texto": "Domingo · 19h", "referencia": "", "estilo": "destaque",
             "posicao": "centro", "tamanho": 1.0, "inicio": 0, "fim": None},
            {"id": "arroba", "tipo": "frase", "texto": "{instagram}", "referencia": "", "estilo": "limpo",
             "posicao": "base", "tamanho": 0.7, "inicio": 0, "fim": None},
        ],
    },
    {
        "id": "frase-da-pregacao",
        "nome": "Frase da pregação",
        "descricao": "Uma frase forte da mensagem em destaque sobre o vídeo, com o logo no alto.",
        "fundo": {"escurecer": 0.25, "desfoque": 0},
        "marca": {"logo": True, "posicao": "topo_direita", "tamanho": 0.16, "opacidade": 0.9},
        "textos": [
            {"id": "frase", "tipo": "frase", "texto": "Escreva aqui a frase da pregação", "referencia": "",
             "estilo": "destaque", "posicao": "base", "tamanho": 1.0, "inicio": 0, "fim": None},
        ],
    },
    {
        "id": "versiculo",
        "nome": "Versículo",
        "descricao": "O versículo no centro, com a referência na cor da igreja e o vídeo desfocado atrás.",
        "fundo": {"escurecer": 0.45, "desfoque": 14},
        "marca": {"logo": True, "posicao": "topo_direita", "tamanho": 0.14, "opacidade": 0.9},
        "textos": [
            {"id": "versiculo", "tipo": "versiculo", "texto": "Tudo posso naquele que me fortalece",
             "referencia": "Filipenses 4:13", "estilo": "limpo", "posicao": "centro", "tamanho": 1.1,
             "inicio": 0, "fim": None},
        ],
    },
]
IDS_PADRAO = {modelo["id"] for modelo in MODELOS_PADRAO}


def modelo_padrao(modelo_id: str) -> dict | None:
    return next((copy.deepcopy(m) for m in MODELOS_PADRAO if m["id"] == modelo_id), None)


def preencher(texto: str, identidade: dict) -> str:
    """Troca {igreja} e {instagram} pelos dados de Sua Identidade."""
    return (texto.replace("{igreja}", identidade.get("nome_exibicao") or "")
                 .replace("{instagram}", identidade.get("instagram") or ""))


def aplicar_modelo(modelo: dict, identidade: dict) -> dict:
    """Fundo, marca e textos que o projeto novo recebe do modelo."""
    marca = copy.deepcopy(modelo.get("marca") or {})
    marca["logo"] = bool(marca.get("logo")) and bool(identidade.get("logo"))
    textos = []
    for texto in copy.deepcopy(modelo.get("textos") or []):
        texto["texto"] = preencher(texto.get("texto", ""), identidade)
        if texto["texto"].strip():
            textos.append(texto)
    return {"fundo": copy.deepcopy(modelo.get("fundo") or {}), "marca": marca, "textos": textos}


def montar_modelo_da_igreja(organizacao_id, projeto: dict, nome: str, criado_por,
                            momento: datetime | None = None) -> dict:
    """Guarda o visual de um projeto (fundo, logo e textos) para reaproveitar em outros."""
    momento = momento or datetime.now(TZ)
    return {
        "organizacao_id": organizacao_id,
        "nome": nome[:60],
        "descricao": f"Salvo a partir de {projeto['nome']}"[:160],
        "tipo": projeto.get("tipo", "reel"),
        "proporcao": projeto.get("proporcao", "9:16"),
        "fundo": copy.deepcopy(projeto.get("fundo") or {}),
        "marca": copy.deepcopy(projeto.get("marca") or {}),
        "textos": copy.deepcopy(projeto.get("textos") or []),
        "criado_por": criado_por,
        "criado_em": momento,
    }
