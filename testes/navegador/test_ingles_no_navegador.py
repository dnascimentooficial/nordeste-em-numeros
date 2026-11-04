"""A versao em ingles no Chromium: o peso da inicial, o seletor de idioma (barra e gaveta, de 320 px ao computador),
os numeros no formato americano no que o site.js escreve (contagem da abertura, dica de valor, redesenho do Explorar).

As paginas em ingles tambem entram em todas as rotas de test_site_no_navegador.py (axe, largura, movimento, console).
Marcador `navegador`: `python -m pytest -m navegador testes/navegador`.
"""

import re

import pytest

from test_site_no_navegador import LIMITE_DA_INICIAL, _estouro, _recursos_do_site

pytestmark = pytest.mark.navegador
NUMERO_EN = re.compile(r"\d{1,3}(,\d{3})*(\.\d+)?%?")


def test_peso_da_inicial_em_ingles(abrir):
    """O mesmo teto da inicial em portugues: 500 KB na primeira carga, sem a foto da abertura."""
    with abrir("/en/") as pagina:
        recursos = pagina.evaluate(
            """() => [performance.getEntriesByType('navigation')[0], ...performance.getEntriesByType('resource')]
                 .map((r) => ({ nome: r.name, bytes: r.transferSize }))"""
        )
    sem_a_foto = [r for r in _recursos_do_site(recursos) if "foto-abertura" not in r["nome"]]
    assert len(sem_a_foto) >= 5 and all(r["bytes"] > 0 for r in sem_a_foto), sem_a_foto
    assert sum(r["bytes"] for r in sem_a_foto) <= LIMITE_DA_INICIAL, sorted(sem_a_foto, key=lambda r: -r["bytes"])[:3]


@pytest.mark.parametrize("rota, par", [("/", "/en/"), ("/inovacao/", "/en/innovation/"), ("/cards/pobreza/", "/en/cards/pobreza/"),
                                       ("/en/states/", "/estados/"), ("/en/how-we-got-here/", "/como-chegamos/")])
def test_seletor_de_idioma_leva_a_mesma_pagina_no_outro_idioma(abrir, rota, par):
    with abrir(rota, largura=1280, reduced_motion="reduce") as pagina:
        atual = pagina.locator(".nn-menu .nn-idioma[aria-current='true']")
        assert atual.count() == 1
        lang = pagina.evaluate("document.documentElement.lang")
        assert atual.get_attribute("lang") == lang
        outro = pagina.locator(".nn-menu .nn-idioma:not([aria-current])")
        assert outro.is_visible()
        bandeira = outro.locator("img.nn-bandeira").bounding_box()
        assert 16 <= bandeira["width"] == bandeira["height"] <= 24  # bandeira redonda pequena, com a sigla ao lado
        assert outro.evaluate("a => getComputedStyle(a.querySelector('img')).borderRadius") == "50%"
        outro.click()
        pagina.wait_for_load_state("networkidle")
        assert pagina.evaluate("location.pathname") == par
        assert pagina.evaluate("document.documentElement.lang") == ("en" if par.startswith("/en/") else "pt-BR")


@pytest.mark.parametrize("largura", [1100, 1150, 1280, 1440])
@pytest.mark.parametrize("rota", ["/", "/en/", "/sobre/", "/en/about/"])
def test_seletor_cabe_na_barra_do_computador_numa_linha_so(abrir, rota, largura):
    with abrir(rota, largura=largura, reduced_motion="reduce") as pagina:
        menu = pagina.locator(".nn-menu").bounding_box()
        assert menu["height"] <= 52, menu  # sem quebrar em duas linhas
        caixas = [pagina.locator(s).bounding_box() for s in (".nn-marca", ".nn-topo-alca", ".nn-topo-botao")]
        assert caixas[0]["x"] + caixas[0]["width"] <= caixas[1]["x"] and caixas[1]["x"] + caixas[1]["width"] <= caixas[2]["x"]
        for idioma in pagina.locator(".nn-menu .nn-idioma").all():
            caixa = idioma.bounding_box()
            assert caixa["y"] + caixa["height"] <= menu["y"] + menu["height"]
        assert _estouro(pagina) == {}


@pytest.mark.parametrize("largura", [320, 360, 390])
@pytest.mark.parametrize("rota", ["/", "/en/", "/en/how-we-got-here/", "/en/cards/renda_rs/"])
def test_seletor_na_gaveta_do_celular_sem_estourar(abrir, rota, largura):
    with abrir(rota, largura=largura, reduced_motion="reduce") as pagina:
        assert not pagina.locator(".nn-menu .nn-idioma").first.is_visible()  # a barra preta nao existe no celular
        assert _estouro(pagina) == {}
        pagina.locator(".nn-menu-movel > summary").click()
        idiomas = pagina.locator(".nn-gaveta .nn-idioma")
        assert idiomas.count() == 2
        for i in range(2):
            caixa = idiomas.nth(i).bounding_box()
            assert caixa["height"] >= 44 and caixa["x"] >= 0 and caixa["x"] + caixa["width"] <= largura  # alvo de toque
        assert _estouro(pagina) == {}


def test_contagem_da_abertura_termina_no_numero_em_ingles(abrir):
    with abrir("/en/", reduced_motion="no-preference") as pagina:
        finais = pagina.evaluate(  # os numeros como vem no HTML (a contagem ja comecou na tela)
            """() => fetch(location.href).then((r) => r.text()).then((t) => [...new DOMParser().parseFromString(t, 'text/html')
                 .querySelectorAll('.nn-numero-valor')].map((e) => e.textContent))"""
        )
        pagina.wait_for_timeout(1800)  # a contagem dura 1,2 s
        assert pagina.locator(".nn-numero-valor").all_text_contents() == finais
        assert pagina.locator(".nn-conta").count() >= 2  # os numeros com ponto decimal foram reconhecidos e contados
        assert all(NUMERO_EN.fullmatch(t.strip()) for t in pagina.locator(".nn-conta").all_text_contents())


def test_dica_de_valor_no_formato_americano(abrir):
    with abrir("/en/", largura=1280, reduced_motion="reduce") as pagina:
        svg = pagina.locator("#resumo .nn-graf-largo svg").first
        svg.scroll_into_view_if_needed()
        caixa = svg.bounding_box()
        svg.hover(position={"x": caixa["width"] * 0.6, "y": caixa["height"] / 2})
        textos = svg.locator(".nn-dica-valor").all_text_contents()
        assert textos and all(re.search(r"\d\.\d", t) for t in textos), textos
        assert not any(re.search(r"\d,\d(?!\d\d)", t) for t in textos), textos


def test_explorar_em_ingles_redesenha_com_os_rotulos_e_numeros_em_ingles(abrir):
    with abrir("/en/explore/", largura=1280, reduced_motion="reduce") as pagina:
        pagina.select_option("#sel-expl-ind", "renda")
        pagina.select_option("#sel-expl-terr", "BR_FORA_NE")
        pagina.select_option("#sel-expl-terr2", "CO")
        pagina.wait_for_function("() => document.getElementById('explorar-titulo').textContent.includes('Brazil outside the Northeast')")
        assert "Center-West region" in pagina.locator("#explorar-titulo").text_content()
        desc = pagina.locator("#explorar-vista .nn-graf-largo svg desc").text_content()
        assert desc.startswith("Line chart, Household income per capita, Brazil outside the Northeast and Center-West region.")
        assert " in 20" in desc and "The table with all values is right below." in desc
        cabecalho = pagina.locator("#explorar-vista thead th").all_text_contents()
        assert cabecalho == ["Year", "Area", "Value", "Source series"]
        valores = pagina.locator("#explorar-vista tbody td.nn-num").all_text_contents()
        assert valores and all(NUMERO_EN.fullmatch(v) for v in valores), valores[:5]
        assert _estouro(pagina) == {}
