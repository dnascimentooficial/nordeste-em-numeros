"""A medicao de audiencia (Umami Cloud) no site gerado: o script em toda pagina dos dois idiomas, configurado num lugar
so (gerar.MEDICAO); a CSP que libera so ele e o envio; os eventos dos links e botoes (data-umami-event); os do site.js;
e a secao "O que eu meco neste site" em Sobre, nos dois idiomas."""

import re
from pathlib import Path

import pytest
import yaml

from nordeste.caminhos import Caminhos
from nordeste.site.gerar import MEDICAO, gerar_site, host_do_link

from auxiliares import RAIZ, Arvore

SITE_ID = "4cd60c19-92f7-4c3d-a590-1a8c86a93120"
SCRIPT = "https://cloud.umami.is/script.js"
FONTES_DO_UMAMI = {
    "script-src": ["'self'", "https://cloud.umami.is"],
    "connect-src": ["'self'", "https://cloud.umami.is", "https://*.umami.is", "https://*.umami.dev"],
}
EVENTO = re.compile(r"^[a-z]+(-[a-z]+)*$")  # nome do evento em ingles, kebab-case
EVENTOS_DO_SITE_JS = ("explore-select", "states-select", "era-open", "scroll-depth", "chart-enlarge", "map-tab", "map-tile")


@pytest.fixture(scope="module")
def saida(tmp_path_factory) -> Path:
    destino = tmp_path_factory.mktemp("site") / "saida"
    gerar_site(Caminhos(raiz=RAIZ), destino, imagens=False)
    return destino


def _arvore(saida: Path, rota: str) -> Arvore:
    return Arvore((saida / rota.strip("/") / "index.html").read_text(encoding="utf-8"))


def _paginas(saida: Path) -> list[Path]:
    return sorted(saida.rglob("index.html"))


def _eventos(arvore: Arvore, nome: str) -> list[dict]:
    return [e for e in arvore.elementos if e["attrs"].get("data-umami-event") == nome]


def _props(elemento: dict) -> dict:
    return {k.removeprefix("data-umami-event-"): v for k, v in elemento["attrs"].items() if k.startswith("data-umami-event-")}


# --- o script ---


def test_configuracao_num_lugar_so():
    assert MEDICAO == {"script": SCRIPT, "site": SITE_ID, "dominio": "nordeste.dnascimento.com.br"}
    for modelo in (RAIZ / "src" / "nordeste" / "site" / "modelos").glob("*.html"):
        texto = modelo.read_text(encoding="utf-8")
        assert SITE_ID not in texto and "umami.is" not in texto, modelo.name  # so em gerar.MEDICAO


def test_script_em_toda_pagina_dos_dois_idiomas(saida):
    paginas = _paginas(saida)
    assert any("/en/" in p.as_posix() for p in paginas) and len(paginas) > 12
    for pagina in paginas:
        texto = pagina.read_text(encoding="utf-8")
        arvore = Arvore(texto)
        [script] = [s for s in arvore.achar("script") if s["attrs"].get("src") == SCRIPT]
        assert script["attrs"] == {
            "defer": None, "src": SCRIPT, "data-website-id": SITE_ID, "data-domains": "nordeste.dnascimento.com.br",
            "data-do-not-track": "true", "data-exclude-search": "true",
        }, pagina
        assert not Arvore.texto(script), pagina  # nada inline: a CSP nao deixa
        # no <head>, depois do site.js: o site nao espera pelo Umami
        assert texto.index('<script src="/site.js?v=') < texto.index(f'src="{SCRIPT}"') < texto.index("</head>"), pagina
        assert texto.count("umami.is") == 1, pagina
        assert arvore.achar("body")[0]["attrs"].get("data-pagina"), pagina


def test_imagem_de_compartilhar_nao_tem_o_script():
    """A pagina de apoio que o Chromium fotografa (og.html) nao e publicada e nao herda o base.html."""
    assert "medicao" not in (RAIZ / "src" / "nordeste" / "site" / "modelos" / "og.html").read_text(encoding="utf-8")


# --- CSP ---


def _csp(saida: Path) -> dict[str, list[str]]:
    linha = next(l for l in (saida / ".htaccess").read_text(encoding="utf-8").splitlines() if "Content-Security-Policy" in l)
    diretivas = [d.split() for d in linha.split('"')[1].split(";") if d.strip()]
    return {d[0]: d[1:] for d in diretivas}


def test_csp_libera_so_o_umami_e_continua_sem_inline(saida):
    csp = _csp(saida)
    for diretiva, fontes in FONTES_DO_UMAMI.items():
        assert csp[diretiva] == fontes, diretiva
    assert csp["default-src"] == csp["style-src"] == csp["font-src"] == ["'self'"]
    assert csp["img-src"] == ["'self'", "data:"]
    texto = " ".join(" ".join(v) for v in csp.values())
    for proibido in ("'unsafe-inline'", "'unsafe-eval'", "'unsafe-hashes'", "'nonce-", "'sha256-", "*.", "http:"):
        if proibido == "*.":  # curinga so nos dois dominios do envio do Umami
            assert re.findall(r"\S*\*\S*", texto) == ["https://*.umami.is", "https://*.umami.dev"]
            continue
        assert proibido not in texto, proibido


# --- eventos dos links e botoes ---


def test_nomes_e_propriedades_curtos_em_toda_pagina(saida):
    for pagina in _paginas(saida):
        for e in Arvore(pagina.read_text(encoding="utf-8")).elementos:
            nome = e["attrs"].get("data-umami-event")
            if nome is None:
                assert not _props(e), (pagina, e["tag"])  # propriedade sem evento nao vai a lugar nenhum
                continue
            assert EVENTO.fullmatch(nome) and len(nome) <= 50, (pagina, nome)
            assert e["tag"] in ("a", "button"), (pagina, nome)  # o Umami so conta o clique em <a> e <button>
            for prop, valor in _props(e).items():
                assert re.fullmatch(r"[a-z]+", prop) and valor and len(valor) <= 50 and " " not in valor, (pagina, nome, prop, valor)


@pytest.mark.parametrize("rota, lang", [("/cards/pobreza/", "pt"), ("/en/cards/pobreza/", "en")])
def test_download_do_card(saida, rota, lang):
    [link] = _arvore(saida, rota).achar("a", classe="nn-baixar")
    assert link["attrs"]["data-umami-event"] == "card-download"
    assert _props(link) == {"card": "pobreza", "lang": lang}
    # o Umami troca o clique num link com evento por uma navegacao ao href, a nao ser com target="_blank": sem ele, o
    # PNG abriria em vez de baixar
    assert "download" in link["attrs"] and link["attrs"]["target"] == "_blank"


@pytest.mark.parametrize("rota", ["/dados/", "/en/data/"])
def test_download_das_planilhas(saida, rota):
    links = _arvore(saida, rota).achar("a", classe="nn-baixar")
    assert len(links) >= 2
    for link in links:
        assert link["attrs"]["data-umami-event"] == "csv-download"
        assert _props(link) == {"file": link["attrs"]["href"].rsplit("/", 1)[1]}
        assert "download" in link["attrs"] and link["attrs"]["target"] == "_blank"


@pytest.mark.parametrize("rota, chave", [("/", "index"), ("/en/", "index"), ("/inovacao/", "inovacao"), ("/en/innovation/", "inovacao")])
def test_botoes_ampliar(saida, rota, chave):
    arvore = _arvore(saida, rota)
    botoes = arvore.achar("button", classe="nn-ampliar")
    assert len(botoes) >= 3
    for botao in botoes:
        assert botao["attrs"]["data-umami-event"] == "chart-enlarge"
        assert _props(botao) == {"chart": botao["attrs"]["data-ampliado"].removeprefix("nn-ampliado-"), "page": chave}


@pytest.mark.parametrize("rota", ["/", "/en/states/", "/sobre/", "/cards/pobreza/"])
def test_menu_gaveta_idioma_e_botao_laranja(saida, rota):
    arvore = _arvore(saida, rota)
    menu = _eventos(arvore, "menu-click")
    itens = [_props(e)["item"] for e in menu]
    # cada item duas vezes: na barra do computador e na gaveta do celular
    assert sorted(set(itens)) == sorted(["index", "como-chegamos", "inovacao", "cards", "estados", "explorar", "dados", "sobre"])
    assert all(itens.count(i) == 2 for i in set(itens)), itens
    trocas = _eventos(arvore, "lang-switch")
    outro = "pt" if rota.startswith("/en/") else "en"
    assert [_props(e) for e in trocas] == [{"to": outro}] * 2  # barra e gaveta; o idioma atual nao conta
    assert all(e["attrs"]["class"] == "nn-idioma" for e in trocas)
    [botao] = arvore.achar("a", classe="nn-topo-botao")
    assert botao["attrs"]["data-umami-event"] == "cta-click"
    assert _props(botao) == {"target": "como-chegamos", "place": "top"}


def test_chamadas_das_paginas(saida):
    inicio = _arvore(saida, "/")
    chamadas = _eventos(inicio, "cta-click")
    alvos = {(_props(e)["target"], _props(e)["place"]) for e in chamadas}
    assert ("como-chegamos", "top") in alvos and ("como-chegamos", "home") in alvos
    assert {"card", "estados", "explorar"} <= {alvo for alvo, _ in alvos}
    ids = {e["attrs"]["id"] for e in inicio.achar("article", classe="nn-capitulo")}
    do_pe = [_props(e) for e in chamadas if _props(e)["target"] in ("card", "estados", "explorar")]
    assert len(do_pe) >= 2 * len(ids)  # o pe de cada pergunta diz de que pergunta saiu (place: o id dela)
    assert {f"q-{p['place']}" for p in do_pe} == ids
    inovacao = _eventos(_arvore(saida, "/inovacao/"), "cta-click")
    assert "dados" in {_props(e)["target"] for e in inovacao}
    historia = _eventos(_arvore(saida, "/como-chegamos/"), "cta-click")
    assert {(_props(e)["target"], _props(e)["place"]) for e in historia} >= {("index", "fecho"), ("cards", "fecho")}
    [botao] = _arvore(saida, "/como-chegamos/").achar("a", classe="nn-topo-botao")
    assert _props(botao) == {"target": "cards", "place": "top"}  # nesta pagina o botao laranja leva aos cards


@pytest.mark.parametrize("rota", ["/sobre/", "/en/about/"])
def test_links_das_fontes_em_sobre(saida, rota):
    arvore = _arvore(saida, rota)
    externos = [e for e in arvore.achar("a") if e["attrs"].get("href", "").startswith("http")
                and not e["attrs"]["href"].startswith("https://nordeste.dnascimento.com.br")]
    fontes = [e for e in externos if e["attrs"].get("data-umami-event") == "source-click"]
    assert len(fontes) >= 20
    for link in fontes:
        assert _props(link) == {"host": host_do_link(link["attrs"]["href"])}
    hosts = {_props(l)["host"] for l in fontes}
    assert any(h.endswith("ibge.gov.br") for h in hosts) and "commons.wikimedia.org" in hosts, hosts
    # de fora ficam so o site do autor e a licenca: os links externos de Sobre sao fontes e creditos de imagem
    sem_evento = {host_do_link(e["attrs"]["href"]) for e in externos if e not in fontes}
    assert sem_evento <= {"dnascimento.com.br", "creativecommons.org"}, sem_evento


def test_links_das_fontes_das_epocas(saida):
    arvore = _arvore(saida, "/como-chegamos/")
    fontes = [e for e in arvore.elementos if e["tag"] == "a" and e["attrs"].get("data-umami-event") == "source-click"]
    assert len(fontes) >= 10
    assert all(_props(e)["host"] == host_do_link(e["attrs"]["href"]) for e in fontes)


def test_host_do_link():
    assert host_do_link("https://www.ibge.gov.br/estatisticas/x.html?y=1") == "ibge.gov.br"
    assert host_do_link("https://sidra.ibge.gov.br/tabela/5938") == "sidra.ibge.gov.br"
    assert host_do_link("ftp://ftp.ibge.gov.br/a") == "ftp.ibge.gov.br"


# --- eventos do site.js ---


def test_site_js_mede_so_com_o_umami_e_sem_quebrar(saida):
    js = (saida / "site.js").read_text(encoding="utf-8")
    for nome in EVENTOS_DO_SITE_JS:
        assert f"medir('{nome}'" in js, nome
    # um lugar so chama o Umami, e so se ele existe; um erro dele nunca sobe
    assert js.count("umami.track(") == 1
    assert "if (window.umami && typeof window.umami.track === 'function')" in js
    assert re.search(r"function medir\(nome, dados\) \{\ntry \{", js)
    # as secoes lidas ligam no load (depois do script do Umami) e so com ele
    assert "if (!window.umami || !('IntersectionObserver' in window)) return;" in js
    assert "window.addEventListener('load', comecarLeitura, { once: true })" in js


# --- "O que eu meco neste site" ---


@pytest.mark.parametrize("rota, titulo, trechos", [
    ("/sobre/", "O que eu meço neste site",
     ("Umami", "código aberto", "cookies", "não grava sessões", "dados pessoais", "IP", "páginas visitadas",
      "tempo", "país", "aparelho", "cards baixados", "planilhas baixadas", "gráficos ampliados", "seções lidas",
      "Do Not Track", "umami.disabled", "1", "aquele navegador", "o que melhorar")),
    ("/en/about/", "What I measure on this site",
     ("Umami", "open-source", "cookies", "records no sessions", "personal data", "IP", "pages visited", "time",
      "country", "device", "cards downloaded", "spreadsheets downloaded", "charts enlarged", "sections read",
      "Do Not Track", "umami.disabled", "1", "per browser", "what to improve")),
])
def test_secao_o_que_eu_meco(saida, rota, titulo, trechos):
    arvore = _arvore(saida, rota)
    [secao] = arvore.achar("article", id="sobre-medicao")
    texto = Arvore.texto(secao)
    assert texto.startswith(titulo)
    for trecho in trechos:
        assert trecho in texto, trecho
    assert 90 <= len(texto.split()) <= 150  # curta: umas 120 palavras
    ordem = [e["attrs"]["id"] for e in arvore.achar("article") if e["attrs"].get("id", "").startswith(("sobre-", "autor"))]
    assert ordem[-2:] == ["sobre-medicao", "autor"]


def test_textos_da_medicao_nos_dois_idiomas():
    pt = yaml.safe_load((RAIZ / "metadados" / "site" / "textos.yaml").read_text(encoding="utf-8"))["medicao"]
    en = yaml.safe_load((RAIZ / "metadados" / "site" / "en" / "textos.yaml").read_text(encoding="utf-8"))["medicao"]
    assert set(pt) == set(en) == {"titulo", "paragrafos"}
    assert len(pt["paragrafos"]) == len(en["paragrafos"]) == 3
