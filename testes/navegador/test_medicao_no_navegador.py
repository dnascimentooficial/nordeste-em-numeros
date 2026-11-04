"""A medicao de audiencia no Chromium: os eventos que o site.js manda ao Umami (explore-select, states-select, era-open,
scroll-depth e chart-enlarge), com um `window.umami` de mentira posto antes dos scripts da pagina, e o site inteiro
funcionando com o script do Umami barrado (o conftest o barra em todo contexto: os testes rodam sem rede).

Marcador `navegador`: `python -m pytest -m navegador testes/navegador -k medicao`.
"""

from contextlib import contextmanager

import pytest

from test_site_no_navegador import CELULAR, DESKTOP, UMAMI

pytestmark = pytest.mark.navegador
# o Umami de mentira: guarda cada chamada de track(nome, dados) em window.__medidas
UMAMI_DE_MENTIRA = "window.__medidas = []; window.umami = { track: (...a) => { window.__medidas.push(a); } };"
MEDIDAS = "() => window.__medidas"


@contextmanager
def _com_umami(navegador, endereco, rota, largura=DESKTOP, altura=800):
    """A pagina com o Umami de mentira; afirma ao sair que nao houve erro de pagina nem de console (o pedido barrado do
    script de verdade e o unico tolerado)."""
    contexto = navegador.new_context(viewport={"width": largura, "height": altura}, reduced_motion="reduce")
    try:
        pagina = contexto.new_page()
        erros: list[str] = []
        pagina.on("pageerror", lambda e: erros.append(f"pageerror: {e}"))
        pagina.on("console", lambda m: erros.append(m.text) if m.type == "error" and "favicon" not in m.location.get("url", "") and not m.location.get("url", "").startswith(UMAMI) else None)
        pagina.add_init_script(UMAMI_DE_MENTIRA)
        pagina.goto(endereco + rota, wait_until="networkidle")
        pagina.wait_for_function("() => document.readyState === 'complete'")
        yield pagina
        assert erros == [], erros
    finally:
        contexto.close()


def _de(pagina, nome: str) -> list[dict]:
    return [dados for evento, dados in pagina.evaluate(MEDIDAS) if evento == nome]


# --- sem o Umami ---


@pytest.mark.parametrize("rota", ["/", "/en/", "/explorar/", "/estados/", "/como-chegamos/", "/en/how-we-got-here/", "/inovacao/", "/sobre/"])
def test_sem_o_umami_nada_quebra(abrir, endereco, rota):
    """O script do Umami barrado (como num bloqueador): a pagina abre sem erro (a `abrir` afirma), nao ha window.umami,
    e o que mede (rolar ate o fim, ampliar, escolher, abrir uma epoca) segue sem erro."""
    with abrir(rota, reduced_motion="reduce") as pagina:
        pedidos = pagina.evaluate("() => performance.getEntriesByType('resource').map((r) => r.name)")
        assert [p for p in pedidos if not p.startswith(endereco)] in ([], [UMAMI + "script.js"])  # o unico de fora
        assert pagina.evaluate("() => typeof window.umami") == "undefined"
        pagina.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        pagina.wait_for_timeout(200)
        botao = pagina.locator("button.nn-ampliar:visible").first
        if botao.count():
            botao.click()
            pagina.keyboard.press("Escape")
        if pagina.locator("#sel-expl-ind").count():
            pagina.select_option("#sel-expl-ind", index=1)
            pagina.wait_for_timeout(1000)
        if pagina.locator("#sel-estado-ind").count():
            pagina.select_option("#sel-estado-ind", index=1)
        cartao = pagina.locator("button.nn-epoca-abrir").first
        if cartao.count():
            cartao.click()
            assert pagina.evaluate("() => document.querySelector('dialog.nn-modal-historia').open")
            pagina.keyboard.press("Escape")


# --- com o Umami ---


def test_scroll_depth_uma_vez_por_secao_ao_ficar_meio_a_vista(navegador, endereco):
    with _com_umami(navegador, endereco, "/") as pagina:
        ids = pagina.evaluate("() => [...document.querySelectorAll('main .nn-capitulo[id]')].map((a) => a.id)")
        assert len(ids) >= 5
        assert not [d for d in _de(pagina, "scroll-depth") if d["section"] in ids]  # a primeira tela e a abertura
        pagina.evaluate("() => document.querySelector('.nn-placar').scrollIntoView({ block: 'start' })")
        pagina.wait_for_function("() => window.__medidas.some(([n, d]) => n === 'scroll-depth' && d.section === 'placar')")
        for id_ in ids:
            pagina.evaluate("(id) => document.getElementById(id).scrollIntoView({ block: 'start' })", id_)
            pagina.wait_for_function("(id) => window.__medidas.some(([n, d]) => n === 'scroll-depth' && d.section === id)", arg=id_)
        pagina.evaluate("() => window.scrollTo(0, 0)")  # e voltar nao conta de novo
        pagina.evaluate("(id) => document.getElementById(id).scrollIntoView()", ids[0])
        pagina.wait_for_timeout(300)
        lidas = _de(pagina, "scroll-depth")
        secoes = [d["section"] for d in lidas]
        assert len(secoes) == len(set(secoes)), secoes
        assert set(ids) <= set(secoes) and "placar" in secoes
        assert all(d == {"page": "index", "section": d["section"], "lang": "pt"} for d in lidas), lidas


@pytest.mark.parametrize("rota, secoes, pagina_", [
    ("/como-chegamos/", {"abertura", "linha", "fecho"}, "como-chegamos"),
    ("/en/how-we-got-here/", {"abertura", "linha", "fecho"}, "como-chegamos"),
    ("/en/innovation/", None, "inovacao"),
    ("/sobre/", {"sobre-o-que", "sobre-medicao", "autor"}, "sobre"),
])
def test_scroll_depth_nas_outras_paginas(navegador, endereco, rota, secoes, pagina_):
    with _com_umami(navegador, endereco, rota, largura=CELULAR) as pagina:
        alvos = pagina.evaluate("""() => [...document.querySelectorAll('main .nn-capitulo[id], main .nn-hist-bloco, main .nn-hist-linha, main #sobre > article[id]')]
            .map((s) => s.id || s.getAttribute('aria-labelledby').replace(/^titulo-/, ''))""")
        if secoes:
            assert secoes <= set(alvos)
        for i in range(len(alvos)):
            pagina.evaluate("(i) => document.querySelectorAll('main .nn-capitulo[id], main .nn-hist-bloco, main .nn-hist-linha, main #sobre > article[id]')[i].scrollIntoView({ block: 'start' })", i)
            pagina.wait_for_function("(id) => window.__medidas.some(([n, d]) => n === 'scroll-depth' && d.section === id)", arg=alvos[i])
        lidas = _de(pagina, "scroll-depth")
        lang = "en" if rota.startswith("/en/") else "pt"
        assert {d["section"] for d in lidas} >= set(alvos)
        assert all(d["page"] == pagina_ and d["lang"] == lang for d in lidas), lidas


def test_chart_enlarge_pelo_grafico_e_nao_em_dobro_pelo_botao(navegador, endereco):
    """O botao Ampliar conta pelo data-umami-event dele (o script do Umami ve o clique); o clique no proprio grafico,
    que tambem abre o modal, conta pelo site.js. O botao nao manda nada pelo site.js: o evento nao sai em dobro."""
    with _com_umami(navegador, endereco, "/") as pagina:
        caixa = pagina.locator("#resumo .nn-grafico .nn-graf").first
        grafico = caixa.get_attribute("id")
        caixa.scroll_into_view_if_needed()
        caixa.click()
        pagina.wait_for_function("() => document.querySelector('dialog.nn-modal:not(.nn-modal-historia):not(.nn-modal-autor)').open")
        assert _de(pagina, "chart-enlarge") == [{"chart": grafico, "page": "index", "lang": "pt"}]
        pagina.keyboard.press("Escape")
        pagina.locator("#resumo button.nn-ampliar").first.click()
        pagina.wait_for_function("() => document.querySelector('dialog.nn-modal:not(.nn-modal-historia):not(.nn-modal-autor)').open")
        assert len(_de(pagina, "chart-enlarge")) == 1
    with _com_umami(navegador, endereco, "/en/innovation/") as pagina:
        caixa = pagina.locator("#resumo .nn-grafico .nn-graf").first
        caixa.scroll_into_view_if_needed()
        caixa.click()
        pagina.wait_for_function("() => window.__medidas.some(([n]) => n === 'chart-enlarge')")
        assert _de(pagina, "chart-enlarge") == [{"chart": caixa.get_attribute("id"), "page": "inovacao", "lang": "en"}]


def test_explore_select_uma_vez_por_escolha_depois_de_desenhar(navegador, endereco):
    with _com_umami(navegador, endereco, "/explorar/") as pagina:
        assert _de(pagina, "explore-select") == []  # abrir a pagina nao e escolher
        pagina.select_option("#sel-expl-ind", "renda")
        pagina.select_option("#sel-expl-terr", "CE")  # duas trocas seguidas: uma escolha so
        pagina.wait_for_function("() => window.__medidas.some(([n]) => n === 'explore-select')")
        assert "Ceará" in pagina.locator("#explorar-titulo").inner_text()  # a vista ja estava desenhada
        pagina.wait_for_timeout(1200)
        assert _de(pagina, "explore-select") == [{"indicator": "renda", "territory": "CE", "lang": "pt"}]
        pagina.select_option("#sel-expl-terr2", "PE")
        pagina.wait_for_function("() => window.__medidas.filter(([n]) => n === 'explore-select').length === 2")
        assert _de(pagina, "explore-select")[1] == {"indicator": "renda", "territory": "CE", "compare": "PE", "lang": "pt"}
        # o zoom de periodo redesenha, mas nao e uma escolha de indicador ou territorio
        pagina.locator("#explorar-zoom select").first.select_option(index=3)
        pagina.wait_for_timeout(1200)
        assert len(_de(pagina, "explore-select")) == 2


def test_states_select(navegador, endereco):
    with _com_umami(navegador, endereco, "/en/states/") as pagina:
        pagina.select_option("#sel-estado-ind", "renda")
        assert _de(pagina, "states-select") == [{"indicator": "renda", "lang": "en"}]


@pytest.mark.parametrize("rota, lang", [("/como-chegamos/", "pt"), ("/en/how-we-got-here/", "en")])
def test_era_open_ao_abrir_cada_epoca(navegador, endereco, rota, lang):
    with _com_umami(navegador, endereco, rota) as pagina:
        assert _de(pagina, "era-open") == []
        ids = pagina.evaluate("() => [...document.querySelectorAll('li.nn-epoca')].map((li) => li.id)")
        pagina.locator(f"button.nn-epoca-abrir[data-epoca='{ids[1]}']").click()
        pagina.wait_for_function("() => document.querySelector('dialog.nn-modal-historia').open")
        assert _de(pagina, "era-open") == [{"era": ids[1], "lang": lang}]
        pagina.locator("dialog.nn-modal-historia .nn-epoca-proxima").click()  # a proxima, no mesmo modal, tambem
        pagina.wait_for_function("(n) => window.__medidas.filter(([e]) => e === 'era-open').length === n", arg=2)
        assert _de(pagina, "era-open")[1] == {"era": ids[2], "lang": lang}
    with _com_umami(navegador, endereco, f"{rota}#{ids[0]}") as pagina:  # quem chega pelo endereco da epoca
        assert _de(pagina, "era-open") == [{"era": ids[0], "lang": lang}]


def test_um_umami_que_falha_nao_derruba_a_pagina(navegador, endereco):
    """track() que lanca erro (Umami quebrado ou mudado): a medicao engole o erro e o resto funciona."""
    contexto = navegador.new_context(viewport={"width": DESKTOP, "height": 800}, reduced_motion="reduce")
    try:
        pagina = contexto.new_page()
        erros: list[str] = []
        pagina.on("pageerror", lambda e: erros.append(str(e)))
        pagina.add_init_script("window.umami = { track: () => { throw new Error('umami quebrado'); } };")
        pagina.goto(endereco + "/como-chegamos/", wait_until="networkidle")
        pagina.locator("button.nn-epoca-abrir").first.click()
        assert pagina.evaluate("() => document.querySelector('dialog.nn-modal-historia').open")
        pagina.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")
        pagina.wait_for_timeout(300)
        assert erros == []
    finally:
        contexto.close()
