"""Autoria no Chromium: o cabecalho de duas linhas (titulo e "por", linha fina, menu), o bloco "Desenvolvido por" do
rodape e o modal "Sobre o autor" (clique, Enter, Esc, X, clique fora, foco preso e devolvido, axe nos dois temas), a
largura a 390 px, o contraste nos pixels reais e o que vale sem JavaScript.

Marcador `navegador`: `python -m pytest -m navegador testes/navegador`.
"""

import io
import re

import numpy as np
import pytest
from PIL import Image

from test_site_no_navegador import CELULAR, DESKTOP, _contrastes, _cor_computada, _estouro, _violacoes_do_axe

pytestmark = pytest.mark.navegador
MODAL = "dialog.nn-modal-autor"
GATILHO = "a.nn-autor-abrir"
LIMITE_DO_CONTRASTE = 4.5
PAGINAS_COM_CABECALHO = ["/", "/como-chegamos/", "/estados/", "/sobre/"]  # a abertura com foto, o papel antigo e duas comuns

_ESTADO = """() => {
  const d = document.querySelector('dialog.nn-modal-autor');
  const a = document.activeElement;
  return {
    aberto: d.open, hash: location.hash, caminho: location.pathname,
    foco: a === document.body ? 'body' : (d.contains(a) ? 'modal' : (a.className || a.tagName.toLowerCase())),
    focoTag: a.tagName.toLowerCase(),
    rolagemTrava: getComputedStyle(document.documentElement).overflow,
  };
}"""


def _esperar_a_entrada(pagina) -> None:
    """A entrada do modal acabou: o contraste e a posicao valem os do estado final, nao os de um quadro da animacao."""
    pagina.wait_for_function(
        "() => document.querySelector('dialog.nn-modal-autor').getAnimations({ subtree: true })"
        ".every((a) => a.playState === 'finished')"
    )


# --- modal: abrir, fechar, foco ---


def test_modal_abre_pelo_clique_e_pelo_enter_fecha_com_esc_e_o_foco_volta(abrir):
    with abrir("/", reduced_motion="reduce") as pagina:
        assert not pagina.locator(MODAL).evaluate("d => d.open")
        gatilho = pagina.locator(GATILHO)
        assert gatilho.get_attribute("href") == "/sobre/#autor"
        # clique: o modal abre e a pagina nao navega
        gatilho.click()
        estado = pagina.evaluate(_ESTADO)
        assert estado["aberto"] and estado["foco"] == "modal" and estado["caminho"] == "/" and estado["hash"] == "", estado
        assert pagina.locator(f"{MODAL} h2").inner_text() == "Sobre o autor"
        assert pagina.locator(f"{MODAL} h3").all_inner_texts() == ["Quem sou", "Por que fiz este estudo", "Formação"]
        pagina.keyboard.press("Escape")
        assert not pagina.evaluate(_ESTADO)["aberto"]
        assert pagina.evaluate("() => document.activeElement.classList.contains('nn-autor-abrir')")  # o foco voltou
        # Enter no gatilho focado: abre do mesmo jeito
        pagina.keyboard.press("Enter")
        estado = pagina.evaluate(_ESTADO)
        assert estado["aberto"] and estado["foco"] == "modal" and estado["caminho"] == "/", estado
        pagina.keyboard.press("Escape")
        assert not pagina.evaluate(_ESTADO)["aberto"]
        assert pagina.evaluate("() => document.activeElement.classList.contains('nn-autor-abrir')")


def test_modal_fecha_no_x_e_clicando_fora_e_devolve_o_foco(abrir):
    with abrir("/estados/", reduced_motion="reduce") as pagina:
        for como in ("x", "fora"):
            pagina.locator(GATILHO).click()
            assert pagina.evaluate(_ESTADO)["aberto"]
            if como == "x":
                pagina.locator(f"{MODAL} .nn-modal-fechar").click()
            else:
                caixa = pagina.locator(MODAL).bounding_box()
                assert caixa["x"] > 20 and caixa["width"] <= 681  # no desktop o modal e estreito: ha o que clicar fora
                pagina.mouse.click(caixa["x"] / 2, 400)
            estado = pagina.evaluate(_ESTADO)
            assert not estado["aberto"] and estado["caminho"] == "/estados/", estado
            assert pagina.evaluate("() => document.activeElement.classList.contains('nn-autor-abrir')"), como


def test_modal_prende_o_foco_e_nao_deixa_a_pagina_rolar(abrir):
    """showModal() deixa o resto da pagina inerte: o Tab nunca cai num link de tras do modal (ao fim dele o foco sai para o
    navegador, `body`, e volta ao primeiro controle do modal)."""
    with abrir("/", reduced_motion="reduce") as pagina:
        pagina.locator(GATILHO).click()
        assert pagina.evaluate(_ESTADO)["rolagemTrava"] == "hidden"
        focos = []
        for tecla in ("Tab",) * 12 + ("Shift+Tab",) * 12:  # mais voltas do que ha controles (o X e o link) no modal
            pagina.keyboard.press(tecla)
            focos.append(pagina.evaluate(_ESTADO)["foco"])
        assert set(focos) <= {"modal", "body"}, focos  # nunca um controle da pagina por tras
        assert "modal" in focos
        pagina.keyboard.press("Escape")
        assert pagina.evaluate(_ESTADO)["rolagemTrava"] != "hidden"


def test_modal_do_autor_nao_atrapalha_o_ampliar_nem_as_epocas(abrir):
    with abrir("/", reduced_motion="reduce") as pagina:  # o Ampliar do Inicio continua sendo o dele
        pagina.locator("button.nn-ampliar").first.click()
        assert pagina.locator("dialog.nn-modal:not(.nn-modal-autor)").evaluate("d => d.open")
        assert not pagina.locator(MODAL).evaluate("d => d.open")
        pagina.keyboard.press("Escape")
        assert pagina.evaluate("() => document.activeElement.classList.contains('nn-ampliar')")
    with abrir("/como-chegamos/", reduced_motion="reduce") as pagina:  # e a pagina sem Ampliar nao o pega para o dela
        pagina.locator(GATILHO).click()
        estado = pagina.evaluate(_ESTADO)
        assert estado["aberto"] and estado["hash"] == "", estado
        pagina.keyboard.press("Escape")
        assert not pagina.evaluate(_ESTADO)["aberto"]
        pagina.locator("button.nn-epoca-abrir").first.click()  # a linha do tempo segue abrindo as epocas
        assert pagina.locator("dialog.nn-modal-historia").evaluate("d => d.open")
        pagina.keyboard.press("Escape")


@pytest.mark.parametrize("esquema", ["light", "dark"])
@pytest.mark.parametrize("largura", [DESKTOP, CELULAR])
def test_axe_com_o_modal_do_autor_aberto(abrir, esquema, largura):
    for rota in ("/", "/sobre/"):
        with abrir(rota, largura=largura, color_scheme=esquema, reduced_motion="reduce") as pagina:
            pagina.locator(GATILHO).click()
            _esperar_a_entrada(pagina)
            assert _violacoes_do_axe(pagina) == [], (rota, esquema, largura)


@pytest.mark.parametrize("esquema, marca", [("light", "marca-autor-escura.webp"), ("dark", "marca-autor-clara.webp")])
def test_a_marca_do_modal_segue_o_tema_e_a_do_rodape_e_sempre_a_clara(abrir, esquema, marca):
    with abrir("/", color_scheme=esquema, reduced_motion="reduce") as pagina:
        pagina.locator(GATILHO).click()
        _esperar_a_entrada(pagina)
        atual = pagina.locator(f"{MODAL} picture img").evaluate(
            "async (i) => { await i.decode(); return { src: i.currentSrc, w: i.naturalWidth, h: i.height }; }"
        )
        assert atual["src"].endswith("/" + marca) and atual["w"] == 462 and 24 <= atual["h"] <= 28, atual
        rodape = pagina.locator("footer img.nn-autor-marca").evaluate(
            "async (i) => { await i.decode(); return { src: i.currentSrc, h: i.height }; }"
        )
        assert rodape["src"].endswith("/marca-autor-clara.webp") and 24 <= rodape["h"] <= 28, rodape  # rodape preto nos dois temas


# --- cabecalho: duas linhas, o "por" abaixo do titulo no celular ---

_CAIXAS_DO_CABECALHO = """() => {
  const caixa = (s) => { const c = document.querySelector(s).getBoundingClientRect(); return { x: c.left, y: c.top, r: c.right, b: c.bottom, w: c.width, h: c.height }; };
  const linha = getComputedStyle(document.querySelector('.nn-topo-linha'));
  return {
    topo: caixa('.nn-topo'), marca: caixa('.nn-marca'), autoria: caixa('.nn-autoria'), linha: caixa('.nn-topo-linha'),
    menu: caixa('.nn-menu'), linhaFundo: linha.backgroundColor, largura: window.innerWidth,
    rolagem: document.documentElement.scrollWidth,
  };
}"""


def _fontes_da_autoria(pagina) -> dict:
    """O "por" pequeno e discreto; o nome em destaque (18 px no desktop, 16 px no celular), em negrito, com o link."""
    return pagina.evaluate("""() => {
      const p = document.querySelector('.nn-autoria'), n = p.querySelector('strong');
      return { por: parseFloat(getComputedStyle(p).fontSize), nome: parseFloat(getComputedStyle(n).fontSize),
               peso: Number(getComputedStyle(n).fontWeight), href: n.closest('a').getAttribute('href') };
    }""")


@pytest.mark.parametrize("rota", PAGINAS_COM_CABECALHO)
def test_cabecalho_no_desktop_titulo_a_esquerda_autor_a_direita_linha_e_menu_embaixo(abrir, rota):
    with abrir(rota, largura=DESKTOP, reduced_motion="reduce") as pagina:
        m = pagina.evaluate(_CAIXAS_DO_CABECALHO)
        assert m["marca"]["x"] < m["topo"]["x"] + m["topo"]["w"] * 0.2  # o titulo na ponta esquerda
        assert m["autoria"]["r"] > m["topo"]["r"] - m["topo"]["w"] * 0.1  # o "por" na ponta direita
        assert m["autoria"]["x"] >= m["marca"]["r"] + 8  # lado a lado, sem se tocar
        assert abs((m["autoria"]["y"] + m["autoria"]["b"]) / 2 - (m["marca"]["y"] + m["marca"]["b"]) / 2) < 14  # na mesma linha
        assert m["linha"]["h"] == 1 and m["linha"]["y"] >= m["marca"]["b"] and m["linha"]["y"] >= m["autoria"]["b"]
        assert m["menu"]["y"] >= m["linha"]["b"]  # o menu, embaixo da linha fina
        assert m["linha"]["w"] > m["topo"]["w"] * 0.9  # a linha vai de ponta a ponta
        assert _estouro(pagina) == {}
        assert pagina.locator(".nn-menu a[aria-current='page']").count() == 1
        assert _fontes_da_autoria(pagina) == {"por": 13, "nome": 18, "peso": 700, "href": "https://dnascimento.com.br"}


@pytest.mark.parametrize("rota", PAGINAS_COM_CABECALHO)
def test_cabecalho_no_celular_o_por_desce_o_menu_rola_de_lado_e_nada_estoura(abrir, rota):
    with abrir(rota, largura=CELULAR, reduced_motion="reduce") as pagina:
        m = pagina.evaluate(_CAIXAS_DO_CABECALHO)
        assert m["autoria"]["y"] >= m["marca"]["b"] - 1  # o "por" fica embaixo do titulo
        assert m["autoria"]["x"] < m["marca"]["x"] + 8  # alinhado a esquerda, como o titulo
        assert m["linha"]["y"] >= m["autoria"]["b"] and m["menu"]["y"] >= m["linha"]["b"]
        assert m["topo"]["r"] <= m["largura"] and m["rolagem"] <= m["largura"]
        assert _fontes_da_autoria(pagina) == {"por": 13, "nome": 16, "peso": 700, "href": "https://dnascimento.com.br"}
        menu = pagina.locator(".nn-menu").evaluate("m => ({ rola: m.scrollWidth > m.clientWidth, overflowX: getComputedStyle(m).overflowX })")
        assert menu == {"rola": True, "overflowX": "auto"}, menu  # sete abas nao cabem em 390 px: o menu rola, a pagina nao
        assert _estouro(pagina) == {}
        pagina.evaluate("() => { const m = document.querySelector('.nn-menu'); m.scrollLeft = m.scrollWidth; }")
        assert _estouro(pagina) == {}


@pytest.mark.parametrize("largura", [CELULAR, 561, 900, DESKTOP])
def test_cabecalho_e_rodape_nao_estouram_a_largura_e_o_circulo_tem_56_px(abrir, largura):
    for rota in PAGINAS_COM_CABECALHO:
        with abrir(rota, largura=largura, reduced_motion="reduce") as pagina:
            assert _estouro(pagina) == {}, (rota, largura)
            circulo = pagina.locator(".nn-autor-circulo").evaluate(
                "c => { const r = c.getBoundingClientRect(); return { w: r.width, h: r.height, raio: getComputedStyle(c).borderTopLeftRadius }; }"
            )
            assert circulo["w"] == circulo["h"] == 56 and circulo["raio"] in ("50%", "28px"), circulo
            rodape = pagina.locator("footer").bounding_box()
            assert rodape["x"] >= 0 and rodape["x"] + rodape["width"] <= largura


# --- contraste nos pixels reais ---

_TEXTOS = """(seletores) => {
  const saida = [];
  for (const el of document.querySelectorAll(seletores)) {
    const menu = el.closest('.nn-menu');
    const corte = menu ? menu.getBoundingClientRect() : null;
    const intervalo = document.createRange();
    intervalo.selectNodeContents(el);
    const caixas = [...intervalo.getClientRects()].filter((c) => c.width > 0 && c.height > 0)
      .map((c) => ({ x: c.left + scrollX, y: c.top + scrollY, w: c.width, h: c.height }));
    // no menu que rola de lado, a borda direita esmaece (mascara): so vale o que esta inteiro na parte nitida
    if (corte && (el.getBoundingClientRect().right > corte.left + corte.width * 0.8)) continue;
    if (caixas.length) saida.push({ nome: `${el.tagName.toLowerCase()}.${el.className}`, cor: getComputedStyle(el).color, caixas });
  }
  return saida;
}"""
_ESCONDER = """(seletor) => {
  for (const e of document.querySelectorAll(`${seletor}, ${seletor} *`)) {
    for (const [p, v] of [['color', 'transparent'], ['-webkit-text-fill-color', 'transparent'], ['text-decoration-color', 'transparent']]) {
      e.style.setProperty(p, v, 'important');
    }
  }
}"""


def _pior_contraste(pagina, seletor_da_caixa: str, seletor_dos_textos: str) -> tuple[float, int]:
    textos = pagina.evaluate(_TEXTOS, seletor_dos_textos)
    pagina.evaluate(_ESCONDER, seletor_da_caixa)
    fundo = np.array(Image.open(io.BytesIO(pagina.screenshot(full_page=True))).convert("RGB"), dtype=float)
    alto, largo = fundo.shape[:2]
    pior = 99.0
    for texto in textos:
        cor, alfa = _cor_computada(texto["cor"])
        for c in texto["caixas"]:
            xa, xb = max(0, int(c["x"])), min(largo, int(np.ceil(c["x"] + c["w"])))
            ya, yb = max(0, int(c["y"])), min(alto, int(np.ceil(c["y"] + c["h"])))
            atras = fundo[ya:yb, xa:xb].reshape(-1, 3)
            if len(atras):
                pior = min(pior, float(_contrastes(alfa * cor + (1 - alfa) * atras, atras).min()))
    return pior, len(textos)


@pytest.mark.parametrize("esquema", ["light", "dark"])
@pytest.mark.parametrize("largura", [CELULAR, DESKTOP])
@pytest.mark.parametrize("rota", ["/", "/como-chegamos/"])
def test_contraste_do_cabecalho_nos_pixels_reais(abrir, rota, largura, esquema):
    """Titulo, "por", nome e abas >= 4,5:1 contra o pior pixel atras de cada linha: sobre a abertura com foto (o Inicio)
    e sobre a pagina de papel antigo (Como chegamos), nos dois temas. O topo e uma barra preta propria, entao a foto e o
    papel nao chegam atras do texto; o teste confere o que o navegador de fato pinta."""
    with abrir(rota, largura=largura, color_scheme=esquema, reduced_motion="reduce") as pagina:
        pagina.evaluate("() => document.fonts.ready")
        pior, quantos = _pior_contraste(pagina, ".nn-topo", ".nn-marca, .nn-autoria, .nn-autoria strong, .nn-menu a")
    assert quantos >= 5, quantos  # o titulo, o "por", o nome e ao menos duas abas
    assert pior >= LIMITE_DO_CONTRASTE, f"{rota} {largura} {esquema}: {pior:.2f}:1"


@pytest.mark.parametrize("esquema", ["light", "dark"])
@pytest.mark.parametrize("largura", [CELULAR, DESKTOP])
def test_contraste_do_bloco_de_autoria_do_rodape(abrir, largura, esquema):
    with abrir("/", largura=largura, color_scheme=esquema, reduced_motion="reduce") as pagina:
        # os textos do rodape, sem o circulo (foto ou iniciais)
        pior, quantos = _pior_contraste(
            pagina, ".nn-rodape", ".nn-rodape > span, .nn-rodape > a, .nn-rodape code, .nn-autor-texto, .nn-autor-nome"
        )
    assert quantos >= 5, quantos
    assert pior >= LIMITE_DO_CONTRASTE, f"{largura} {esquema}: {pior:.2f}:1"


# --- sem JavaScript ---


def test_sem_javascript_o_link_leva_a_secao_autor_de_sobre_e_o_modal_nao_abre(abrir):
    with abrir("/estados/", java_script_enabled=False, reduced_motion="reduce") as pagina:
        assert not pagina.locator(MODAL).evaluate("d => d.open")
        assert not pagina.locator(MODAL).is_visible()
        pagina.locator(GATILHO).click()
        pagina.wait_for_url(re.compile(r"/sobre/#autor$"))
        secao = pagina.locator("#autor")
        assert secao.is_visible()
        assert "Fiz este estudo por raiva, e também por orgulho." in secao.inner_text()
        assert pagina.locator("#autor h2").inner_text() == "Sobre o autor"
        assert not pagina.locator(MODAL).is_visible()
    with abrir("/", java_script_enabled=False, reduced_motion="reduce") as pagina:
        # o cabecalho e o rodape se leem sem script: titulo com link, "por" com o nome, menu, foto no circulo
        assert pagina.locator(".nn-marca").get_attribute("href") == "/"
        assert pagina.locator(".nn-autoria a").get_attribute("href") == "https://dnascimento.com.br"
        assert pagina.locator(".nn-menu a").count() == 7
        assert pagina.locator(".nn-autor-circulo img").evaluate("i => i.complete && i.naturalWidth === 320")


def test_a_pagina_sobre_com_javascript_mostra_a_secao_autor_e_o_rodape_ainda_abre_o_modal(abrir):
    with abrir("/sobre/#autor", reduced_motion="reduce") as pagina:
        assert pagina.locator("#autor").is_visible()
        pagina.locator(GATILHO).click()
        assert pagina.evaluate(_ESTADO)["aberto"]
        pagina.keyboard.press("Escape")
        assert not pagina.evaluate(_ESTADO)["aberto"]
