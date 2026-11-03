"""Padronizador da TIC Domicilios (Cetic.br), tabela A4: paginas reais e mudancas de layout que tem de barrar.

`testes/reais/cetic-a4-<ano>.html` sao paginas oficiais sem alteracao, as que o coletor baixou em 2026-11-03 de
https://cetic.br/pt/tics/domicilios/<ano>/domicilios/A4/ (2006, 2011, 2014, 2020 e 2025). As mudancas de layout usam a
pagina sintetica do gerador de fixtures.
"""

from dataclasses import replace
from pathlib import Path

import pytest
from gerar_fixtures import pagina_cetic

from nordeste.coletores.arquivo import empacotar_partes
from nordeste.fichas import carregar_ficha
from nordeste.padronizacao import ErroLayout
from nordeste.padronizacao.cetic import ler_pagina, padronizar_cetic
from nordeste.territorios import carregar_territorios

RAIZ = Path(__file__).resolve().parent.parent
REAIS = RAIZ / "testes" / "reais"
URL = "https://cetic.br/pt/tics/domicilios/{}/domicilios/A4/"


@pytest.fixture(scope="module")
def ficha():
    return carregar_ficha(RAIZ / "metadados" / "indicadores" / "internet_domicilios.yaml")


@pytest.fixture(scope="module")
def territorios():
    return carregar_territorios(RAIZ / "metadados" / "territorios.csv")


def _real(ano: int) -> bytes:
    return (REAIS / f"cetic-a4-{ano}.html").read_bytes()


def _serie(ficha, anos, so_computador, nota=""):
    """Serie da ficha com as partes dos anos dados (para montar pacotes so com as paginas reais guardadas)."""
    parametros = {"padronizador": "cetic", "tabela": "A4", "so_computador": so_computador,
                  "partes": [{"url": URL.format(a), "ano": a} for a in anos]}
    if nota:
        parametros["nota"] = nota
    return replace(ficha.series[0], parametros=parametros, inicio=min(anos), fim=max(anos))


def _padronizar(ficha, territorios, serie, paginas: dict[int, bytes]):
    pacote = empacotar_partes({URL.format(a): b for a, b in paginas.items()})
    return padronizar_cetic(pacote, ficha, serie, "teste", territorios)


def _valor(df, territorio, ano):
    achado = df[(df.territorio_id == territorio) & (df.ano == ano)]
    assert len(achado) == 1, (territorio, ano)
    return achado.iloc[0]


# --- paginas reais ---


@pytest.mark.parametrize("ano, brasil, nordeste", [(2006, 14.49, 5.54), (2025, 86, 84), (2020, 83, 79), (2011, 36, 21)])
def test_brasil_e_nordeste_das_paginas_reais(ano, brasil, nordeste):
    valores, _ = ler_pagina(_real(ano), "A4", ano, str(ano))
    assert (valores["BR"], valores["NE"]) == (brasil, nordeste)
    assert set(valores) == {"BR", "N", "NE", "SE", "S", "CO"}


def test_notas_de_rodape_saem_da_pagina(ficha, territorios):
    _, notas_2006 = ler_pagina(_real(2006), "A4", 2006, "2006")
    _, notas_2011 = ler_pagina(_real(2011), "A4", 2011, "2011")
    _, notas_2014 = ler_pagina(_real(2014), "A4", 2014, "2014")
    _, notas_2020 = ler_pagina(_real(2020), "A4", 2020, "2020")
    _, notas_2025 = ler_pagina(_real(2025), "A4", 2025, "2025")
    assert notas_2006 == ["Considerado somente o acesso à internet via computador de mesa (desktop) ou computador "
                          "portátil (laptop e notebook)."]
    assert notas_2011 == ["Excluindo-se o acesso via telefone celular no domicílio."]
    assert notas_2014 == [] and notas_2025 == []
    assert notas_2020 == ["Edição COVID-19 - Metodologia adaptada"]


def test_serie_atual_marca_2020_e_mais_nada(ficha, territorios):
    serie = _serie(ficha, [2014, 2020, 2025], so_computador=False)
    df = _padronizar(ficha, territorios, serie, {a: _real(a) for a in (2014, 2020, 2025)})
    assert len(df) == 3 * 6 and set(df.tipo_dado) == {"observado"}
    assert _valor(df, "NE", 2020).nota == "Cetic.br: Edição COVID-19 - Metodologia adaptada"
    assert set(df[df.ano != 2020].nota) == {""}
    assert _valor(df, "NE", 2025).valor == 84 and _valor(df, "BR", 2025).valor == 86


def test_serie_urbana_leva_a_nota_da_ficha_e_a_do_rodape(ficha, territorios):
    serie = _serie(ficha, [2006], so_computador=True, nota="Só área urbana")
    df = _padronizar(ficha, territorios, serie, {2006: _real(2006)})
    assert _valor(df, "NE", 2006).valor == 5.54 and _valor(df, "BR", 2006).valor == 14.49
    assert _valor(df, "NE", 2006).nota.startswith("Só área urbana; Cetic.br: Considerado somente o acesso")


def test_ficha_separa_as_tres_definicoes(ficha):
    assert [(s.id, s.inicio, s.fim, s.parametros["so_computador"]) for s in ficha.series] == [
        ("urbano_computador", 2006, 2007, True), ("computador", 2008, 2013, True), ("sem_restricao", 2014, 2025, False)]
    for serie in ficha.series:
        assert [p["ano"] for p in serie.parametros["partes"]] == list(range(serie.inicio, serie.fim + 1))
        assert all(p["url"] == URL.format(p["ano"]) for p in serie.parametros["partes"])
    assert ficha.comparacao.referencia == "brasil" and ficha.comparacao.metodo is None
    assert ficha.sentido == "maior_melhor" and ficha.limites == {"min": 0, "max": 100}
    assert "Brasil fora do" in ficha.observacoes and "Edição COVID-19" in ficha.observacoes


# --- mudancas de layout ---


def test_definicao_que_muda_e_erro(ficha, territorios):
    # Pagina de 2014 com a nota "so computador" (ou de 2010 sem ela): a serie declarada nao bate.
    com_nota = _serie(ficha, [2014], so_computador=False)
    with pytest.raises(ErroLayout, match="so_computador: false, mas o rodapé traz a restrição"):
        _padronizar(ficha, territorios, com_nota, {2014: pagina_cetic(2014, so_computador=True)})
    sem_nota = _serie(ficha, [2010], so_computador=True)
    with pytest.raises(ErroLayout, match="so_computador: true, mas o rodapé não traz a restrição"):
        _padronizar(ficha, territorios, sem_nota, {2010: pagina_cetic(2010, so_computador=False)})


def _trocada(ano: int, antes: str, depois: str) -> bytes:
    pagina = pagina_cetic(ano).decode("utf-8")
    assert antes in pagina
    return pagina.replace(antes, depois, 1).encode("utf-8")


@pytest.mark.parametrize("pagina, trecho", [
    (b"<html><body><p>Erro 500</p></body></html>", "a página não tem tabela"),
    (_trocada(2022, "A4 - DOMICÍLIOS COM ACESSO À INTERNET", "A5 - DOMICÍLIOS COM COMPUTADOR"), "não é a A4"),
    (_trocada(2022, "<th>Sim</th><th>Não</th>", "<th>Não</th><th>Sim</th>"), "cabeçalho fora do esperado"),
    (_trocada(2022, "<td>Nordeste</td><td>9,9999</td>", "<td>Nordeste</td><td>-</td>"),
     "Nordeste, coluna Sim: esperava percentual, achou '-'"),
    (_trocada(2022, "<td>Nordeste</td><td>9,9999</td>", "<td>Nordeste</td><td>109,9</td>"),
     "Nordeste, coluna Sim: esperava percentual"),
    (_trocada(2022, "<td>Nordeste</td>", "<td>Região Nordeste</td>"), "faltam as linhas de NE"),
    (_trocada(2022, "<td>TOTAL</td>", "<td>Total geral</td>"), "faltam as linhas de BR"),
    (_trocada(2022, "TIC Domicílios 2022", "TIC Domicílios 2021"), "o rodapé da tabela não cita 2022"),
])
def test_mudanca_de_layout_e_erro_com_o_lugar(pagina, trecho):
    with pytest.raises(ErroLayout) as erro:
        ler_pagina(pagina, "A4", 2022, "2022")
    assert trecho in str(erro.value)


def test_linha_repetida_e_erro():
    pagina = _trocada(2022, "<td>Sul</td>", "<td>Nordeste</td>")
    with pytest.raises(ErroLayout, match="'Nordeste' aparece mais de uma vez"):
        ler_pagina(pagina, "A4", 2022, "2022")


def test_pagina_que_falta_no_pacote_e_erro(ficha, territorios):
    serie = _serie(ficha, [2024, 2025], so_computador=False)
    with pytest.raises(ErroLayout, match="2025 .*página ausente do pacote coletado"):
        _padronizar(ficha, territorios, serie, {2024: pagina_cetic(2024)})
