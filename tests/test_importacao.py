# Importar pelo link: os formatos de link e de canal, o feed RSS e as datas
from datetime import UTC, datetime

import pytest
from bson import ObjectId

from core.modelos.importacao import (
    MAXIMO_VISTOS,
    data_do_video,
    do_canal,
    lembrar_visto,
    ler_feed,
    ler_link,
    montar_importacao,
    nome_de_arquivo_do_video,
    normalizar_canal,
    precisa_esperar,
    titulo_do_video,
    videos_novos,
)

VIDEO = "dQw4w9WgXcQ"
CANAL = "UC" + "a1B2c3D4e5F6g7H8i9J0kL"
DRIVE = "1AbCdEfGhIjKlMnOpQrStUvWxYz0123456"

FEED = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns="http://www.w3.org/2005/Atom">
  <yt:channelId>{CANAL}</yt:channelId>
  <entry><yt:videoId>BBBBBBBBBBB</yt:videoId><title>Culto de Domingo</title>
    <published>2026-09-28T13:00:00+00:00</published></entry>
  <entry><yt:videoId>AAAAAAAAAAA</yt:videoId><title>Culto de Quarta</title>
    <published>2026-09-24T22:00:00+00:00</published></entry>
  <entry><yt:videoId>curto</yt:videoId><title>Sem id válido</title>
    <published>2026-09-20T22:00:00+00:00</published></entry>
</feed>"""


@pytest.mark.parametrize("url", [
    f"https://www.youtube.com/watch?v={VIDEO}&t=120s", f"youtube.com/watch?v={VIDEO}", f"https://youtu.be/{VIDEO}?si=x",
    f"https://www.youtube.com/live/{VIDEO}?feature=share", f"https://m.youtube.com/watch?v={VIDEO}",
    f"https://www.youtube.com/shorts/{VIDEO}",
])
def test_links_do_youtube(url):
    assert ler_link(url) == {"origem": "youtube", "id": VIDEO, "url": f"https://www.youtube.com/watch?v={VIDEO}"}


@pytest.mark.parametrize("url", [
    f"https://drive.google.com/file/d/{DRIVE}/view?usp=sharing", f"https://drive.google.com/open?id={DRIVE}",
    f"https://drive.google.com/uc?id={DRIVE}&export=download",
])
def test_links_do_drive(url):
    assert ler_link(url) == {"origem": "drive", "id": DRIVE, "url": f"https://drive.google.com/file/d/{DRIVE}/view"}


@pytest.mark.parametrize("url", ["https://vimeo.com/123", "https://www.youtube.com/watch?v=curto",
                                 "https://www.youtube.com/@igreja", "texto qualquer", ""])
def test_links_que_nao_servem(url):
    assert ler_link(url) is None


def test_canal_pelo_arroba_pelo_endereco_ou_pelo_id():
    assert normalizar_canal("@IgrejaViva") == {"id": None, "handle": "@igrejaviva"}
    assert normalizar_canal("https://www.youtube.com/@IgrejaViva/videos") == {"id": None, "handle": "@igrejaviva"}
    assert normalizar_canal("IgrejaViva") == {"id": None, "handle": "@igrejaviva"}
    assert normalizar_canal(f"youtube.com/channel/{CANAL}") == {"id": CANAL, "handle": None}
    assert normalizar_canal(CANAL) == {"id": CANAL, "handle": None}
    with pytest.raises(ValueError, match="Não reconheci"):
        normalizar_canal("a")


def test_o_video_e_do_canal_da_igreja():
    metadados = {"channel_id": CANAL, "uploader_id": "@IgrejaViva", "channel_url": f"https://www.youtube.com/channel/{CANAL}"}
    assert do_canal(metadados, {"id": CANAL, "handle": None})
    assert do_canal(metadados, {"id": None, "handle": "@igrejaviva"})
    assert do_canal({"uploader_url": "https://www.youtube.com/@igrejaviva"}, {"id": None, "handle": "@igrejaviva"})
    assert not do_canal(metadados, {"id": "UC" + "x" * 22, "handle": "@outraigreja"})
    assert not do_canal(metadados, None)


def test_live_no_ar_espera_e_a_que_terminou_entra():
    assert precisa_esperar({"live_status": "is_live"}) and precisa_esperar({"live_status": "is_upcoming"})
    assert precisa_esperar({"live_status": "post_live"})   # o YouTube ainda prepara o vídeo da live
    assert not precisa_esperar({"live_status": "was_live"}) and not precisa_esperar({"live_status": "not_live"})


def test_data_titulo_e_nome_do_arquivo():
    # 01:30 em UTC ainda é dia 27 em São Paulo
    assert data_do_video({"release_timestamp": datetime(2026, 9, 28, 1, 30, tzinfo=UTC).timestamp()}) == "2026-09-27"
    assert data_do_video({"upload_date": "20260928"}) == "2026-09-28"
    assert data_do_video({}) is None
    assert titulo_do_video({"title": "  Culto   de Domingo "}) == "Culto de Domingo"
    assert titulo_do_video({}) == "Culto"
    assert nome_de_arquivo_do_video('Culto: "Fé" / Domingo?', ".mp4") == "Culto Fé Domingo.mp4"


def test_feed_e_os_videos_novos():
    videos = ler_feed(FEED)
    assert [video["video_id"] for video in videos] == ["BBBBBBBBBBB", "AAAAAAAAAAA"]
    assert videos[0]["titulo"] == "Culto de Domingo" and videos[0]["publicado"].tzinfo is not None
    assert ler_feed("isso não é xml") == []
    # Do mais antigo ao mais novo, sem o que já foi visto
    assert [video["video_id"] for video in videos_novos(videos, [])] == ["AAAAAAAAAAA", "BBBBBBBBBBB"]
    assert [video["video_id"] for video in videos_novos(videos, ["AAAAAAAAAAA"])] == ["BBBBBBBBBBB"]
    vistos = lembrar_visto([f"v{indice}" for indice in range(MAXIMO_VISTOS)], "novo")
    assert len(vistos) == MAXIMO_VISTOS and vistos[-1] == "novo" and "v0" not in vistos


def test_montar_importacao():
    organizacao_id, pessoa = ObjectId(), ObjectId()
    link = ler_link(f"https://youtu.be/{VIDEO}")
    midia, job = montar_importacao(organizacao_id, pessoa, link)
    assert midia["status"] == "processando" and midia["nome"] == "Importando do YouTube"
    assert midia["importacao"] == link and midia["original"] == "original.mp4"
    assert job["tipo"] == "importar_link" and job["entrada"]["url"] == link["url"] and job["prioridade"] == 5
