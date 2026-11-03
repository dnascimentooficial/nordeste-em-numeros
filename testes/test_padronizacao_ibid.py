"""Padronizador do IBID (INPI): a planilha real da serie historica e as mudancas de layout que tem de barrar.

`testes/reais/ibid-serie-historica.xlsx` e o arquivo oficial, sem nenhuma alteracao: baixado em 2026-11-03 de
https://www.gov.br/inpi/pt-br/inpi-data/indice-brasil-de-inovacao-e-desenvolvimento-ibid/ibid-serie-historica.xlsx
(sha256 conferido abaixo). Os valores esperados de 2025 conferem com a Tab1B de `ibid-2025-quadros-completos.xlsx`, da
mesma pagina (Nordeste e "Média nacional"). As mudancas de layout usam a planilha sintetica do gerador de fixtures.
"""

import hashlib
import io
from dataclasses import replace
from pathlib import Path

import openpyxl
import pytest
from gerar_fixtures import aba_ibid, abas_ibid, xlsx_abas

from nordeste.caminhos import Caminhos
from nordeste.coletores.registro import Coleta
from nordeste.fichas import carregar_ficha
from nordeste.padronizacao import ErroLayout, padronizar
from nordeste.padronizacao.ibid import (
    AGREGADOS_DO_INPI, UFS_DO_INPI, ler_abas, ler_ibid, padronizar_ibid, posicoes_calculadas,
)
from nordeste.territorios import UFS_NE, carregar_territorios

RAIZ = Path(__file__).resolve().parent.parent
REAL = RAIZ / "testes" / "reais" / "ibid-serie-historica.xlsx"
SHA256_REAL = "eec72964c17fa714ea014e549e3e4dea2a322e1efd18a30da67887ae9adc92bc"
TERRITORIOS_DA_BASE = {"BR", "N", "NE", "SE", "S", "CO", *UFS_NE}


@pytest.fixture(scope="module")
def ficha():
    return carregar_ficha(RAIZ / "metadados" / "indicadores" / "ibid.yaml")


@pytest.fixture(scope="module")
def territorios():
    return carregar_territorios(RAIZ / "metadados" / "territorios.csv")


@pytest.fixture(scope="module")
def real() -> bytes:
    return REAL.read_bytes()


@pytest.fixture(scope="module")
def lido(real, ficha):
    return ler_ibid(real, ficha.series[0])


@pytest.fixture(scope="module")
def base_real(real, ficha, territorios):
    return padronizar_ibid(real, ficha, ficha.series[0], "ibid.serie_historica.teste", territorios)


def _valor(df, territorio, ano, sub="geral"):
    achado = df[(df.territorio_id == territorio) & (df.ano == ano) & (df.subindicador == sub)]
    assert len(achado) == 1, (territorio, ano, sub)
    return achado.valor.iloc[0]


# --- arquivo real ---


def test_o_arquivo_real_e_o_oficial_sem_alteracao(real):
    assert hashlib.sha256(real).hexdigest() == SHA256_REAL


def test_nordeste_e_media_nacional_de_2025_sao_os_da_tab1b(base_real):
    assert _valor(base_real, "NE", 2025) == 0.17852447616672143
    assert _valor(base_real, "BR", 2025) == 0.2955745342721538


def test_valores_de_2014_e_dos_subindices_vem_das_colunas_certas(base_real):
    assert _valor(base_real, "NE", 2014) == 0.17262468701455425
    assert _valor(base_real, "BR", 2014) == 0.2944789104979655
    assert _valor(base_real, "NE", 2025, "contexto") == 0.23877156757159568  # Tab1B, 1. IBID-Contexto
    assert _valor(base_real, "NE", 2025, "resultado") == 0.11827738476184713  # Tab1B, 2. IBID-Resultado


def test_base_tem_15_territorios_12_anos_e_3_subindicadores(base_real, ficha):
    assert len(base_real) == 15 * 12 * 3
    assert set(base_real.territorio_id) == TERRITORIOS_DA_BASE
    assert sorted(base_real.ano.unique()) == list(range(2014, 2026))
    assert set(base_real.subindicador) == {"geral", "contexto", "resultado"}
    assert set(base_real.tipo_dado) == {"observado"} and base_real.valor.between(0, 1).all()
    assert set(base_real.serie_id) == {"serie_historica"} and set(base_real.indicador_id) == {ficha.id}
    assert not base_real.duplicated(["territorio_id", "ano", "subindicador"]).any()


def test_sigla_repetida_do_inpi_nao_confunde_sergipe_com_o_sudeste(base_real, lido):
    # O INPI usa SE para Sergipe e para o Sudeste: o territorio sai do nome, e os dois ficam separados.
    assert _valor(base_real, "SE_UF", 2025) == lido[2025]["SE"]["geral"]
    assert _valor(base_real, "SE", 2025) == lido[2025]["Sudeste"]["geral"]
    assert _valor(base_real, "SE_UF", 2025) != _valor(base_real, "SE", 2025)


def test_tabela_de_pesos_ao_lado_das_regioes_nao_vira_territorio(real, lido):
    # Colunas N e O, abaixo do cabecalho "UF" / "PIB pc (R$10k)": linhas como ["CE", 9.71] em 2014.
    grade = ler_abas(real)["IBID 2014"]
    pesos = [linha[13:15] for linha in grade if len(linha) > 14 and linha[13] == "CE"]
    assert pesos == [["CE", 9.71]]
    assert set(lido[2014]) == {*UFS_DO_INPI, *AGREGADOS_DO_INPI}  # 27 UFs, cinco regioes e o Brasil, nada mais


def test_posicoes_calculadas_batem_com_o_ranking_do_inpi(lido):
    # A aba IBID_série hist publica a posicao no ranking do indice geral; o padronizador ja confere, e aqui os casos
    # conhecidos: Piaui de 21o para 18o e Paraiba de 18o para 15o, entre 2014 e 2025.
    posicoes = {ano: posicoes_calculadas({uf: do_ano[uf]["geral"] for uf in UFS_DO_INPI})
                for ano, do_ano in lido.items()}
    assert (posicoes[2014]["PI"], posicoes[2025]["PI"]) == (21, 18)
    assert (posicoes[2014]["PB"], posicoes[2025]["PB"]) == (18, 15)
    assert posicoes[2025]["SP"] == 1 and sorted(posicoes[2025].values()) == list(range(1, 28))


def test_padronizar_usa_o_padronizador_ibid_da_ficha(tmp_path, ficha, territorios):
    bruto = tmp_path / "dados" / "brutos" / "ibid" / "serie_historica" / "eec72964.xlsx"
    bruto.parent.mkdir(parents=True)
    bruto.write_bytes(REAL.read_bytes())
    coleta = Coleta("ibid.serie_historica.2026-11-03.eec72964", "ibid", "serie_historica",
                    ficha.series[0].parametros["url"], "2026-11-03", SHA256_REAL, "rede",
                    bruto.relative_to(tmp_path).as_posix())
    df = padronizar(ficha, ficha.series[0], coleta, Caminhos(tmp_path), territorios)
    assert len(df) == 540 and set(df.coleta_id) == {coleta.coleta_id}


# --- mudancas de layout: sempre ErroLayout, com o lugar ---


def _sintetica(**trocas) -> bytes:
    """Planilha sintetica do gerador; `trocas`: aba -> funcao que altera a grade dela (None tira a aba)."""
    abas = abas_ibid()
    for aba, troca in trocas.items():
        if troca is None:
            del abas[aba]
        else:
            abas[aba] = troca(abas.get(aba))
    return xlsx_abas(abas)


def _ler(ficha, conteudo):
    return ler_ibid(conteudo, ficha.series[0])


def test_sintetica_sem_troca_passa(ficha):
    assert sorted(_ler(ficha, _sintetica())) == list(range(2014, 2026))


def _com(linha, coluna, valor):
    """Troca que poe `valor` na celula (linha e coluna contadas de 0)."""
    def trocar(grade):
        grade = [list(l) for l in grade]
        grade[linha] += [None] * (coluna + 1 - len(grade[linha]))
        grade[linha][coluna] = valor
        return grade
    return trocar


@pytest.mark.parametrize("trocas, trecho", [
    ({"IBID 2019": None}, "faltam as abas IBID 2019"),
    ({"IBID 2026": lambda _: aba_ibid(2026)}, "Edição nova: suba o fim da série"),
    ({"IBID_série hist": None}, "falta a aba 'IBID_série hist'"),
    ({"IBID 2020": _com(0, 2, "IBID - Índice")}, "aba IBID 2020: esperava 'IBID - Geral' em C1"),
    ({"IBID 2020": _com(0, 0, 2019)}, "aba IBID 2020: esperava 2020 em A1"),
    ({"IBID 2021": _com(2, 9, "IBID - Resultados")}, "esperava 'IBID - Resultado' em J3"),
    ({"IBID 2022": _com(4, 2, None)}, "Alagoas, coluna C: esperava índice de 0 a 1, achou None"),
    ({"IBID 2022": _com(4, 3, "0,5")}, "Alagoas, coluna D: esperava índice de 0 a 1, achou '0,5'"),
    ({"IBID 2022": _com(4, 9, 1.5)}, "Alagoas, coluna J: esperava índice de 0 a 1, achou 1.5"),
    ({"IBID 2023": _com(33, 0, "Região Nordeste")}, "linha 34: território não reconhecido 'Região Nordeste'/'NE'"),
    ({"IBID 2023": _com(33, 1, "N")}, "linha 34: território não reconhecido 'Nordeste'/'N'"),
    ({"IBID 2023": _com(3, 1, "AL")}, "território não reconhecido 'Acre'/'AL'"),
])
def test_mudanca_de_layout_e_erro_com_o_lugar(ficha, trocas, trecho):
    with pytest.raises(ErroLayout) as erro:
        _ler(ficha, _sintetica(**trocas))
    assert trecho in str(erro.value)


def test_territorio_que_some_ou_repete_e_erro(ficha):
    def sem_nordeste(grade):
        grade = [list(l) for l in grade]
        grade[33][:12] = [None] * 12
        return grade

    with pytest.raises(ErroLayout, match="aba IBID 2018: faltam as linhas de Nordeste"):
        _ler(ficha, _sintetica(**{"IBID 2018": sem_nordeste}))

    def piaui_duas_vezes(grade):
        grade = [list(l) for l in grade]
        return grade[:31] + [grade[19]] + grade[32:]  # a linha em branco antes das regioes vira outro Piaui

    with pytest.raises(ErroLayout, match="linha 32: Piauí repetido"):
        _ler(ficha, _sintetica(**{"IBID 2018": piaui_duas_vezes}))


def test_tabela_de_pesos_nas_colunas_do_territorio_e_erro(ficha):
    # Hoje os pesos ficam nas colunas N e O e sao ignorados; se descerem para A e B, a planilha mudou.
    def pesos_em_a_e_b(grade):
        return [list(l) for l in grade] + [["CE", 9.71]]

    with pytest.raises(ErroLayout, match=r"território não reconhecido 'CE'/9\.71"):
        _ler(ficha, _sintetica(**{"IBID 2017": pesos_em_a_e_b}))


def test_coluna_do_indice_geral_trocada_e_barrada_pelo_ranking(ficha):
    # Rotulos no lugar, mas a coluna C traz outro numero: a posicao calculada deixa de ser a publicada.
    def geral_invertido(grade):
        grade = [list(l) for l in grade]
        for linha in grade[3:30]:
            linha[2] = 1 - linha[2]
        return grade

    with pytest.raises(ErroLayout, match="IBID 2016: a posição calculada com a coluna C não é a publicada"):
        _ler(ficha, _sintetica(**{"IBID 2016": geral_invertido}))


def test_coluna_inserida_no_arquivo_real_e_erro(real, ficha):
    pasta = openpyxl.load_workbook(io.BytesIO(real))
    pasta["IBID 2025"].insert_cols(3)  # uma coluna nova antes do indice geral
    gravado = io.BytesIO()
    pasta.save(gravado)
    with pytest.raises(ErroLayout, match="aba IBID 2025: esperava 'IBID - Geral' em C1, achou None"):
        _ler(ficha, gravado.getvalue())


def test_arquivo_que_nao_e_planilha_e_erro(ficha):
    with pytest.raises(ErroLayout, match="IBID: planilha ilegível"):
        _ler(ficha, b"<html>pagina de erro servida com status 200</html>")


def test_serie_com_fim_menor_recusa_a_aba_do_ano_novo(real, ficha):
    serie = replace(ficha.series[0], fim=2024)
    with pytest.raises(ErroLayout, match=r"abas fora da cobertura da série \(2014 a 2024\): IBID 2025"):
        ler_ibid(real, serie)
