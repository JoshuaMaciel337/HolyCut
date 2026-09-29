# -----------------------------------------------
# HolyCut — armazenamento de arquivos
#
# Hoje grava numa pasta local. O resto do sistema só conhece "chaves"
# (ex.: "org_123/midias/abc/original.mp4"), então trocar para S3 ou
# Cloudflare R2 depois é só criar outra implementação destas funções.
# -----------------------------------------------
import logging
import shutil
from pathlib import Path, PurePosixPath

from core.config import PASTA_ARMAZENAMENTO


def caminho_local(chave: str, raiz: Path = PASTA_ARMAZENAMENTO) -> Path:
    """Converte uma chave em caminho dentro da raiz, recusando chaves que tentem sair dela."""
    partes = PurePosixPath(chave).parts
    if not partes or PurePosixPath(chave).is_absolute() or ".." in partes:
        raise ValueError(f"Chave de armazenamento inválida: {chave!r}")
    return raiz.joinpath(*partes)


def salvar_bytes(chave: str, conteudo: bytes, raiz: Path = PASTA_ARMAZENAMENTO) -> bool:
    try:
        destino = caminho_local(chave, raiz)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(conteudo)
        return True
    except Exception as e:
        logging.error(f"Erro ao salvar {chave}: {e}")
        return False


def salvar_arquivo(chave: str, origem: Path, raiz: Path = PASTA_ARMAZENAMENTO) -> bool:
    """Move um arquivo já existente (ex.: upload terminado) para o armazenamento."""
    try:
        destino = caminho_local(chave, raiz)
        destino.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(origem), destino)
        return True
    except Exception as e:
        logging.error(f"Erro ao mover {origem} para {chave}: {e}")
        return False


def existe(chave: str, raiz: Path = PASTA_ARMAZENAMENTO) -> bool:
    try:
        return caminho_local(chave, raiz).is_file()
    except ValueError:
        return False


def remover(chave: str, raiz: Path = PASTA_ARMAZENAMENTO) -> bool:
    try:
        caminho_local(chave, raiz).unlink(missing_ok=True)
        return True
    except Exception as e:
        logging.error(f"Erro ao remover {chave}: {e}")
        return False
