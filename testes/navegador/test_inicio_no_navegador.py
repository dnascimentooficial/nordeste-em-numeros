"""O redesenho no Chromium: o menu do alto (barra pendurada, painéis, gaveta), a abertura e as capas em seção cheia, o
placar, os capítulos com o menu lateral e a folha, o botão voltar ao topo, a abertura de Como chegamos em duas colunas e
a linha do tempo de canto a canto.

Marcador `navegador`: `python -m pytest -m navegador testes/navegador -k inicio`.

Texto sobre foto (a abertura, as capas, a marca sobre elas) não tem um fundo liso: o contraste é medido nos pixels de
cada letra. O navegador desenha a página três vezes: com as letras pretas e sem sombra, brancas e sem sombra (onde as
duas diferem está a letra, seja qual for a foto atrás) e transparentes com a sombra (o que de fato fica atrás de cada
letra). O pior pixel coberto por letra, contra a cor do texto, tem de passar de 4,5:1, ou de 3:1 no texto grande da
WCAG (24 px, ou 18,66 px em negrito), em 99,5% dos pixels das letras: o meio pixel restante é a borda serrilhada de
uma ou outra letra sobre o ponto mais claro da foto, que nenhuma sombra razoável cobre por inteiro.
"""

import io
import re

import numpy as np
import pytest
from PIL import Image

from test_site_no_navegador import CELULAR, DESKTOP, _contrastes, _cor_computada, _estouro, _violacoes_do_axe

pytestmark = pytest.mark.navegador
LARGO = 1440
CAPAS = {  # rota -> imagem de fundo da capa, com o repositorio inteiro (pagina historica publicada)
    "/como-chegamos/": "/historia/1530.webp", "/estados/": "/historia/1964.webp", "/explorar/": "/historia/1950.webp",
    "/cards/": "/historia/marco-1932.webp", "/dados/": "/historia/marco-1934.webp", "/sobre/": "/foto-abertura.webp",
}

# --- contraste nos pixels das letras ---

_LETRAS = """(seletores) => {
  const saida = [];
  for (const el of document.querySelectorAll(seletores)) {
    const estilo = getComputedStyle(el);
    if (estilo.visibility === 'hidden' || estilo.display === 'none') continue;
    const intervalo = document.createRange();
    intervalo.selectNodeContents(el);
    const caixas = [...intervalo.getClientRects()].filter((c) => c.width > 0 && c.height > 0)
      .map((c) => ({ x: c.left + scrollX, y: c.top + scrollY, w: c.width, h: c.height }));
    const tamanho = parseFloat(estilo.fontSize), peso = Number(estilo.fontWeight);
    if (caixas.length) saida.push({ nome: `${el.tagName.toLowerCase()}.${el.className}`, cor: estilo.color, caixas,
      grande: tamanho >= 24 || (tamanho >= 18.66 && peso >= 700) });
  }
  return saida;
}"""
_PINTAR = """([seletores, cor, sombra]) => {
  for (const e of document.querySelectorAll(seletores.split(',').map((s) => `${s}, ${s} *`).join(','))) {
    e.style.setProperty('color', cor, 'important');
    e.style.setProperty('-webkit-text-fill-color', cor, 'important');
    e.style.setProperty('text-decoration-color', 'transparent', 'important');
    if (!sombra) e.style.setProperty('text-shadow', 'none', 'important');
  }
}"""


def _foto_da_pagina(pagina) -> np.ndarray:
    return np.array(Image.open(io.BytesIO(pagina.screenshot(full_page=True))).convert("RGB"), dtype=float)


def _contraste_das_letras(pagina, seletores: str) -> dict[str, tuple[float, float]]:
    """nome -> (pior contraste nos pixels das letras, minimo exigido) de cada elemento de `seletores`."""
    textos = pagina.evaluate(_LETRAS, seletores)
    assert textos, seletores
    pagina.evaluate(_PINTAR, [seletores, "#000", False])
    preto = _foto_da_pagina(pagina)
    pagina.evaluate(_PINTAR, [seletores, "#fff", False])
    branco = _foto_da_pagina(pagina)
    pagina.evaluate("() => { for (const e of document.querySelectorAll('*')) { e.style.removeProperty('text-shadow'); } }")
    pagina.evaluate(_PINTAR, [seletores, "transparent", True])
    fundo = _foto_da_pagina(pagina)
    letra = np.abs(branco - preto).mean(axis=2) > 128  # cobertura da letra acima de metade do pixel
    alto, largo = fundo.shape[:2]
    medidas = {}
    for n, texto in enumerate(textos):
        cor, alfa = _cor_computada(texto["cor"])
        valores = []
        for c in texto["caixas"]:
            xa, xb = max(0, int(c["x"])), min(largo, int(np.ceil(c["x"] + c["w"])))
            ya, yb = max(0, int(c["y"])), min(alto, int(np.ceil(c["y"] + c["h"])))
            mascara = letra[ya:yb, xa:xb]
            atras = fundo[ya:yb, xa:xb][mascara]
            assert len(atras) > 10, (texto["nome"], c)  # a letra apareceu no desenho
            valores.append(_contrastes(alfa * cor + (1 - alfa) * atras, atras))
        pior = float(np.percentile(np.concatenate(valores), 0.5))
        medidas[f"{n}:{texto['nome']}"] = (round(pior, 2), 3.0 if texto["grande"] else 4.5)
    return medidas


def _reprovados(medidas: dict) -> dict:
    return {nome: v for nome, v in medidas.items() if v[0] < v[1]}


# --- abertura em secao cheia ---

_ABERTURA = """() => {
  const hero = document.querySelector('#topo');
  const caixa = hero.getBoundingClientRect();
  const antes = getComputedStyle(hero, '::before');
  const depois = getComputedStyle(hero, '::after');
  const marca = document.querySelector('.nn-marca').getBoundingClientRect();
  const conteudo = document.querySelector('.nn-faixa-abertura').getBoundingClientRect();
  return {
    hero: { x: caixa.left, y: caixa.top + scrollY, w: caixa.width, h: caixa.height }, janela: document.documentElement.clientWidth,
    foto: antes.backgroundImage, inset: [antes.top, antes.right, antes.bottom, antes.left], circulo: depois.content,
    eyebrow: document.querySelector('#topo .nn-eyebrow').getBoundingClientRect().left, marca: marca.left,
    margem: conteudo.left, destaque: getComputedStyle(document.querySelector('#topo .nn-destaque')).color,
    marcaCor: getComputedStyle(document.querySelector('.nn-marca')).color,
    vidro: getComputedStyle(document.querySelector('.nn-hero-intro')).backdropFilter,
  };
}"""


@pytest.mark.parametrize("largura", [CELULAR, 900, 1100, DESKTOP, LARGO])
def test_inicio_abertura_em_secao_cheia_com_a_foto_inteira_e_contraste_nas_letras(abrir, largura):
    with abrir("/", largura=largura, altura=900, reduced_motion="reduce") as pagina:
        m = pagina.evaluate(_ABERTURA)
        # na largura toda da tela, comecando no alto, por baixo do menu
        assert m["hero"]["x"] == 0 and abs(m["hero"]["w"] - m["janela"]) <= 1 and m["hero"]["y"] == 0, m
        # a foto inteira, num veu uniforme de 30%, sem degradê nem recorte; sem o circulo decorativo
        assert m["foto"].startswith("linear-gradient(rgba(8, 8, 8, 0.3), rgba(8, 8, 8, 0.3)), url(") and "foto-abertura.webp" in m["foto"]
        assert m["inset"] == ["0px"] * 4 and m["circulo"] in ("none", "normal")
        # o texto na largura padrao: o selo alinha com a marca e com os blocos de baixo
        assert abs(m["eyebrow"] - m["marca"]) <= 1 and abs(m["eyebrow"] - m["margem"]) <= 1, m
        assert m["destaque"] == "rgb(255, 90, 31)" and m["marcaCor"] == "rgb(255, 255, 255)" and m["vidro"] == "blur(3px)"
        assert _estouro(pagina) == {}
        medidas = _contraste_das_letras(pagina, "#topo .nn-eyebrow, #topo .nn-hero-titulo > span, #topo .nn-hero-intro, .nn-topo .nn-marca")
    assert len(medidas) >= 6
    assert _reprovados(medidas) == {}, medidas


# --- capas ---


@pytest.mark.parametrize("largura", [CELULAR, LARGO])
@pytest.mark.parametrize("rota", list(CAPAS))
def test_inicio_capa_em_secao_cheia_com_a_imagem_da_pagina(abrir, rota, largura):
    with abrir(rota, largura=largura, altura=900, reduced_motion="reduce") as pagina:
        m = pagina.evaluate("""() => {
          const c = document.querySelector('main > section.nn-capa'), r = c.getBoundingClientRect();
          return { x: r.left, y: r.top + scrollY, w: r.width, janela: document.documentElement.clientWidth,
                   fundo: getComputedStyle(c).backgroundImage, titulo: getComputedStyle(c.querySelector('h1')).color,
                   marca: getComputedStyle(document.querySelector('.nn-marca')).color,
                   texto: c.querySelector('.nn-capa-texto').getBoundingClientRect().left,
                   margem: document.querySelector('.nn-marca').getBoundingClientRect().left };
        }""")
        assert m["x"] == 0 and abs(m["w"] - m["janela"]) <= 1 and m["y"] == 0, m
        assert CAPAS[rota] in m["fundo"] and "linear-gradient" in m["fundo"]
        assert m["titulo"] == m["marca"] == "rgb(255, 255, 255)" and abs(m["texto"] - m["margem"]) <= 1
        carregada = pagina.evaluate("async (u) => { const i = new Image(); i.src = u; await i.decode(); return i.naturalWidth; }", CAPAS[rota])
        assert carregada > 0
        assert _estouro(pagina) == {}
        medidas = _contraste_das_letras(pagina, "main > .nn-capa h1, main > .nn-capa .nn-capa-intro, main > .nn-capa .nn-capa-credito")
    assert _reprovados(medidas) == {}, medidas


def test_inicio_pagina_de_card_sem_capa_com_a_marca_na_tinta_do_tema(abrir):
    for esquema, cor in (("light", "rgb(8, 8, 8)"), ("dark", "rgb(245, 244, 239)")):
        with abrir("/cards/pibpc/", color_scheme=esquema, reduced_motion="reduce") as pagina:
            assert pagina.locator(".nn-capa").count() == 0
            assert pagina.locator(".nn-marca").evaluate("e => getComputedStyle(e).color") == cor


# --- menu do alto ---

_MENU = """() => {
  const r = (s) => { const e = document.querySelector(s); if (!e) return null; const c = e.getBoundingClientRect();
    return { x: c.left, y: c.top, r: c.right, b: c.bottom, w: c.width, h: c.height, visivel: c.width > 0 && getComputedStyle(e).visibility !== 'hidden' }; };
  const abertos = [...document.querySelectorAll('.nn-topo details')].filter((d) => d.open).map((d) => d.querySelector('summary').textContent.trim());
  return { alca: r('.nn-topo-alca'), painel: r('.nn-menu-grupo[open] .nn-menu-painel'), movel: r('.nn-menu-movel > summary'),
           gaveta: r('.nn-menu-movel[open] .nn-gaveta'), marca: r('.nn-marca'), botao: r('.nn-topo-botao'), abertos,
           foco: document.activeElement && document.activeElement.textContent.trim() };
}"""


def test_inicio_menu_no_computador_abre_um_grupo_por_vez_e_fecha_com_esc_e_clique_fora(abrir):
    with abrir("/estados/", largura=DESKTOP, reduced_motion="reduce") as pagina:
        m = pagina.evaluate(_MENU)
        assert m["alca"]["visivel"] and m["alca"]["y"] == 0 and not m["movel"]["visivel"]
        # a barra no meio, entre a marca e o botao, sem tocar nenhum
        assert m["marca"]["r"] < m["alca"]["x"] and m["alca"]["r"] < m["botao"]["x"]
        assert pagina.locator(".nn-menu-grupo[data-atual] > summary").inner_text() == "Dados"
        pagina.locator(".nn-menu-grupo > summary", has_text="Histórias").click()
        m = pagina.evaluate(_MENU)
        assert m["abertos"] == ["Histórias"]
        # o painel desce como continuacao da barra: na largura dela, logo embaixo
        assert abs(m["painel"]["x"] - m["alca"]["x"]) <= 1 and abs(m["painel"]["w"] - m["alca"]["w"]) <= 1
        assert abs(m["painel"]["y"] - m["alca"]["b"]) <= 1
        pagina.locator(".nn-menu-grupo > summary", has_text="Dados").click()
        assert pagina.evaluate(_MENU)["abertos"] == ["Dados"]  # um grupo por vez
        assert pagina.locator(".nn-menu-painel a[aria-current='page']").inner_text().startswith("Estados")
        pagina.keyboard.press("Escape")
        m = pagina.evaluate(_MENU)
        assert m["abertos"] == [] and m["foco"] == "Dados"  # o foco volta ao summary
        pagina.locator(".nn-menu-grupo > summary", has_text="Histórias").click()
        pagina.mouse.click(700, 600)  # fora do menu
        assert pagina.evaluate(_MENU)["abertos"] == []
        assert _estouro(pagina) == {}


def test_inicio_menu_sem_javascript_abre_pelo_proprio_details(abrir):
    with abrir("/", largura=DESKTOP, java_script_enabled=False, reduced_motion="reduce") as pagina:
        pagina.locator(".nn-menu-grupo > summary", has_text="Dados").click()
        assert pagina.locator(".nn-menu-painel a", has_text="Explorar").is_visible()
        pagina.locator(".nn-menu-painel a", has_text="Explorar").click()
        pagina.wait_for_url(re.compile(r"/explorar/$"))


@pytest.mark.parametrize("largura", [CELULAR, 1099])
def test_inicio_gaveta_no_celular_com_os_grupos_em_sanfona(abrir, largura):
    with abrir("/", largura=largura, reduced_motion="reduce") as pagina:
        m = pagina.evaluate(_MENU)
        assert not m["alca"]["visivel"] and m["movel"]["visivel"]
        assert m["movel"]["w"] >= 44 and m["movel"]["h"] >= 44  # alvo de toque
        pagina.locator(".nn-menu-movel > summary").click()
        assert pagina.evaluate(_MENU)["gaveta"]["visivel"]
        gaveta = pagina.locator(".nn-gaveta")
        gaveta.locator("summary", has_text="Histórias").click()
        assert gaveta.locator("a", has_text="Como chegamos até aqui").is_visible()
        gaveta.locator("summary", has_text="Dados").click()
        assert not gaveta.locator("a", has_text="Como chegamos até aqui").is_visible()  # um grupo por vez
        assert gaveta.locator("a", has_text="Explorar").is_visible()
        assert _estouro(pagina) == {}
        pagina.keyboard.press("Escape")
        assert not pagina.evaluate(_MENU)["gaveta"]
        assert pagina.evaluate("() => document.activeElement.closest('.nn-menu-movel') !== null")
        if largura == CELULAR:
            assert " ".join(pagina.locator(".nn-topo-botao").inner_text().split()) == "linha do tempo →"  # o "Ver a" some abaixo de 520 px


@pytest.mark.parametrize("esquema", ["light", "dark"])
@pytest.mark.parametrize("largura", [CELULAR, DESKTOP])
def test_inicio_axe_com_o_menu_aberto(abrir, largura, esquema):
    with abrir("/explorar/", largura=largura, color_scheme=esquema, reduced_motion="reduce") as pagina:
        if largura == DESKTOP:
            pagina.locator(".nn-menu-grupo > summary", has_text="Histórias").click()
        else:
            pagina.locator(".nn-menu-movel > summary").click()
            pagina.locator(".nn-gaveta summary", has_text="Dados").click()
        assert _violacoes_do_axe(pagina) == []


@pytest.mark.parametrize("esquema", ["light", "dark"])
@pytest.mark.parametrize("rota", ["/", "/cards/pibpc/"])
def test_inicio_contraste_do_menu_nos_pixels(abrir, rota, esquema):
    """As abas, os cartoes do painel aberto e o botao, nos dois temas: sobre a barra preta e o laranja-escuro."""
    with abrir(rota, largura=DESKTOP, color_scheme=esquema, reduced_motion="reduce") as pagina:
        pagina.locator(".nn-menu-grupo > summary", has_text="Histórias").click()
        medidas = _contraste_das_letras(
            pagina, ".nn-menu > a, .nn-menu-grupo > summary, .nn-menu-cartao-titulo, .nn-menu-cartao-texto, .nn-topo-botao, .nn-topo .nn-marca"
        )
    assert len(medidas) >= 9
    assert _reprovados(medidas) == {}, medidas


# --- placar, capitulos, menu lateral e folha ---

_EDITORIAL = """() => {
  const r = (e) => { const c = e.getBoundingClientRect(); return { x: c.left, y: c.top, r: c.right, b: c.bottom, w: c.width }; };
  const indice = document.querySelector('.nn-indice');
  const estilo = getComputedStyle(indice);
  const capitulo = document.querySelector('.nn-capitulo');
  const ce = getComputedStyle(capitulo);
  return {
    indice: { ...r(indice), opacidade: estilo.opacity, visibilidade: estilo.visibility, posicao: estilo.position, display: getComputedStyle(indice.querySelector('ol')).display },
    folha: r(document.querySelector('.nn-folha')), legenda: r(document.querySelector('.nn-folha > .nn-legenda')),
    atual: [...indice.querySelectorAll('a')].findIndex((a) => a.getAttribute('aria-current') === 'true'),
    capitulo: { borda: ce.borderTopWidth + ' ' + ce.borderLeftWidth, fundo: ce.backgroundColor, raio: ce.borderTopLeftRadius },
  };
}"""


def test_inicio_menu_lateral_aparece_depois_do_placar_e_marca_a_pergunta_em_leitura(abrir):
    with abrir("/", largura=DESKTOP, reduced_motion="reduce") as pagina:
        pagina.locator(".nn-placar").scroll_into_view_if_needed()
        m = pagina.evaluate(_EDITORIAL)
        assert m["indice"]["opacidade"] == "0" and m["indice"]["visibilidade"] == "hidden"  # o placar ainda na tela
        terceira = pagina.locator(".nn-capitulo").nth(2)
        pagina.evaluate("(y) => window.scrollTo(0, y)", terceira.evaluate("e => e.getBoundingClientRect().top + scrollY - 100"))
        pagina.wait_for_function("() => document.querySelector('.nn-indice').classList.contains('nn-indice-visivel')")
        pagina.wait_for_function("() => document.querySelectorAll('.nn-indice a')[2].getAttribute('aria-current') === 'true'")
        m = pagina.evaluate(_EDITORIAL)
        assert m["indice"]["opacidade"] == "1" and m["indice"]["visibilidade"] == "visible" and m["atual"] == 2
        assert pagina.locator(".nn-indice a[aria-current]").count() == 1
        # a legenda segue presa no alto da folha, a vista, depois de rolar ate a terceira pergunta
        assert -1 <= m["legenda"]["y"] <= 1 and m["legenda"]["b"] > 20
        # a folha sobrepoe a coluna do menu (margem de -28 px)
        assert m["folha"]["x"] < m["indice"]["r"] and abs((m["indice"]["r"] - m["folha"]["x"]) - 28) <= 1
        assert m["capitulo"] == {"borda": "0px 0px", "fundo": "rgba(0, 0, 0, 0)", "raio": "0px"}  # sem cartao
        assert _violacoes_do_axe(pagina) == []


def test_inicio_sem_javascript_o_menu_lateral_fica_a_vista_e_os_links_sao_ancoras(abrir):
    with abrir("/", largura=DESKTOP, java_script_enabled=False, reduced_motion="reduce") as pagina:
        m = pagina.evaluate(_EDITORIAL)
        assert m["indice"]["opacidade"] == "1" and m["indice"]["visibilidade"] == "visible" and m["atual"] == -1
        pagina.locator(".nn-indice a").nth(3).click()
        pagina.wait_for_url(re.compile(r"#q-trabalho$"))
        assert pagina.locator("#q-trabalho h2").evaluate("e => e.getBoundingClientRect().top") >= 0


def test_inicio_ancora_do_placar_nao_esconde_o_titulo_atras_da_legenda(abrir):
    with abrir("/", largura=DESKTOP, reduced_motion="reduce") as pagina:
        pagina.locator(".nn-placar-lista a[href='#q-escola']").click()
        pagina.wait_for_url(re.compile(r"#q-escola$"))
        legenda = pagina.locator(".nn-folha > .nn-legenda").evaluate("e => e.getBoundingClientRect().bottom")
        eyebrow = pagina.locator("#q-escola .nn-eyebrow").evaluate("e => e.getBoundingClientRect().top")
        assert eyebrow >= legenda, (eyebrow, legenda)


def test_inicio_capitulos_pares_trocam_o_grafico_de_lado(abrir):
    with abrir("/", largura=DESKTOP, reduced_motion="reduce") as pagina:
        lados = pagina.evaluate("""() => [...document.querySelectorAll('.nn-capitulo')].map((c) => {
          const g = c.querySelector('.nn-pergunta-corpo > .nn-grafico'), t = c.querySelector('.nn-pergunta-texto');
          return g.getBoundingClientRect().left < t.getBoundingClientRect().left ? 'grafico-texto' : 'texto-grafico'; })""")
    assert lados == ["grafico-texto", "texto-grafico"] * (len(lados) // 2) + ["grafico-texto"] * (len(lados) % 2)


@pytest.mark.parametrize("largura", [CELULAR, 1000, 1100])
def test_inicio_faixa_de_atalhos_ate_1100_px(abrir, largura):
    with abrir("/", largura=largura, reduced_motion="reduce") as pagina:
        pagina.evaluate("(y) => window.scrollTo(0, y)", pagina.locator("#q-idhm").evaluate("e => e.getBoundingClientRect().top + scrollY"))
        pagina.wait_for_function("() => document.querySelectorAll('.nn-indice a')[4].getAttribute('aria-current') === 'true'")
        m = pagina.evaluate(_EDITORIAL)
        assert m["indice"]["posicao"] == "sticky" and m["indice"]["display"] == "flex" and -1 <= m["indice"]["y"] <= 1
        assert m["indice"]["opacidade"] == "1" and m["indice"]["visibilidade"] == "visible"
        assert abs(m["folha"]["x"] - m["indice"]["x"]) <= 1  # a folha nao sobrepoe nada
        # a pilula ativa rola para dentro da vista da faixa
        pilula = pagina.locator(".nn-indice a[aria-current]").evaluate("a => { const r = a.getBoundingClientRect(); return [r.left, r.right]; }")
        pagina.wait_for_function("() => { const a = document.querySelector('.nn-indice a[aria-current]').getBoundingClientRect(); return a.left >= 0 && a.right <= innerWidth; }")
        assert pilula
        assert _estouro(pagina) == {}


@pytest.mark.parametrize("esquema", ["light", "dark"])
def test_inicio_axe_com_o_menu_lateral_e_a_faixa_a_vista(abrir, esquema):
    for largura in (DESKTOP, CELULAR):
        with abrir("/", largura=largura, color_scheme=esquema, reduced_motion="reduce") as pagina:
            pagina.locator("#q-escola").scroll_into_view_if_needed()
            pagina.wait_for_function("() => document.querySelector('.nn-indice').classList.contains('nn-indice-visivel')")
            assert _violacoes_do_axe(pagina) == [], (largura, esquema)


def test_inicio_ampliar_dentro_de_details_aberto_abre_o_grafico_certo(abrir):
    with abrir("/", largura=DESKTOP, reduced_motion="reduce") as pagina:
        mais = pagina.locator("#q-escola details.nn-mais-graficos")
        mais.locator("summary").click()
        botao = mais.locator("button.nn-ampliar").first
        alvo = botao.get_attribute("data-ampliado")
        titulo = pagina.locator(f"template#{alvo}").evaluate("t => t.content.querySelector('h3').textContent")
        botao.click()
        dialogo = pagina.locator("dialog.nn-modal:not(.nn-modal-autor)")
        assert dialogo.evaluate("d => d.open") and dialogo.locator(".nn-modal-corpo h3").inner_text() == titulo
        pagina.keyboard.press("Escape")
        assert pagina.evaluate("() => document.activeElement.getAttribute('data-ampliado')") == alvo


# --- voltar ao topo ---

_VOLTAR = """() => {
  const b = document.querySelector('.nn-voltar'), e = getComputedStyle(b), r = b.getBoundingClientRect();
  return { visivel: e.visibility === 'visible' && e.opacity === '1', w: r.width, direita: innerWidth - r.right, baixo: innerHeight - r.bottom,
           anel: getComputedStyle(b.querySelector('.nn-voltar-progresso')).strokeDashoffset, y: scrollY,
           href: b.getAttribute('href'), rotulo: b.getAttribute('aria-label') };
}"""


@pytest.mark.parametrize("largura, lado", [(DESKTOP, 56), (CELULAR, 48)])
def test_inicio_voltar_ao_topo_aparece_mostra_a_leitura_e_sobe(abrir, largura, lado):
    with abrir("/", largura=largura, altura=800, reduced_motion="reduce") as pagina:
        m = pagina.evaluate(_VOLTAR)
        assert not m["visivel"] and m["href"] == "#" and m["rotulo"] == "Voltar ao topo"
        pagina.evaluate("() => window.scrollTo(0, innerHeight * 0.5)")
        pagina.wait_for_timeout(100)
        assert not pagina.evaluate(_VOLTAR)["visivel"]  # antes de 80% da tela
        pagina.evaluate("() => window.scrollTo(0, innerHeight * 2)")
        pagina.wait_for_function("() => document.querySelector('.nn-voltar').classList.contains('nn-voltar-visivel')")
        m = pagina.evaluate(_VOLTAR)
        assert m["visivel"] and m["w"] == lado and m["direita"] > 0 and m["baixo"] > 0
        anel_antes = float(m["anel"].removesuffix("px"))
        pagina.evaluate("() => window.scrollTo(0, innerHeight * 4)")
        pagina.wait_for_timeout(100)
        assert float(pagina.evaluate(_VOLTAR)["anel"].removesuffix("px")) < anel_antes  # o anel acompanha a leitura
        pagina.locator(".nn-voltar").click()
        pagina.wait_for_function("() => scrollY === 0")  # movimento reduzido: na hora
        assert pagina.evaluate("() => document.activeElement.classList.contains('nn-marca')")
        # com o rodape na tela, o botao some e nao cobre os links dele
        pagina.locator("footer").scroll_into_view_if_needed()
        pagina.wait_for_function("() => document.querySelector('.nn-voltar').classList.contains('nn-voltar-no-rodape')")
        assert not pagina.evaluate(_VOLTAR)["visivel"]
        assert _estouro(pagina) == {}


def test_inicio_voltar_ao_topo_sem_javascript_e_um_link_sempre_a_vista(abrir):
    with abrir("/estados/", java_script_enabled=False, reduced_motion="reduce") as pagina:
        assert pagina.evaluate(_VOLTAR)["visivel"]
        pagina.evaluate("() => window.scrollTo(0, 1500)")
        pagina.locator(".nn-voltar").click()
        pagina.wait_for_function("() => scrollY === 0")


def test_inicio_voltar_ao_topo_tem_foco_visivel(abrir):
    with abrir("/", reduced_motion="reduce") as pagina:
        pagina.evaluate("() => window.scrollTo(0, innerHeight * 2)")
        pagina.wait_for_function("() => document.querySelector('.nn-voltar').classList.contains('nn-voltar-visivel')")
        # o foco chega pelo teclado (so a ultima entrada por tecla liga o :focus-visible). Nao se usa Shift+Tab e Tab: o
        # Shift+Tab leva o foco a outro elemento, a pagina rola ate ele e o botao, que some no topo e no rodape, nao
        # volta a ser alcancavel (falhava em uma execucao de cada tres).
        pagina.keyboard.press("Shift")
        pagina.locator(".nn-voltar").focus()
        assert pagina.evaluate("() => document.activeElement.classList.contains('nn-voltar')")
        contorno = pagina.locator(".nn-voltar").evaluate("b => { const e = getComputedStyle(b); return [e.outlineStyle, e.outlineWidth, e.outlineColor]; }")
        assert contorno == ["solid", "3px", "rgb(255, 255, 255)"]


def test_inicio_voltar_ao_topo_da_os_pulinhos_so_sem_reducao_de_movimento(abrir):
    with abrir("/", reduced_motion="no-preference") as pagina:
        pagina.evaluate("() => window.scrollTo({ top: innerHeight * 2, behavior: 'instant' })")
        pagina.wait_for_function("() => document.querySelector('.nn-voltar').classList.contains('nn-voltar-visivel')")
        animacao = pagina.locator(".nn-voltar-seta").evaluate("s => [getComputedStyle(s).animationName, getComputedStyle(s).animationIterationCount]")
        assert animacao == ["nn-pulinho", "2"]


# --- Como chegamos: abertura em duas colunas e linha do tempo de canto a canto ---


def test_historia_abertura_em_duas_colunas_no_computador_e_empilhada_no_celular(abrir):
    medida = """() => { const r = (s) => document.querySelector(s).getBoundingClientRect();
      return { resumo: r('.nn-hist-resumo'), grafico: r('.nn-hist-grafico'), pe: r('.nn-hist-pe') }; }"""
    with abrir("/como-chegamos/", largura=DESKTOP, reduced_motion="reduce") as pagina:
        m = pagina.evaluate(medida)
        assert m["resumo"]["right"] <= m["grafico"]["left"] and m["pe"]["top"] >= max(m["resumo"]["bottom"], m["grafico"]["bottom"])
    with abrir("/como-chegamos/", largura=CELULAR, reduced_motion="reduce") as pagina:
        m = pagina.evaluate(medida)
        assert m["resumo"]["bottom"] <= m["grafico"]["top"] and _estouro(pagina) == {}


@pytest.mark.parametrize("largura", [901, DESKTOP, LARGO])
def test_historia_linha_do_tempo_de_canto_a_canto_com_o_titulo_na_largura_padrao(abrir, largura):
    with abrir("/como-chegamos/", largura=largura, reduced_motion="reduce") as pagina:
        m = pagina.evaluate("""() => {
          const linha = document.querySelector('.nn-hist-linha').getBoundingClientRect();
          const titulo = document.querySelector('.nn-hist-linha > .nn-hist-secao');
          const fecho = document.querySelector('.nn-hist-fecho').getBoundingClientRect();
          const respiro = parseFloat(getComputedStyle(document.querySelector('.nn-hist-linha')).paddingLeft);
          return { x: linha.left, w: linha.width, janela: document.documentElement.clientWidth, respiro,
                   titulo: titulo.getBoundingClientRect().left + parseFloat(getComputedStyle(titulo).paddingLeft), margem: fecho.left,
                   setas: document.querySelectorAll('.nn-faixa-seta').length, mascara: getComputedStyle(document.querySelector('ol.nn-linha-tempo')).maskImage };
        }""")
        assert m["x"] == 0 and abs(m["w"] - m["janela"]) <= 1
        assert abs(m["respiro"] - min(72, max(24, 0.04 * largura))) <= 1
        # o titulo alinha com os blocos de papel (onde a margem padrao e menor que o respiro, fica no respiro)
        assert abs(m["titulo"] - max(m["margem"], m["respiro"])) <= 1, m
        assert m["setas"] == 2 and "linear-gradient" in m["mascara"]
        pagina.locator(".nn-faixa-seta").last.click()  # as setas continuam rolando a faixa
        pagina.wait_for_function("() => document.querySelector('ol.nn-linha-tempo').scrollLeft > 0")
        assert _estouro(pagina) == {}


def test_historia_linha_do_tempo_no_celular_nao_muda(abrir):
    with abrir("/como-chegamos/", largura=CELULAR, reduced_motion="reduce") as pagina:
        m = pagina.evaluate("""() => ({ linha: document.querySelector('.nn-hist-linha').getBoundingClientRect().width,
                                        main: document.querySelector('main').getBoundingClientRect().width })""")
        assert abs(m["linha"] - m["main"]) <= 1
