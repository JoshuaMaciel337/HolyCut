# -----------------------------------------------
# HolyCut — modelo de projeto (um Reel montado a partir de uma gravação)
# e de exportação (o vídeo final renderizado de um projeto)
# Funções puras: montam e calculam, sem acessar o banco.
# -----------------------------------------------
import copy
from datetime import datetime

from core.config import TZ
from core.modelos.identidade import marca_padrao
from core.modelos.modelos_story import DURACAO_PADRAO_STORY, aplicar_modelo

PROPORCOES = {
    "9:16": (1080, 1920),   # Reels, Stories, TikTok, Shorts
    "4:5": (1080, 1350),    # feed do Instagram
    "1:1": (1080, 1080),
    "16:9": (1920, 1080),   # YouTube
}
INTENSIDADES_CORTE = ("leve", "media", "forte")
DURACAO_MINIMA_TRECHO = 1.0
ZOOM_MAXIMO = 3.0

STATUS_EXPORTACAO_PROCESSANDO = "processando"
STATUS_EXPORTACAO_PRONTA = "pronta"
STATUS_EXPORTACAO_ERRO = "erro"
ARQUIVO_VIDEO_EXPORTADO = "video.mp4"
ARQUIVO_CAPA_EXPORTADA = "capa.jpg"
ARQUIVO_IMAGEM_EXPORTADA = "imagem.jpg"
ARQUIVOS_EXPORTACAO = {ARQUIVO_VIDEO_EXPORTADO, ARQUIVO_CAPA_EXPORTADA, ARQUIVO_IMAGEM_EXPORTADA}
FORMATOS_EXPORTACAO = ("video", "imagem")
FUNDO_PADRAO = {"escurecer": 0.0, "desfoque": 0}
COR_PADRAO = {"filtro": "natural", "intensidade": 1.0}
ESCURECER_MAXIMO = 0.8
DESFOQUE_MAXIMO = 30

# Campos do projeto que definem o vídeo. A exportação guarda uma cópia deles,
# então editar o projeto depois não muda um vídeo já exportado.
CAMPOS_DO_VIDEO = ("proporcao", "trecho", "silencios", "enquadramento", "audio", "marca", "textos", "fundo", "cor")


def _id_do_modelo(modelo: dict | None) -> str | None:
    """Modelos prontos têm "id"; os da igreja vêm do banco com "_id"."""
    if not modelo:
        return None
    return str(modelo.get("id") or modelo.get("_id"))


def montar_projeto(organizacao_id, midia: dict, criado_por, nome: str | None = None,
                   proporcao: str = "9:16", momento: datetime | None = None, identidade: dict | None = None,
                   tipo: str = "reel", modelo: dict | None = None, inicio: float = 0.0) -> dict:
    """
    Reel: a gravação inteira, com corte de silêncios médio.
    Story: 15 s a partir de inicio, sem corte de silêncios, com o visual do modelo escolhido.
    """
    if proporcao not in PROPORCOES:
        raise ValueError(f"Proporção desconhecida: {proporcao}")
    if tipo not in ("reel", "story"):
        raise ValueError(f"Tipo de projeto desconhecido: {tipo}")
    momento = momento or datetime.now(TZ)
    duracao = round(float(midia["duracao"]), 2)
    if tipo == "story":
        inicio = min(max(round(inicio, 2), 0.0), max(duracao - DURACAO_MINIMA_TRECHO, 0.0))
        trecho = {"inicio": inicio, "fim": round(min(inicio + DURACAO_PADRAO_STORY, duracao), 2)}
        rotulo, proporcao, silencios = "Story", "9:16", {"intensidade": None}
    else:
        trecho, rotulo, silencios = {"inicio": 0.0, "fim": duracao}, "Reel", {"intensidade": "media"}
    visual = aplicar_modelo(modelo, identidade or {}) if modelo else {}
    return {
        "organizacao_id": organizacao_id,
        "midia_id": midia["_id"],
        "criado_por": criado_por,
        "nome": (nome or f"{rotulo} · {midia['nome']}")[:120],
        "tipo": tipo,
        "modelo_id": _id_do_modelo(modelo),
        "proporcao": proporcao,
        "trecho": trecho,
        "silencios": silencios,
        "enquadramento": {"x": 0.5, "y": 0.5, "zoom": 1.0},
        "audio": {"normalizar": True},
        "marca": visual.get("marca") or marca_padrao(identidade),
        "textos": visual.get("textos", []),
        "fundo": {**FUNDO_PADRAO, **visual.get("fundo", {})},
        "cor": {**COR_PADRAO, **visual.get("cor", {})},
        "versao": 1,
        "criado_em": momento,
        "atualizado_em": momento,
    }


def montar_exportacao(projeto: dict, criado_por, momento: datetime | None = None,
                      formato: str = "video", instante: float = 0.0) -> dict:
    """formato "imagem": um quadro só, no instante dado (segundos do vídeo final), em JPG."""
    if formato not in FORMATOS_EXPORTACAO:
        raise ValueError(f"Formato desconhecido: {formato}")
    momento = momento or datetime.now(TZ)
    return {
        "formato": formato,
        "instante": max(float(instante), 0.0),
        "organizacao_id": projeto["organizacao_id"],
        "projeto_id": projeto["_id"],
        "midia_id": projeto["midia_id"],
        "criado_por": criado_por,
        "nome": projeto["nome"],
        "versao_projeto": projeto["versao"],
        "configuracao": copy.deepcopy({campo: projeto.get(campo) for campo in CAMPOS_DO_VIDEO}),
        "status": STATUS_EXPORTACAO_PROCESSANDO,
        "arquivos": [],
        "duracao": None,
        "tamanho": None,
        "largura": PROPORCOES[projeto["proporcao"]][0],
        "altura": PROPORCOES[projeto["proporcao"]][1],
        "job_id": None,
        "erro": None,
        "criado_em": momento,
        "atualizado_em": momento,
        "concluido_em": None,
    }


def pasta_da_exportacao(organizacao_id, exportacao_id) -> str:
    return f"org_{organizacao_id}/exportacoes/{exportacao_id}"


def chave_exportacao(organizacao_id, exportacao_id, nome: str) -> str:
    return f"{pasta_da_exportacao(organizacao_id, exportacao_id)}/{nome}"


def _par(valor: float) -> int:
    return max(int(valor) // 2 * 2, 2)


def calcular_recorte(largura: int, altura: int, proporcao: str, x: float = 0.5, y: float = 0.5,
                     zoom: float = 1.0) -> dict:
    """
    Retângulo da gravação que vira o vídeo final. (x, y) é o centro desejado, em
    fração da largura e da altura; o recorte nunca sai da imagem.
    A mesma conta existe em apps/web/src/lib/recorte.ts, para a prévia bater com o render.
    """
    alvo_largura, alvo_altura = PROPORCOES[proporcao]
    razao = alvo_largura / alvo_altura
    if largura / altura > razao:
        recorte_largura, recorte_altura = altura * razao, float(altura)
    else:
        recorte_largura, recorte_altura = float(largura), largura / razao
    zoom = min(max(zoom, 1.0), ZOOM_MAXIMO)
    recorte_largura, recorte_altura = _par(recorte_largura / zoom), _par(recorte_altura / zoom)
    esquerda = min(max(x * largura - recorte_largura / 2, 0), largura - recorte_largura)
    topo = min(max(y * altura - recorte_altura / 2, 0), altura - recorte_altura)
    return {"x": _par(esquerda) if esquerda >= 2 else 0, "y": _par(topo) if topo >= 2 else 0,
            "largura": recorte_largura, "altura": recorte_altura}
