"""A página Inovação no Chromium: peso da primeira carga com teto próprio, axe e contraste nos dois temas (com os
gráficos recolhidos abertos), 390 px sem estouro, sem JavaScript e o menu lateral.

Marcador `navegador`: `python -m pytest -m navegador testes/navegador -k inovacao`. O teto do Início não muda.
"""

import re

import pytest

from test_site_no_navegador import CELULAR, DESKTOP, _estouro, _violacoes_do_axe

pytestmark = pytest.mark.navegador
ROTA = "/inovacao/"
LIMITE_DA_INOVACAO = 600_000  # bytes na primeira carga, com a imagem da capa e as fontes

_ABRIR_TUDO = "() => document.querySelectorAll('main details').forEach((d) => { d.open = true; })"


def test_inovacao_peso_da_primeira_carga(abrir):
    with abrir(ROTA) as pagina:
        pagina.evaluate("() => document.fonts.ready.then(() => true)")
        recursos = pagina.evaluate(
            """() => [performance.getEntriesByType('navigation')[0], ...performance.getEntriesByType('resource')]
                 .map((r) => ({ nome: r.name, bytes: r.transferSize }))""")
    assert len(recursos) >= 5 and all(r["bytes"] > 0 for r in recursos), recursos
    assert any("marco-1959" in r["nome"] for r in recursos)  # a imagem da capa conta no teto
    assert sum(r["bytes"] for r in recursos) <= LIMITE_DA_INOVACAO, sorted(recursos, key=lambda r: -r["bytes"])[:3]


@pytest.mark.parametrize("esquema", ["light", "dark"])
@pytest.mark.parametrize("largura", [CELULAR, DESKTOP])
def test_inovacao_axe_e_contraste_com_tudo_aberto(abrir, esquema, largura):
    with abrir(ROTA, largura=largura, color_scheme=esquema, reduced_motion="reduce") as pagina:
        assert _violacoes_do_axe(pagina) == []
        pagina.evaluate(_ABRIR_TUDO)
        assert _violacoes_do_axe(pagina) == []


@pytest.mark.parametrize("largura", [360, CELULAR, 1100, 1440])
def test_inovacao_sem_estouro_com_os_graficos_recolhidos_abertos(abrir, largura):
    with abrir(ROTA, largura=largura) as pagina:
        assert _estouro(pagina) == {}
        pagina.evaluate(_ABRIR_TUDO)
        assert _estouro(pagina) == {}


def test_inovacao_sem_javascript_mostra_numeros_graficos_e_regua(abrir):
    with abrir(ROTA, java_script_enabled=False) as pagina:
        assert pagina.locator(".nn-placar-lista li").count() == 4
        assert pagina.locator("article.nn-capitulo").count() == 5
        lide = pagina.locator("#resumo .nn-frase").first.inner_text()
        assert re.search(r"\d", lide) and "{" not in lide and "}" not in lide
        assert pagina.locator("#resumo .nn-graf-largo svg").first.is_visible()
        assert pagina.locator(".nn-leitura").first.is_visible()
        assert pagina.locator(".nn-leitura .nn-rk").count() == 2 * pagina.locator(".nn-leitura-pop").count() >= 10
        assert pagina.locator(".nn-indice").is_visible()  # sem JavaScript o menu lateral fica a vista
        pagina.locator(".nn-placar-lista a").nth(2).click()
        assert pagina.url.endswith("#q-inovacao")


def test_inovacao_menu_lateral_aparece_depois_do_placar(abrir):
    with abrir(ROTA, largura=1440, reduced_motion="reduce") as pagina:
        assert "nn-indice-ligado" in pagina.locator(".nn-indice").get_attribute("class")
        pagina.locator("#q-trabalho").scroll_into_view_if_needed()
        pagina.wait_for_function("() => document.querySelector('.nn-indice').classList.contains('nn-indice-visivel')")
        pagina.wait_for_function("() => document.querySelector('.nn-indice a[aria-current=\"true\"]') !== null")


def test_inovacao_ampliar_abre_o_grafico_do_capitulo(abrir):
    with abrir(ROTA, largura=DESKTOP, reduced_motion="reduce") as pagina:
        pagina.locator("#q-conhecimento button.nn-ampliar").first.click()
        pagina.wait_for_selector("dialog.nn-modal[open]")
        titulo = pagina.locator("dialog.nn-modal .nn-modal-titulo").inner_text()
        assert titulo == pagina.locator("#q-conhecimento h2").first.inner_text()
        pagina.keyboard.press("Escape")
