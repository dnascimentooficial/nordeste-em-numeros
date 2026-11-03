"""O menu do alto (textos.yaml, menu), as capas das páginas internas e o botão voltar ao topo, no HTML gerado."""

import re
from pathlib import Path

import pytest
import yaml

from nordeste.caminhos import Caminhos
from nordeste.site import gerar
from nordeste.site.conteudo import ErroConteudo, carregar_conteudo
from nordeste.site.gerar import gerar_site
from nordeste.site.historia import carregar_historia

from auxiliares import RAIZ, Arvore, copiar_base, definir_foto, estaticos_sem_foto

PAGINAS_COM_CAPA = {  # pagina -> (chave em CAPAS, classe esperada com o repositorio inteiro)
    "como-chegamos/index.html": "nn-capa-1530", "estados/index.html": "nn-capa-1964",
    "explorar/index.html": "nn-capa-1950", "cards/index.html": "nn-capa-marco-1932",
    "dados/index.html": "nn-capa-marco-1934", "sobre/index.html": "nn-capa-abertura",
    "inovacao/index.html": "nn-capa-marco-1959",
}
TODAS = ("index.html", *PAGINAS_COM_CAPA)


def _ler(saida: Path, pagina: str) -> str:
    return (saida / pagina).read_text(encoding="utf-8")


def _cabecalho(html: str) -> str:
    return re.search(r"<header\b.*?</header>", html, flags=re.S)[0]


def _botao(html: str) -> tuple[str, str]:
    a = Arvore(_cabecalho(html)).achar("a", classe="nn-topo-botao")
    assert len(a) == 1
    return a[0]["attrs"]["href"], Arvore.texto(a[0])


def _sem_historia(raiz: Path) -> Path:
    (raiz / "metadados" / "site" / "historia.yaml").unlink()
    return raiz


@pytest.fixture(scope="module")
def gerado(tmp_path_factory) -> Path:
    saida = tmp_path_factory.mktemp("site") / "saida"
    gerar_site(Caminhos(raiz=RAIZ), saida, imagens=False)
    return saida


@pytest.fixture(scope="module")
def sem_historia(tmp_path_factory) -> Path:
    raiz = _sem_historia(copiar_base(tmp_path_factory.mktemp("repo") / "repo"))
    saida = tmp_path_factory.mktemp("site") / "saida"
    gerar_site(Caminhos(raiz=raiz), saida, imagens=False)
    return saida


# --- menu ---


def test_cartoes_do_menu_trazem_as_contagens_da_pagina_e_dos_cards(gerado):
    html = _ler(gerado, "index.html")
    cartoes = {a["attrs"]["href"]: Arvore.texto(a) for a in Arvore(_cabecalho(html)).achar("a", classe="nn-menu-cartao")}
    assert list(cartoes) == ["/como-chegamos/", "/inovacao/", "/cards/", "/estados/", "/explorar/", "/dados/"]
    epocas = len(carregar_historia(RAIZ / "metadados" / "site").epocas)
    cards = len(list((gerado / "cards").glob("*/index.html")))
    por_extenso = gerar.POR_EXTENSO[epocas] if epocas < len(gerar.POR_EXTENSO) else str(epocas)
    assert f"em {por_extenso} épocas" in cartoes["/como-chegamos/"]
    assert cartoes["/cards/"].startswith("Cards para compartilhar") and f"{cards} frases feitas" in cartoes["/cards/"]
    assert "[" not in _cabecalho(html)  # nenhum marcador cru


def test_botao_do_alto_leva_a_linha_do_tempo_e_aos_cards_na_propria_pagina(gerado):
    for pagina in TODAS:
        href, texto = _botao(_ler(gerado, pagina))
        if pagina == "como-chegamos/index.html":
            assert (href, texto) == ("/cards/", "Baixar um card →")
        else:
            assert (href, texto) == ("/como-chegamos/", "Ver a linha do tempo →"), pagina
    # abaixo de 520 px o "Ver a" some: ele e um trecho a parte
    longo = Arvore(_cabecalho(_ler(gerado, "index.html"))).achar(classe="nn-topo-botao-longo")
    assert [Arvore.texto(e) for e in longo] == ["Ver a"]


def test_sem_a_pagina_historica_o_menu_fica_sem_ela_e_o_botao_leva_aos_cards(sem_historia):
    for pagina in ("index.html", "estados/index.html", "sobre/index.html"):
        html = _ler(sem_historia, pagina)
        assert _botao(html) == ("/cards/", "Baixar um card →")
        assert "/como-chegamos/" not in _cabecalho(html) and "/historia/" not in html
        hrefs = [a["attrs"]["href"] for a in Arvore(_cabecalho(html)).achar("a", classe="nn-menu-cartao")]
        assert hrefs == ["/inovacao/", "/cards/", "/estados/", "/explorar/", "/dados/"]
        assert 'nn-menu-painel nn-menu-painel-2' in html


def test_grupos_do_menu_funcionam_sem_javascript(gerado):
    cabecalho = _cabecalho(_ler(gerado, "index.html"))
    grupos = Arvore(cabecalho).achar("details", classe="nn-menu-grupo")
    assert [g["attrs"]["name"] for g in grupos] == ["nn-menu", "nn-menu"]
    movel = Arvore(cabecalho).achar("details", classe="nn-menu-movel")
    assert len(movel) == 1 and "open" not in movel[0]["attrs"]
    assert Arvore(cabecalho).achar("summary")[-3]["attrs"]["aria-label"] == "Abrir o menu"


@pytest.mark.parametrize("alterar, mensagem", [
    (lambda m: m["cartoes"]["cards"].update(texto="Frases feitas sobre o Nordeste."), r"menu.cartoes.cards.texto usa o marcador \[cards\]"),
    (lambda m: m["cartoes"]["estados"].update(texto="Os [n] estados."), r"menu.cartoes.estados.texto não usa marcador"),
    (lambda m: m.update(inicio=""), r"menu.inicio é um texto"),
    (lambda m: m.pop("botao_cards"), r"falta textos.menu.botao_cards"),
    (lambda m: m["cartoes"].pop("explorar"), r"falta textos.menu.cartoes.explorar"),
])
def test_textos_do_menu_sao_validados(tmp_path, alterar, mensagem):
    raiz = copiar_base(tmp_path / "repo")
    arquivo = raiz / "metadados" / "site" / "textos.yaml"
    textos = yaml.safe_load(arquivo.read_text(encoding="utf-8"))
    alterar(textos["menu"])
    arquivo.write_text(yaml.safe_dump(textos, allow_unicode=True, sort_keys=False), encoding="utf-8")
    with pytest.raises(ErroConteudo, match=mensagem):
        gerar_site(Caminhos(raiz=raiz), tmp_path / "saida", imagens=False)


def test_textos_do_menu_vem_do_textos_yaml(gerado):
    menu = carregar_conteudo(RAIZ / "metadados" / "site").textos["menu"]
    cabecalho = _cabecalho(_ler(gerado, "estados/index.html"))
    nav = re.search(r'<nav class="nn-menu".*?</nav>', cabecalho, flags=re.S)[0]
    soltos = [Arvore.texto(a) for a in Arvore(nav).achar("a") if not a["attrs"].get("class")]
    assert soltos == [menu["inicio"], menu["sobre"]]
    assert [Arvore.texto(s) for s in Arvore(nav).achar("summary")] == [menu["historias"], menu["dados"]]
    titulos = [Arvore.texto(t) for t in Arvore(nav).achar(classe="nn-menu-cartao-titulo")]
    assert titulos == [
        menu["cartoes"][c]["titulo"] for c in ("como-chegamos", "inovacao", "cards", "estados", "explorar", "dados")]


# --- capas ---


@pytest.mark.parametrize("pagina, classe", PAGINAS_COM_CAPA.items())
def test_cada_pagina_interna_abre_com_a_capa_e_o_credito_da_imagem(gerado, pagina, classe):
    html = _ler(gerado, pagina)
    main = html[html.index('<main id="conteudo"'):]
    primeiro = re.search(r"<main[^>]*>\s*<(\w+)[^>]*class=\"([^\"]+)\"", main)
    assert primeiro[1] == "section" and primeiro[2].split() == ["nn-capa", classe], pagina
    capa = re.search(r'<section class="nn-capa.*?</section>', main, flags=re.S)[0]
    arvore = Arvore(capa)
    titulo = arvore.achar("h1", id="titulo-principal")
    assert len(titulo) == 1 and len(Arvore(html).achar("h1")) == 1
    credito = arvore.achar("p", classe="nn-capa-credito")
    assert len(credito) == 1 and Arvore.texto(credito[0]).startswith("Imagem: ")
    assert "nn-topo-sobre-foto" in _cabecalho(html)
    if classe == "nn-capa-abertura":
        assert Arvore.texto(credito[0]) == "Imagem: Júlio Diógenes (composição com praia, mata e sertão do Nordeste)"
    else:
        # o credito da epoca ou do marco, do historia.yaml: autor, data e licenca, com o link da fonte
        imagem = gerar._imagem_historica(carregar_historia(RAIZ / "metadados" / "site"), classe.removeprefix("nn-capa-") + ".webp")
        assert Arvore.texto(credito[0]) == f"Imagem: {imagem.autor}, {imagem.data} (domínio público)"
        assert arvore.achar("a")[0]["attrs"]["href"] == imagem.url
        assert (gerado / "historia" / f"{classe.removeprefix('nn-capa-')}.webp").is_file()


def test_capas_tiram_o_titulo_e_a_abertura_da_pagina(gerado):
    textos = carregar_conteudo(RAIZ / "metadados" / "site").textos
    for pagina, chave in (("estados/index.html", "estados"), ("explorar/index.html", "explorar"), ("cards/index.html", "cards")):
        capa = Arvore(re.search(r'<section class="nn-capa.*?</section>', _ler(gerado, pagina), flags=re.S)[0])
        assert Arvore.texto(capa.achar("h1")[0]) == textos[chave]["titulo"]
        assert Arvore.texto(capa.achar("p", classe="nn-capa-intro")[0]) == " ".join(textos[chave]["intro"].split())
        assert _ler(gerado, pagina).count(textos[chave]["intro"][:40]) == 1  # a frase saiu da secao da pagina


def test_paginas_de_card_nao_ganham_capa(gerado):
    for card in (gerado / "cards").glob("*/index.html"):
        html = card.read_text(encoding="utf-8")
        assert "nn-capa" not in html and "nn-topo-sobre-foto" not in html, card


def test_sem_a_pagina_historica_as_capas_usam_a_foto_da_abertura(sem_historia):
    assert not (sem_historia / "historia").exists()
    for pagina in ("estados/index.html", "explorar/index.html", "cards/index.html", "dados/index.html", "sobre/index.html"):
        capa = re.search(r'<section class="([^"]+)"', _ler(sem_historia, pagina))[1]
        assert capa == "nn-capa nn-capa-abertura", pagina


def test_sem_historia_e_sem_foto_a_capa_fica_preta_e_sem_credito(tmp_path, monkeypatch):
    estaticos_sem_foto(tmp_path / "e", monkeypatch)
    raiz = _sem_historia(copiar_base(tmp_path / "repo"))
    definir_foto(raiz, None)
    saida = tmp_path / "saida"
    gerar_site(Caminhos(raiz=raiz), saida, imagens=False)
    html = _ler(saida, "estados/index.html")
    assert '<section class="nn-capa" aria-labelledby="titulo-principal">' in html and "nn-capa-credito" not in html


def test_imagem_da_capa_que_saiu_do_historia_yaml_volta_para_a_foto(tmp_path, monkeypatch):
    monkeypatch.setattr(gerar, "CAPAS", {**gerar.CAPAS, "estados": "nao-existe.webp"})
    saida = tmp_path / "saida"
    gerar_site(Caminhos(raiz=RAIZ), saida, imagens=False)
    assert '<section class="nn-capa nn-capa-abertura"' in _ler(saida, "estados/index.html")
    assert '<section class="nn-capa nn-capa-1950"' in _ler(saida, "explorar/index.html")


def test_imagens_das_capas_sao_de_epocas_ou_marcos_do_historia_yaml():
    historia = carregar_historia(RAIZ / "metadados" / "site")
    for chave, arquivo in gerar.CAPAS.items():
        if arquivo:
            assert gerar._imagem_historica(historia, arquivo) is not None, (chave, arquivo)


# --- voltar ao topo ---


@pytest.mark.parametrize("pagina", [*TODAS, "cards/pibpc/index.html"])
def test_voltar_ao_topo_em_todas_as_paginas_e_um_link_para_o_alto(gerado, pagina):
    voltar = Arvore(_ler(gerado, pagina)).achar("a", classe="nn-voltar")
    assert len(voltar) == 1
    assert voltar[0]["attrs"]["href"] == "#" and voltar[0]["attrs"]["aria-label"] == "Voltar ao topo"
