"""Autoria e menu no Chromium: o menu do alto (marca, barra preta com <details>, botao laranja, gaveta no celular; sem "por"), o bloco "Desenvolvido por" do
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
# a abertura com foto, o papel antigo e duas comuns; e as duas primeiras em ingles (o seletor de idioma no menu)
PAGINAS_COM_CABECALHO = ["/", "/como-chegamos/", "/estados/", "/sobre/", "/en/", "/en/how-we-got-here/"]

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


# --- menu do alto: marca, barra preta pendurada com <details>, botao laranja; a autoria so no rodape ---

MENU_FIXO = 1100  # de 1100 px para cima a barra preta; abaixo, o botao de menu e a gaveta

_CAIXAS_DO_MENU = """() => {
  const caixa = (s) => { const e = document.querySelector(s); if (!e) return null; const c = e.getBoundingClientRect();
    return { x: c.left, y: c.top, r: c.right, b: c.bottom, w: c.width, h: c.height }; };
  const alca = document.querySelector('.nn-topo-alca');
  return {
    topo: caixa('.nn-topo'), marca: caixa('.nn-marca'), alca: caixa('.nn-topo-alca'), botao: caixa('.nn-topo-botao'),
    movel: caixa('.nn-menu-movel > summary'), alcaExibe: getComputedStyle(alca).display,
    alcaFundo: getComputedStyle(alca).backgroundColor, botaoFundo: getComputedStyle(document.querySelector('.nn-topo-botao')).backgroundColor,
    largura: window.innerWidth, rolagem: document.documentElement.scrollWidth,
  };
}"""


@pytest.mark.parametrize("rota", PAGINAS_COM_CABECALHO)
def test_menu_no_desktop_marca_a_esquerda_barra_preta_no_centro_e_botao_laranja_a_direita(abrir, rota):
    with abrir(rota, largura=DESKTOP, reduced_motion="reduce") as pagina:
        m = pagina.evaluate(_CAIXAS_DO_MENU)
        assert m["alcaExibe"] != "none" and m["alcaFundo"] == "rgb(10, 10, 10)", m  # a barra pendurada, preta nos dois temas
        assert m["alca"]["y"] <= 1  # pendurada no alto da pagina
        assert m["marca"]["x"] < m["topo"]["x"] + m["topo"]["w"] * 0.2  # a marca na ponta esquerda
        assert m["botao"]["r"] > m["topo"]["r"] - m["topo"]["w"] * 0.1  # o botao laranja na ponta direita
        assert m["marca"]["r"] + 8 <= m["alca"]["x"] and m["alca"]["r"] + 8 <= m["botao"]["x"]  # tres blocos, sem se tocar
        assert abs((m["alca"]["x"] + m["alca"]["r"]) / 2 - m["largura"] / 2) <= 2  # a barra, centrada
        assert m["botaoFundo"] == "rgb(196, 38, 0)"  # o laranja-escuro, que passa de 4,5:1 com o texto branco
        assert m["movel"]["w"] == 0 or m["movel"] is None  # o botao de menu do celular nao aparece
        assert _estouro(pagina) == {}
        # autoria so no rodape: nenhum "por ..." no topo, e o credito do autor continua no rodape
        assert pagina.locator(".nn-autoria").count() == 0
        assert pagina.locator("header .nn-autor-abrir, header a[href='https://dnascimento.com.br']").count() == 0
        assert pagina.locator("footer .nn-autor-abrir").count() == 1
        # a pagina atual marcada uma vez (o link de cima ou o cartao dentro do grupo, que tambem marca o grupo)
        assert pagina.locator(".nn-menu [aria-current='page']").count() == 1
        grupo_atual = pagina.locator(".nn-menu-grupo[data-atual]").count()
        assert grupo_atual == (1 if rota in ("/como-chegamos/", "/estados/", "/en/how-we-got-here/") else 0)
        assert pagina.locator(".nn-menu > a").count() == 2 and pagina.locator(".nn-menu-grupo").count() == 2


def test_menu_no_desktop_os_grupos_abrem_um_de_cada_vez_e_fecham_com_esc(abrir):
    with abrir("/", largura=DESKTOP, reduced_motion="reduce") as pagina:
        grupos = pagina.locator("details.nn-menu-grupo")
        assert grupos.count() == 2 and all(g.get_attribute("name") == "nn-menu" for g in (grupos.nth(0), grupos.nth(1)))
        assert not pagina.locator(".nn-menu-painel:visible").count()  # fechados, nenhum painel a vista
        grupos.nth(0).locator("summary").click()
        assert pagina.locator("details.nn-menu-grupo[open]").count() == 1 and pagina.locator(".nn-menu-painel:visible").count() == 1
        painel = pagina.locator("details.nn-menu-grupo[open] .nn-menu-painel").bounding_box()
        barra = pagina.locator(".nn-topo-alca").bounding_box()
        assert painel["y"] >= barra["y"] + 40 and painel["x"] >= 0 and painel["x"] + painel["width"] <= 1280  # desce da barra, na tela
        grupos.nth(1).locator("summary").click()  # o mesmo `name`: abrir o outro fecha o primeiro
        assert pagina.locator("details.nn-menu-grupo[open]").count() == 1
        assert grupos.nth(1).evaluate("d => d.open") and not grupos.nth(0).evaluate("d => d.open")
        assert _estouro(pagina) == {}


@pytest.mark.parametrize("rota", PAGINAS_COM_CABECALHO)
def test_menu_no_celular_a_barra_some_o_botao_de_menu_abre_a_gaveta_e_nada_estoura(abrir, rota):
    with abrir(rota, largura=CELULAR, reduced_motion="reduce") as pagina:
        m = pagina.evaluate(_CAIXAS_DO_MENU)
        assert m["alcaExibe"] == "none"  # a barra preta so existe de 1100 px para cima
        assert m["marca"]["x"] < 40 and m["botao"]["b"] <= m["topo"]["b"]  # a marca a esquerda e o botao laranja na barra
        assert m["movel"]["w"] >= 44 and m["movel"]["h"] >= 44 and m["movel"]["r"] <= m["largura"]  # alvo de toque
        assert m["topo"]["r"] <= m["largura"] and m["rolagem"] <= m["largura"]
        assert pagina.locator(".nn-autoria").count() == 0
        assert not pagina.locator(".nn-gaveta").is_visible()
        pagina.locator(".nn-menu-movel > summary").click()
        gaveta = pagina.locator(".nn-gaveta")
        assert gaveta.is_visible()
        caixa = gaveta.bounding_box()
        assert caixa["x"] >= 0 and caixa["x"] + caixa["width"] <= CELULAR
        assert pagina.locator(".nn-gaveta > a").count() == 2 and pagina.locator(".nn-gaveta details").count() == 2
        pagina.locator(".nn-gaveta details > summary").first.click()  # a sanfona abre sem estourar a largura
        assert pagina.locator(".nn-gaveta details[open] .nn-gaveta-itens a:visible").count() >= 1
        assert _estouro(pagina) == {}


@pytest.mark.parametrize("largura", [320, 360, CELULAR])
@pytest.mark.parametrize("rota", PAGINAS_COM_CABECALHO)
def test_menu_no_celular_marca_botao_e_menu_cabem_na_largura_e_a_marca(abrir, rota, largura):
    """A marca, o botao laranja e o botao de menu cabem lado a lado em 360 px (somavam 384 e o de menu saia da tela)."""
    with abrir(rota, largura=largura, reduced_motion="reduce") as pagina:
        m = pagina.evaluate(_CAIXAS_DO_MENU)
        assert m["rolagem"] <= largura and m["movel"]["r"] <= largura and m["botao"]["r"] <= m["movel"]["x"], m
        assert m["marca"]["r"] <= m["botao"]["x"], m


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
    // so os nos de texto: a bandeira do seletor de idioma (<img>) e o nome so para leitor de tela nao sao texto pintado
    const caixas = [];
    const andar = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    while (andar.nextNode()) {
      if (andar.currentNode.parentElement.closest('.nn-so-leitor')) continue;
      const intervalo = document.createRange();
      intervalo.selectNodeContents(andar.currentNode);
      caixas.push(...[...intervalo.getClientRects()].filter((c) => c.width > 0 && c.height > 0)
        .map((c) => ({ x: c.left + scrollX, y: c.top + scrollY, w: c.width, h: c.height })));
    }
    if (!el.checkVisibility()) continue;  // dentro de um <details> fechado (o texto nao esta na tela)
    if (!caixas.length) continue;
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
@pytest.mark.parametrize("rota", ["/", "/como-chegamos/", "/en/"])
def test_contraste_do_menu_nos_pixels_reais(abrir, rota, largura, esquema):
    """Marca, abas, grupos e botao laranja >= 4,5:1 contra o pior pixel atras de cada linha: sobre a abertura com foto
    (o Inicio) e sobre a capa da pagina de papel antigo (Como chegamos), nos dois temas, com o menu fechado e com o
    painel (desktop) ou a gaveta (celular) aberto. O teste confere o que o navegador de fato pinta."""
    desktop = largura >= MENU_FIXO
    textos = ".nn-marca, .nn-topo-botao" + (", .nn-menu > a, .nn-menu-grupo > summary, .nn-menu .nn-idioma" if desktop else "")
    with abrir(rota, largura=largura, color_scheme=esquema, reduced_motion="reduce") as pagina:
        pagina.evaluate("() => document.fonts.ready")
        pior, quantos = _pior_contraste(pagina, ".nn-topo", textos)
    assert quantos >= (6 if desktop else 2), quantos  # marca e botao; no desktop, tambem as quatro abas
    assert pior >= LIMITE_DO_CONTRASTE, f"{rota} {largura} {esquema} (fechado): {pior:.2f}:1"
    with abrir(rota, largura=largura, color_scheme=esquema, reduced_motion="reduce") as pagina:
        pagina.evaluate("() => document.fonts.ready")
        if desktop:
            pagina.locator("details.nn-menu-grupo > summary").first.click()
            abertos = ".nn-menu-cartao-titulo, .nn-menu-cartao-texto"
        else:
            pagina.locator(".nn-menu-movel > summary").click()
            pagina.locator(".nn-gaveta details > summary").first.click()
            abertos = ".nn-gaveta a, .nn-gaveta summary"
        pagina.evaluate("() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))")
        pior, quantos = _pior_contraste(pagina, ".nn-topo", abertos)
    assert quantos >= 3, quantos
    assert pior >= LIMITE_DO_CONTRASTE, f"{rota} {largura} {esquema} (aberto): {pior:.2f}:1"


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
        assert pagina.locator(".nn-autoria").count() == 0  # o topo nao tem mais "por": a autoria so no rodape
        assert pagina.locator("footer .nn-autor-abrir").get_attribute("href") == "/sobre/#autor"
        assert pagina.locator("footer a[href='https://dnascimento.com.br']").count() >= 1
        # o menu abre sem script: os grupos sao <details> e o painel mostra os cartoes
        assert pagina.locator(".nn-menu > a:visible").count() == 2 and pagina.locator(".nn-menu-grupo > summary:visible").count() == 2
        pagina.locator(".nn-menu-grupo > summary").first.click()
        assert pagina.locator(".nn-menu-grupo[open] .nn-menu-cartao:visible").count() >= 2
        assert pagina.locator(".nn-autor-circulo img").evaluate("i => i.complete && i.naturalWidth === 320")


def test_a_pagina_sobre_com_javascript_mostra_a_secao_autor_e_o_rodape_ainda_abre_o_modal(abrir):
    with abrir("/sobre/#autor", reduced_motion="reduce") as pagina:
        assert pagina.locator("#autor").is_visible()
        pagina.locator(GATILHO).click()
        assert pagina.evaluate(_ESTADO)["aberto"]
        pagina.keyboard.press("Escape")
        assert not pagina.evaluate(_ESTADO)["aberto"]
