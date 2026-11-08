"""O mapa do Inicio "Onde a renda mais cresceu desde 2012?" no Chromium: as abas (botoes com aria-pressed), o estado
apontado na linha de leitura, o teclado, sem JavaScript, as larguras do celular ao computador, o axe nas duas vistas e
nos dois temas e os eventos da medicao com um Umami de mentira.

Marcador `navegador`: `python -m pytest -m navegador testes/navegador -k mapa`.
"""

import pytest

from test_medicao_no_navegador import _com_umami, _de
from test_site_no_navegador import _estouro, _violacoes_do_axe

pytestmark = pytest.mark.navegador
BLOCO = "section.nn-mosaico"
ABAS = f"{BLOCO} .nn-mosaico-aba"


def _visiveis(pagina, seletor: str) -> list[str]:
    return pagina.evaluate(
        "(s) => [...document.querySelectorAll(s)].filter((e) => e.offsetParent !== null).map((e) => e.textContent.trim())",
        seletor)


@pytest.mark.parametrize("rota, abas", [
    ("/", ["Quanto cresceu", "Quanto é hoje"]), ("/en/", ["How much it grew", "How much it is today"]),
])
def test_abas_trocam_a_vista_com_aria_pressed(abrir, rota, abas):
    with abrir(rota, largura=1440, reduced_motion="reduce") as pagina:
        assert pagina.locator(ABAS).all_inner_texts() == abas
        assert pagina.locator(f"{BLOCO} .nn-mosaico-abas").is_visible()  # o JS tirou o hidden
        assert pagina.locator(ABAS).evaluate_all("(b) => b.map((x) => x.getAttribute('aria-pressed'))") == ["true", "false"]
        cresceu = _visiveis(pagina, f"{BLOCO} .nn-mosaico-uf .nn-mosaico-v")
        assert len(cresceu) == 27 and all(v.endswith("%") for v in cresceu)
        pagina.locator(ABAS).nth(1).click()
        assert pagina.locator(ABAS).evaluate_all("(b) => b.map((x) => x.getAttribute('aria-pressed'))") == ["false", "true"]
        assert "nn-mosaico-vista-hoje" in pagina.locator(BLOCO).get_attribute("class")
        hoje = _visiveis(pagina, f"{BLOCO} .nn-mosaico-uf .nn-mosaico-v")
        assert len(hoje) == 27 and not any(v.endswith("%") for v in hoje)
        assert len(_visiveis(pagina, f"{BLOCO} .nn-mosaico-ranking h3")) == 2  # so o ranking da vista
        fundo = "(e) => getComputedStyle(e).backgroundColor"
        df_hoje = pagina.locator(f"{BLOCO} .nn-mosaico-uf[data-uf='DF']").evaluate(fundo)
        pagina.locator(ABAS).nth(0).click()
        assert pagina.locator(f"{BLOCO} .nn-mosaico-uf[data-uf='DF']").evaluate(fundo) != df_hoje  # o tom troca
        assert _visiveis(pagina, f"{BLOCO} .nn-mosaico-uf .nn-mosaico-v") == cresceu


def test_teclado_nas_abas_e_nos_estados(abrir):
    with abrir("/", largura=1440, reduced_motion="reduce") as pagina:
        pagina.locator(ABAS).nth(1).focus()
        pagina.keyboard.press("Enter")
        assert pagina.locator(ABAS).nth(1).get_attribute("aria-pressed") == "true"
        pagina.keyboard.press("Tab")  # da ultima aba, o foco chega ao primeiro estado da grade
        focado = pagina.evaluate("() => document.activeElement.getAttribute('data-uf')")
        assert focado == "RR"
        rotulo = pagina.evaluate("() => document.activeElement.getAttribute('aria-label')")
        assert rotulo.startswith("Roraima: ") and "R$" in rotulo
        assert pagina.locator(f"{BLOCO} .nn-mosaico-leitura").inner_text() == rotulo  # a leitura segue o foco
        pagina.keyboard.press(" ")
        assert pagina.evaluate("() => document.activeElement.getAttribute('data-uf')") == "RR"


def test_passar_o_mouse_mostra_o_nome_e_o_valor(abrir):
    with abrir("/", largura=1440, reduced_motion="reduce") as pagina:
        leitura = pagina.locator(f"{BLOCO} .nn-mosaico-leitura")
        assert leitura.is_visible() and leitura.inner_text().startswith("Passe o mouse")
        pagina.locator(f"{BLOCO} .nn-mosaico-uf[data-uf='RN']").hover()
        assert leitura.inner_text().startswith("Rio Grande do Norte: +58,6% de 2012 a 2025")


def test_sem_javascript_a_vista_do_crescimento_e_a_tabela(abrir):
    with abrir("/", largura=390, java_script_enabled=False) as pagina:
        assert not pagina.locator(f"{BLOCO} .nn-mosaico-abas").is_visible()
        assert not pagina.locator(f"{BLOCO} .nn-mosaico-leitura").is_visible()
        valores = _visiveis(pagina, f"{BLOCO} .nn-mosaico-uf .nn-mosaico-v")
        assert len(valores) == 27 and all(v.endswith("%") for v in valores)
        pagina.locator(f"{BLOCO} details summary").click()
        assert pagina.locator(f"{BLOCO} table tbody tr").count() == 27
        assert pagina.locator(f"{BLOCO} table").is_visible()
        assert pagina.locator(f"{BLOCO} .nn-mosaico-veredito").is_visible()


@pytest.mark.parametrize("largura", [320, 360, 390, 1440])
def test_larguras_sem_estouro_e_quadrados_legiveis(abrir, largura):
    for rota in ("/", "/en/"):
        with abrir(rota, largura=largura, reduced_motion="reduce") as pagina:
            assert _estouro(pagina) == {}
            medidas = pagina.evaluate("""() => [...document.querySelectorAll('section.nn-mosaico .nn-mosaico-uf')].map((q) => {
                const c = q.getBoundingClientRect();
                const textos = [...q.querySelectorAll('span')].filter((s) => s.offsetParent !== null);
                return { lado: Math.min(c.width, c.height),
                         cabe: textos.every((s) => { const r = s.getBoundingClientRect(); return r.left >= c.left - 0.5 && r.right <= c.right + 0.5; }),
                         fonte: Math.min(...textos.map((s) => parseFloat(getComputedStyle(s).fontSize))) };
            })""")
            assert len(medidas) == 27
            assert min(m["lado"] for m in medidas) >= 34, (rota, largura)
            assert all(m["cabe"] for m in medidas), (rota, largura)
            assert min(m["fonte"] for m in medidas) >= 10, (rota, largura)
            pagina.locator(ABAS).nth(1).click()
            assert _estouro(pagina) == {}


@pytest.mark.parametrize("esquema", ["light", "dark"])
def test_axe_nas_duas_vistas(abrir, esquema):
    with abrir("/", largura=390, color_scheme=esquema, reduced_motion="reduce") as pagina:
        pagina.locator(f"{BLOCO} details summary").click()
        assert _violacoes_do_axe(pagina) == []
        pagina.locator(ABAS).nth(1).click()
        assert _violacoes_do_axe(pagina) == []


def test_axe_no_card_do_mapa(abrir):
    with abrir("/cards/mapa_renda/", reduced_motion="reduce") as pagina:
        assert pagina.locator("svg.nn-mosaico-svg rect").count() == 27
        assert _violacoes_do_axe(pagina) == []


def test_medicao_das_abas_e_dos_estados(navegador, endereco):
    with _com_umami(navegador, endereco, "/") as pagina:
        pagina.locator(ABAS).nth(1).click()
        pagina.locator(ABAS).nth(1).click()  # a aba ja escolhida nao conta de novo
        pagina.locator(ABAS).nth(0).click()
        assert _de(pagina, "map-tab") == [{"tab": "hoje", "lang": "pt"}, {"tab": "cresceu", "lang": "pt"}]
        pagina.locator(f"{BLOCO} .nn-mosaico-uf[data-uf='PI']").click()
        pagina.locator(f"{BLOCO} .nn-mosaico-uf[data-uf='SE']").focus()
        pagina.keyboard.press("Enter")
        assert _de(pagina, "map-tile") == [{"uf": "PI", "lang": "pt"}, {"uf": "SE", "lang": "pt"}]
        pagina.locator(f"{BLOCO} .nn-mosaico-uf[data-uf='BA']").hover()  # passar o mouse nao conta
        assert len(_de(pagina, "map-tile")) == 2
        assert pagina.locator(f"{BLOCO} a[data-umami-event='cta-click']").get_attribute("data-umami-event-target") == "estados"
    with _com_umami(navegador, endereco, "/en/") as pagina:
        pagina.locator(ABAS).nth(1).click()
        pagina.locator(f"{BLOCO} .nn-mosaico-uf[data-uf='DF']").click()
        assert _de(pagina, "map-tab") == [{"tab": "hoje", "lang": "en"}]
        assert _de(pagina, "map-tile") == [{"uf": "DF", "lang": "en"}]


def test_sem_o_umami_o_mapa_funciona(abrir):
    with abrir("/", reduced_motion="reduce") as pagina:  # o conftest barra o script do Umami
        assert pagina.evaluate("() => typeof window.umami") == "undefined"
        pagina.locator(ABAS).nth(1).click()
        pagina.locator(f"{BLOCO} .nn-mosaico-uf[data-uf='MA']").click()
        assert pagina.locator(f"{BLOCO} .nn-mosaico-leitura").inner_text().startswith("Maranhão: ")


def test_o_modal_ampliar_pede_os_templates_so_quando_precisa(abrir):
    with abrir("/", largura=1440, reduced_motion="reduce") as pagina:
        pedidos = lambda: [n for n in pagina.evaluate("() => performance.getEntriesByType('resource').map((r) => r.name)")  # noqa: E731
                           if "/ampliados/" in n]
        assert pedidos() == []  # a pagina abre sem os graficos ampliados
        pagina.locator("button.nn-ampliar").first.click()
        pagina.wait_for_function("() => document.querySelector('dialog.nn-modal:not(.nn-modal-autor)').open")
        assert len(pedidos()) == 1 and pedidos()[0].split("?")[0].endswith("/ampliados/pt-index.json")
        pagina.keyboard.press("Escape")
        pagina.locator("button.nn-ampliar").nth(1).click()
        pagina.wait_for_function("() => document.querySelector('dialog.nn-modal:not(.nn-modal-autor)').open")
        assert len(pedidos()) == 1  # pedido uma vez so
