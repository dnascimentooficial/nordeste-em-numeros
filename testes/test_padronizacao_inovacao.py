"""Padronizadores dos indicadores da página Inovação: arquivos oficiais sem alteração (testes/reais/) e mudanças de
layout, que têm de falhar alto (ErroLayout ou ErroColeta), nunca passar caladas."""

import copy
import io
import json
import zipfile
from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from nordeste.coletores import conferir_link
from nordeste.coletores.arquivo import empacotar_partes
from nordeste.coletores.erros import ErroColeta
from nordeste.fichas import carregar_fichas
from nordeste.padronizacao.badepi import padronizar_badepi, tipo_do_pedido
from nordeste.padronizacao.erros import ErroLayout
from nordeste.padronizacao.geocapes import padronizar_geocapes
from nordeste.padronizacao.ibid import padronizar_ibid
from nordeste.padronizacao.mcti import padronizar_mcti
from nordeste.padronizacao.pintec import padronizar_pintec
from nordeste.padronizacao.sidra import padronizar_sidra
from nordeste.territorios import UFS_NE, carregar_territorios, territorios_do_nordeste

RAIZ = Path(__file__).resolve().parent.parent
REAIS = RAIZ / "testes" / "reais"
FIXTURES = RAIZ / "testes" / "fixtures"


@pytest.fixture(scope="module")
def fichas():
    return carregar_fichas(RAIZ / "metadados" / "indicadores")


@pytest.fixture(scope="module")
def territorios():
    # a tabela que padronizar() passa as series sem `todas_as_ufs`: sem as UFs de fora do Nordeste
    return territorios_do_nordeste(carregar_territorios(RAIZ / "metadados" / "territorios.csv"))


def _valor(df: pd.DataFrame, territorio: str, ano: int, sub: str = "") -> float:
    (valor,) = df[(df.territorio_id == territorio) & (df.ano == ano) & (df.subindicador == sub)].valor
    return valor


def _serie(fichas, indicador, serie_id, **mudancas):
    serie = fichas[indicador].serie(serie_id)
    return replace(serie, **mudancas) if mudancas else serie


# --- IBID: posição nacional, para a página Estados ---

def test_ibid_posicao_le_a_posicao_publicada_das_ufs_do_nordeste(fichas, territorios):
    f = fichas["ibid_posicao"]
    df = padronizar_ibid((REAIS / "ibid-serie-historica.xlsx").read_bytes(), f, f.series[0], "c", territorios)
    assert set(df.territorio_id) == set(UFS_NE) and len(df) == 9 * 12
    esperado = {"PI": (21, 18), "PB": (18, 15), "RN": (13, 12), "CE": (15, 14), "PE": (12, 13), "BA": (16, 16),
                "SE_UF": (14, 19), "AL": (27, 25), "MA": (25, 26)}
    for uf, (antes, depois) in esperado.items():
        assert (_valor(df, uf, 2014), _valor(df, uf, 2025)) == (antes, depois), uf


def test_ibid_com_medida_desconhecida_e_erro(fichas, territorios):
    f = fichas["ibid_posicao"]
    serie = replace(f.series[0], parametros={**f.series[0].parametros, "medida": "nota"})
    with pytest.raises(ErroLayout, match="medida"):
        padronizar_ibid((REAIS / "ibid-serie-historica.xlsx").read_bytes(), f, serie, "c", territorios)


# --- MCTI: dispêndio dos governos estaduais (tabelas 2.3.3 e 2.3.5) ---

def _pacote_mcti(serie, troca=None):
    arquivos = {}
    for parte in serie.parametros["partes"]:
        texto = (REAIS / f"mcti-{parte['url'].rsplit('/', 1)[1]}").read_bytes()
        arquivos[parte["url"]] = troca(texto) if troca else texto
    return empacotar_partes(arquivos)


def test_mcti_le_os_valores_publicados_do_levantamento(fichas, territorios):
    f = fichas["gasto_estadual_cti"]
    df = padronizar_mcti(_pacote_mcti(f.series[0]), f, f.series[0], "c", territorios)
    assert len(df) == 20 * 15 * 3
    esperado = {("ct", 2000): (139.2, 2854.3), ("ct", 2019): (2201.7, 18571.8), ("pd", 2000): (82.5, 2486.2),
                ("pd", 2019): (1110.8, 13785.3), ("pd_pos_graduacao", 2019): (772.8, 10247.8)}
    for (sub, ano), (ne, br) in esperado.items():
        assert (_valor(df, "NE", ano, sub), _valor(df, "BR", ano, sub)) == (ne, br), (sub, ano)
    assert _valor(df, "PI", 2000, "pd_pos_graduacao") == 0.0  # "-" e zero


@pytest.mark.parametrize("troca, mensagem", [
    (lambda b: b.replace(b"2000-2019", b"2000-2018"), "não cobre"),
    (lambda b: b.replace("milhões de R$ correntes".encode("latin-1"), "mil R$ correntes".encode("latin-1")), "unidade"),
    (lambda b: b.replace("Piauí;".encode("latin-1"), b"Piaui do Norte;"), "faltam as linhas"),
    (lambda b: b.replace(b"Tabela 2.3.", b"Quadro 2.3."), "não achei a linha"),
    (lambda b: b"<!DOCTYPE html><html><body>Please enable JavaScript</body></html>", "HTML"),
])
def test_mcti_falha_alto_se_a_tabela_mudar(fichas, territorios, troca, mensagem):
    f = fichas["gasto_estadual_cti"]
    with pytest.raises(ErroLayout, match=mensagem):
        padronizar_mcti(_pacote_mcti(f.series[0], troca), f, f.series[0], "c", territorios)


def test_mcti_sem_a_coluna_declarada_e_erro(fichas, territorios):
    f = fichas["gasto_estadual_cti"]
    partes = copy.deepcopy(f.series[0].parametros["partes"])
    partes[1]["coluna"] = "Pesquisa"
    serie = replace(f.series[0], parametros={**f.series[0].parametros, "partes": partes})
    with pytest.raises(ErroLayout, match="Pesquisa"):
        padronizar_mcti(_pacote_mcti(serie), f, serie, "c", territorios)


# --- CEMPRE (SIDRA 9418): soma das divisões 62 e 63 ---

def test_cempre_soma_as_duas_divisoes_publicadas(fichas, territorios):
    f = fichas["empregos_ti"]
    serie = f.serie("cempre_9418")
    df = padronizar_sidra((REAIS / "sidra-cempre-9418.json").read_bytes(), f, serie, "c", territorios)
    assert len(df) == 3 * 15
    assert (_valor(df, "NE", 2022), _valor(df, "BR", 2022)) == (57243, 726114)  # 46.217 + 11.026; 583.428 + 142.686
    assert (_valor(df, "NE", 2024), _valor(df, "BR", 2024)) == (75113, 765225)
    assert sum(_valor(df, uf, 2024) for uf in UFS_NE) == _valor(df, "NE", 2024)


def test_cempre_com_rotulo_de_divisao_mudado_e_erro(fichas, territorios):
    f = fichas["empregos_ti"]
    texto = (REAIS / "sidra-cempre-9418.json").read_text(encoding="utf-8")
    mudado = texto.replace("63 Atividades de prestação de serviços de informação", "63 Outra coisa").encode("utf-8")
    with pytest.raises(ErroLayout, match="63"):
        padronizar_sidra(mudado, f, f.serie("cempre_9418"), "c", territorios)


def test_cempre_sem_uma_das_divisoes_e_erro(fichas, territorios):
    f = fichas["empregos_ti"]
    dados = json.loads((REAIS / "sidra-cempre-9418.json").read_text(encoding="utf-8"))
    sem = [dados[0], *(l for l in dados[1:] if not (l["D1C"] == "2" and l["D3C"] == "2023" and l["D4C"] == "117601"))]
    with pytest.raises(ErroLayout, match="sem as categorias"):
        padronizar_sidra(json.dumps(sem).encode(), f, f.serie("cempre_9418"), "c", territorios)


# --- GeoCAPES: programas e doutores titulados ---

def test_geocapes_programas_e_titulados_do_levantamento(fichas, territorios):
    f = fichas["programas_pos"]
    df = padronizar_geocapes((REAIS / "geocapes-programas-2017-2024.json").read_bytes(), f,
                             f.serie("sem_filtro_de_nota"), "c", territorios)
    assert (_valor(df, "NE", 2024), _valor(df, "BR", 2024)) == (962, 4635)
    assert sum(_valor(df, r, 2024) for r in ("N", "NE", "SE", "S", "CO")) == _valor(df, "BR", 2024)
    f = fichas["doutores_titulados"]
    df = padronizar_geocapes((REAIS / "geocapes-titulados-2017-2024.json").read_bytes(), f,
                             f.serie("sem_filtro_de_nota"), "c", territorios)
    assert (_valor(df, "NE", 2024), _valor(df, "BR", 2024)) == (4328, 25915)
    assert round(_valor(df, "NE", 2024) / _valor(df, "BR", 2024) * 100, 1) == 16.7


def _bruto_titulados():
    return json.loads((REAIS / "geocapes-titulados-2017-2024.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("mexer, mensagem", [
    (lambda b: b["anos"]["2020"]["dados"].append({"UF": "SP", "GRAU": "Doutorado Sanduíche", "FLUXO": "Titulado",
                                                   "REFERENCIAL": 1}), "fora dos valores conhecidos"),
    (lambda b: b["indicador"].update(mensagem="Contamos tudo de outro jeito."), "aviso"),
    (lambda b: b["anos"].pop("2019"), "anos"),
    (lambda b: b["anos"]["2018"]["dados"].append({"UF": "XX", "GRAU": "Doutorado", "FLUXO": "Titulado",
                                                   "REFERENCIAL": 1}), "UF desconhecida"),
    (lambda b: b["anos"]["2018"]["dados"][0].update(REFERENCIAL=-3), "contagem inválida"),
    (lambda b: b["anos"]["2018"]["dados"][0].update(PROGRAMA="x"), "campos"),
])
def test_geocapes_falha_alto_se_a_api_mudar(fichas, territorios, mexer, mensagem):
    f = fichas["doutores_titulados"]
    bruto = _bruto_titulados()
    mexer(bruto)
    with pytest.raises(ErroLayout, match=mensagem):
        padronizar_geocapes(json.dumps(bruto).encode(), f, f.serie("sem_filtro_de_nota"), "c", territorios)


# --- PINTEC ---

def _pacote_pintec(serie, arquivos_reais):
    return empacotar_partes({p["url"]: arquivos_reais[p["ano"]] for p in serie.parametros["partes"]
                             if p["ano"] in arquivos_reais})


def test_pintec_2017_e_2000_contagens_e_taxa(fichas, territorios):
    reais = {2017: (REAIS / "pintec2017-grandes-regioes.xls").read_bytes(),
             2000: (REAIS / "pintec2000-grandes-regioes.zip").read_bytes()}
    for indicador in ("pintec_empresas", "inovacao_industria"):
        f = fichas[indicador]
        for serie_id, ano in (("cnae2", 2017), ("cnae1", 2000)):
            serie = f.serie(serie_id)
            partes = [p for p in serie.parametros["partes"] if p["ano"] == ano]
            serie = replace(serie, parametros={**serie.parametros, "partes": partes})
            df = padronizar_pintec(_pacote_pintec(serie, reais), f, serie, "c", territorios)
            if indicador == "pintec_empresas" and ano == 2017:
                assert round(_valor(df, "NE", 2017, "inovadoras")) == 4278 and round(_valor(df, "NE", 2017, "total")) == 12654
                assert round(_valor(df, "BR", 2017, "inovadoras")) == 34732 and round(_valor(df, "BR", 2017, "total")) == 102514
            elif indicador == "pintec_empresas":
                assert round(_valor(df, "NE", 2000, "inovadoras")) == 2119 and round(_valor(df, "NE", 2000, "total")) == 6799
                assert "SE" not in set(df.territorio_id)  # em 2000 o Sudeste vem sem Sao Paulo
            elif ano == 2017:
                assert (round(_valor(df, "NE", 2017), 1), round(_valor(df, "BR", 2017), 1)) == (33.8, 33.9)
                assert set(df.nota) == {"taxa calculada pelo projeto: empresas que implementaram inovação ÷ total de "
                                        "empresas, contagens da mesma tabela"}
            else:
                assert (round(_valor(df, "NE", 2000), 1), round(_valor(df, "BR", 2000), 1)) == (31.2, 31.5)


def test_pintec_com_periodo_errado_e_erro(fichas, territorios):
    f = fichas["inovacao_industria"]
    serie = f.serie("cnae2")
    partes = [dict(p, periodo="2014-2016") for p in serie.parametros["partes"] if p["ano"] == 2017]
    serie = replace(serie, parametros={**serie.parametros, "partes": partes})
    pacote = _pacote_pintec(serie, {2017: (REAIS / "pintec2017-grandes-regioes.xls").read_bytes()})
    with pytest.raises(ErroLayout, match="título"):
        padronizar_pintec(pacote, f, serie, "c", territorios)


# --- BADEPI: microdados de patentes ---

def test_tipo_do_pedido_nos_dois_formatos():
    prefixos, naturezas = ("PI", "MU"), ("10", "11", "20", "21")
    assert tipo_do_pedido("PI0102344", prefixos, naturezas) and tipo_do_pedido("MU8401405", prefixos, naturezas)
    assert tipo_do_pedido("112024005420", prefixos, naturezas) and tipo_do_pedido("202024002870", prefixos, naturezas)
    assert not tipo_do_pedido("C10101741", prefixos, naturezas)  # certificado de adicao
    assert not tipo_do_pedido("132024000001", prefixos, naturezas)  # natureza 13
    assert not tipo_do_pedido("122024000001", prefixos, naturezas)  # natureza 12, fora do mapeamento


def _zip_badepi(deposito: str, depositante: str) -> bytes:
    saida = io.BytesIO()
    with zipfile.ZipFile(saida, "w") as zip_:
        zip_.writestr("badepiv12_ptn_deposito.csv", deposito.encode("latin-1"))
        zip_.writestr("badepiv12_ptn_depositante.csv", depositante.encode("latin-1"))
    return saida.getvalue()


def _badepi(fichas, deposito, depositante, inicio=2000, fim=2001):
    f = fichas["patentes_residentes"]
    serie = replace(f.series[0], inicio=inicio, fim=fim)
    pacote = empacotar_partes({serie.parametros["partes"][0]["url"]: _zip_badepi(deposito, depositante)})
    return f, serie, pacote


CABECALHO_DEPOSITO = '"NO_PEDIDO";"ANO";"DT_ENTRADA_INPI";"DT_DEPOSITO";"NM_TITULO_PATENTE"\n'
CABECALHO_DEPOSITANTE = ('"NO_PEDIDO";"NO_ORDEM";"CD_TIPO_PFPJ";"NO_CNPJ_CPF";"NM_COMPLET_PFPJ";"CD_PAIS_PFPJ";'
                         '"CD_UF_PFPJ";"NM_CIDADE_PFPJ";"CD_IBGE_CIDADE"\n')


def test_badepi_conta_o_primeiro_depositante_residente_com_pais(fichas, territorios):
    deposito = CABECALHO_DEPOSITO + "".join(f"{n};{a};;;Título\n" for n, a in (
        ("PI0000001   ", 2000), ("MU8000002", 2000), ("PI0000003", 2000), ("C10000004", 2000), ("PI0000005", 2001),
        ("PI0000006", 2001), ("PI0000007", 2001)))
    depositante = CABECALHO_DEPOSITANTE + "".join(f"{linha}\n" for linha in (
        "PI0000001   ;1;F;;A;BR;PI;;", "PI0000001   ;2;F;;B;BR;SP;;",  # so a ordem 1 conta
        "MU8000002;1;J;;C;BR;CE;;",
        "PI0000003;1;J;;D;US;;;",  # estrangeiro
        "C10000004;1;J;;E;BR;BA;;",  # certificado de adicao: fora
        "PI0000005;1;;;F;;;;", "PI0000005;1;J;;F;BR;RS;;",  # a primeira linha de ordem 1 sem pais nao conta
        "PI0000006;1;J;;G;BR;MA;;", "PI0000006;1;J;;G;BR;SP;;",  # duas com pais: vale a primeira
        "PI0000007;1;F;;H;BR;;;",  # residente sem UF: fora das UFs e do Brasil
    ))
    f, serie, pacote = _badepi(fichas, deposito, depositante)
    df = padronizar_badepi(pacote, f, serie, "c", territorios)
    assert (_valor(df, "PI", 2000), _valor(df, "CE", 2000), _valor(df, "BA", 2000)) == (1, 1, 0)
    assert (_valor(df, "NE", 2000), _valor(df, "BR", 2000)) == (2, 2)
    assert (_valor(df, "MA", 2001), _valor(df, "S", 2001), _valor(df, "SE", 2001), _valor(df, "BR", 2001)) == (1, 1, 0, 2)


def test_badepi_com_ano_fora_da_serie_e_erro(fichas, territorios):
    deposito = CABECALHO_DEPOSITO + "PI0000001;2002;;;T\n"
    f, serie, pacote = _badepi(fichas, deposito, CABECALHO_DEPOSITANTE + "PI0000001;1;F;;A;BR;PI;;\n")
    with pytest.raises(ErroLayout, match="fora da série"):
        padronizar_badepi(pacote, f, serie, "c", territorios)


def test_badepi_sem_coluna_e_erro(fichas, territorios):
    deposito = CABECALHO_DEPOSITO.replace('"ANO"', '"ANO_DEPOSITO"') + "PI0000001;2000;;;T\n"
    f, serie, pacote = _badepi(fichas, deposito, CABECALHO_DEPOSITANTE + "PI0000001;1;F;;A;BR;PI;;\n")
    with pytest.raises(ErroLayout, match="ANO"):
        padronizar_badepi(pacote, f, serie, "c", territorios)


class _Sessao:
    def __init__(self, pagina: str):
        self.pagina = pagina

    def get(self, url, **kwargs):
        pagina = self.pagina

        class Resposta:
            content = pagina.encode("utf-8")

            def raise_for_status(self):
                pass
        return Resposta()


PAGINA_BADEPI = ('<a href="https://www.gov.br/inpi/pt-br/servicos/patentes">Patentes</a>'
                 '<a class="external-link" href="https://inpidrive.inpi.gov.br/index.php/s/{token}" title="x">Patentes</a>'
                 '<a href="https://inpidrive.inpi.gov.br/index.php/s/outro">Marcas</a>')


def test_conferir_link_aceita_o_link_da_ficha_e_recusa_o_token_novo(fichas):
    parametros = fichas["patentes_residentes"].series[0].parametros
    conferir_link(parametros, _Sessao(PAGINA_BADEPI.format(token="G33ljb4puihwzDR")))
    with pytest.raises(ErroColeta, match="NovoToken123/download"):
        conferir_link(parametros, _Sessao(PAGINA_BADEPI.format(token="NovoToken123")))
    with pytest.raises(ErroColeta, match="0 links"):
        conferir_link(parametros, _Sessao("<p>página nova, sem o link</p>"))
