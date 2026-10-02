# -----------------------------------------------
# HolyCut — conexão, índices e upsert no MongoDB
# -----------------------------------------------
import logging
import re
from datetime import datetime

import pymongo
from pymongo import AsyncMongoClient, MongoClient

from core.config import DATABASE_NAME, MONGO_URI, TZ

# -----------------------------------------------
# ÍNDICES — criados sempre na inicialização da API e dos workers
# -----------------------------------------------
INDICES = {
    "organizacoes": [
        ([("slug", 1)], {"unique": True}),
    ],
    "usuarios": [
        ([("email", 1)], {"unique": True}),
        ([("organizacao_id", 1)], {}),
    ],
    "cache_pixabay": [
        ([("chave", 1)], {"unique": True}),
        ([("expira_em", 1)], {"expireAfterSeconds": 0}),
    ],
    "jobs": [
        ([("status", 1), ("tipo", 1), ("prioridade", -1), ("criado_em", 1)], {"name": "fila_busca"}),
        ([("organizacao_id", 1), ("criado_em", -1)], {}),
        ([("status", 1), ("lease_ate", 1)], {}),
        ([("entrada.midia_id", 1)], {}),
        ([("entrada.exportacao_id", 1)], {}),
        ([("entrada.musica_id", 1)], {}),
    ],
    "midias": [
        ([("organizacao_id", 1), ("criado_em", -1)], {}),
    ],
    "transcricoes": [
        ([("midia_id", 1)], {"unique": True}),
        ([("organizacao_id", 1), ("midia_id", 1)], {}),
    ],
    "sugestoes": [
        ([("midia_id", 1)], {"unique": True}),
        ([("organizacao_id", 1), ("midia_id", 1)], {}),
    ],
    "rostos": [
        ([("midia_id", 1)], {"unique": True}),
        ([("organizacao_id", 1), ("midia_id", 1)], {}),
    ],
    "momentos": [
        ([("midia_id", 1)], {"unique": True}),
        ([("organizacao_id", 1), ("midia_id", 1)], {}),
    ],
    "blocos": [
        ([("midia_id", 1)], {"unique": True}),
        ([("organizacao_id", 1), ("midia_id", 1)], {}),
    ],
    "estudos": [
        ([("midia_id", 1)], {"unique": True}),
        ([("organizacao_id", 1), ("midia_id", 1)], {}),
    ],
    "projetos": [
        ([("organizacao_id", 1), ("atualizado_em", -1)], {}),
        ([("midia_id", 1)], {}),
    ],
    "musicas": [
        ([("organizacao_id", 1), ("criado_em", -1)], {}),
    ],
    "modelos": [
        ([("organizacao_id", 1), ("criado_em", -1)], {}),
    ],
    "exportacoes": [
        ([("projeto_id", 1), ("criado_em", -1)], {}),
        ([("organizacao_id", 1), ("criado_em", -1)], {}),
        ([("midia_id", 1)], {}),
        # O link de aprovação procura a exportação pelo hash do token
        ([("aprovacao.token_hash", 1)], {"unique": True, "sparse": True}),
    ],
    "chaves_envio": [
        ([("hash", 1)], {"unique": True}),
        ([("organizacao_id", 1), ("criado_em", -1)], {}),
    ],
    # Registro de workers online. O MongoDB apaga sozinho quem sumiu há mais de 1 hora.
    "workers": [
        ([("visto_em", 1)], {"expireAfterSeconds": 3600}),
    ],
}


# -----------------------------------------------
# FUNÇÕES AUXILIARES
# -----------------------------------------------
def agora() -> datetime:
    """Data e hora atual no fuso de São Paulo."""
    return datetime.now(TZ)


def ocultar_credenciais(uri: str) -> str:
    """Esconde usuário e senha da URI antes de ir para o log."""
    return re.sub(r"//[^@/]+@", "//***@", uri)


def _preenchido(v) -> bool:
    """True se o valor justifica sobrescrever o campo existente."""
    if isinstance(v, bool):
        return True
    if v is None:
        return False
    if isinstance(v, str):
        return v.strip() != ""
    if isinstance(v, (list, dict, set, tuple)):
        return len(v) > 0
    return True


# -----------------------------------------------
# CONEXÃO
# -----------------------------------------------
def conectar(uri: str = MONGO_URI, nome_banco: str = DATABASE_NAME, timeout_ms: int = 5000):
    """Conecta ao MongoDB (síncrono, usado por workers e scripts). Retorna db ou None."""
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=timeout_ms, connectTimeoutMS=10000,
                             tz_aware=True, tzinfo=TZ)
        client.admin.command("ping")
        logging.info(f"MongoDB conectado: {ocultar_credenciais(uri)}")
        return client[nome_banco]
    except Exception as e:
        logging.error(f"Falha ao conectar ({ocultar_credenciais(uri)}): {e}")
        return None


def criar_cliente_async(uri: str = MONGO_URI) -> AsyncMongoClient:
    """Cliente assíncrono usado pela API. A verificação de conexão fica a cargo de quem chama."""
    return AsyncMongoClient(uri, serverSelectionTimeoutMS=5000, connectTimeoutMS=10000,
                            tz_aware=True, tzinfo=TZ)


def criar_indices(db):
    """Cria os índices de todas as coleções. Seguro para rodar várias vezes."""
    for colecao, indices in INDICES.items():
        for chaves, opcoes in indices:
            try:
                db[colecao].create_index(chaves, **opcoes)
            except Exception as e:
                logging.error(f"Erro ao criar índice {chaves} em {colecao}: {e}")


# -----------------------------------------------
# UPSERT COM MERGE — padrão da equipe
# -----------------------------------------------
def upsert(db, colecao: str, documento: dict, chave: str = "_id") -> str:
    """
    Insere novo documento ou mescla com existente.
    Campos vazios não sobrescrevem dados existentes.
    """
    try:
        existente = db[colecao].find_one({chave: documento[chave]})
        if existente:
            campos = {k: v for k, v in documento.items() if _preenchido(v) and k != "_id"}
            db[colecao].update_one({chave: documento[chave]}, {"$set": campos})
            logging.info(f"Mesclado: {documento[chave]} em {colecao}")
            return "mesclado"
        db[colecao].insert_one(documento)
        logging.info(f"Inserido: {documento[chave]} em {colecao}")
        return "inserido"
    except pymongo.errors.DuplicateKeyError:
        logging.warning(f"Duplicata ignorada: {documento.get(chave)}")
        return "duplicata"
    except Exception as e:
        logging.error(f"Erro ao salvar {documento.get(chave)}: {e}")
        return "erro"
