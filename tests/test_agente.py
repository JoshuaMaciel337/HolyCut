# Agente do OBS: funções que não precisam de rede
import base64
import os

from agente.agendador_gravacoes import VISTO, conferir_pasta, gravacao_terminou, listar_gravacoes, metadados_tus


def criar(pasta, nome, tamanho=100, modificado=None):
    arquivo = pasta / nome
    arquivo.write_bytes(b"x" * tamanho)
    if modificado is not None:
        os.utime(arquivo, (modificado, modificado))
    return arquivo


def test_lista_so_videos_e_deixa_o_mkv_convertido_de_fora(tmp_path):
    criar(tmp_path, "culto.mkv", modificado=1000)
    criar(tmp_path, "culto.mp4", modificado=1100)          # o OBS converteu o MKV
    criar(tmp_path, "ensaio.mkv", modificado=900)          # este não foi convertido
    criar(tmp_path, "notas.txt")
    (tmp_path / "subpasta.mp4").mkdir()
    assert [a.name for a in listar_gravacoes(tmp_path)] == ["ensaio.mkv", "culto.mp4"]


def test_gravacao_terminou():
    # O arquivo mudou pela última vez em 1990 s e foi observado assim a partir de 2000 s
    parado = {"tamanho": 500, "modificado": 1990.0, "observado_desde": 2000.0}
    assert not gravacao_terminou({}, 500, 1990.0, 2000.0, minutos=2)            # nunca observado
    assert not gravacao_terminou(parado, 600, 2150.0, 2200.0, minutos=2)        # ainda crescendo
    assert not gravacao_terminou(parado, 500, 1990.0, 2100.0, minutos=2)        # parado há só 100 s
    assert gravacao_terminou(parado, 500, 1990.0, 2120.0, minutos=2)            # 2 min parado
    antigo = {"tamanho": 500, "modificado": 1000.0, "observado_desde": 5000.0}
    assert gravacao_terminou(antigo, 500, 1000.0, 5000.0, minutos=2)            # parado há mais de 10 min
    assert not gravacao_terminou({"tamanho": 0, "modificado": 1.0, "observado_desde": 0.0}, 0, 1.0, 999.0, 2)


def test_metadados_do_envio():
    metadados = dict(par.split(" ") for par in metadados_tus("Culto de domingo.MP4").split(","))
    assert base64.b64decode(metadados["filename"]).decode() == "Culto de domingo.MP4"
    assert base64.b64decode(metadados["filetype"]).decode() == "video/mp4"


def test_primeira_vez_so_marca_o_que_ja_existia(tmp_path):
    pasta = tmp_path / "obs"
    pasta.mkdir()
    criar(pasta, "domingo-passado.mp4", tamanho=300)
    estado = {}
    configuracao = {"servidor": "http://sem-rede.invalid", "chave": "hc_x", "pasta": str(pasta), "minutos_estavel": 0}
    assert conferir_pasta(configuracao, estado, tmp_path / "estado.json") == []
    registro = estado["arquivos"][str(pasta / "domingo-passado.mp4")]
    assert registro == {"situacao": VISTO, "tamanho": 300}
    assert "iniciado_em" in estado and (tmp_path / "estado.json").is_file()
    # Nas voltas seguintes ele continua de fora (a não ser que mude de tamanho)
    assert conferir_pasta(configuracao, estado, tmp_path / "estado.json") == []
