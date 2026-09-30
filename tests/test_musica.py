# Cadastro de músicas da biblioteca: funções puras
import pytest

from core.modelos.musica import ErroLicenca, chave_musica, montar_musica, validar_licenca


def test_licenca_obrigatoria():
    with pytest.raises(ErroLicenca, match="licença"):
        validar_licenca("", "")
    with pytest.raises(ErroLicenca):
        validar_licenca("baixei_do_youtube", "")
    for licenca in ("propria", "dominio_publico", "licenciada"):
        validar_licenca(licenca, "")


def test_cc_by_exige_atribuicao():
    with pytest.raises(ErroLicenca, match="atribuição"):
        validar_licenca("cc_by", "   ")
    validar_licenca("cc_by", "Autor X, via site Y (CC BY 4.0)")


def test_montar_musica():
    musica = montar_musica("org1", "u1", "  Hino   de  louvor ", "Coral  da igreja", "propria")
    assert (musica["titulo"], musica["artista"]) == ("Hino de louvor", "Coral da igreja")
    assert musica["status"] == "aguardando_arquivo"
    assert musica["duracao"] is None and musica["original"] is None
    assert chave_musica("org1", "m1", "musica.m4a") == "org_org1/musicas/m1/musica.m4a"
