# -----------------------------------------------
# HolyCut — cultos de exemplo para ver o acervo cheio
#
#   docker compose exec worker-cpu python -m worker.semear_exemplos --agora
#   docker compose exec worker-cpu python -m worker.semear_exemplos --agora --igreja "Nome da igreja"
#   docker compose exec worker-cpu python -m worker.semear_exemplos --remover
#
# Cria 5 cultos fictícios na igreja escolhida. Cada um ganha um vídeo curto
# feito pelo FFmpeg a partir de uma foto (em worker/exemplos) e passa pelo
# caminho de verdade: a ingestão gera a prévia, a forma de onda e as capas.
# Depois entram uma transcrição de exemplo (com versículo citado), o estudo
# e um corte renderizado em 3 deles. Tudo fica marcado com "exemplo": true,
# e --remover apaga só isso. Os pregadores e as falas são inventados.
# -----------------------------------------------
import argparse
import logging
import shutil
import subprocess
import time
from datetime import timedelta
from pathlib import Path

from bson import ObjectId

from core.config import FFMPEG
from core.modelos.estudo import montar_estudo
from core.modelos.identidade import identidade_padrao
from core.modelos.job import montar_job
from core.modelos.midia import PRIORIDADE_INGESTAO, STATUS_ERRO, STATUS_PRONTA, montar_midia, pasta_da_midia
from core.modelos.projeto import montar_exportacao, montar_projeto, pasta_da_exportacao
from core.modelos.sermon import palavras_do_documento
from core.modelos.transcricao import montar_segmentos, montar_transcricao
from core.modelos.versiculo import detectar_versiculos
from core.utils import storage
from core.utils.mongo import agora, conectar

# -----------------------------------------------
# CONFIGURAÇÕES
# -----------------------------------------------
PASTA_FOTOS = Path(__file__).resolve().parent / "exemplos"
DURACAO_VIDEO = 40          # segundos
PRIORIDADE_RENDER = 3
ESPERA_MAXIMA_SEGUNDOS = 900
COLECOES_DA_ANALISE = ("transcricoes", "sugestoes", "rostos", "momentos", "estudos", "blocos")

CULTOS = [
    {"titulo": "Ele é Digno", "pregador": "Pr. André Lima (exemplo)", "serie": "Adoração", "dias": 2,
     "foto": "story-cruz.jpg", "corte": True,
     "fala": ["Boa noite igreja que alegria estar aqui com vocês",
              "Abra a sua Bíblia em Apocalipse capítulo 5 versículo 12",
              "Ele é digno de toda honra de toda glória e de todo louvor",
              "Quando a gente adora a Deus o coração muda de lugar",
              "Que nesta semana a sua vida inteira seja um culto a ele"]},
    {"titulo": "Deus cuida dos detalhes", "pregador": "Pra. Marta Souza (exemplo)", "serie": "Confiança", "dias": 9,
     "foto": "louvor-maos.jpg", "corte": True,
     "fala": ["Deus não esquece de nenhum detalhe da sua história",
              "Em Mateus capítulo 6 versículo 26 Jesus fala das aves do céu",
              "Se ele cuida dos pássaros ele vai cuidar de você também",
              "A ansiedade diminui quando a gente entrega o amanhã nas mãos dele",
              "Escreva hoje uma preocupação e ore entregando ela a Deus"]},
    {"titulo": "O caminho da graça", "pregador": "Pr. André Lima (exemplo)", "serie": "Adoração", "dias": 16,
     "foto": "cruz-banda.jpg", "corte": True,
     "fala": ["A graça chega antes de nós sabermos pedir",
              "Leia comigo Efésios capítulo 2 versículo 8",
              "Ninguém conquista a graça ela é presente de Deus",
              "Paulo entendeu isso quando encontrou Jesus no caminho",
              "Procure alguém que precisa de perdão e seja graça para essa pessoa"]},
    {"titulo": "Juntos mais fortes", "pregador": "Pra. Marta Souza (exemplo)", "serie": "Confiança", "dias": 23,
     "foto": "pregador-palco.jpg", "corte": False,
     "fala": ["A igreja não foi feita para caminhar sozinha",
              "Em Eclesiastes capítulo 4 versículo 9 diz que melhor são dois do que um",
              "Quando um cai o outro levanta e assim a fé fica de pé",
              "Davi tinha Jônatas e você precisa de amigos na fé",
              "Participe de uma célula nesta semana e chame alguém para ir junto"]},
    {"titulo": "Culto da família", "pregador": "Pr. Daniel Rocha (exemplo)", "serie": "", "dias": 30,
     "foto": "louvor-palco.jpg", "corte": False,
     "fala": ["Hoje é dia de celebrar a família que Deus nos deu",
              "Josué capítulo 24 versículo 15 diz eu e a minha casa serviremos ao Senhor",
              "A fé começa na mesa de casa e não só no templo",
              "Pais e filhos aprendem juntos a ouvir a voz de Deus",
              "Separe um momento nesta semana para orar com a sua família"]},
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[logging.StreamHandler()])


# -----------------------------------------------
# FUNÇÕES AUXILIARES
# -----------------------------------------------
def escolher_igreja(db, email: str | None, igreja: str | None = None) -> tuple[dict, dict]:
    """A igreja pelo id ou nome, ou a do e-mail; sem nenhum dos dois, a única cadastrada."""
    if igreja:
        filtro = {"_id": ObjectId(igreja)} if ObjectId.is_valid(igreja) else {"nome": igreja}
        encontradas = list(db.organizacoes.find(filtro).limit(2))
        if len(encontradas) != 1:
            raise SystemExit(f"Não achei uma igreja só com {igreja!r}. Use o id dela.")
        usuario = db.usuarios.find_one({"organizacao_id": encontradas[0]["_id"]})
        if usuario is None:
            raise SystemExit("A igreja não tem ninguém cadastrado.")
        return encontradas[0], usuario
    if email:
        usuario = db.usuarios.find_one({"email": email.strip().lower()})
        if usuario is None:
            raise SystemExit(f"Nenhuma pessoa com o e-mail {email}.")
    else:
        organizacoes = list(db.organizacoes.find({}, {"_id": 1}).limit(2))
        if len(organizacoes) != 1:
            raise SystemExit("Há mais de uma igreja (ou nenhuma). Diga qual com --igreja ou --email.")
        usuario = db.usuarios.find_one({"organizacao_id": organizacoes[0]["_id"]})
        if usuario is None:
            raise SystemExit("A igreja não tem ninguém cadastrado.")
    return db.organizacoes.find_one({"_id": usuario["organizacao_id"]}), usuario


def gerar_video(foto: Path, destino: Path):
    """Um vídeo 1280x720 que se aproxima devagar da foto, com um som que fala e pausa (para os silêncios)."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    quadros = DURACAO_VIDEO * 30
    comando = [
        FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
        "-loop", "1", "-i", str(foto),
        "-f", "lavfi", "-i", f"aevalsrc=0.25*sin(2*PI*190*t)*lt(mod(t\\,4)\\,3):s=48000:d={DURACAO_VIDEO}",
        "-filter_complex",
        f"[0:v]scale=2560:1440:force_original_aspect_ratio=increase,crop=2560:1440,"
        f"zoompan=z='min(1+on/{quadros}*0.15,1.15)':d={quadros}:s=1280x720:fps=30,format=yuv420p[v]",
        "-map", "[v]", "-map", "1:a", "-t", str(DURACAO_VIDEO),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-c:a", "aac", "-b:a", "128k", str(destino),
    ]
    subprocess.run(comando, check=True, timeout=600)


def transcricao_de_exemplo(organizacao_id, midia_id, fala: list[str]) -> dict:
    """As frases espalhadas pelos 40 s, uma palavra a cada 0,35 s, como o Whisper entregaria."""
    brutos, instante = [], 1.0
    for frase in fala:
        palavras = []
        for texto in frase.split():
            palavras.append({"texto": texto, "inicio": round(instante, 2), "fim": round(instante + 0.3, 2)})
            instante += 0.35
        brutos.append({"texto": frase + ".", "inicio": palavras[0]["inicio"], "fim": palavras[-1]["fim"],
                       "palavras": palavras})
        instante += 1.2
    documento = montar_transcricao(organizacao_id, midia_id, montar_segmentos(brutos), DURACAO_VIDEO, agora())
    documento["versiculos"] = detectar_versiculos(palavras_do_documento(documento))
    documento["exemplo"] = True
    return documento


def estudo_de_exemplo(organizacao_id, midia_id, transcricao: dict, fala: list[str]) -> dict | None:
    """O estudo passa pela mesma conferência do HolyStudy: só fica o que está na fala."""
    resposta = {
        "frases_centrais": [{"frase": frase, "importancia": 9 - indice} for indice, frase in enumerate(fala[2:4])],
        "temas": [palavra for palavra in fala[2].split() if len(palavra) > 5][:2],
        "personagens": ["Paulo", "Davi", "Jesus"],
        "perguntas": [{"pergunta": "O que essa frase muda na sua semana?", "frase_base": fala[2]}],
        "aplicacoes": [fala[4]],
    }
    estudo = montar_estudo([resposta], palavras_do_documento(transcricao), transcricao.get("versiculos") or [])
    return {"organizacao_id": organizacao_id, "midia_id": midia_id, "gerado_por_ia": True, "modelo": "exemplo",
            **estudo, "exemplo": True, "criado_em": agora()}


# -----------------------------------------------
# FUNÇÕES PRINCIPAIS
# -----------------------------------------------
def criar_cultos(db, organizacao: dict, usuario: dict) -> list[ObjectId]:
    """Cada culto entra como um envio comum: o original no armazenamento e a ingestão na fila."""
    ids = []
    for culto in CULTOS:
        momento = agora()
        midia = montar_midia(organizacao["_id"], usuario["_id"], f"{culto['titulo']}.mp4", 0, momento=momento)
        midia.update({
            "status": "processando", "exemplo": True, "enviado_em": momento,
            "ficha": {"data": (momento - timedelta(days=culto["dias"])).date().isoformat(),
                      "pregador": culto["pregador"], "serie": culto["serie"],
                      "descricao": "Culto de exemplo, para ver como o acervo fica com conteúdo."},
        })
        midia_id = db.midias.insert_one(midia).inserted_id
        original = storage.caminho_local(f"{pasta_da_midia(organizacao['_id'], midia_id)}/{midia['original']}")
        gerar_video(PASTA_FOTOS / culto["foto"], original)
        tamanho = original.stat().st_size
        job = montar_job("ingestao", organizacao["_id"], {"midia_id": str(midia_id)},
                         prioridade=PRIORIDADE_INGESTAO, criado_por=usuario["_id"])
        job_id = db.jobs.insert_one(job).inserted_id
        db.midias.update_one({"_id": midia_id}, {"$set": {"tamanho_total": tamanho, "bytes_recebidos": tamanho,
                                                          "job_ingestao_id": job_id}})
        db.transcricoes.insert_one(transcricao := transcricao_de_exemplo(organizacao["_id"], midia_id, culto["fala"]))
        estudo = estudo_de_exemplo(organizacao["_id"], midia_id, transcricao, culto["fala"])
        if estudo:
            db.estudos.insert_one(estudo)
        logging.info(f"[{organizacao['nome']}] Culto de exemplo na fila: {culto['titulo']}")
        ids.append(midia_id)
    return ids


def esperar_ingestao(db, ids: list[ObjectId]) -> list[dict]:
    """O worker processa enquanto o script espera. Devolve as gravações prontas."""
    limite = time.monotonic() + ESPERA_MAXIMA_SEGUNDOS
    while time.monotonic() < limite:
        midias = list(db.midias.find({"_id": {"$in": ids}}))
        if all(midia["status"] in (STATUS_PRONTA, STATUS_ERRO) for midia in midias):
            return [midia for midia in midias if midia["status"] == STATUS_PRONTA]
        time.sleep(3)
    logging.warning("A ingestão passou de 15 min. Os cortes ficam só para as gravações já prontas.")
    return list(db.midias.find({"_id": {"$in": ids}, "status": STATUS_PRONTA}))


def criar_cortes(db, organizacao: dict, usuario: dict, midias: list[dict]):
    """Um Reel de 15 s com legenda em 3 cultos, renderizado pela fila como uma exportação comum."""
    identidade = {**identidade_padrao(organizacao["nome"]), **(organizacao.get("identidade") or {})}
    titulos = {culto["titulo"] for culto in CULTOS if culto["corte"]}
    for midia in midias:
        if midia["nome"] not in titulos:
            continue
        projeto = montar_projeto(organizacao["_id"], midia, usuario["_id"], f"Reel · {midia['nome']}",
                                 identidade=identidade)
        projeto["partes"] = [{"id": "p1", "inicio": 1.0, "fim": 16.0}]
        projeto["exemplo"] = True
        projeto["_id"] = db.projetos.insert_one(projeto).inserted_id
        exportacao = montar_exportacao(projeto, usuario["_id"])
        exportacao["exemplo"] = True
        exportacao["_id"] = db.exportacoes.insert_one(exportacao).inserted_id
        job = montar_job("renderizacao", organizacao["_id"], {"exportacao_id": str(exportacao["_id"])},
                         prioridade=PRIORIDADE_RENDER, criado_por=usuario["_id"])
        job_id = db.jobs.insert_one(job).inserted_id
        db.exportacoes.update_one({"_id": exportacao["_id"]}, {"$set": {"job_id": job_id}})
        logging.info(f"[{organizacao['nome']}] Corte de exemplo na fila: {projeto['nome']}")


def remover_exemplos(db):
    """Apaga só o que este script criou: gravações, análises, projetos, exportações, jobs e arquivos."""
    midias = list(db.midias.find({"exemplo": True}, {"_id": 1, "organizacao_id": 1}))
    for midia in midias:
        for colecao in COLECOES_DA_ANALISE:
            db[colecao].delete_many({"midia_id": midia["_id"]})
        for exportacao in db.exportacoes.find({"midia_id": midia["_id"]}, {"_id": 1}):
            shutil.rmtree(storage.caminho_local(pasta_da_exportacao(midia["organizacao_id"], exportacao["_id"])),
                          ignore_errors=True)
        db.exportacoes.delete_many({"midia_id": midia["_id"]})
        db.projetos.delete_many({"midia_id": midia["_id"]})
        db.jobs.delete_many({"entrada.midia_id": str(midia["_id"])})
        shutil.rmtree(storage.caminho_local(pasta_da_midia(midia["organizacao_id"], midia["_id"])), ignore_errors=True)
        db.midias.delete_one({"_id": midia["_id"]})
    logging.info(f"{len(midias)} cultos de exemplo removidos.")


# -----------------------------------------------
# EXECUÇÃO
# -----------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Cultos de exemplo para ver o acervo do HolyCut cheio")
    parser.add_argument("--agora", action="store_true", help="Cria os 5 cultos de exemplo agora")
    parser.add_argument("--automatico", action="store_true", help="Sem perguntas (o script já não pergunta nada)")
    parser.add_argument("--email", default=None, help="E-mail de quem é da igreja que recebe os exemplos")
    parser.add_argument("--igreja", default=None, help="Id ou nome da igreja que recebe os exemplos")
    parser.add_argument("--remover", action="store_true", help="Apaga os cultos de exemplo")
    args = parser.parse_args()

    db = conectar()
    if db is None:
        raise SystemExit("Sem conexão com o MongoDB.")
    if args.remover:
        remover_exemplos(db)
        return
    if not args.agora:
        parser.print_help()
        return
    if db.midias.count_documents({"exemplo": True}):
        raise SystemExit("Já existem cultos de exemplo. Rode com --remover antes de criar de novo.")
    organizacao, usuario = escolher_igreja(db, args.email, args.igreja)
    ids = criar_cultos(db, organizacao, usuario)
    logging.info("Esperando a ingestão (prévia, forma de onda e capas)...")
    prontas = esperar_ingestao(db, ids)
    criar_cortes(db, organizacao, usuario, prontas)
    logging.info(f"Pronto: {len(prontas)} cultos de exemplo no acervo de {organizacao['nome']}. "
                 "Os cortes terminam de renderizar em alguns minutos.")


if __name__ == "__main__":
    main()
