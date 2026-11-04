"""A versao em ingles (/en/): a camada de traducao sobre o conteudo em portugues, as paginas em par nos dois idiomas, o
seletor de idioma, os metadados de SEO e a formatacao de numeros e datas em ingles."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

from nordeste.caminhos import Caminhos
from nordeste.site import gerar
from nordeste.site.conteudo import ErroConteudo, carregar_conteudo
from nordeste.site.formatacao import escala_auto, numero, ordinal
from nordeste.site.gerar import gerar_site
from nordeste.site.idioma import (
    ARQUIVOS_TRADUZIDOS, ROTAS, ErroTraducao, _com_traducao, em_idioma, marcadores, outra_rota, traducoes_faltando,
    traduzir,
)
from nordeste.site.interface import (
    INDICADORES_ESTADOS_EN, INDICADORES_EXPLORAR_EN, ROTULOS, TERRITORIOS_EN,
)
from nordeste.site.explorar import INDICADORES_ESTADOS, INDICADORES_EXPLORAR, TERRITORIOS

from auxiliares import RAIZ, Arvore, copiar_base

SITE = "https://nordeste.dnascimento.com.br"
PASTA = RAIZ / "metadados" / "site"
# palavras e trechos da interface em portugues que nao podem sobrar nas paginas em ingles (fora de nomes proprios e
# titulos de fontes, que ficam no original: "Atlas Brasil", "Rio Grande do Norte", "PNAD Contínua"...)
PORTUGUES_DA_INTERFACE = (
    "Início", "Histórias", "Sobre os dados", "Abrir o menu", "Voltar ao topo", "Ir para o conteúdo", "Páginas do site",
    "Ver os números", "Fonte e método", "Atualizado em", "Próximo dado", "Desenvolvido por", "Compilação sob",
    "Dados oficiais publicados", "Legenda dos gráficos", "Faixas de governo", "Interinidade", "Gráfico de linhas",
    "No frigir dos ovos", "Em resumo", "Baixar", "Indicador", "Território", "Comparar lado a lado", "nenhum",
    "época anterior", "próxima época", "Linha do tempo", "A conta dos censos", "O que ficou disso", "Marcos de",
    "sem dado", "no país", "Ampliar", "Fechar", "Quebra de série", "Gire o celular", "Publicados em", "Ranking dos estados",
    "Série da fonte", "Órgão", "Tabela ou arquivo", "Imagem de compartilhamento", "Ir para Dados", "Continuar",
    "Ver a resposta", "Ver mais", "As seis perguntas", "O que os dados dizem", "Cards para compartilhar",
    "Explorar os dados", "dados de", "Imagem:", "Foto:", "domínio público", "dado oficial", "estimativa de historiador",
)


def _ler(saida: Path, arquivo: str) -> str:
    return (saida / arquivo).read_text(encoding="utf-8")


def _texto_e_atributos(html: str) -> str:
    arvore = Arvore(html)
    atributos = [
        v for e in arvore.elementos for k, v in e["attrs"].items()
        if v and k in ("aria-label", "title", "alt", "placeholder") or (v and k.startswith("data-") and " " in (v or ""))
    ]
    return arvore.texto_visivel() + " " + " ".join(atributos)


@pytest.fixture(scope="module")
def gerado(tmp_path_factory) -> tuple[Path, object]:
    saida = tmp_path_factory.mktemp("site") / "saida"
    return saida, gerar_site(Caminhos(raiz=RAIZ), saida, imagens=False)


# --- a camada de traducao ---


def test_traducoes_do_repositorio_completas_e_com_os_mesmos_marcadores():
    """Os arquivos em ingles do repositorio repetem a estrutura dos em portugues, sem texto faltando nem sobrando, e
    cada texto traduzido traz os mesmos marcadores de dado e de modelo do original."""
    assert traducoes_faltando(PASTA) == []
    for nome in ARQUIVOS_TRADUZIDOS:
        if nome == "fichas":
            continue
        original = yaml.safe_load((PASTA / f"{nome}.yaml").read_text(encoding="utf-8"))
        traducao = yaml.safe_load((PASTA / "en" / f"{nome}.yaml").read_text(encoding="utf-8"))
        assert _caminhos(original) == _caminhos(traducao), nome  # mesmas chaves e listas do mesmo tamanho
        for (onde, pt), (_, en) in zip(_folhas(original), _folhas(traducao)):
            if isinstance(pt, str):
                assert marcadores(pt) == marcadores(en), f"{nome}: {onde}"
        traduzir(original, PASTA, nome, "en")  # e a carga aceita (marcador diferente levantaria ErroTraducao)


def _caminhos(obj: object, onde: str = "") -> list[str]:
    if isinstance(obj, dict):
        return [onde] + [c for k, v in obj.items() for c in _caminhos(v, f"{onde}/{k}")]
    if isinstance(obj, list):
        return [f"{onde}[{len(obj)}]"] + [c for i, v in enumerate(obj) for c in _caminhos(v, f"{onde}/{i}")]
    return [onde]


def _folhas(obj: object, onde: str = ""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _folhas(v, f"{onde}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _folhas(v, f"{onde}[{i}]")
    else:
        yield onde, obj


def test_fichas_em_ingles_cobrem_os_campos_mostrados():
    fichas = yaml.safe_load((PASTA / "en" / "fichas.yaml").read_text(encoding="utf-8"))
    ids = {yaml.safe_load(f.read_text(encoding="utf-8"))["id"] for f in (RAIZ / "metadados" / "indicadores").glob("*.yaml")}
    assert set(fichas) == ids


def _traducao_temporaria(tmp_path: Path, nome: str, alterar) -> Path:
    pasta = tmp_path / "site"
    shutil.copytree(PASTA, pasta)
    arquivo = pasta / "en" / f"{nome}.yaml"
    dados = yaml.safe_load(arquivo.read_text(encoding="utf-8"))
    alterar(dados)
    arquivo.write_text(yaml.safe_dump(dados, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return pasta


def test_texto_sem_traducao_cai_no_portugues_e_vai_para_o_relatorio(tmp_path):
    def tirar(textos):
        del textos["menu"]["inicio"]
        textos["placar"]["titulo"] = ""
        textos["perguntas_rotulos"].pop("indice")
    pasta = _traducao_temporaria(tmp_path, "textos", tirar)
    textos = carregar_conteudo(pasta, "en").textos
    assert textos["menu"]["inicio"] == "Início" and textos["placar"]["titulo"] == "O que os números respondem"
    assert textos["menu"]["sobre"] == "About the data"  # o resto continua traduzido
    assert traducoes_faltando(pasta) == [
        "en/textos.yaml: placar.titulo", "en/textos.yaml: perguntas_rotulos.indice", "en/textos.yaml: menu.inicio",
    ]


def test_arquivo_de_traducao_ausente_vira_portugues_inteiro(tmp_path):
    pasta = tmp_path / "site"
    shutil.copytree(PASTA, pasta)
    (pasta / "en" / "cards.yaml").unlink()
    cards = carregar_conteudo(pasta, "en").cards
    assert cards[0]["frase_feita"] == carregar_conteudo(PASTA).cards[0]["frase_feita"]
    assert "en/cards.yaml: (arquivo inteiro)" in traducoes_faltando(pasta)


def test_marcador_diferente_do_portugues_e_erro(tmp_path):
    def trocar(perguntas):
        perguntas[0]["lide"] = perguntas[0]["lide"].replace("{", "{x", 1)
    pasta = _traducao_temporaria(tmp_path, "perguntas", trocar)
    with pytest.raises(ErroConteudo, match="marcadores"):
        carregar_conteudo(pasta, "en")
    with pytest.raises(ErroTraducao, match="marcadores"):  # tambem os de modelo, entre colchetes
        _com_traducao({"a": "Ver mais [n] gráficos"}, {"a": "Show [m] more charts"}, "teste")
    assert _com_traducao({"a": "Ver mais [n] gráficos"}, {"a": "Show [n] more charts"}, "teste") == {"a": "Show [n] more charts"}


def test_ids_condicoes_e_selecao_dos_dados_ficam_sempre_os_do_portugues(tmp_path):
    def mexer(perguntas):
        perguntas[0]["fecho"]["condicao"] = "vol_ne.ultimo > 0"
        perguntas[0]["id"] = "outro"
        perguntas[0]["graficos"][0]["linhas"][0]["indicador"] = "populacao"
    pasta = _traducao_temporaria(tmp_path, "perguntas", mexer)
    pt, en = carregar_conteudo(PASTA).perguntas[0], carregar_conteudo(pasta, "en").perguntas[0]
    assert en["fecho"]["condicao"] == pt["fecho"]["condicao"]
    assert en["graficos"][0]["linhas"][0]["indicador"] == pt["graficos"][0]["linhas"][0]["indicador"]
    # o item da lista com id diferente nao casa com o do portugues: o texto dele fica em portugues
    assert en["id"] == pt["id"] and en["frase_feita"] == pt["frase_feita"]


def test_traducao_faltando_nao_para_a_geracao(tmp_path):
    raiz = copiar_base(tmp_path / "repo")
    for nome in ("textos", "perguntas", "historia"):
        (raiz / "metadados" / "site" / "en" / f"{nome}.yaml").unlink()
    saida = tmp_path / "saida"
    relatorio = gerar_site(Caminhos(raiz=raiz), saida, imagens=False)
    assert "en/textos.yaml: (arquivo inteiro)" in relatorio.traducoes_faltando
    assert (saida / "en" / "index.html").is_file() and (saida / "en" / "how-we-got-here" / "index.html").is_file()


# --- rotulos fixos do codigo ---


def test_rotulos_da_interface_tem_as_mesmas_chaves_e_os_mesmos_campos_nos_dois_idiomas():
    assert ROTULOS["pt"].keys() == ROTULOS["en"].keys()
    for chave, pt in ROTULOS["pt"].items():
        assert re.findall(r"\{\w+\}", pt) == re.findall(r"\{\w+\}", ROTULOS["en"][chave]), chave
    assert set(INDICADORES_EXPLORAR_EN) == {i.chave for i in INDICADORES_EXPLORAR}
    assert set(INDICADORES_ESTADOS_EN) == {i.chave for i in INDICADORES_ESTADOS}
    assert set(TERRITORIOS_EN) <= {t[0] for t in TERRITORIOS}


# --- formatacao ---


def test_numeros_em_ingles():
    with em_idioma("en"):
        assert numero(1234.5, 1) == "1,234.5"
        assert numero(0.5032, 3) == "0.503"
        assert numero(-0.04, 1) == "0.0"
        assert escala_auto(2186521) == "2.19 million"
        assert escala_auto(403431) == "403 thousand"
        assert [ordinal(n) for n in (1, 2, 3, 4, 11, 12, 13, 21, 22, 23, 27)] == [
            "1st", "2nd", "3rd", "4th", "11th", "12th", "13th", "21st", "22nd", "23rd", "27th"]
        assert gerar.data_por_extenso("2026-11-01") == "November 1, 2026"
        assert gerar.mes_por_extenso("2027-02") == "February 2027"
        assert gerar.data_curta("2026-11-03") == "Nov. 3, 2026"
    # fora do `with`, o portugues de sempre
    assert numero(1234.5, 1) == "1.234,5" and ordinal(3) == "3º"
    assert gerar.data_por_extenso("2026-11-01") == "1º de novembro de 2026" and gerar.data_curta("2026-11-03") == "03/11/2026"


@pytest.mark.skipif(shutil.which("node") is None, reason="sem Node.js para rodar o site.js")
def test_numeros_do_script_em_ingles_iguais_aos_do_python():
    casos = [[1234.5, 1], [0.5032, 3], [1234567.891, 0], [-0.04, 1], [-1.5, 1], [2.5, 0], [0.125, 2], [38.75, 1]]
    programa = (
        "const NN = require(process.argv[1]); const casos = " + json.dumps(casos) + ";"
        "console.log(JSON.stringify(casos.map(([v, c]) => [NN.numero(v, c, 'en'), NN.numero(v, c, 'pt')])));"
    )
    feito = subprocess.run(["node", "-e", programa, str(gerar.PASTA_ESTATICOS / "site.js")], capture_output=True,
                           text=True, check=True)
    assert json.loads(feito.stdout) == [[numero(v, c, "en"), numero(v, c, "pt")] for v, c in casos]


def test_script_conta_os_numeros_no_formato_da_pagina():
    """A contagem da abertura reconhece 38,8% no portugues e 38.8% no ingles (o idioma vem do <html lang>)."""
    js = (gerar.PASTA_ESTATICOS / "site.js").read_text(encoding="utf-8")
    assert "document.documentElement.lang" in js
    assert r"/(\d{1,3}(?:,\d{3})*\.\d+%?)/" in js and r"/(\d{1,3}(?:\.\d{3})*,\d+%?)/" in js


# --- paginas nos dois idiomas ---


def _rota_do_arquivo(arquivo: str) -> str:
    return "/" + arquivo.removesuffix("index.html")


def test_cada_pagina_em_portugues_tem_a_sua_em_ingles_e_o_seletor_leva_de_uma_a_outra(gerado):
    saida, relatorio = gerado
    portugues = [p for p in relatorio.paginas if not p.startswith("en/")]
    ingles = [p for p in relatorio.paginas if p.startswith("en/")]
    assert len(portugues) == len(ingles) > 8
    for arquivo in portugues:
        rota = _rota_do_arquivo(arquivo)
        par = outra_rota(rota, "en")
        assert (saida / par.lstrip("/") / "index.html").is_file(), par
        assert outra_rota(par, "pt") == rota
        for de, para, lang in ((rota, par, "en"), (par, rota, "pt-BR")):
            html = _ler(saida, de.lstrip("/") + "index.html")
            seletores = [a for a in Arvore(html).achar("a", classe="nn-idioma")]
            assert len(seletores) == 4, de  # PT e EN na barra e na gaveta
            atuais = [a["attrs"]["href"] for a in seletores if a["attrs"].get("aria-current") == "true"]
            outros = [a for a in seletores if a["attrs"].get("aria-current") != "true"]
            assert atuais == [de, de]
            assert {(a["attrs"]["href"], a["attrs"]["lang"], a["attrs"]["hreflang"]) for a in outros} == {(para, lang, lang)}


def test_rotas_em_ingles(gerado):
    saida, _ = gerado
    for chave, rota in ROTAS["en"].items():
        assert (saida / rota.lstrip("/") / "index.html").is_file(), chave
    assert ROTAS["en"]["como-chegamos"] == "/en/how-we-got-here/" and ROTAS["en"]["inovacao"] == "/en/innovation/"


def test_lang_hreflang_canonical_e_og_locale_em_todas_as_paginas(gerado):
    saida, relatorio = gerado
    for arquivo in relatorio.paginas:
        ingles = arquivo.startswith("en/")
        rota = _rota_do_arquivo(arquivo)
        pt, en = (outra_rota(rota, "pt"), rota) if ingles else (rota, outra_rota(rota, "en"))
        html = _ler(saida, arquivo)
        arvore = Arvore(html)
        assert arvore.achar("html")[0]["attrs"]["lang"] == ("en" if ingles else "pt-BR"), arquivo
        alternativas = {a["attrs"]["hreflang"]: a["attrs"]["href"] for a in arvore.achar("link", rel="alternate")}
        assert alternativas == {"pt-BR": SITE + pt, "en": SITE + en, "x-default": SITE + pt}, arquivo
        assert arvore.achar("link", rel="canonical")[0]["attrs"]["href"] == SITE + rota
        locale = {m["attrs"]["property"]: m["attrs"]["content"] for m in arvore.achar("meta") if
                  m["attrs"].get("property", "").startswith("og:locale")}
        assert locale == ({"og:locale": "en_US", "og:locale:alternate": "pt_BR"} if ingles
                          else {"og:locale": "pt_BR", "og:locale:alternate": "en_US"}), arquivo


def test_json_ld_no_idioma_da_pagina(gerado):
    saida, _ = gerado
    for arquivo, lang, url in (("index.html", "pt-BR", "/dados/"), ("en/index.html", "en", "/en/data/"),
                               ("en/data/index.html", "en", "/en/data/")):
        bloco = re.search(r'<script type="application/ld\+json">(.*?)</script>', _ler(saida, arquivo), flags=re.S)[1]
        ld = json.loads(bloco)
        assert ld["inLanguage"] == lang and ld["url"] == SITE + url
        assert all(d["contentUrl"].startswith(f"{SITE}/dados/") for d in ld["distribution"])  # os mesmos CSV


def test_paginas_em_ingles_usam_os_mesmos_arquivos_estaticos_e_de_dados(gerado):
    saida, _ = gerado
    assert sorted(p.name for p in (saida / "en").iterdir()) == sorted(
        [r.strip("/").split("/")[1] for r in ROTAS["en"].values() if r != "/en/"] + ["index.html"])
    assert not list((saida / "en").rglob("*.css")) and not list((saida / "en").rglob("*.js"))
    assert not list((saida / "en").rglob("*.csv")) and not list((saida / "en").rglob("*.json"))
    html = _ler(saida, "en/explore/index.html")
    assert 'data-dados="/explorar/dados/"' in html
    dados = _ler(saida, "en/data/index.html")
    assert 'href="/dados/base_nordeste.csv"' in dados and 'href="/dados/derivados.csv"' in dados


def test_paginas_em_ingles_sem_interface_em_portugues(gerado):
    saida, relatorio = gerado
    sobras = {}
    for arquivo in (p for p in relatorio.paginas if p.startswith("en/")):
        texto = _texto_e_atributos(_ler(saida, arquivo))
        achados = [t for t in PORTUGUES_DA_INTERFACE if re.search(rf"(?<!\w){re.escape(t)}(?!\w)", texto)]
        if achados:
            sobras[arquivo] = achados
    assert sobras == {}


def test_numeros_das_paginas_em_ingles_no_formato_americano(gerado):
    saida, _ = gerado
    inicio = Arvore(_ler(saida, "en/index.html"))
    valores = [Arvore.texto(e) for e in inicio.achar("span", classe="nn-numero-valor")]
    assert valores and all(re.fullmatch(r"\d{1,3}(,\d{3})*\.\d%", v) for v in valores), valores
    estados = _ler(saida, "en/states/index.html")
    assert re.search(r"<span>1st [A-Z]", estados) and re.search(r"\d+(st|nd|rd|th) in Brazil", estados)
    assert "º" not in Arvore(estados).texto_visivel()
    assert "Line chart, " in _ler(saida, "en/explore/index.html")
    # o portugues continua com virgula decimal
    assert all("," in Arvore.texto(e) for e in Arvore(_ler(saida, "index.html")).achar("span", classe="nn-numero-valor"))


def test_explorar_em_ingles_leva_os_rotulos_do_redesenho(gerado):
    saida, _ = gerado
    cartao = Arvore(_ler(saida, "en/explore/index.html")).achar("article", id="explorar-grafico")[0]
    rotulos = json.loads(cartao["attrs"]["data-rotulos"])
    assert rotulos["colunas"] == ["Year", "Area", "Value", "Source series"] and rotulos["e"] == "and"
    assert rotulos["desc"].startswith("Line chart, {titulo}.")


def test_cards_em_ingles_com_o_aviso_da_frase_comum_e_a_imagem_propria(gerado):
    saida, relatorio = gerado
    cards = [p for p in relatorio.paginas if re.fullmatch(r"en/cards/[^/]+/index\.html", p)]
    assert cards
    for arquivo in cards:
        id_ = arquivo.split("/")[2]
        arvore = Arvore(_ler(saida, arquivo))
        assert Arvore.texto(arvore.achar("p", classe="nn-c-comum")[0]) == "A common saying in Brazil"
        og = {m["attrs"]["property"]: m["attrs"]["content"] for m in arvore.achar("meta") if "property" in m["attrs"]}
        assert og["og:image"] == f"{SITE}/en/cards/{id_}.png"
        assert arvore.achar("a", classe="nn-baixar")[0]["attrs"]["href"] == f"/en/cards/{id_}.png"
    portugues = Arvore(_ler(saida, "cards/pobreza/index.html"))
    assert not portugues.achar("p", classe="nn-c-comum")
