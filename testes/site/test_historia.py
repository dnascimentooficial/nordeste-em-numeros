from pathlib import Path

import pytest
import yaml

from nordeste.site.conteudo import ErroConteudo
from nordeste.site.dados import Ponto
from nordeste.site.historia import (
    Epoca,
    Historia,
    ImagemHistorica,
    Marco,
    NumeroHistorico,
    TIPOS,
    carregar_historia,
    parcela_do_nordeste,
)

RAIZ = Path(__file__).resolve().parents[2]

CENSOS = "ano,populacao_nordeste,populacao_brasil,fonte\n1872,4638560,9930478,Fixture de teste\n"


def _texto(palavras: int) -> str:
    return " ".join(["palavra"] * palavras)


def _epoca(i: int) -> dict:
    inicio = 1500 + 100 * i
    return {
        "id": str(inicio),
        "inicio": inicio,
        "fim": inicio + 100,
        "nome": f"Época {i}",
        "resumo": "Resumo de teste.",
        "texto": _texto(200),
        "marcos": [
            {"ano": inicio + 50, "titulo": "Segundo marco", "texto": "Texto do marco."},
            {"ano": inicio + 10, "titulo": "Primeiro marco", "texto": "Texto do marco."},
        ],
        "numeros": [{"valor": "10%", "legenda": "Legenda de teste", "tipo": "oficial", "fonte": "IBGE, tabela de teste"}],
        "o_que_ficou": "Frase de teste.",
        "fontes": [{"texto": "Obra de teste"}, {"texto": "Outra obra", "url": "https://exemplo.org/obra"}],
        "imagem": {
            "arquivo": f"epoca-{inicio}.webp",
            "titulo": "Título da imagem",
            "autor": "Autor de teste",
            "data": "1640",
            "licenca": "dominio-publico",
            "alt": "Descrição da cena",
            "url": None,
        },
    }


def _historia(n: int = 3, provisoria: bool = False) -> dict:
    return {
        "provisoria": provisoria,
        "abertura": {
            "titulo": "Como chegamos até aqui",
            "subtitulo": "Subtítulo",
            "legenda": "Legenda",
            "nota_estados": "Nota",
            "texto": "Texto da abertura.",
        },
        "epocas": [_epoca(i) for i in range(n)],
        "fecho": {
            "titulo": "E de 2000 para cá?",
            "texto": "Texto do fecho.",
            "links": [{"texto": "Início", "url": "../"}],
        },
    }


def _escrever(pasta: Path, dados: dict | None = None, censos: str = CENSOS) -> Path:
    dados = _historia() if dados is None else dados
    (pasta / "historia").mkdir(parents=True, exist_ok=True)
    (pasta / "historia.yaml").write_text(yaml.safe_dump(dados, allow_unicode=True, sort_keys=False), encoding="utf-8")
    (pasta / "historia" / "censos.csv").write_text(censos, encoding="utf-8")
    return pasta


def _recusa(tmp_path: Path, dados: dict, caminho: str, censos: str = CENSOS) -> str:
    with pytest.raises(ErroConteudo) as erro:
        carregar_historia(_escrever(tmp_path, dados, censos))
    assert caminho in str(erro.value)
    return str(erro.value)


def test_carrega_epocas_na_ordem_e_marcos_ordenados(tmp_path):
    dados = _historia(8)
    dados["epocas"].reverse()  # fora de ordem no arquivo
    historia = carregar_historia(_escrever(tmp_path, dados))
    assert isinstance(historia, Historia)
    assert len(historia.epocas) == 8
    inicios = [e.inicio for e in historia.epocas]
    assert inicios == sorted(inicios)
    for epoca in historia.epocas:
        assert isinstance(epoca, Epoca)
        anos = [m.ano for m in epoca.marcos]
        assert anos == sorted(anos) and len(anos) == 2
    primeira = historia.epocas[0]
    assert primeira.marcos[0] == Marco(1510, "Primeiro marco", "Texto do marco.")
    assert primeira.numeros == (NumeroHistorico("10%", "Legenda de teste", "oficial", "IBGE, tabela de teste"),)
    assert primeira.fontes == ({"texto": "Obra de teste"}, {"texto": "Outra obra", "url": "https://exemplo.org/obra"})
    assert primeira.imagem == ImagemHistorica(
        "epoca-1500.webp", "Título da imagem", "Autor de teste", "1640", "dominio-publico", "Descrição da cena", None,
    )
    assert historia.provisoria is False
    assert historia.abertura["titulo"] == "Como chegamos até aqui"
    assert historia.fecho["links"] == [{"texto": "Início", "url": "../"}]
    assert historia.censos == ((1872, 4_638_560, 9_930_478, "Fixture de teste"),)


def test_tipos_dos_numeros():
    assert TIPOS == {"oficial": "dado oficial", "historiador": "estimativa de historiador", "interpretacao": "interpretação"}


def test_parcela_do_nordeste_calculada_dos_censos(tmp_path):
    censos = CENSOS + "1900,6749507,17438434,Fixture de teste\n"
    historia = carregar_historia(_escrever(tmp_path, censos=censos))
    assert parcela_do_nordeste(historia) == [Ponto(1872, 46.7, "censo"), Ponto(1900, 38.7, "censo")]


@pytest.mark.parametrize("campo", ["tipo", "fonte"])
def test_recusa_numero_sem_tipo_ou_sem_fonte(tmp_path, campo):
    dados = _historia()
    del dados["epocas"][2]["numeros"][0][campo]
    _recusa(tmp_path, dados, f"epocas[2].numeros[0].{campo}")


def test_recusa_numero_com_fonte_vazia(tmp_path):
    dados = _historia()
    dados["epocas"][1]["numeros"][0]["fonte"] = "  "
    _recusa(tmp_path, dados, "epocas[1].numeros[0].fonte")


def test_recusa_tipo_desconhecido(tmp_path):
    dados = _historia()
    dados["epocas"][1]["numeros"][0]["tipo"] = "palpite"
    _recusa(tmp_path, dados, "epocas[1].numeros[0].tipo")


def test_recusa_interpretacao_fora_de_o_que_ficou(tmp_path):
    dados = _historia()
    dados["epocas"][0]["numeros"][0]["tipo"] = "interpretacao"
    mensagem = _recusa(tmp_path, dados, "epocas[0].numeros[0].tipo")
    assert "o_que_ficou" in mensagem


def test_recusa_marco_sem_ano(tmp_path):
    dados = _historia()
    del dados["epocas"][1]["marcos"][1]["ano"]
    _recusa(tmp_path, dados, "epocas[1].marcos[1].ano")


@pytest.mark.parametrize("lista", ["ausente", "vazia"])
def test_recusa_epoca_sem_fontes(tmp_path, lista):
    dados = _historia()
    if lista == "ausente":
        del dados["epocas"][2]["fontes"]
    else:
        dados["epocas"][2]["fontes"] = []
    _recusa(tmp_path, dados, "epocas[2].fontes")


def test_recusa_id_repetido(tmp_path):
    dados = _historia()
    dados["epocas"][2]["id"] = dados["epocas"][0]["id"]
    _recusa(tmp_path, dados, "epocas[2].id")


@pytest.mark.parametrize("palavras, passa", [(149, False), (150, True), (300, True), (301, False)])
def test_recusa_texto_fora_de_150_a_300_palavras(tmp_path, palavras, passa):
    dados = _historia()
    dados["epocas"][1]["texto"] = _texto(palavras)
    if passa:
        assert len(carregar_historia(_escrever(tmp_path, dados)).epocas) == 3
    else:
        mensagem = _recusa(tmp_path, dados, "epocas[1].texto")
        assert str(palavras) in mensagem


@pytest.mark.parametrize("campo", ["autor", "data", "licenca", "alt"])
def test_recusa_imagem_sem_autor_data_licenca_ou_alt(tmp_path, campo):
    dados = _historia()
    del dados["epocas"][1]["imagem"][campo]
    _recusa(tmp_path, dados, f"epocas[1].imagem.{campo}")


def test_recusa_imagem_com_campo_vazio(tmp_path):
    dados = _historia()
    dados["epocas"][0]["imagem"]["alt"] = ""
    _recusa(tmp_path, dados, "epocas[0].imagem.alt")


def test_aceita_as_duas_licencas_e_recusa_outra(tmp_path):
    dados = _historia()
    dados["epocas"][0]["imagem"]["licenca"] = "ilustracao-do-autor"
    assert carregar_historia(_escrever(tmp_path, dados)).epocas[0].imagem.licenca == "ilustracao-do-autor"


def test_recusa_licenca_desconhecida(tmp_path):
    dados = _historia()
    dados["epocas"][1]["imagem"]["licenca"] = "cc-by-nc"
    _recusa(tmp_path, dados, "epocas[1].imagem.licenca")


def test_cc_by_exige_url(tmp_path):
    dados = _historia()
    dados["epocas"][1]["imagem"]["licenca"] = "cc-by"
    dados["epocas"][1]["imagem"]["url"] = None
    _recusa(tmp_path, dados, "epocas[1].imagem.url")
    del dados["epocas"][1]["imagem"]["url"]
    _recusa(tmp_path, dados, "epocas[1].imagem.url")
    dados["epocas"][1]["imagem"]["url"] = "https://commons.wikimedia.org/wiki/File:Exemplo.jpg"
    imagem = carregar_historia(_escrever(tmp_path, dados)).epocas[1].imagem
    assert imagem.licenca == "cc-by" and imagem.url == "https://commons.wikimedia.org/wiki/File:Exemplo.jpg"


def test_recusa_marco_fora_do_periodo_da_epoca(tmp_path):
    dados = _historia()
    dados["epocas"][0]["marcos"][0]["ano"] = 1499
    _recusa(tmp_path, dados, "epocas[0].marcos[0].ano")
    dados["epocas"][0]["marcos"][0]["ano"] = 1601  # o fim da primeira época é 1600
    _recusa(tmp_path, dados, "epocas[0].marcos[0].ano")


def test_marco_nos_limites_do_periodo_passa(tmp_path):
    dados = _historia()
    dados["epocas"][0]["marcos"][0]["ano"] = 1500
    dados["epocas"][0]["marcos"][1]["ano"] = 1600
    assert [m.ano for m in carregar_historia(_escrever(tmp_path, dados)).epocas[0].marcos] == [1500, 1600]


def test_recusa_censo_com_nordeste_maior_que_brasil(tmp_path):
    censos = "ano,populacao_nordeste,populacao_brasil,fonte\n1872,9930479,9930478,Fixture de teste\n"
    mensagem = _recusa(tmp_path, _historia(), "populacao_nordeste", censos)
    assert "censos.csv" in mensagem and "1872" in mensagem


@pytest.mark.parametrize("censos", [
    "ano,populacao_nordeste,populacao_brasil,fonte\n",  # sem linhas
    "ano,populacao_nordeste,populacao_brasil\n1872,1,2\n",  # sem a coluna fonte
    "ano,populacao_nordeste,populacao_brasil,fonte\n1872,x,2,F\n",  # numero invalido
    "ano,populacao_nordeste,populacao_brasil,fonte\n1872,1,2,F\n1872,1,2,F\n",  # ano repetido
    "ano,populacao_nordeste,populacao_brasil,fonte\n1872,1,2,\n",  # fonte vazia
])
def test_recusa_censos_malformados(tmp_path, censos):
    _recusa(tmp_path, _historia(), "censos.csv", censos)


def test_recusa_censos_ausente(tmp_path):
    _escrever(tmp_path)
    (tmp_path / "historia" / "censos.csv").unlink()
    with pytest.raises(ErroConteudo, match="censos.csv"):
        carregar_historia(tmp_path)


def test_imagem_opcional_so_quando_provisoria(tmp_path):
    dados = _historia(provisoria=True)
    del dados["epocas"][0]["imagem"]
    assert carregar_historia(_escrever(tmp_path, dados)).epocas[0].imagem is None
    dados["provisoria"] = False
    _recusa(tmp_path, dados, "epocas[0].imagem")


def test_recusa_chaves_desconhecidas_e_tipos_errados(tmp_path):
    dados = _historia()
    dados["epocas"][0]["extra"] = 1
    _recusa(tmp_path, dados, "epocas[0]")
    dados = _historia()
    dados["epocas"][0]["inicio"] = "1500"
    _recusa(tmp_path, dados, "epocas[0].inicio")
    dados = _historia()
    dados["provisoria"] = "sim"
    _recusa(tmp_path, dados, "provisoria")
    dados = _historia()
    dados["epocas"][1]["fim"] = dados["epocas"][1]["inicio"]
    _recusa(tmp_path, dados, "epocas[1].fim")


def test_recusa_abertura_e_fecho_incompletos(tmp_path):
    dados = _historia()
    del dados["abertura"]["nota_estados"]
    _recusa(tmp_path, dados, "abertura.nota_estados")
    dados = _historia()
    dados["fecho"]["links"] = []
    _recusa(tmp_path, dados, "fecho.links")


def test_sem_historia_yaml_devolve_none(tmp_path):
    assert carregar_historia(tmp_path) is None


def test_yaml_ilegivel_levanta_erro_de_conteudo(tmp_path):
    (tmp_path / "historia.yaml").write_text("provisoria: [", encoding="utf-8")
    with pytest.raises(ErroConteudo, match="historia.yaml"):
        carregar_historia(tmp_path)


def test_historia_provisoria_do_repositorio_e_valida():
    historia = carregar_historia(RAIZ / "metadados" / "site")
    assert historia is not None and historia.provisoria is True
    assert len(historia.epocas) == 8
    assert [e.inicio for e in historia.epocas] == [1530, 1654, 1808, 1889, 1930, 1950, 1964, 1985]
    assert all("[provisório]" in e.texto for e in historia.epocas)
    assert [(p.ano, p.valor) for p in parcela_do_nordeste(historia)] == [(1872, 46.7), (2022, 26.9)]
