# -----------------------------------------------
# HolyCut — backup diário do MongoDB
#
#   python infra/backup/agendador_backup.py --agora            (um backup e encerra)
#   python infra/backup/agendador_backup.py --automatico       (todo dia no --hora)
#
# Grava cada coleção em <pasta>/backup_DD-MM-AAAA_HH-MM/<banco>/<colecao>.bson.gz,
# o mesmo formato do mongodump. Para restaurar:
#   mongorestore --gzip --db holycut <pasta>/backup_.../holycut
# -----------------------------------------------

# -----------------------------------------------
# IMPORTS — stdlib primeiro, depois terceiros
# -----------------------------------------------
import argparse
import gzip
import logging
import os
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path

import schedule
from bson.codec_options import CodecOptions
from bson.raw_bson import RawBSONDocument

from core.config import DATABASE_NAME, PASTA_RAIZ, TZ
from core.utils.mongo import conectar

# -----------------------------------------------
# CONFIGURAÇÕES
# -----------------------------------------------
PASTA_BACKUP = Path(os.environ.get("PASTA_BACKUP", PASTA_RAIZ / "backups"))
HORA_PADRAO = os.environ.get("BACKUP_HORA", "03:00")
RETENCAO_DIAS = int(os.environ.get("BACKUP_RETENCAO_DIAS", "14"))
PREFIXO = "backup_"
FORMATO_PASTA = "%d-%m-%Y_%H-%M"

# -----------------------------------------------
# LOGGING
# -----------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)


# -----------------------------------------------
# FUNÇÕES AUXILIARES
# -----------------------------------------------
def exportar_colecao(db, nome: str, destino: Path) -> int:
    """Grava a coleção byte a byte, sem decodificar os documentos. Retorna quantos foram gravados."""
    colecao = db.get_collection(nome, codec_options=CodecOptions(document_class=RawBSONDocument))
    total = 0
    with gzip.open(destino / f"{nome}.bson.gz", "wb") as arquivo:
        for documento in colecao.find({}):
            arquivo.write(documento.raw)
            total += 1
    return total


def remover_backups_antigos(pasta: Path, retencao_dias: int, momento: datetime) -> int:
    """Apaga só as pastas criadas por este script com mais de retencao_dias."""
    limite = momento - timedelta(days=retencao_dias)
    removidos = 0
    for item in pasta.glob(f"{PREFIXO}*"):
        try:
            data = datetime.strptime(item.name.removeprefix(PREFIXO), FORMATO_PASTA).replace(tzinfo=TZ)
        except ValueError:
            continue
        if item.is_dir() and data < limite:
            shutil.rmtree(item)
            removidos += 1
            logging.info(f"Backup antigo removido: {item.name}")
    return removidos


# -----------------------------------------------
# FUNÇÕES PRINCIPAIS
# -----------------------------------------------
def executar_backup(pasta: Path = PASTA_BACKUP, retencao_dias: int = RETENCAO_DIAS) -> Path | None:
    """Faz um backup completo. Nunca lança exceção para fora."""
    momento = datetime.now(TZ)
    logging.info(f"Iniciando backup: {momento.strftime('%d/%m/%Y %H:%M:%S')}")
    try:
        db = conectar()
        if db is None:
            return None
        destino = pasta / f"{PREFIXO}{momento.strftime(FORMATO_PASTA)}" / DATABASE_NAME
        destino.mkdir(parents=True, exist_ok=True)
        for nome in sorted(db.list_collection_names()):
            total = exportar_colecao(db, nome, destino)
            logging.info(f"  {nome}: {total} documentos")
        db.client.close()
        remover_backups_antigos(pasta, retencao_dias, momento)
        logging.info(f"Backup concluído em {destino}")
        return destino
    except Exception as e:
        logging.error(f"Erro no backup: {e}")
        return None


# -----------------------------------------------
# EXECUÇÃO
# -----------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Backup diário do MongoDB do HolyCut")
    parser.add_argument("--automatico", action="store_true", help="Sem input() do usuário")
    parser.add_argument("--agora", action="store_true", help="Executa imediatamente e encerra")
    parser.add_argument("--hora", default=HORA_PADRAO, help="Horário de execução HH:MM")
    args = parser.parse_args()

    if args.agora:
        executar_backup()
        return

    schedule.every().day.at(args.hora).do(executar_backup)
    logging.info(f"Agendador de backup ativo. Próxima execução: {args.hora}. Pasta: {PASTA_BACKUP}")
    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
