"""IBID no site: Estados (pela posicao) e Explorar (pelo indice) leem da base publicada, Sobre lista a fonte e o
inicio ainda nao fala dele."""

import json
from pathlib import Path

import pytest

from nordeste.caminhos import Caminhos
from nordeste.site.dados import DadosSite
from nordeste.site.explorar import INDICADORES_ESTADOS, POR_CHAVE, UFS, vista_estados
from nordeste.site.formatacao import numero
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


def test_base_publicada_tem_o_ibid_sem_brasil_fora_do_nordeste(dados):
    ibid = dados.base[dados.base.indicador_id == "ibid"]
    assert not ibid.empty
    assert set(ibid.subindicador) == {"geral", "contexto", "resultado"}
    assert "BR_FORA_NE" not in set(ibid.territorio_id)  # a referencia e a media nacional do INPI
    serie = dados.fichas["ibid"].serie("serie_historica")
    assert sorted(ibid.ano.unique()) == list(range(serie.inicio, serie.fim + 1))


def test_estados_mostra_a_posicao_do_ibid_com_os_valores_da_base(saida, dados):
    """Em Estados, o IBID e a posicao nacional (ficha ibid_posicao): o valor do indice nao se compara entre anos."""
    arvore = Arvore(_ler(saida, "estados/index.html"))
    ind = next(i for i in INDICADORES_ESTADOS if i.chave == "ibid")
    assert ind.indicador_id == "ibid_posicao" and not ind.maior_melhor
    assert any(o["attrs"]["value"] == "ibid" and Arvore.texto(o) == ind.rotulo for o in arvore.achar("option"))
    assert len(arvore.achar("div", classe="nn-vista", data_vista="ibid")) == 1

    vista = vista_estados(dados, ind)
    pontos = {uf: dados.serie("ibid_posicao", uf) for uf in UFS}
    anos = sorted({p.ano for lista in pontos.values() for p in lista})
    assert vista["anos"] == anos and len(vista["linhas"]) == 9
    for linha, uf in zip(vista["linhas"], UFS):
        por_ano = {p.ano: p.valor for p in pontos[uf]}
        assert [c["titulo"].rsplit(": ", 1)[1] for c in linha["celulas"]] == [f"{int(por_ano[a])}º no país" for a in anos]
    ultimo = anos[-1]
    esperado = sorted(UFS, key=lambda uf: next(p.valor for p in pontos[uf] if p.ano == ultimo))  # menor e melhor
    assert vista["ano_do_ranking"] == ultimo
    assert [r["posicao"].split(" ", 1)[1] for r in vista["ranking"]] == [
        next(l["estado"] for l in vista["linhas"] if l["uf"] == ("SE" if uf == "SE_UF" else uf)) for uf in esperado]


def test_explorar_tem_o_json_e_o_seletor_do_ibid(saida, dados):
    arvore = Arvore(_ler(saida, "explorar/index.html"))
    assert any(o["attrs"]["value"] == "ibid" for o in arvore.achar("option"))
    do_arquivo = json.loads(_ler(saida, "explorar/dados/ibid.json"))
    for territorio in ("NE", "BR", "PI", "SE_UF", "SE"):
        esperado = [[p.ano, p.valor, p.serie] for p in dados.serie("ibid", territorio, sub="geral")]
        assert do_arquivo[territorio] == esperado and esperado, territorio
    assert do_arquivo["BR_FORA_NE"] == []
    assert POR_CHAVE["ibid"].sub == "geral"


def test_sobre_lista_a_fonte_do_ibid(saida, dados):
    arvore = Arvore(_ler(saida, "sobre/index.html"))
    serie = dados.fichas["ibid"].serie("serie_historica")
    assert serie.url in {e["attrs"]["href"] for e in arvore.achar("a")}
    visivel = arvore.texto_visivel()
    assert dados.fichas["ibid"].nome in visivel and serie.fonte in visivel


def test_inicio_ainda_nao_fala_do_ibid(saida):
    """O IBID e a inovacao tem pagina propria; o Inicio so os cita no menu do alto (cartao da pagina Inovacao)."""
    html = _ler(saida, "index.html")
    conteudo = html[html.index("<main"):html.index("</main>")]
    assert "IBID" not in conteudo and "Inovação" not in conteudo
