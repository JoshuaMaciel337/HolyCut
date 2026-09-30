# -----------------------------------------------
# HolyCut — biblioteca de músicas da igreja
#
# Toda faixa entra com a licença registrada. Postar música sem licença
# derruba o vídeo nas redes e pode gerar problema para a igreja, então o
# HolyCut só usa faixas que a igreja declarou poder usar.
# Funções puras: montam e validam, sem acessar o banco.
# -----------------------------------------------
from datetime import datetime

from core.config import TZ

LICENCAS = {
    "propria": "Própria da igreja (gravação ou composição nossa)",
    "dominio_publico": "Domínio público ou CC0",
    "cc_by": "Creative Commons com atribuição (CC BY)",
    "licenciada": "Licenciada (temos permissão por escrito ou assinatura)",
}
LICENCAS_COM_ATRIBUICAO = {"cc_by"}
EXTENSOES_MUSICA = {".mp3", ".m4a", ".aac", ".wav", ".ogg", ".flac"}
MUSICA_MAX_BYTES = 40 * 1024 * 1024

STATUS_AGUARDANDO_ARQUIVO = "aguardando_arquivo"
STATUS_PROCESSANDO = "processando"
STATUS_PRONTA = "pronta"
STATUS_ERRO = "erro"
ARQUIVO_MUSICA = "musica.m4a"

# No projeto: nenhuma música, volume de 25% e abaixando sob a fala
MUSICA_DO_PROJETO_PADRAO = {"id": None, "volume": 0.25, "abaixar_na_fala": True, "inicio": 0.0}


class ErroLicenca(ValueError):
    pass


def pasta_da_musica(organizacao_id, musica_id) -> str:
    return f"org_{organizacao_id}/musicas/{musica_id}"


def chave_musica(organizacao_id, musica_id, nome: str) -> str:
    return f"{pasta_da_musica(organizacao_id, musica_id)}/{nome}"


def validar_licenca(licenca: str, atribuicao: str) -> None:
    if licenca not in LICENCAS:
        raise ErroLicenca("Escolha a licença da música.")
    if licenca in LICENCAS_COM_ATRIBUICAO and not atribuicao.strip():
        raise ErroLicenca("Esta licença exige atribuição: escreva o autor e a fonte, como a licença pede.")


def montar_musica(organizacao_id, criado_por, titulo: str, artista: str, licenca: str, atribuicao: str = "",
                  fonte: str = "", momento: datetime | None = None) -> dict:
    validar_licenca(licenca, atribuicao)
    momento = momento or datetime.now(TZ)
    return {
        "organizacao_id": organizacao_id,
        "criado_por": criado_por,
        "titulo": " ".join(titulo.split())[:120],
        "artista": " ".join(artista.split())[:120],
        "licenca": licenca,
        "atribuicao": atribuicao.strip()[:300],
        "fonte": fonte.strip()[:300],
        "status": STATUS_AGUARDANDO_ARQUIVO,
        "original": None,
        "duracao": None,
        "job_id": None,
        "erro": None,
        "criado_em": momento,
        "atualizado_em": momento,
    }
