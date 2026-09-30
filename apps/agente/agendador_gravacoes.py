# -----------------------------------------------
# HolyCut — agente que envia sozinho as gravações do OBS
#
# Roda no PC da mídia. Olha a pasta onde o OBS grava e, quando uma gravação
# termina (o arquivo fica alguns minutos sem mudar), envia para o HolyCut
# pelo mesmo upload retomável do site (protocolo tus). Se a internet cair,
# continua de onde parou na próxima volta, sem mandar tudo de novo.
#
# Na primeira vez, o que já estava na pasta só é marcado como visto: o agente
# envia as gravações novas, não o histórico todo (a não ser com
# --enviar-existentes).
#
# Uso:
#   python agendador_gravacoes.py                 pergunta o que faltar e fica rodando
#   python agendador_gravacoes.py --agora         confere a pasta uma vez e encerra
#   python agendador_gravacoes.py --automatico    fica rodando, sem perguntas (para iniciar com o Windows)
#
# O endereço, a chave e a pasta podem vir dos argumentos, das variáveis
# HOLYCUT_SERVIDOR, HOLYCUT_CHAVE e HOLYCUT_PASTA, ou da configuração salva
# na primeira execução.
# -----------------------------------------------
import argparse
import base64
import json
import logging
import logging.handlers
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

# -----------------------------------------------
# CONFIGURAÇÕES
# -----------------------------------------------
TZ = ZoneInfo("America/Sao_Paulo")
PASTA_DO_AGENTE = Path(os.environ.get("HOLYCUT_PASTA_AGENTE", str(Path.home() / ".holycut")))
ARQUIVO_ESTADO = PASTA_DO_AGENTE / "agente.json"
ARQUIVO_LOG = PASTA_DO_AGENTE / "agente.log"

# Os mesmos formatos de vídeo que o HolyCut aceita (core/config.py, EXTENSOES_VIDEO)
EXTENSOES_VIDEO = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm", ".mts", ".m2ts", ".ts"}
# O OBS pode gravar em MKV e depois converter para MP4 ("remux"): se existir o MP4, o MKV fica de fora
EXTENSOES_PREFERIDAS = (".mp4", ".mov")

MINUTOS_ESTAVEL = 2          # sem mudar de tamanho por esse tempo = a gravação terminou
INTERVALO_SEGUNDOS = 30      # de quanto em quanto tempo olha a pasta
TAMANHO_PEDACO = 8 * 1024 * 1024
TIMEOUT_SEGUNDOS = 30
TIMEOUT_PEDACO_SEGUNDOS = 180  # 8 MB numa internet de 1 Mbps levam pouco mais de 1 minuto
MAX_TENTATIVAS = 3
ESPERA_ENTRE_TENTATIVAS = 10
TUS_VERSAO = "1.0.0"

# Situação de cada arquivo no estado salvo
VISTO = "visto"              # já estava na pasta na primeira execução
ENVIANDO = "enviando"
ENVIADO = "enviado"
RECUSADO = "recusado"        # o servidor não aceita (formato, tamanho): não adianta tentar de novo

# -----------------------------------------------
# LOGGING
# -----------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[logging.StreamHandler()])


class ErroChave(Exception):
    """A chave foi recusada: não adianta continuar até alguém trocar a chave."""


class ErroEnvio(Exception):
    """Falhou agora, mas pode dar certo numa próxima volta (internet, servidor fora, sem espaço)."""


# -----------------------------------------------
# FUNÇÕES AUXILIARES
# -----------------------------------------------
def agora() -> datetime:
    return datetime.now(TZ)


def ler_estado(caminho: Path = ARQUIVO_ESTADO) -> dict:
    if not caminho.exists():
        return {}
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except Exception as e:
        logging.error(f"Não foi possível ler {caminho}: {e}. Começando do zero.")
        return {}


def salvar_estado(estado: dict, caminho: Path = ARQUIVO_ESTADO):
    """Grava num arquivo temporário e troca: um desligamento no meio não corrompe o estado."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_suffix(".tmp")
    temporario.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporario, caminho)


def listar_gravacoes(pasta: Path) -> list[Path]:
    """Vídeos da pasta (sem entrar em subpastas), sem o MKV que já foi convertido para MP4."""
    arquivos = [a for a in pasta.iterdir() if a.is_file() and a.suffix.lower() in EXTENSOES_VIDEO]
    convertidos = {a.stem.lower() for a in arquivos if a.suffix.lower() in EXTENSOES_PREFERIDAS}
    return sorted((a for a in arquivos if not (a.suffix.lower() == ".mkv" and a.stem.lower() in convertidos)),
                  key=lambda a: a.stat().st_mtime)


def gravacao_terminou(registro: dict, tamanho: int, modificado: float, instante: float, minutos: float) -> bool:
    """
    Terminou quando o tamanho e a data do arquivo não mudam desde a última observação há pelo menos
    `minutos`. Um arquivo parado há muito mais tempo que isso (o PC estava desligado) já conta como terminado.
    """
    if tamanho <= 0 or registro.get("tamanho") != tamanho or registro.get("modificado") != modificado:
        return False
    janela = minutos * 60
    return instante - registro.get("observado_desde", instante) >= janela or instante - modificado >= 5 * janela


def cabecalhos(chave: str, extras: dict | None = None) -> dict:
    return {"Authorization": f"Bearer {chave}", "Tus-Resumable": TUS_VERSAO, **(extras or {})}


def metadados_tus(nome: str) -> str:
    codificar = lambda texto: base64.b64encode(texto.encode("utf-8")).decode()  # noqa: E731
    return f"filename {codificar(nome)},filetype {codificar('video/' + Path(nome).suffix.lower().lstrip('.'))}"


def tratar_resposta_de_erro(resposta: requests.Response, contexto: str):
    if resposta.status_code == 401:
        raise ErroChave("A chave de envio foi recusada. Crie outra em HolyCut > Envio automático.")
    if resposta.status_code in (413, 415):
        raise ValueError(resposta.text or f"O servidor recusou o arquivo ({resposta.status_code}).")
    raise ErroEnvio(f"{contexto}: HTTP {resposta.status_code} {resposta.text[:200]}")


def conferir_chave(servidor: str, chave: str) -> str | None:
    """Nome da igreja ligada à chave, ou None se o servidor não respondeu."""
    try:
        resposta = requests.get(f"{servidor}/api/chaves-envio/conferir", headers=cabecalhos(chave),
                                timeout=TIMEOUT_SEGUNDOS)
    except requests.RequestException as e:
        logging.warning(f"Sem conexão com {servidor}: {e}")
        return None
    if resposta.status_code == 401:
        raise ErroChave("A chave de envio foi recusada. Crie outra em HolyCut > Envio automático.")
    if resposta.status_code != 200:
        logging.warning(f"O HolyCut respondeu HTTP {resposta.status_code} ao conferir a chave.")
        return None
    return resposta.json()["igreja"]


# -----------------------------------------------
# ENVIO (tus 1.0.0)
# -----------------------------------------------
def criar_envio(servidor: str, chave: str, arquivo: Path) -> str:
    resposta = requests.post(f"{servidor}/api/uploads", timeout=TIMEOUT_SEGUNDOS, headers=cabecalhos(chave, {
        "Upload-Length": str(arquivo.stat().st_size), "Upload-Metadata": metadados_tus(arquivo.name)}))
    if resposta.status_code != 201:
        tratar_resposta_de_erro(resposta, "Não foi possível começar o envio")
    return f"{servidor}{resposta.headers['Location']}"


def posicao_no_servidor(url: str, chave: str) -> int | None:
    """Quanto do arquivo o servidor já tem, ou None se ele não conhece mais esse envio."""
    resposta = requests.head(url, headers=cabecalhos(chave), timeout=TIMEOUT_SEGUNDOS)
    if resposta.status_code == 404:
        return None
    if resposta.status_code != 200:
        tratar_resposta_de_erro(resposta, "Não foi possível consultar o envio")
    return int(resposta.headers["Upload-Offset"])


def enviar_pedacos(url: str, chave: str, arquivo: Path, posicao: int, rotulo: str) -> int:
    total = arquivo.stat().st_size
    proximo_aviso = (posicao * 10 // total + 1) * 10 if total else 100
    with arquivo.open("rb") as origem:
        while posicao < total:
            origem.seek(posicao)
            pedaco = origem.read(TAMANHO_PEDACO)
            for tentativa in range(1, MAX_TENTATIVAS + 1):
                try:
                    resposta = requests.patch(url, data=pedaco, timeout=TIMEOUT_PEDACO_SEGUNDOS,
                                              headers=cabecalhos(chave, {
                                                  "Upload-Offset": str(posicao),
                                                  "Content-Type": "application/offset+octet-stream"}))
                except requests.RequestException as e:
                    logging.warning(f"{rotulo} Tentativa {tentativa}/{MAX_TENTATIVAS} falhou: {e}")
                    time.sleep(ESPERA_ENTRE_TENTATIVAS * tentativa)
                    continue
                if resposta.status_code == 204:
                    posicao = int(resposta.headers["Upload-Offset"])
                    break
                if resposta.status_code == 409 and "Upload-Offset" in resposta.headers:
                    posicao = int(resposta.headers["Upload-Offset"])   # o servidor diz de onde continuar
                    break
                if resposta.status_code == 423:   # outro envio do mesmo arquivo em andamento
                    time.sleep(ESPERA_ENTRE_TENTATIVAS)
                    continue
                tratar_resposta_de_erro(resposta, "O servidor recusou um pedaço")
            else:
                raise ErroEnvio(f"Sem conexão depois de {MAX_TENTATIVAS} tentativas. Continua na próxima volta.")
            if total and posicao * 100 // total >= proximo_aviso:
                logging.info(f"{rotulo} {posicao * 100 // total}% enviado "
                             f"({posicao / 1024**2:.0f} de {total / 1024**2:.0f} MB)")
                proximo_aviso = (posicao * 10 // total + 1) * 10
    return posicao


def enviar_gravacao(servidor: str, chave: str, arquivo: Path, registro: dict, estado: dict,
                    caminho_estado: Path) -> dict:
    """Envia (ou continua enviando) um arquivo. Atualiza e salva o registro a cada etapa."""
    rotulo = f"[{arquivo.name}]"
    posicao = posicao_no_servidor(registro["url"], chave) if registro.get("url") else None
    if posicao is None:
        registro.update({"situacao": ENVIANDO, "url": criar_envio(servidor, chave, arquivo),
                         "atualizado_em": agora().isoformat()})
        salvar_estado(estado, caminho_estado)
        posicao = 0
        logging.info(f"{rotulo} Enviando {arquivo.stat().st_size / 1024**2:.0f} MB para o HolyCut.")
    else:
        logging.info(f"{rotulo} Continuando o envio de onde parou ({posicao / 1024**2:.0f} MB já no servidor).")
    enviar_pedacos(registro["url"], chave, arquivo, posicao, rotulo)
    registro.update({"situacao": ENVIADO, "midia_id": registro["url"].rstrip("/").rsplit("/", 1)[-1],
                     "erro": None, "atualizado_em": agora().isoformat()})
    salvar_estado(estado, caminho_estado)
    logging.info(f"{rotulo} Envio concluído. O HolyCut já está preparando a gravação.")
    return registro


# -----------------------------------------------
# FUNÇÕES PRINCIPAIS
# -----------------------------------------------
def conferir_pasta(configuracao: dict, estado: dict, caminho_estado: Path = ARQUIVO_ESTADO,
                   instante: float | None = None) -> list[str]:
    """Uma volta: observa os arquivos e envia os que terminaram. Devolve os nomes enviados nesta volta."""
    pasta = Path(configuracao["pasta"])
    if not pasta.is_dir():
        logging.error(f"A pasta {pasta} não existe. Confira onde o OBS salva as gravações.")
        return []
    instante = time.time() if instante is None else instante
    arquivos = estado.setdefault("arquivos", {})
    primeira_vez = "iniciado_em" not in estado
    enviados = []
    for arquivo in listar_gravacoes(pasta):
        informacoes = arquivo.stat()
        registro = arquivos.setdefault(str(arquivo), {})
        if primeira_vez and not configuracao.get("enviar_existentes") and not registro:
            registro.update({"situacao": VISTO, "tamanho": informacoes.st_size})
            continue
        if registro.get("situacao") in (VISTO, ENVIADO, RECUSADO):
            if registro.get("tamanho") == informacoes.st_size:
                continue
            # O arquivo mudou depois (o OBS ainda gravava na primeira vez, ou regravou com o mesmo nome):
            # vale como gravação nova
            registro.clear()
        if not gravacao_terminou(registro, informacoes.st_size, informacoes.st_mtime, instante,
                                 configuracao.get("minutos_estavel", MINUTOS_ESTAVEL)):
            if (registro.get("tamanho"), registro.get("modificado")) != (informacoes.st_size, informacoes.st_mtime):
                registro.update({"tamanho": informacoes.st_size, "modificado": informacoes.st_mtime,
                                 "observado_desde": instante})
            continue
        try:
            enviar_gravacao(configuracao["servidor"], configuracao["chave"], arquivo, registro, estado, caminho_estado)
            enviados.append(arquivo.name)
        except ValueError as e:
            registro.update({"situacao": RECUSADO, "erro": str(e), "atualizado_em": agora().isoformat()})
            logging.error(f"[{arquivo.name}] O HolyCut recusou o arquivo: {e}")
        except (ErroEnvio, requests.RequestException) as e:
            registro.update({"erro": str(e), "atualizado_em": agora().isoformat()})
            logging.warning(f"[{arquivo.name}] Envio interrompido: {e}")
    if primeira_vez:
        estado["iniciado_em"] = agora().isoformat()
        ja_existiam = sum(1 for r in arquivos.values() if r.get("situacao") == VISTO)
        if ja_existiam:
            logging.info(f"{ja_existiam} gravações já estavam na pasta e não serão enviadas "
                         "(use --enviar-existentes para mandar também).")
    salvar_estado(estado, caminho_estado)
    return enviados


def montar_configuracao(args, estado: dict) -> dict:
    """Argumentos > variáveis de ambiente > configuração salva. Sem --automatico, pergunta o que faltar."""
    salva = estado.get("configuracao", {})
    configuracao = {
        "servidor": (args.servidor or os.environ.get("HOLYCUT_SERVIDOR") or salva.get("servidor") or "").rstrip("/"),
        "chave": args.chave or os.environ.get("HOLYCUT_CHAVE") or salva.get("chave") or "",
        "pasta": args.pasta or os.environ.get("HOLYCUT_PASTA") or salva.get("pasta") or "",
        "minutos_estavel": args.minutos_estavel,
        "enviar_existentes": args.enviar_existentes,
    }
    perguntas = {"servidor": "Endereço do HolyCut (ex.: https://holycut.app): ",
                 "chave": "Chave de envio (crie em HolyCut > Envio automático): ",
                 "pasta": "Pasta onde o OBS salva as gravações: "}
    for campo, pergunta in perguntas.items():
        if not configuracao[campo] and not args.automatico:
            configuracao[campo] = input(pergunta).strip().strip('"').rstrip("/")
        if not configuracao[campo]:
            raise SystemExit(f"Falta a configuração '{campo}'. Veja --help.")
    estado["configuracao"] = {campo: configuracao[campo] for campo in perguntas}
    return configuracao


# -----------------------------------------------
# EXECUÇÃO
# -----------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Envia sozinho para o HolyCut as gravações novas do OBS.")
    parser.add_argument("--pasta", help="Pasta onde o OBS salva as gravações")
    parser.add_argument("--servidor", help="Endereço do HolyCut, ex.: https://holycut.app")
    parser.add_argument("--chave", help="Chave de envio criada no site")
    parser.add_argument("--agora", action="store_true", help="Confere a pasta uma vez e encerra")
    parser.add_argument("--automatico", action="store_true", help="Fica rodando, sem perguntas")
    parser.add_argument("--enviar-existentes", action="store_true",
                        help="Na primeira vez, envia também as gravações que já estavam na pasta")
    parser.add_argument("--minutos-estavel", type=float, default=MINUTOS_ESTAVEL,
                        help="Minutos sem mudar para considerar que a gravação terminou")
    parser.add_argument("--intervalo", type=int, default=INTERVALO_SEGUNDOS, help="Segundos entre uma volta e outra")
    args = parser.parse_args()

    PASTA_DO_AGENTE.mkdir(parents=True, exist_ok=True)
    arquivo_log = logging.handlers.RotatingFileHandler(ARQUIVO_LOG, maxBytes=1024 * 1024, backupCount=3,
                                                       encoding="utf-8")
    arquivo_log.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logging.getLogger().addHandler(arquivo_log)

    estado = ler_estado()
    configuracao = montar_configuracao(args, estado)
    salvar_estado(estado)
    try:
        igreja = conferir_chave(configuracao["servidor"], configuracao["chave"])
    except ErroChave as e:
        logging.error(str(e))
        sys.exit(2)
    logging.info(f"Conectado a {igreja}." if igreja else "O HolyCut não respondeu agora. Tentando nas próximas voltas.")
    logging.info(f"Olhando {configuracao['pasta']} a cada {args.intervalo} s.")

    while True:
        try:
            conferir_pasta(configuracao, estado)
        except ErroChave as e:
            logging.error(str(e))
            sys.exit(2)
        except Exception as e:   # o agente não pode parar por causa de um erro numa volta
            logging.error(f"Erro nesta volta: {e}")
        if args.agora:
            return
        time.sleep(args.intervalo)


if __name__ == "__main__":
    main()
