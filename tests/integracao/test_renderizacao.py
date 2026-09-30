# Renderização de ponta a ponta: ingestão, projeto, exportação e o vídeo final.
# FFmpeg de verdade e MongoDB de verdade. Pulado quando o FFmpeg não está instalado.
import io
import json
import re
import shutil
import subprocess

import pytest
from bson import ObjectId
from PIL import Image

from core.modelos.identidade import chave_logo
from core.modelos.job import montar_job
from core.modelos.midia import chave_arquivo, montar_midia
from core.modelos.projeto import chave_exportacao, montar_exportacao, montar_projeto
from core.utils import storage
from core.utils.arte import preparar_logo
from core.utils.fila import enfileirar_job, pegar_proximo_job
from worker.worker_principal import processar_job

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="FFmpeg não instalado")

# 3 s de som e 1 s de silêncio, repetindo: silêncios em 3-4, 7-8, 11-12...
AUDIO_COM_PAUSAS = "aevalsrc=0.5*sin(2*PI*220*t)*lt(mod(t\\,4)\\,3):s=48000:d={d}"


def gerar_gravacao(caminho, largura, altura, duracao):
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-f", "lavfi", "-i", f"testsrc2=size={largura}x{altura}:rate=30:duration={duracao}",
         "-f", "lavfi", "-i", AUDIO_COM_PAUSAS.format(d=duracao),
         "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(caminho)],
        check=True, timeout=120)


def rodar(db, tipo):
    job = pegar_proximo_job(db, [tipo], "w-teste")
    assert job is not None, f"nenhum job {tipo} na fila"
    resultado = processar_job(db, job, "w-teste")
    assert resultado == "concluido", db.jobs.find_one({"_id": job["_id"]}).get("erro")


def midia_pronta(db, largura=1920, altura=1080, duracao=20):
    midia = montar_midia(ObjectId(), ObjectId(), "Culto.mp4", 1)
    midia["_id"] = db.midias.insert_one(midia).inserted_id
    original = storage.caminho_local(chave_arquivo(midia["organizacao_id"], midia["_id"], midia["original"]))
    original.parent.mkdir(parents=True, exist_ok=True)
    gerar_gravacao(original, largura, altura, duracao)
    db.midias.update_one({"_id": midia["_id"]}, {"$set": {"status": "processando"}})
    enfileirar_job(db, montar_job("ingestao", midia["organizacao_id"], {"midia_id": str(midia["_id"])}))
    rodar(db, "ingestao")
    return db.midias.find_one({"_id": midia["_id"]})


def exportar(db, midia, **alteracoes):
    projeto = {**montar_projeto(midia["organizacao_id"], midia, None), **alteracoes}
    projeto["_id"] = db.projetos.insert_one(projeto).inserted_id
    exportacao = montar_exportacao(projeto, None)
    exportacao["_id"] = db.exportacoes.insert_one(exportacao).inserted_id
    enfileirar_job(db, montar_job("renderizacao", midia["organizacao_id"], {"exportacao_id": str(exportacao["_id"])}))
    rodar(db, "renderizacao")
    exportacao = db.exportacoes.find_one({"_id": exportacao["_id"]})
    video = storage.caminho_local(chave_exportacao(exportacao["organizacao_id"], exportacao["_id"], "video.mp4"))
    return exportacao, video


def sondar(caminho):
    saida = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height,duration",
                            "-of", "json", str(caminho)], capture_output=True, text=True, check=True).stdout
    streams = {s["codec_type"]: s for s in json.loads(saida)["streams"]}
    return streams["video"], streams.get("audio")


def volume_integrado(caminho) -> float:
    comando = ["ffmpeg", "-hide_banner", "-nostats", "-i", str(caminho), "-af", "ebur128", "-f", "null", "-"]
    saida = subprocess.run(comando, capture_output=True, text=True, timeout=120).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", saida)[-1])


def test_reel_9_16_com_corte_de_silencios(db_limpo):
    midia = midia_pronta(db_limpo)
    exportacao, video = exportar(db_limpo, midia, trecho={"inicio": 2.0, "fim": 18.0})

    # 16 s escolhidos menos 4 silêncios de cerca de 0,75 s (perto de 3-4, 7-8, 11-12 e 15-16).
    # O AAC da gravação suaviza as bordas de cada silêncio em alguns milissegundos.
    assert exportacao["status"] == "pronta"
    assert exportacao["trechos"] == 5
    assert 12.8 < exportacao["duracao"] < 13.2
    fluxo_video, fluxo_audio = sondar(video)
    assert (fluxo_video["width"], fluxo_video["height"]) == (1080, 1920)
    assert abs(float(fluxo_video["duration"]) - exportacao["duracao"]) < 0.05   # o arquivo tem o que foi planejado
    # Áudio e vídeo terminam juntos: não houve deriva de sincronia nos cortes
    assert abs(float(fluxo_audio["duration"]) - float(fluxo_video["duration"])) < 0.07
    assert -15.5 < volume_integrado(video) < -12.5          # normalizado para -14 LUFS
    assert set(exportacao["arquivos"]) == {"video.mp4", "capa.jpg"}


def test_reel_sem_corte_de_video_gravado_em_pe(db_limpo):
    midia = midia_pronta(db_limpo, largura=1080, altura=1920, duracao=6)
    exportacao, video = exportar(db_limpo, midia, silencios={"intensidade": None},
                                 enquadramento={"x": 0.5, "y": 0.5, "zoom": 1.5})
    assert abs(exportacao["duracao"] - 6.0) < 0.1
    fluxo_video, fluxo_audio = sondar(video)
    assert (fluxo_video["width"], fluxo_video["height"]) == (1080, 1920)
    assert abs(float(fluxo_audio["duration"]) - float(fluxo_video["duration"])) < 0.07


def test_trecho_todo_em_silencio_falha_sem_novas_tentativas(db_limpo):
    midia = midia_pronta(db_limpo, duracao=8)
    projeto = {**montar_projeto(midia["organizacao_id"], midia, None), "trecho": {"inicio": 3.2, "fim": 3.8}}
    projeto["_id"] = db_limpo.projetos.insert_one(projeto).inserted_id
    exportacao = montar_exportacao(projeto, None)
    exportacao["_id"] = db_limpo.exportacoes.insert_one(exportacao).inserted_id
    enfileirar_job(db_limpo, montar_job("renderizacao", midia["organizacao_id"],
                                        {"exportacao_id": str(exportacao["_id"])}))
    job = pegar_proximo_job(db_limpo, ["renderizacao"], "w-teste")
    assert processar_job(db_limpo, job, "w-teste") == "erro"
    salvo = db_limpo.exportacoes.find_one({"_id": exportacao["_id"]})
    assert salvo["status"] == "erro"
    assert "ficou vazio" in salvo["erro"]


def test_reel_com_logo_e_texto_da_igreja(db_limpo):
    midia = midia_pronta(db_limpo, duracao=6)
    organizacao_id = midia["organizacao_id"]
    db_limpo.organizacoes.insert_one({"_id": organizacao_id, "nome": "Igreja Teste",
                                      "identidade": {"cor_destaque": "#00C853", "logo": True}})
    logo = Image.new("RGBA", (400, 200), (255, 0, 0, 255))   # logo vermelho
    saida_logo = io.BytesIO()
    logo.save(saida_logo, format="PNG")
    storage.salvar_bytes(chave_logo(organizacao_id), preparar_logo(saida_logo.getvalue()))

    exportacao, video = exportar(
        db_limpo, midia, silencios={"intensidade": None},
        marca={"logo": True, "posicao": "topo_esquerda", "tamanho": 0.25, "opacidade": 1.0},
        textos=[{"id": "t", "texto": "Ele é digno", "estilo": "destaque", "posicao": "base", "inicio": 0, "fim": None},
                {"id": "u", "texto": "Só no começo", "estilo": "limpo", "posicao": "centro", "inicio": 0, "fim": 1}])
    assert exportacao["status"] == "pronta", exportacao.get("erro")

    def quadro(segundos):
        bruto = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(segundos), "-i", str(video), "-frames:v", "1",
                                "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
        return Image.frombytes("RGB", (1080, 1920), bruto)

    depois = quadro(3.0)
    r, g, b = depois.getpixel((64 + 130, 64 + 60))                  # meio do logo, no canto de cima
    assert r > 200 and g < 60 and b < 60
    faixa = [depois.getpixel((x, y)) for x in range(200, 880, 20) for y in range(1450, 1700, 10)]
    assert any(g > 150 and r < 80 and b < 130 for r, g, b in faixa)  # faixa verde da igreja atrás do texto
    antes = quadro(0.3)
    centro_antes = [antes.getpixel((x, 960)) for x in range(300, 780, 5)]
    centro_depois = [depois.getpixel((x, 960)) for x in range(300, 780, 5)]
    assert centro_antes != centro_depois                              # o texto do centro só aparece no primeiro segundo


def brilho_e_nitidez(caminho_ou_imagem):
    """Brilho médio e uma medida simples de nitidez (diferença entre pixels vizinhos)."""
    imagem = (caminho_ou_imagem if isinstance(caminho_ou_imagem, Image.Image) else Image.open(caminho_ou_imagem))
    cinza = imagem.convert("L").resize((270, 480))
    pixels = list(cinza.get_flattened_data())
    brilho = sum(pixels) / len(pixels)
    nitidez = sum(abs(pixels[i] - pixels[i + 1]) for i in range(len(pixels) - 1)) / len(pixels)
    return brilho, nitidez


def quadro_do_video(video, segundos=2.0):
    bruto = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(segundos), "-i", str(video), "-frames:v", "1",
                            "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    return Image.frombytes("RGB", (1080, 1920), bruto)


def test_story_com_fundo_escurecido_e_desfocado(db_limpo):
    midia = midia_pronta(db_limpo, duracao=6)
    _, sem_fundo = exportar(db_limpo, midia, silencios={"intensidade": None})
    exportacao, com_fundo = exportar(db_limpo, midia, silencios={"intensidade": None}, tipo="story",
                                     fundo={"escurecer": 0.6, "desfoque": 12})
    assert exportacao["status"] == "pronta"
    brilho_normal, nitidez_normal = brilho_e_nitidez(quadro_do_video(sem_fundo))
    brilho_story, nitidez_story = brilho_e_nitidez(quadro_do_video(com_fundo))
    assert brilho_story < brilho_normal * 0.55          # escurecido em 60%
    assert nitidez_story < nitidez_normal * 0.5         # desfocado
    # Escurecer em RGB preserva a cor, como na prévia do navegador: amarelo continua amarelo
    r, g, b = quadro_do_video(com_fundo).crop((60, 1200, 300, 1400)).resize((1, 1)).getpixel((0, 0))
    assert r > 80 and g > 80 and b < 30


def test_exportar_imagem_do_story(db_limpo):
    midia = midia_pronta(db_limpo, duracao=8)
    projeto = {**montar_projeto(midia["organizacao_id"], midia, None), "silencios": {"intensidade": None},
               "fundo": {"escurecer": 0.5, "desfoque": 0},
               "textos": [
                   {"id": "t", "texto": "Culto de hoje", "estilo": "limpo", "posicao": "centro", "inicio": 0, "fim": 3},
                   {"id": "u", "texto": "Depois", "estilo": "limpo", "posicao": "topo", "inicio": 5, "fim": None},
               ]}
    projeto["_id"] = db_limpo.projetos.insert_one(projeto).inserted_id
    exportacao = montar_exportacao(projeto, None, formato="imagem", instante=2.0)
    exportacao["_id"] = db_limpo.exportacoes.insert_one(exportacao).inserted_id
    enfileirar_job(db_limpo, montar_job("renderizacao", midia["organizacao_id"],
                                        {"exportacao_id": str(exportacao["_id"])}))
    rodar(db_limpo, "renderizacao")

    salvo = db_limpo.exportacoes.find_one({"_id": exportacao["_id"]})
    assert salvo["status"] == "pronta"
    assert set(salvo["arquivos"]) == {"imagem.jpg", "capa.jpg"}
    pasta = storage.caminho_local(f"org_{salvo['organizacao_id']}/exportacoes/{salvo['_id']}")
    imagem = Image.open(pasta / "imagem.jpg")
    assert imagem.size == (1080, 1920)
    assert Image.open(pasta / "capa.jpg").size[0] == 540
    centro = [imagem.getpixel((x, 960)) for x in range(300, 780, 4)]
    assert any(min(p) > 225 for p in centro)                 # o texto do centro (0 a 3 s) aparece aos 2 s
    topo = [imagem.getpixel((x, y)) for x in range(300, 780, 6) for y in range(230, 300, 5)]
    assert not any(min(p) > 235 for p in topo)               # o texto de depois dos 5 s não aparece
    assert sorted(p.name for p in pasta.iterdir()) == ["capa.jpg", "imagem.jpg"]   # sem sobras
