# -----------------------------------------------
# Tarefa "preparar_musica" — deixa a faixa da biblioteca pronta para a mixagem
# Converte para AAC 48 kHz estéreo e guarda a duração.
# -----------------------------------------------
from collections.abc import Callable

from bson import ObjectId

from core.modelos.job import ErroDefinitivo
from core.modelos.musica import ARQUIVO_MUSICA, STATUS_ERRO, STATUS_PRONTA, chave_musica
from core.utils import storage
from core.utils.ffmpeg import ErroFFmpeg, executar_ffmpeg, resumir_sondagem, sondar
from core.utils.mongo import agora


def marcar_musica_com_erro(db, job: dict, mensagem: str):
    musica_id = (job.get("entrada") or {}).get("musica_id")
    if musica_id:
        db.musicas.update_one({"_id": ObjectId(musica_id)}, {"$set": {
            "status": STATUS_ERRO, "erro": mensagem, "atualizado_em": agora(),
        }})


def executar_preparar_musica(db, job: dict, reportar: Callable[[int, str], None]) -> dict:
    musica_id = ObjectId(job["entrada"]["musica_id"])
    musica = db.musicas.find_one({"_id": musica_id})
    if musica is None or not musica.get("original"):
        raise ErroDefinitivo("A música foi excluída antes de ficar pronta.")
    organizacao_id = musica["organizacao_id"]
    original = storage.caminho_local(chave_musica(organizacao_id, musica_id, musica["original"]))
    if not original.is_file():
        raise ErroDefinitivo("O arquivo da música não foi encontrado no servidor. Envie de novo.")

    reportar(5, "Lendo a música")
    try:
        resumo = resumir_sondagem(sondar(original))
    except ErroFFmpeg as e:
        raise ErroDefinitivo("O arquivo não é um áudio válido.") from e
    if not resumo["audio"] or not resumo["duracao"]:
        raise ErroDefinitivo("O arquivo não tem áudio que dê para usar.")

    saida = storage.caminho_local(chave_musica(organizacao_id, musica_id, ARQUIVO_MUSICA))
    executar_ffmpeg(["-i", str(original), "-map", "0:a:0", "-vn", "-ac", "2", "-ar", "48000",
                     "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(saida)],
                    resumo["duracao"], lambda f: reportar(10 + int(f * 85), "Preparando a música"))
    storage.remover(chave_musica(organizacao_id, musica_id, musica["original"]))

    momento = agora()
    db.musicas.update_one({"_id": musica_id}, {"$set": {
        "status": STATUS_PRONTA, "duracao": resumo["duracao"], "original": None, "erro": None,
        "atualizado_em": momento,
    }})
    reportar(100, "Música pronta")
    return {"musica_id": str(musica_id), "duracao": resumo["duracao"]}
