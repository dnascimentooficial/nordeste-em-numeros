"""O mapa do Inicio "Onde a renda mais cresceu desde 2012?": os destaques novos (variacao, diferenca, proporcao,
no_topo), a grade dos 27 estados e o veredito, que muda de redacao ou sai quando os fatos mudam.

Os valores sinteticos abaixo sao os da tabela 7533 do SIDRA (2012 e 2025, reais de 2025), para o teste ler como o
site; os testes nao dependem da base publicada.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

from nordeste.esquema import COLUNAS_BASE, COLUNAS_DERIVADOS, normalizar_base
from nordeste.site import gerar
from nordeste.site.conteudo import (
    ErroConteudo, _validar_destaques, calcular_destaques, carregar_conteudo, comparacao_das_ufs, pontos_da_selecao,
)
from nordeste.site.dados import DadosSite, Ponto
from nordeste.site.idioma import em_idioma
from nordeste.site.mapa import GRADE, faixa_do_valor, faixas, mapa_svg, montar_mapa, tom
from nordeste.territorios import carregar_territorios

RAIZ = Path(__file__).resolve().parents[2]
PASTA_SITE = RAIZ / "metadados" / "site"
RENDA = {  # territorio: (2012, 2025)
    "BR": (1782, 2264), "N": (1199, 1558), "NE": (1088, 1470), "SE": (2170, 2669), "S": (2147, 2734),
    "CO": (2076, 2712), "RO": (1364, 1970), "AC": (1222, 1372), "AM": (1290, 1450), "RR": (1595, 1870),
    "PA": (1095, 1435), "AP": (1215, 1675), "TO": (1218, 1979), "MA": (791, 1231), "PI": (975, 1534),
    "CE": (1109, 1379), "RN": (1122, 1779), "PB": (1067, 1542), "PE": (1231, 1568), "AL": (928, 1401),
    "SE_UF": (1273, 1688), "BA": (1155, 1452), "MG": (1685, 2289), "ES": (1720, 2209), "RJ": (2079, 2732),
    "SP": (2470, 2862), "PR": (2091, 2687), "SC": (2168, 2752), "RS": (2189, 2772), "MS": (1787, 2369),
    "MT": (1758, 2297), "GO": (1734, 2378), "DF": (3518, 4401),
}


def _dados(renda: dict[str, tuple[float, float]] = RENDA) -> DadosSite:
    linhas, metricas = [], []
    for territorio, (inicial, final) in renda.items():
        for ano, valor in ((2012, inicial), (2025, final)):
            linhas.append({"indicador_id": "renda_dom_pc", "territorio_id": territorio, "ano": ano, "valor": float(valor),
                           "tipo_dado": "observado", "serie_id": "pnadc", "coleta_id": "c"})
            metricas.append({"indicador_id": "renda_dom_pc", "subindicador": "", "etapa": "", "rede": "",
                             "metrica": "variacao_acumulada", "referencia": "", "territorio_id": territorio, "ano": ano,
                             "valor": (valor / inicial - 1) * 100, "serie_id": "pnadc"})
    vazio = pd.DataFrame(columns=["indicador_id", "territorio_id", "proxima_publicacao"])
    return DadosSite(
        base=normalizar_base(pd.DataFrame(linhas).reindex(columns=COLUNAS_BASE).fillna("")),
        derivados=pd.DataFrame(metricas, columns=COLUNAS_DERIVADOS), cobertura=vazio,
        coletas=pd.DataFrame({"indicador_id": ["renda_dom_pc"], "data_coleta": ["2026-11-08"]}), fichas={},
        governos=pd.DataFrame(), sha256_base="0" * 64, data_base="2026-11-08",
        territorios=carregar_territorios(RAIZ / "metadados" / "territorios.csv"),
    )


@pytest.fixture(scope="module")
def conteudo():
    return carregar_conteudo(PASTA_SITE)


def _sp(texto: str) -> str:
    """O texto com o espaco sem quebra (depois de R$) como espaco comum."""
    return texto.replace("\u00a0", " ")


def _mapa(renda=RENDA, idioma="pt"):
    with em_idioma(idioma):
        conteudo = carregar_conteudo(PASTA_SITE, idioma)
        dados = _dados(renda)
        destaques = calcular_destaques(dados, conteudo)
        return gerar._mapa_renda(dados, destaques, conteudo.textos["mapa_renda"], "8 de novembro de 2026"), destaques


# --- destaques novos ---


def test_no_topo_conta_as_ufs_do_nordeste_entre_as_seis_que_mais_cresceram():
    dados = _dados()
    spec = {"tipo": "no_topo", "indicador": "renda_dom_pc", "territorio": "NE", "topo": 6}
    assert pontos_da_selecao(dados, spec) == [Ponto(2012, 5.0, "pnadc"), Ponto(2025, 5.0, "pnadc")]
    comparacao = comparacao_das_ufs(dados, "renda_dom_pc")
    assert comparacao.por_variacao()[:6] == ["TO", "RN", "PI", "MA", "AL", "PB"]
    assert comparacao.variacao("TO") == pytest.approx(62.48, abs=0.01)
    assert comparacao.por_variacao()[-1] == "AC" and len(comparacao.valores) == 27


def test_no_topo_sem_as_27_ufs_nao_conta_nada():
    so_o_nordeste = {t: v for t, v in RENDA.items() if t not in {"SP", "TO"}}
    dados = _dados(so_o_nordeste)
    spec = {"tipo": "no_topo", "indicador": "renda_dom_pc", "territorio": "NE", "topo": 6}
    assert comparacao_das_ufs(dados, "renda_dom_pc") is None and pontos_da_selecao(dados, spec) == []


def test_diferenca_proporcao_e_variacao():
    dados = _dados()
    gap = pontos_da_selecao(dados, {"tipo": "diferenca", "indicador": "renda_dom_pc", "territorio": "SE", "referencia": "NE"})
    assert [(p.ano, p.valor) for p in gap] == [(2012, 1082.0), (2025, 1199.0)]
    prop = pontos_da_selecao(dados, {"tipo": "proporcao", "indicador": "renda_dom_pc", "territorio": "NE", "referencia": "SE"})
    assert [round(p.valor, 1) for p in prop] == [50.1, 55.1]
    cresc = pontos_da_selecao(dados, {"tipo": "variacao", "indicador": "renda_dom_pc", "territorio": "NE"})
    assert [round(p.valor, 1) for p in cresc] == [0.0, 35.1]


@pytest.mark.parametrize("spec", [
    {"tipo": "no_topo", "indicador": "x", "territorio": "NE"},  # sem topo
    {"tipo": "no_topo", "indicador": "x", "territorio": "NE", "topo": 0},
    {"tipo": "no_topo", "indicador": "x", "territorio": "NE", "topo": True},
    {"tipo": "serie", "indicador": "x", "territorio": "NE", "topo": 6},  # topo so no no_topo
    {"tipo": "diferenca", "indicador": "x", "territorio": "SE"},  # sem referencia
    {"tipo": "variacao", "indicador": "x", "territorio": "NE", "referencia": "BR"},
    {"tipo": "variacao", "indicador": "x", "territorio": "NE", "serie": "pnadc"},
    {"tipo": "outro", "indicador": "x", "territorio": "NE"},
])
def test_destaques_novos_invalidos(spec):
    with pytest.raises(ErroConteudo):
        _validar_destaques({"d": spec})


# --- grade e escala ---


def test_grade_tem_as_27_ufs_sem_duas_na_mesma_casa_e_o_nordeste_junto():
    assert sorted(GRADE) == sorted(RENDA.keys() - {"BR", "N", "NE", "SE", "S", "CO"})
    assert len(set(GRADE.values())) == 27
    assert all(0 <= c < 6 and 0 <= l < 8 for c, l in GRADE.values())
    nordeste = {GRADE[uf] for uf in ("MA", "PI", "CE", "RN", "PB", "PE", "AL", "SE_UF", "BA")}
    assert all(c >= 3 for c, _ in nordeste)  # o bloco do Nordeste a leste


def test_faixas_redondas_e_tons_espalhados():
    assert faixas([12.3, 62.5]) == [10, 20, 30, 40, 50, 60, 70]
    assert faixas([1231, 4401]) == [1000, 2000, 3000, 4000, 5000]
    assert faixa_do_valor(62.5, [10, 20, 30, 40, 50, 60, 70]) == 5 and faixa_do_valor(70, [10, 20, 70]) == 1
    assert [tom(i, 4) for i in range(4)] == [0, 2, 3, 5]
    assert [tom(i, 6) for i in range(6)] == [0, 1, 2, 3, 4, 5]


def test_mapa_montado_com_ranking_tabela_e_rotulos():
    (mapa, _), _ = _mapa()
    d = mapa["dados"]
    assert len(d["quadrados"]) == 27 and sum(q["ne"] for q in d["quadrados"]) == 9
    to = next(q for q in d["quadrados"] if q["uf"] == "TO")
    assert to["valores"] == {"cresceu": "+62%", "hoje": "1.979"} and to["tons"]["cresceu"] == 5
    assert _sp(to["rotulo"]) == "Tocantins: +62,5% de 2012 a 2025, de R$ 1.218 para R$ 1.979 por pessoa, por mês"
    assert next(q for q in d["quadrados"] if q["uf"] == "SE_UF")["sigla"] == "SE"
    mais = d["rankings"]["cresceu"]["mais"]
    assert [i["uf"] for i in mais] == ["TO", "RN", "PI", "MA", "AL"] and [i["ne"] for i in mais] == [False] + [True] * 4
    assert [i["posicao"] for i in d["rankings"]["cresceu"]["menos"]] == [23, 24, 25, 26, 27]
    assert [i["uf"] for i in d["rankings"]["cresceu"]["menos"]] == ["CE", "RR", "SP", "AM", "AC"]
    assert d["rankings"]["hoje"]["mais"][0]["uf"] == "DF" and d["rankings"]["hoje"]["menos"][-1]["uf"] == "MA"
    assert d["tabela"][0] == {"nome": "Tocantins", "ne": False, "regiao": "N", "v0": "1.218", "v1": "1.979",
                              "variacao": "+62,5%"}
    assert [f["texto"] for f in d["legendas"]["hoje"]] == ["1.000–2.000", "2.000–3.000", "3.000–4.000", "4.000–5.000"]


def test_mapa_em_ingles_formata_no_padrao_americano():
    (mapa, _), _ = _mapa(idioma="en")
    to = next(q for q in mapa["dados"]["quadrados"] if q["uf"] == "TO")
    assert _sp(to["rotulo"]) == "Tocantins: +62.5% from 2012 to 2025, from R$ 1,218 to R$ 1,979 per person, per month"
    assert mapa["titulo"] == "Where has income grown the most since 2012?"
    assert mapa["veredito"].startswith("Income grew the most where it was lowest: 5 of the six states")
    assert "R$ 1,082 in 2012, R$ 1,199 in 2025" in _sp(mapa["veredito"])


def test_svg_do_card_sem_estilo_inline():
    (mapa, _), _ = _mapa()
    svg = mapa_svg(mapa["dados"])
    assert svg.count("<rect") == 27 and svg.count("nn-mosaico-svg-ne") == 9
    assert "style=" not in svg and "<script" not in svg and 'aria-hidden="true"' in svg


# --- o veredito: as palavras mudam ou a frase sai quando os fatos mudam ---


def test_veredito_com_a_base_de_hoje():
    (mapa, suprimidos), _ = _mapa()
    assert mapa["titulo"] == "Onde a renda mais cresceu desde 2012?"
    assert _sp(mapa["veredito"]) == (
        "A renda cresceu mais onde era menor: 5 dos seis estados que mais cresceram desde 2012 são do Nordeste. "
        "Mas, em reais, a distância para o Sudeste aumentou: R$ 1.082 em 2012, R$ 1.199 em 2025."
    )
    assert mapa["complemento"] == ("Em proporção, o Nordeste se aproximou: a renda por pessoa da região foi de 50% para 55% "
                                   "da do Sudeste. O Nordeste cresceu 35,1%; o Brasil, 27,0%.")
    assert suprimidos == []


def test_veredito_diz_que_a_distancia_diminuiu_quando_ela_diminui():
    renda = {**RENDA, "SE": (2170, 2500)}  # Sudeste - Nordeste: 1.082 -> 1.030
    (mapa, suprimidos), _ = _mapa(renda)
    assert "a distância para o Sudeste também diminuiu: R$ 1.082 em 2012, R$ 1.030 em 2025." in _sp(mapa["veredito"])
    assert "Mas," not in mapa["veredito"] and suprimidos == []


def test_veredito_sai_quando_o_nordeste_deixa_de_ser_maioria_no_topo():
    # RN, PI e AL crescem pouco: entre os seis que mais cresceram ficam MA, PB e mais quatro de fora
    renda = {**RENDA, "RN": (1122, 1200), "PI": (975, 1000), "AL": (928, 950), "MG": (1685, 2600),
             "RO": (1364, 2100), "GO": (1734, 2700)}
    (mapa, suprimidos), destaques = _mapa(renda)
    assert destaques["renda_topo6"].ultimo.valor < 4
    assert mapa["veredito"] is None and "mapa_renda_veredito" in suprimidos
    assert mapa["dados"]["quadrados"]  # o mapa continua


def test_complemento_sai_quando_o_nordeste_se_afasta_em_proporcao():
    renda = {**RENDA, "SE": (2170, 3300), "BR": (1782, 1900)}  # 1.470 / 3.300 = 45% do Sudeste, abaixo dos 50%
    (mapa, suprimidos), _ = _mapa(renda)
    assert mapa["complemento"] is None and "mapa_renda_proporcao" in suprimidos


def test_sem_as_27_ufs_o_bloco_inteiro_sai():
    so_o_nordeste = {t: v for t, v in RENDA.items() if len(t) > 2 or t in {"BR", "NE", "SE", "MA", "PI", "CE", "RN",
                                                                             "PB", "PE", "AL", "BA"}}
    (mapa, suprimidos), _ = _mapa(so_o_nordeste)
    assert mapa is None and suprimidos == ["mapa_renda"]


# --- o bloco no site gerado (base publicada e copias alteradas) ---


from nordeste.caminhos import Caminhos  # noqa: E402
from nordeste.site.gerar import gerar_site  # noqa: E402

from auxiliares import Arvore, alterar_base, copiar_base  # noqa: E402


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    saida = tmp_path_factory.mktemp("site") / "saida"
    return saida, gerar_site(Caminhos(raiz=RAIZ), saida, imagens=False)


def _gerar_com(tmp_path_factory, alterar):
    raiz = copiar_base(tmp_path_factory.mktemp("repo") / "repo")
    alterar_base(raiz, alterar)
    saida = tmp_path_factory.mktemp("site") / "saida"
    return saida, gerar_site(Caminhos(raiz=raiz), saida, imagens=False)


def _bloco(saida: Path, pagina: str = "index.html") -> tuple[str, Arvore]:
    html = (saida / pagina).read_text(encoding="utf-8")
    inicio = html.find('<section class="nn-card nn-mosaico')
    if inicio < 0:
        return html, Arvore("")
    return html, Arvore(html[inicio:html.index("</section>", html.index("nn-saidas", inicio))])


def test_base_publicada_tem_as_27_ufs_so_na_renda():
    base = pd.read_csv(RAIZ / "dados" / "base" / "base_nordeste.csv", dtype=str, keep_default_na=False)
    fora = {"RO", "AC", "AM", "RR", "PA", "AP", "TO", "MG", "ES", "RJ", "SP", "PR", "SC", "RS", "MS", "MT", "GO", "DF"}
    renda = base[base.indicador_id == "renda_dom_pc"]
    assert fora <= set(renda.territorio_id)
    assert not fora & set(base[base.indicador_id != "renda_dom_pc"].territorio_id)
    anos = set(renda[renda.territorio_id == "NE"].ano)
    for uf in fora:
        assert set(renda[renda.territorio_id == uf].ano) == anos, uf


@pytest.mark.parametrize("pagina, titulo, abas", [
    ("index.html", "Onde a renda mais cresceu desde 2012?", ["Quanto cresceu", "Quanto é hoje"]),
    ("en/index.html", "Where has income grown the most since 2012?", ["How much it grew", "How much it is today"]),
])
def test_bloco_no_inicio_depois_da_faixa_e_antes_do_placar(site, pagina, titulo, abas):
    saida, relatorio = site
    html, bloco = _bloco(saida, pagina)
    assert html.index("nn-faixa-abertura") < html.index('class="nn-card nn-mosaico') < html.index("nn-placar")
    assert Arvore.texto(bloco.achar("h2")[0]) == titulo
    assert [Arvore.texto(b) for b in bloco.achar("button", classe="nn-mosaico-aba")] == abas
    (grupo,) = bloco.achar("div", classe="nn-mosaico-abas")
    assert "hidden" in grupo["attrs"] and grupo["attrs"]["role"] == "group"  # sem JavaScript, so a vista "cresceu"
    assert [b["attrs"]["aria-pressed"] for b in bloco.achar("button", classe="nn-mosaico-aba")] == ["true", "false"]
    quadrados = bloco.achar("button", classe="nn-mosaico-uf")
    assert len(quadrados) == 27 and len(bloco.achar("button", classe="nn-mosaico-ne")) == 9
    assert all(q["attrs"]["aria-label"] and q["attrs"]["data-uf"] for q in quadrados)
    assert len(bloco.achar("tr")) == 28  # a tabela dos 27, legivel sem JavaScript
    assert not any("style" in e["attrs"] for e in bloco.elementos) and not bloco.achar("script")
    assert bloco.achar("p", classe="nn-mosaico-veredito")
    assert "mapa_renda" not in relatorio.fechos_suprimidos and "mapa_renda" not in relatorio.cards_suprimidos


def test_veredito_e_fonte_no_html_publicado(site):
    saida, _ = site
    _, bloco = _bloco(saida)
    veredito = Arvore.texto(bloco.achar("p", classe="nn-mosaico-veredito")[0])
    assert veredito.startswith("A renda cresceu mais onde era menor: 5 dos seis estados que mais cresceram desde 2012")
    assert "a distância para o Sudeste aumentou: R$ 1.082 em 2012, R$ 1.199 em 2025." in veredito
    fonte = Arvore.texto(bloco.achar("div", classe="nn-fonte")[0])
    assert "tabela 7533" in fonte and "a preços médios de 2025" in fonte and "não a emenda com o Censo" in fonte
    (saida_estados,) = bloco.achar("a", data_umami_event="cta-click")
    assert saida_estados["attrs"]["href"] == "/estados/" and saida_estados["attrs"]["data-umami-event-place"] == "mapa-renda"
    _, en = _bloco(saida, "en/index.html")
    veredito_en = Arvore.texto(en.achar("p", classe="nn-mosaico-veredito")[0])
    assert veredito_en.startswith("Income grew the most where it was lowest: 5 of the six states")
    assert "the gap to the Southeast widened: R$ 1,082 in 2012, R$ 1,199 in 2025." in veredito_en


def test_estados_e_explorar_continuam_so_com_o_nordeste(site):
    saida, _ = site
    for pagina in ("estados/index.html", "explorar/index.html"):
        texto = Arvore((saida / pagina).read_text(encoding="utf-8")).texto_visivel()
        for nome in ("São Paulo", "Tocantins", "Distrito Federal", "Acre"):
            assert nome not in texto, (pagina, nome)
    explorar = json.loads((saida / "explorar" / "dados" / "renda.json").read_text(encoding="utf-8"))
    assert not {"SP", "TO", "DF"} & set(explorar)


def test_card_do_mapa_com_o_mapa_dos_27(site):
    saida, relatorio = site
    assert "cards/mapa_renda/index.html" in relatorio.paginas and "en/cards/mapa_renda/index.html" in relatorio.paginas
    arvore = Arvore((saida / "cards" / "mapa_renda" / "index.html").read_text(encoding="utf-8"))
    (cartao,) = arvore.achar("article", classe="nn-cartao-mapa")
    (svg,) = arvore.achar("svg", classe="nn-mosaico-svg")
    assert len(arvore.achar("rect")) == 27
    assert Arvore.texto(arvore.achar("p", classe="nn-c-fecho")[0]) == "5 dos 6 estados que mais cresceram são do Nordeste."


def _sudeste_mais_perto(base):
    ultimo = base[(base.indicador_id == "renda_dom_pc") & (base.territorio_id == "SE")].ano.max()
    linha = (base.indicador_id == "renda_dom_pc") & (base.territorio_id == "SE") & (base.ano == ultimo)
    base.loc[linha, "valor"] = "2500"
    return base


def _sem_sao_paulo(base):
    return base[~((base.indicador_id == "renda_dom_pc") & (base.territorio_id == "SP"))]


def test_com_a_distancia_menor_o_veredito_diz_que_diminuiu(tmp_path_factory):
    saida, relatorio = _gerar_com(tmp_path_factory, _sudeste_mais_perto)
    _, bloco = _bloco(saida)
    veredito = Arvore.texto(bloco.achar("p", classe="nn-mosaico-veredito")[0])
    assert "E, em reais, a distância para o Sudeste também diminuiu: R$ 1.082 em 2012, R$ 1.030 em 2025." in veredito
    assert "aumentou" not in veredito and "mapa_renda_veredito" not in relatorio.fechos_suprimidos


def test_sem_uma_uf_o_bloco_e_o_card_saem(tmp_path_factory):
    saida, relatorio = _gerar_com(tmp_path_factory, _sem_sao_paulo)
    html, _ = _bloco(saida)
    assert "nn-mosaico" not in html and "mapa_renda" in relatorio.fechos_suprimidos
    assert "mapa_renda" in relatorio.cards_suprimidos and not (saida / "cards" / "mapa_renda").exists()
    assert "nn-placar" in html  # o resto do Inicio segue
