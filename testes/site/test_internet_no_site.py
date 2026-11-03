"""Acesso à internet (TIC Domicílios) no site: Explorar, o card e a ausência no Estados (a pesquisa não abre UFs)."""

import json
from pathlib import Path

import pytest

from nordeste.caminhos import Caminhos
from nordeste.site.conteudo import calcular_destaques, carregar_conteudo, preencher
from nordeste.site.dados import DadosSite
from nordeste.site.explorar import INDICADORES_ESTADOS, UFS
from nordeste.site.gerar import gerar_site

from auxiliares import RAIZ, Arvore


@pytest.fixture(scope="module")
def dados() -> DadosSite:
    return DadosSite.carregar(Caminhos(raiz=RAIZ))


@pytest.fixture(scope="module")
def saida(tmp_path_factory) -> Path:
    saida = tmp_path_factory.mktemp("site") / "saida"
    gerar_site(Caminhos(raiz=RAIZ), saida, imagens=False)
    return saida


def _ler(saida: Path, pagina: str) -> str:
    return (saida / pagina).read_text(encoding="utf-8")


def test_base_publicada_tem_tres_series_sem_ufs_e_2020_marcado(dados):
    linhas = dados.base[dados.base.indicador_id == "internet_domicilios"]
    assert set(linhas.serie_id) == {"urbano_computador", "computador", "sem_restricao"}
    assert set(linhas.territorio_id) == {"BR", "N", "NE", "SE", "S", "CO"}  # sem UFs e sem Brasil fora do Nordeste
    assert not set(UFS) & set(linhas.territorio_id)
    de_2020 = linhas[linhas.ano == 2020]
    assert len(de_2020) == 6 and set(de_2020.nota) == {"Cetic.br: Edição COVID-19 - Metodologia adaptada"}
    assert linhas[linhas.serie_id == "urbano_computador"].nota.str.startswith("Só área urbana").all()


def test_explorar_separa_as_series_e_le_da_base(saida, dados):
    arvore = Arvore(_ler(saida, "explorar/index.html"))
    assert any(o["attrs"]["value"] == "internet" for o in arvore.achar("option"))
    do_arquivo = json.loads(_ler(saida, "explorar/dados/internet.json"))
    for territorio in ("NE", "BR"):
        esperado = [[p.ano, p.valor, p.serie] for p in dados.serie("internet_domicilios", territorio)]
        assert do_arquivo[territorio] == esperado and esperado
        assert {s for _, _, s in do_arquivo[territorio]} == {"urbano_computador", "computador", "sem_restricao"}
    assert do_arquivo["PI"] == [] and do_arquivo["BR_FORA_NE"] == []


def test_estados_nao_lista_o_indicador_sem_dado_por_uf():
    assert "internet_domicilios" not in {i.indicador_id for i in INDICADORES_ESTADOS}


def test_card_da_internet_com_os_numeros_da_serie_atual(saida, dados):
    conteudo = carregar_conteudo(RAIZ / "metadados" / "site")
    destaques = calcular_destaques(dados, conteudo)
    card = next(c for c in conteudo.cards if c["id"] == "internet")
    assert destaques["internet_ne"].primeiro.serie == destaques["internet_ne"].ultimo.serie == "sem_restricao"
    arvore = Arvore(_ler(saida, "cards/internet/index.html"))
    assert [Arvore.texto(e) for e in arvore.achar("h1")] == [card["frase_feita"]]
    numero = Arvore.texto(arvore.achar("p", classe="nn-c-numero")[0])
    assert numero == f"{preencher(card['de'], destaques)} → {preencher(card['para'], destaques)}"
    assert [Arvore.texto(e) for e in arvore.achar("p", classe="nn-c-fecho")] == [card["fecho"]]
    # o grafico marca as duas mudancas de definicao e a edicao de 2020 (o card pequeno nao desenha os rotulos)
    assert [q["ano"] for q in card["grafico"]["quebras"]] == [2008, 2014, 2020]
