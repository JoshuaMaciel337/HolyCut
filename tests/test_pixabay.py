# A Pixabay só entrega arquivo de um host dela, e a chave não aparece no erro.
import pytest

from core.modelos.banco import consulta_da_frase, credito
from core.utils.pixabay import ErroPixabay, baixar_arquivo, obter, resumir_imagem, resumir_video, url_permitida


def test_so_aceita_https_da_pixabay():
    assert url_permitida("https://cdn.pixabay.com/video/a.mp4")
    assert url_permitida("https://pixabay.com/videos/id-1/")
    assert not url_permitida("http://cdn.pixabay.com/a.mp4")
    assert not url_permitida("https://evil.example/cdn.pixabay.com/a.mp4")
    assert not url_permitida("https://pixabay.com.evil/a.mp4")


def test_resumo_prefere_a_foto_grande_e_o_video_medio():
    foto = resumir_imagem({
        "id": 7, "tags": "igreja, luz", "user": "Ana", "pageURL": "https://pixabay.com/photos/7/",
        "largeImageURL": "https://pixabay.com/get/grande.jpg",
        "webformatURL": "https://pixabay.com/get/web.jpg",
        "previewURL": "https://cdn.pixabay.com/mini.jpg",
        "imageWidth": 1920, "imageHeight": 1080,
    })
    assert foto["arquivo"].endswith("grande.jpg") and foto["nome"] == "igreja"

    video = resumir_video({
        "id": 9, "tags": "ceu", "user": "João", "pageURL": "https://pixabay.com/videos/9/", "duration": 12,
        "videos": {
            "large": {"url": "", "width": 1920, "height": 1080, "size": 0},
            "medium": {"url": "https://cdn.pixabay.com/v.mp4", "thumbnail": "https://cdn.pixabay.com/t.jpg",
                       "width": 1280, "height": 720, "size": 1000},
        },
    })
    assert video["arquivo"].endswith("v.mp4") and video["duracao"] == 12
    assert resumir_imagem({"id": 1, "largeImageURL": "https://evil.example/a.jpg", "previewURL": "https://x/a"}) is None


def test_erro_de_download_nao_carrega_a_chave(monkeypatch):
    from urllib import error

    def falhar(pedido, timeout=60):
        raise error.HTTPError("https://pixabay.com/api/", 401, "no", hdrs=None, fp=None)

    monkeypatch.setattr("core.utils.pixabay.request.urlopen", falhar)
    monkeypatch.setattr("core.utils.pixabay.PIXABAY_API_KEY", "chave-secreta-de-teste")
    with pytest.raises(ErroPixabay, match="respondeu 401") as erro:
        obter("imagem", 3)
    assert "chave-secreta" not in str(erro.value)


def test_video_sem_mp4_e_recusado(monkeypatch):
    monkeypatch.setattr("core.utils.pixabay._pedir", lambda url, limite: b"nao-e-video")
    with pytest.raises(ErroPixabay, match="MP4"):
        baixar_arquivo("https://cdn.pixabay.com/v.mp4", "video")


def test_sem_modelo_a_busca_e_a_propria_frase(monkeypatch):
    monkeypatch.setattr("core.modelos.banco.MODO_IA", "simulado")
    assert consulta_da_frase("a luz entra pela janela da igreja")["consulta"] == "a luz entra pela janela da igreja"
    assert consulta_da_frase("  ")["usar"] is False
    assert credito("Ana") == "Ana · Pixabay"


def test_resposta_invalida_nao_mostra_o_corpo(monkeypatch):
    monkeypatch.setattr("core.utils.pixabay._pedir", lambda url, limite: b"nao-json")
    monkeypatch.setattr("core.utils.pixabay.PIXABAY_API_KEY", "chave-secreta-de-teste")
    monkeypatch.setattr("core.utils.pixabay.configurada", lambda: True)
    with pytest.raises(ErroPixabay, match="inválida") as erro:
        obter("video", 1)
    assert "chave-secreta" not in str(erro.value)
