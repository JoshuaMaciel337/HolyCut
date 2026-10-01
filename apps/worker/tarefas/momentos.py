# -----------------------------------------------
# Tarefa "momentos" — energia, cenas e uma nota visual curta
# A nota só aceita pregador, plateia, luz ou outro. O modelo sai da memória no fim.
# -----------------------------------------------
import base64
import logging
import re
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path

from bson import ObjectId

from core.config import FFMPEG
from core.modelos.job import ErroDefinitivo
from core.modelos.midia import ARQUIVO_NIVEIS, ARQUIVO_PROXY_VIDEO, NIVEIS_POR_SEGUNDO, chave_arquivo
from core.modelos.momentos import ASSUNTOS, montar_momentos, picos_de_energia
from core.utils import storage
from core.utils.mongo import agora
from core.utils.ollama import ErroOllama, completar_json

ESQUEMA_NOTA = {
    "type": "object",
    "properties": {
        "nota": {"type": "number"},
        "assunto": {"type": "string", "enum": sorted(ASSUNTOS)},
    },
    "required": ["nota", "assunto"],
}


def _cenas(caminho: Path) -> list[float]:
    processo = subprocess.run(
        [FFMPEG, "-hide_banner", "-i", str(caminho), "-vf", "select='gt(scene,0.30)',showinfo", "-f", "null", "-"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900,
    )
    tempos = []
    for achado in re.findall(r"pts_time:([0-9.]+)", processo.stderr):
        try:
            tempos.append(round(float(achado), 2))
        except ValueError:
            continue
    return tempos[:80]


def _quadro(caminho: Path, instante: float) -> str | None:
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as arquivo:
        destino = Path(arquivo.name)
    processo = subprocess.run(
        [FFMPEG, "-hide_banner", "-loglevel", "error", "-ss", f"{instante:.2f}", "-i", str(caminho),
         "-frames:v", "1", "-vf", "scale=640:-2", "-q:v", "5", str(destino)],
        capture_output=True, timeout=60,
    )
    if processo.returncode != 0 or not destino.is_file():
        destino.unlink(missing_ok=True)
        return None
    cru = destino.read_bytes()
    destino.unlink(missing_ok=True)
    return base64.b64encode(cru).decode()


def _notas(caminho: Path, cenas: list[float], reportar) -> dict[float, dict]:
    escolhidas = cenas[::max(len(cenas) // 6, 1)][:6]
    notas = {}
    for indice, cena in enumerate(escolhidas):
        imagem = _quadro(caminho, cena)
        if not imagem:
            continue
        reportar(60 + int(30 * indice / max(len(escolhidas), 1)), "Olhando os quadros")
        try:
            resposta = completar_json(
                "Você olha um quadro de culto. A nota vai de 0 a 10, para servir de capa. "
                "O assunto só pode ser pregador, plateia, luz ou outro. Não comente a mensagem.",
                "Classifique este quadro.",
                ESQUEMA_NOTA,
                descarregar=indice == len(escolhidas) - 1,
                imagens=[imagem],
            )
        except ErroOllama as erro:
            logging.warning("Nota visual indisponível: %s", erro)
            break
        if resposta.get("assunto") in ASSUNTOS:
            notas[cena] = {"assunto": resposta["assunto"], "nota": resposta.get("nota")}
    return notas


def executar_momentos(db, job: dict, reportar: Callable[[int, str], None]) -> dict:
    midia_id = ObjectId(job["entrada"]["midia_id"])
    organizacao_id = job["organizacao_id"]
    midia = db.midias.find_one({"_id": midia_id, "organizacao_id": organizacao_id})
    if midia is None:
        raise ErroDefinitivo("A gravação foi excluída antes dos momentos.")
    niveis = storage.caminho_local(chave_arquivo(organizacao_id, midia_id, ARQUIVO_NIVEIS))
    if not niveis.is_file():
        raise ErroDefinitivo("Os níveis de áudio não foram encontrados.")
    import numpy as np
    reportar(5, "Medindo a energia")
    picos = picos_de_energia(np.fromfile(niveis, dtype=np.int8).tolist(), NIVEIS_POR_SEGUNDO)
    proxy = storage.caminho_local(chave_arquivo(organizacao_id, midia_id, ARQUIVO_PROXY_VIDEO))
    cenas = _cenas(proxy) if proxy.is_file() else []
    reportar(40, "Procurando as cenas")
    notas = _notas(proxy, cenas, reportar) if proxy.is_file() and cenas else {}
    momentos = montar_momentos(picos, cenas, notas)
    db.momentos.replace_one(
        {"midia_id": midia_id, "organizacao_id": organizacao_id},
        {"organizacao_id": organizacao_id, "midia_id": midia_id, "gerado_por_ia": bool(notas),
         "momentos": momentos, "cenas": cenas, "criado_em": agora()},
        upsert=True,
    )
    reportar(100, "Momentos prontos")
    logging.info("[%s] [midia %s] %s momentos, %s cenas.", organizacao_id, midia_id, len(momentos), len(cenas))
    return {"midia_id": str(midia_id), "momentos": len(momentos)}
