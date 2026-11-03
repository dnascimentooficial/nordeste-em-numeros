"""O site gerado, aberto no Chromium: acessibilidade (axe-core), largura no celular, sem JavaScript, movimento reduzido,
peso da primeira tela, o Explorar e o desenho que o site.js refaz no navegador.

Marcador `navegador`: `python -m pytest -m navegador testes/navegador`. As paginas sao servidas com a
Content-Security-Policy do .htaccess, entao script ou estilo inline apareceria como erro de console.
"""

import io
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from nordeste.caminhos import Caminhos
from nordeste.site.conteudo import carregar_conteudo
from nordeste.site.dados import DadosSite
from nordeste.site.explorar import INDICADORES_EXPLORAR, TERRITORIOS
from nordeste.site.gerar import vista_explorar_em_html

pytestmark = pytest.mark.navegador
RAIZ = Path(__file__).resolve().parents[2]
AXE = (Path(__file__).parent / "axe.min.js").read_text(encoding="utf-8")
GRAVES = ("serious", "critical")
CELULAR, DESKTOP = 390, 1280
LIMITE_DA_INICIAL = 500_000  # bytes, sem a foto da abertura


def _violacoes_do_axe(pagina) -> list[str]:
    """`regra (impacto): alvo, ...` de cada violacao grave da pagina aberta (axe-core, todas as regras padrao).

    As paginas inteiras abrem com reduced_motion="reduce": o axe mede o estado final. Com animacao, o que esta fora
    da tela fica com opacidade 0 (o axe nem confere) e o que esta entrando aparece pela metade (a legenda foi medida
    no meio do fade e reprovou o contraste no tema escuro, na CI e, de vez em quando, aqui).
    """
    pagina.evaluate(AXE)  # evaluate nao esta sujeito a CSP; o script tag estaria
    achadas = pagina.evaluate("axe.run(document).then(r => r.violations)")
    return [
        f"{v['id']} ({v['impact']}): " + ", ".join(" ".join(n["target"][0:1]) for n in v["nodes"][:4])
        for v in achadas if v["impact"] in GRAVES
    ]


# --- acessibilidade ---


@pytest.mark.parametrize("esquema", ["light", "dark"])
def test_axe_sem_violacao_grave(abrir, rotas, esquema):
    graves = {}
    for rota in rotas:
        with abrir(rota, color_scheme=esquema, reduced_motion="reduce") as pagina:
            achadas = _violacoes_do_axe(pagina)
            if achadas:
                graves[rota] = achadas
    assert graves == {}


def test_axe_com_o_modal_aberto_e_com_o_explorar_trocado(abrir):
    with abrir("/") as pagina:
        pagina.locator("button.nn-ampliar").first.click()
        assert pagina.locator("dialog.nn-modal:not(.nn-modal-autor)").evaluate("d => d.open")
        # a entrada do modal acabou: o contraste vale o do estado final, nao o de um quadro da animacao
        pagina.wait_for_function(
            "() => document.querySelector('dialog.nn-modal:not(.nn-modal-autor)').getAnimations({ subtree: true }).every((a) => a.playState === 'finished')"
        )
        assert _violacoes_do_axe(pagina) == []
    with abrir("/explorar/", reduced_motion="reduce") as pagina:
        pagina.select_option("#sel-expl-ind", "gini")
        pagina.select_option("#sel-expl-terr2", "BR")
        pagina.wait_for_function("() => document.getElementById('explorar-titulo').textContent.includes('×')")
        assert _violacoes_do_axe(pagina) == []


# --- largura no celular e no desktop (Foco 3) ---

_ESTOUROS = """() => {
  const largura = window.innerWidth;
  const fora = [];
  for (const e of document.body.querySelectorAll('*')) {
    const caixa = e.getBoundingClientRect();
    if (caixa.width === 0 || caixa.right <= largura + 1) continue;
    let contido = false;  // dentro de uma caixa que rola ou corta, o que passa dela nao alarga a pagina
    for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) {
      if (getComputedStyle(p).overflowX !== 'visible') { contido = true; break; }
    }
    if (!contido) fora.push(`${e.tagName.toLowerCase()}${e.id ? '#' + e.id : ''}.${e.className && e.className.baseVal === undefined ? e.className : ''} ate ${Math.round(caixa.right)}`);
  }
  return { largura, rolagem: document.documentElement.scrollWidth, fora: fora.slice(0, 6) };
}"""


def _estouro(pagina) -> dict:
    medidas = pagina.evaluate(_ESTOUROS)
    return {} if medidas["rolagem"] <= medidas["largura"] and not medidas["fora"] else medidas


@pytest.mark.parametrize("largura", [CELULAR, DESKTOP])
def test_sem_estouro_de_largura(abrir, rotas, largura):
    estourou = {}
    for rota in rotas:  # as seis paginas e cada card, inclusive /cards/renda_rs/ (R$ 2.554)
        with abrir(rota, largura=largura) as pagina:
            if medidas := _estouro(pagina):
                estourou[rota] = medidas
            if rota == "/estados/":  # cada vista do seletor, com os nomes e valores mais longos do ranking
                for opcao in pagina.locator("#sel-estado-ind option").evaluate_all("os => os.map(o => o.value)"):
                    pagina.select_option("#sel-estado-ind", opcao)
                    if medidas := _estouro(pagina):
                        estourou[f"{rota}?indicador={opcao}"] = medidas
    assert estourou == {}


@pytest.mark.parametrize("largura", [CELULAR, DESKTOP])
@pytest.mark.parametrize(
    "indicador, comparar",
    [("pib_pc", ""), ("renda", ""), ("renda", "CO"), ("matric", "SE_UF"), ("pop", "CO")],
)
def test_explorar_com_brasil_fora_do_nordeste_cabe_na_largura(abrir, largura, indicador, comparar):
    with abrir("/explorar/", largura=largura) as pagina:
        pagina.select_option("#sel-expl-ind", indicador)
        pagina.select_option("#sel-expl-terr", "BR_FORA_NE")
        if comparar:
            pagina.select_option("#sel-expl-terr2", comparar)
        pagina.wait_for_function("() => document.getElementById('explorar-titulo').textContent.includes('Brasil fora do Nordeste')")
        assert pagina.locator("#explorar-vista svg:visible").count() == 1
        assert _estouro(pagina) == {}
        pagina.locator("#explorar-vista svg:visible").hover(position={"x": largura / 2, "y": 60})  # a dica de valor tambem
        assert _estouro(pagina) == {}


# --- sem JavaScript, movimento reduzido e peso ---


def test_sem_javascript_mostra_numeros_e_graficos(abrir, relatorio_site):
    with abrir("/", java_script_enabled=False) as pagina:
        lide = pagina.locator("#resumo .nn-frase").first.inner_text()
        assert re.search(r"\d", lide) and "{" not in lide and "}" not in lide  # preenchido pela base, nunca o marcador
        assert pagina.locator("#resumo .nn-graf-largo svg").first.is_visible()
        assert pagina.locator("svg").count() >= 6
        # a faixa de numeros depende da condicao abertura_numeros na base viva: os dois estados sao corretos
        if "abertura_numeros" in relatorio_site.fechos_suprimidos:
            assert pagina.locator(".nn-numero-valor").count() == 0  # suprimida: sai inteira, sem numero solto
        else:
            assert pagina.locator(".nn-numero-valor").count() == 3 and pagina.locator(".nn-numero-valor:visible").count() == 3
        assert re.search(r"\d", pagina.locator(".nn-hero-intro").first.inner_text())  # o 1o paragrafo cita 2000 e nao tem condicao


_ANIMADOS = """() => {
  const achados = [];
  for (const e of document.querySelectorAll('*')) {
    for (const pseudo of [null, '::before', '::after']) {
      const estilo = getComputedStyle(e, pseudo);
      const duracoes = estilo.transitionDuration.split(',').map((d) => parseFloat(d));
      if (estilo.animationName !== 'none' || duracoes.some((d) => d > 0)) {
        achados.push(`${e.tagName.toLowerCase()}.${e.getAttribute('class') || ''}${pseudo || ''}`);
      }
    }
  }
  return achados;
}"""


def test_reduced_motion_sem_animacao(abrir, rotas):
    animados = {}
    for rota in rotas:
        with abrir(rota, reduced_motion="reduce") as pagina:
            if achados := pagina.evaluate(_ANIMADOS):
                animados[rota] = achados[:5]
    with abrir("/", reduced_motion="reduce") as pagina:  # o modal tem entrada animada: tambem sem animacao
        pagina.locator("button.nn-ampliar").first.click()
        assert pagina.evaluate(_ANIMADOS) == []
    assert animados == {}


def test_o_teste_de_movimento_enxerga_animacao_quando_ela_existe(abrir):
    with abrir("/", reduced_motion="no-preference") as pagina:  # controle: sem preferencia, a abertura anima
        assert any(a.startswith("span.") for a in pagina.evaluate(_ANIMADOS))


def test_peso_da_inicial(abrir):
    with abrir("/") as pagina:
        recursos = pagina.evaluate(
            """() => [performance.getEntriesByType('navigation')[0], ...performance.getEntriesByType('resource')]
                 .map((r) => ({ nome: r.name, bytes: r.transferSize }))"""
        )
    sem_a_foto = [r for r in recursos if "foto-abertura" not in r["nome"]]
    assert len(sem_a_foto) >= 5  # o HTML, o estilo, o script e as duas fontes
    assert all(r["bytes"] > 0 for r in sem_a_foto), sem_a_foto
    assert sum(r["bytes"] for r in sem_a_foto) <= LIMITE_DA_INICIAL, sorted(sem_a_foto, key=lambda r: -r["bytes"])[:3]


# --- abertura dividida com foto: texto sobre preto sólido, foto ao lado ou acima, sem sobreposição (Ruling S-AC) ---

_ABERTURA = """() => {
  const hero = document.querySelector('#topo');
  const caixa = hero.getBoundingClientRect();
  const pseudo = getComputedStyle(hero, '::before');
  const px = (v) => parseFloat(v);
  // a foto e o ::before, posicionado no padding box da abertura
  const foto = {
    x: caixa.left + hero.clientLeft + hero.clientWidth - px(pseudo.right) - px(pseudo.width),
    y: caixa.top + hero.clientTop + px(pseudo.top),
    w: px(pseudo.width),
    h: px(pseudo.height),
    imagem: pseudo.backgroundImage,
  };
  const alvos = [];
  for (const el of hero.querySelectorAll('.nn-eyebrow, .nn-hero-titulo > span, .nn-hero-intro')) {
    const intervalo = document.createRange();
    intervalo.selectNodeContents(el);
    alvos.push({
      nome: el.className || el.tagName.toLowerCase(),
      cor: getComputedStyle(el).color,
      caixas: [...intervalo.getClientRects()].map((c) => ({ x: c.left, y: c.top, w: c.width, h: c.height })),
    });
  }
  const titulo = hero.querySelector('.nn-hero-titulo');
  const linhas = [...titulo.querySelectorAll(':scope > span')].map((s) => {
    const intervalo = document.createRange();
    intervalo.selectNodeContents(s);
    return new Set([...intervalo.getClientRects()].map((c) => Math.round(c.top))).size;
  });
  const raio = parseFloat(getComputedStyle(hero).borderTopRightRadius);
  return { hero: { x: caixa.left, y: caixa.top, w: caixa.width, h: caixa.height }, foto, alvos, raio,
           titulo: { fonte: parseFloat(getComputedStyle(titulo).fontSize), linhas } };
}"""
_LIMITE_DO_CONTRASTE = 4.5
_LARGURAS_DA_ABERTURA = [CELULAR, 560, 561, 768, 900, 901, DESKTOP]  # os dois lados dos pontos de quebra (560 e 900 px)
# area estourada da foto (o sol): a camada de 15% leva o branco puro a rgb(218, 218, 218), luminancia 0,70, entao nenhum
# pixel da foto passa de 0,9 na tela; 0,55 na tela equivale a ~0,8 na foto. Com o sol no quadro (Rodada 3) eram 0,5% a
# 1,3% dos pixels da foto acima disso; sem ele, ~0,01%.
_LUMINANCIA_ESTOURADA = 0.55
_LIMITE_DA_AREA_ESTOURADA = 0.001  # fracao dos pixels da foto


def _luminancia_relativa(rgb: np.ndarray) -> np.ndarray:
    c = rgb / 255.0
    linear = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return linear @ np.array([0.2126, 0.7152, 0.0722])


def _contrastes(texto: np.ndarray, fundo: np.ndarray) -> np.ndarray:
    a, b = _luminancia_relativa(texto), _luminancia_relativa(fundo)
    return (np.maximum(a, b) + 0.05) / (np.minimum(a, b) + 0.05)


@pytest.mark.parametrize("largura", _LARGURAS_DA_ABERTURA)
def test_abertura_com_foto_texto_fora_da_foto_e_com_contraste_nos_pixels_reais(abrir, largura):
    with abrir("/", largura=largura, altura=900, reduced_motion="reduce") as pagina:
        assert "nn-hero-com-foto" in pagina.locator("#topo").get_attribute("class").split()
        medidas = pagina.evaluate(_ABERTURA)
        foto = medidas["foto"]
        url = re.search(r'url\("?([^")]+)"?\)', foto["imagem"])
        assert url and url[1].endswith("/foto-abertura.webp"), foto["imagem"]
        carregada = pagina.evaluate(
            "async (u) => { const i = new Image(); i.src = u; await i.decode(); return [i.naturalWidth, i.naturalHeight]; }", url[1]
        )
        assert carregada == [1024, 768]
        pagina.evaluate("() => document.querySelectorAll('#topo > *').forEach((e) => { e.style.visibility = 'hidden'; })")
        caixa = medidas["hero"]
        recorte = {"x": 0, "y": caixa["y"], "width": largura, "height": caixa["h"]}
        fundo = np.array(Image.open(io.BytesIO(pagina.screenshot(clip=recorte))).convert("RGB"), dtype=float)

    # a foto: do lado do texto (desktop) ou acima dele (ate 900 px), sempre dentro da abertura e inteira na caixa
    lado_a_lado = foto["w"] < caixa["w"] * 0.9
    assert (largura > 900) == lado_a_lado
    assert 0.45 <= foto["w"] / caixa["w"] <= 0.55 if lado_a_lado else foto["h"] / largura >= 0.3, foto
    assert foto["x"] >= caixa["x"] and foto["x"] + foto["w"] <= caixa["x"] + caixa["w"] + 1
    assert foto["y"] >= caixa["y"] and foto["y"] + foto["h"] <= caixa["y"] + caixa["h"] + 1
    # ela aparece, sem camada pesada: a metade longe da emenda (a direita, ou a de cima) e bem mais clara que o #080808
    fx, fy = int(foto["x"]), int(foto["y"] - caixa["y"])
    longe = fundo[fy:fy + int(foto["h"]), fx + int(foto["w"] / 2):fx + int(foto["w"])] if lado_a_lado \
        else fundo[fy:fy + int(foto["h"] / 2), fx:fx + int(foto["w"])]
    assert _luminancia_relativa(longe.reshape(-1, 3)).mean() > 0.1  # o preto liso tem 0,0024; a foto, uns 0,2
    # e a emenda funde no preto: a borda do lado do texto e preto liso
    emenda = fundo[fy:fy + int(foto["h"]), fx:fx + 2] if lado_a_lado else fundo[fy + int(foto["h"]) - 2:fy + int(foto["h"]), fx:fx + int(foto["w"])]
    assert np.abs(emenda - 8).max() <= 8, "a foto nao funde no preto na emenda"  # os 2 px da borda: preto, a menos de 3% da foto
    if lado_a_lado:
        # o sol fica fora do quadro: quase nenhum pixel estourado na foto (os cantos arredondados, fora da abertura, nao contam)
        regiao = fundo[fy:fy + int(foto["h"]), int(np.ceil(foto["x"])):int(foto["x"] + foto["w"])]
        alt, larg = regiao.shape[:2]
        yy, xx = np.mgrid[0:alt, 0:larg]
        r = medidas["raio"]
        dx, dy = xx - (larg - r), np.maximum(r - yy, yy - (alt - r))
        dentro = ~((dx > 0) & (dy > 0) & (dx ** 2 + dy ** 2 > (r - 1) ** 2))
        estourada = float((_luminancia_relativa(regiao[dentro]) > _LUMINANCIA_ESTOURADA).mean())
        assert estourada < _LIMITE_DA_AREA_ESTOURADA, f"{estourada:.2%} da foto estourada (o sol voltou ao quadro?)"
        # e o titulo volta a crescer: ~72 px a 1280 px, sem quebrar "O Nordeste esta" nem "do mesmo jeito?"
        assert medidas["titulo"]["linhas"][:2] == [1, 1], medidas["titulo"]
        if largura >= DESKTOP:
            assert medidas["titulo"]["fonte"] >= 70, medidas["titulo"]

    reprovados, piores = [], {}
    for n, alvo in enumerate(medidas["alvos"]):
        canais = [float(v) for v in re.findall(r"[\d.]+", alvo["cor"])]
        cor, alfa = np.array(canais[:3]), canais[3] if len(canais) > 3 else 1.0
        assert alvo["caixas"], alvo["nome"]
        if "nn-destaque" in alvo["nome"]:
            assert alvo["cor"] == "rgb(234, 46, 0)"  # sobre preto solido o laranja da identidade passa
        pior = 99.0
        for c in alvo["caixas"]:  # cada linha de texto
            # nenhum texto toca a foto
            assert c["x"] + c["w"] <= foto["x"] + 1 or c["x"] >= foto["x"] + foto["w"] - 1 \
                or c["y"] + c["h"] <= foto["y"] + 1 or c["y"] >= foto["y"] + foto["h"] - 1, (alvo["nome"], c, foto)
            # e o contraste vale o dos pixels de fato atras da linha
            xa, xb = max(0, int(c["x"])), min(largura, int(np.ceil(c["x"] + c["w"])))
            ya, yb = max(0, int(c["y"] - caixa["y"])), min(fundo.shape[0], int(np.ceil(c["y"] + c["h"] - caixa["y"])))
            atras = fundo[ya:yb, xa:xb].reshape(-1, 3)
            pior = min(pior, _contrastes(alfa * cor + (1 - alfa) * atras, atras).min())
        piores[f"{n}:{alvo['nome']}"] = round(float(pior), 2)
        if pior < _LIMITE_DO_CONTRASTE:
            reprovados.append(f"{alvo['nome']} ({alvo['cor']}): {pior:.2f}:1")
    assert len(piores) >= 5  # o selo, as linhas do titulo (com o destaque) e o paragrafo
    assert reprovados == [], piores



# --- pagina Como chegamos: papel envelhecido, serifada so nela, contraste nos pixels reais ---

HISTORIA = "/como-chegamos/"
SERIFADA = "EBGaramond.woff2"
# document.fonts.check() da true tambem quando nenhuma @font-face casa; aqui a face tem de existir e estar carregada
_SERIFADA_CARREGADA = "() => [...document.fonts].some((f) => f.family.replace(/\"/g, '') === 'EB Garamond' && f.status === 'loaded')"
# cada grupo: os textos que o teste mede (o no de texto herda a cor do elemento pai); todo grupo precisa aparecer
_TEXTOS_DA_HISTORIA = {
    "titulos": ".nn-hist-titulo, .nn-hist-secao, .nn-epoca-nome, .nn-epoca-titulo, .nn-epoca-conteudo h4",
    "datas": ".nn-epoca-periodo, .nn-epoca-data, .nn-marco-ano",
    "etiquetas": ".nn-tipo",
    "texto": ".nn-hist-subtitulo, .nn-hist-valor, .nn-hist-rotulo, .nn-hist-legenda, .nn-hist-nota, "
             ".nn-hist-texto, .nn-marco-titulo, .nn-epoca-resumo, .nn-epoca-texto, .nn-epoca-marcos, .nn-epoca-numeros, "
             ".nn-epoca-ficou, .nn-epoca-fontes, .nn-epoca-nav, .nn-epoca-credito, .nn-hist-fecho",
}
# na pagina, o texto fora do modal (coordenadas da pagina, para o print inteiro); com `modal`, so o texto do <dialog>
# aberto (coordenadas da janela, para o print da janela: com o modal aberto a pagina nao rola)
_NOS_DE_TEXTO = """({ grupos, modal }) => {
  const saida = {};
  const dialogo = document.querySelector('dialog[open]');
  for (const [grupo, seletor] of Object.entries(grupos)) {
    const nos = [];
    for (const raiz of document.querySelectorAll(seletor)) {
      const andar = document.createTreeWalker(raiz, NodeFilter.SHOW_TEXT);
      for (let no = andar.nextNode(); no; no = andar.nextNode()) {
        if (!no.textContent.trim()) continue;
        const pai = no.parentElement;
        if (pai.closest('svg')) continue;
        if (modal ? !(dialogo && dialogo.contains(pai)) : pai.closest('dialog')) continue;
        const intervalo = document.createRange();
        intervalo.selectNodeContents(no);
        const dx = modal ? 0 : scrollX, dy = modal ? 0 : scrollY;
        // o que uma caixa que rola (a faixa horizontal) corta nao esta na tela: fica fora da medida
        let corte = null;
        for (let e = pai.parentElement; e && e !== document.body; e = e.parentElement) {
          if (getComputedStyle(e).overflowX !== 'visible' && e.tagName !== 'DIALOG') { corte = e.getBoundingClientRect(); break; }
        }
        const dentro = (c) => !corte || (c.left >= corte.left - 1 && c.right <= corte.right + 1 && c.top >= corte.top - 1 && c.bottom <= corte.bottom + 1);
        const caixas = [...intervalo.getClientRects()].filter((c) => c.width > 0 && c.height > 0 && dentro(c))
          .map((c) => ({ x: c.left + dx, y: c.top + dy, w: c.width, h: c.height }));
        let fundo = 'transparent';  // a primeira cor de fundo opaca de baixo para cima (o selo, o papel ou o modal)
        for (let e = pai; e; e = e.parentElement) {
          const cor = getComputedStyle(e).backgroundColor;
          if (cor !== 'rgba(0, 0, 0, 0)' && !cor.endsWith('/ 0)')) { fundo = cor; break; }
        }
        const estilo = getComputedStyle(pai);
        if (caixas.length) nos.push({ nome: `${pai.tagName.toLowerCase()}.${pai.className}`, cor: estilo.color, caixas,
                                      fundo, pequeno: parseFloat(estilo.fontSize) < 24 });
      }
    }
    saida[grupo] = nos;
  }
  return saida;
}"""
# some todo texto da pagina (inclusive marcadores de lista e sublinhados), sem mexer em fundos, bordas e caixas
_ESCONDER_O_TEXTO = """() => {
  for (const e of document.querySelectorAll('main *, main')) {
    for (const [p, v] of [['color', 'transparent'], ['-webkit-text-fill-color', 'transparent'],
                          ['text-decoration-color', 'transparent'], ['text-shadow', 'none'], ['caret-color', 'transparent']]) {
      e.style.setProperty(p, v, 'important');
    }
  }
}"""


def _cor_computada(texto: str) -> tuple[np.ndarray, float]:
    """(rgb de 0 a 255, alfa) de uma cor do getComputedStyle: `rgb()`/`rgba()` ou, vinda de color-mix, `color(srgb r g b / a)`
    com os canais de 0 a 1."""
    canais = [float(v) for v in re.findall(r"[\d.]+(?:e-?\d+)?", texto)]
    escala = 255.0 if texto.startswith("color(srgb") else 1.0
    return np.array(canais[:3]) * escala, canais[3] if len(canais) > 3 else 1.0


# a cor do texto laranja e a do fundo dos carimbos e etiquetas, como o navegador as calcula (para comparar strings)
_CORES_DA_REGRA = """() => ({
  laranja: getComputedStyle(document.querySelector('.nn-epoca-periodo')).color,
  selo: getComputedStyle(document.querySelector('.nn-epoca-periodo')).backgroundColor,
})"""


def _reprovados_no_contraste(fundo: np.ndarray, grupos: dict, onde: str, piores: dict, regra: dict) -> list[str]:
    """Cada linha de texto contra o pior pixel do fundo atras dela (o print com o texto escondido). E a regra da
    estetica: texto laranja pequeno nunca direto sobre o papel, so sobre o fundo claro dos carimbos (--nn-hist-selo)."""
    alto, largo = fundo.shape[:2]
    reprovados = []
    for grupo, nos in grupos.items():
        for no in nos:
            if no["cor"] == regra["laranja"] and no["pequeno"] and no["fundo"] != regra["selo"]:
                reprovados.append(f"{onde} {grupo} {no['nome']}: laranja pequeno sobre {no['fundo']}, fora do selo")
            cor, alfa = _cor_computada(no["cor"])
            assert alfa > 0, no["nome"]
            for c in no["caixas"]:
                xa, xb = max(0, int(c["x"])), min(largo, int(np.ceil(c["x"] + c["w"])))
                ya, yb = max(0, int(c["y"])), min(alto, int(np.ceil(c["y"] + c["h"])))
                atras = fundo[ya:yb, xa:xb].reshape(-1, 3).astype(float)
                if not len(atras):
                    continue
                pior = float(_contrastes(alfa * cor + (1 - alfa) * atras, atras).min())
                piores[f"{onde} {grupo}"] = round(min(piores.get(f"{onde} {grupo}", 99.0), pior), 2)
                if pior < _LIMITE_DO_CONTRASTE:
                    reprovados.append(f"{onde} {grupo} {no['nome']} ({no['cor']}): {pior:.2f}:1")
    return reprovados


@pytest.mark.parametrize("esquema", ["light", "dark"])
@pytest.mark.parametrize("largura", [CELULAR, DESKTOP])
def test_historia_contraste_em_pixels(abrir, largura, esquema):
    """Titulos, datas dos marcos, etiquetas de tipo e texto: >= 4,5:1 no pior pixel do papel atras de cada linha, na
    pagina (com o site.js os artigos saem da lista) e no modal aberto da primeira e da ultima epoca."""
    vistos: dict[str, int] = {}
    reprovados, piores = [], {}
    with abrir(HISTORIA, largura=largura, color_scheme=esquema, reduced_motion="reduce") as pagina:
        pagina.evaluate("() => document.fonts.ready")
        assert pagina.evaluate(_SERIFADA_CARREGADA)
        regra = pagina.evaluate(_CORES_DA_REGRA)
        grupos = pagina.evaluate(_NOS_DE_TEXTO, {"grupos": _TEXTOS_DA_HISTORIA, "modal": False})
        pagina.evaluate(_ESCONDER_O_TEXTO)
        fundo = np.array(Image.open(io.BytesIO(pagina.screenshot(full_page=True))).convert("RGB"))
        reprovados += _reprovados_no_contraste(fundo, grupos, "pagina", piores, regra)
        for grupo, nos in grupos.items():
            vistos[grupo] = vistos.get(grupo, 0) + len(nos)
    for indice in (0, -1):
        with abrir(HISTORIA, largura=largura, color_scheme=esquema, reduced_motion="reduce") as pagina:
            pagina.evaluate("() => document.fonts.ready")
            cartoes = pagina.locator("button.nn-epoca-abrir")
            (cartoes.first if indice == 0 else cartoes.last).click()
            assert pagina.locator("dialog.nn-modal-historia").evaluate("d => d.open")
            # a janela cresce ate o modal caber inteiro nela: o print da janela pega todo o artigo
            for _ in range(3):
                altura = pagina.locator("dialog.nn-modal-historia").evaluate("d => d.scrollHeight") + 80
                pagina.set_viewport_size({"width": largura, "height": altura})
            grupos = pagina.evaluate(_NOS_DE_TEXTO, {"grupos": _TEXTOS_DA_HISTORIA, "modal": True})
            assert sum(len(n) for n in grupos.values()) > 20  # o artigo esta no modal, e o modal esta a vista
            pagina.evaluate(_ESCONDER_O_TEXTO)
            fundo = np.array(Image.open(io.BytesIO(pagina.screenshot())).convert("RGB"))
            reprovados += _reprovados_no_contraste(fundo, grupos, f"modal {indice}", piores, regra)
            for grupo, nos in grupos.items():
                vistos[grupo] = vistos.get(grupo, 0) + len(nos)
    assert all(vistos.get(g) for g in _TEXTOS_DA_HISTORIA), vistos  # todo grupo aparece na pagina ou no modal
    assert reprovados == [], (piores, reprovados[:8])


def test_historia_so_pede_a_serifada_nesta_pagina(abrir, rotas):
    """A @font-face da EB Garamond fica no estilo.css global, mas o navegador so baixa a fonte onde algo a usa."""
    assert HISTORIA in rotas
    pediram = {}
    for rota in rotas:
        with abrir(rota) as pagina:
            pagina.evaluate("() => document.fonts.ready")
            nomes = pagina.evaluate("() => performance.getEntriesByType('resource').map((r) => r.name)")
            pediram[rota] = [n for n in nomes if n.endswith(SERIFADA)]
            if rota == HISTORIA:
                assert pagina.evaluate(_SERIFADA_CARREGADA)
                familia = pagina.locator("h1.nn-hist-titulo").evaluate("e => getComputedStyle(e).fontFamily")
                assert familia.startswith('"EB Garamond"'), familia
    assert len(pediram.pop(HISTORIA)) == 1  # uma vez so: o preload e o uso pedem o mesmo arquivo (crossorigin)
    assert {r: p for r, p in pediram.items() if p} == {}


# --- pagina Como chegamos: a faixa arrastavel e o modal de cada epoca ---

MODAL_HISTORIA = "dialog.nn-modal-historia"
CARTAO = "button.nn-epoca-abrir"
LIMITE_DA_HISTORIA = 1_000_000  # bytes baixados ao abrir a pagina, sem abrir modal
# o estado que os testes conferem: modal aberto, epoca no modal, endereco, foco, onde estao os artigos e ids repetidos
_ESTADO_DA_HISTORIA = """() => {
  const dialogo = document.querySelector('dialog.nn-modal-historia');
  const artigo = dialogo.querySelector('.nn-epoca-conteudo');
  const ativo = document.activeElement;
  const ids = [...document.querySelectorAll('[id]')].map((e) => e.id);
  return {
    aberto: dialogo.open,
    epoca: artigo ? artigo.getAttribute('aria-labelledby').slice(2) : null,
    rotulo: dialogo.getAttribute('aria-labelledby'),
    hash: location.hash,
    foco: ativo && ativo.matches('button.nn-epoca-abrir') ? ativo.getAttribute('data-epoca') : (ativo && dialogo.contains(ativo) ? 'modal' : null),
    na_lista: [...document.querySelectorAll('li.nn-epoca')].filter((li) => li.querySelector(':scope > .nn-epoca-conteudo')).length,
    artigos: document.querySelectorAll('article.nn-epoca-conteudo').length,
    epocas: document.querySelectorAll('li.nn-epoca').length,
    repetidos: ids.filter((id, i) => ids.indexOf(id) !== i),
    historico: history.length,
  };
}"""
_EPOCAS_E_MARCOS = """() => [...document.querySelectorAll('li.nn-epoca')].map((li) => ({
  id: li.id, marcos: [...li.querySelectorAll('a.nn-marco')].map((a) => a.getAttribute('data-marco')),
}))"""


def _estado(pagina) -> dict:
    return pagina.evaluate(_ESTADO_DA_HISTORIA)


def _cartao(pagina, epoca: str):
    return pagina.locator(f'{CARTAO}[data-epoca="{epoca}"]')


_FECHOU = "() => { const d = document.querySelector('dialog.nn-modal-historia'); return !d.open && !d.querySelector('article') && location.hash === ''; }"


def _esperar_fechar(pagina) -> None:
    """O close() desliga o open na hora, mas o evento close (que devolve o artigo e o foco e acerta o endereco) vem numa
    tarefa depois; o history.back() do fechar tambem e assincrono."""
    pagina.wait_for_function(_FECHOU)


def _fechado_e_no_lugar(estado: dict, foco: str) -> None:
    """Modal fechado, endereco limpo, o foco no cartao e cada artigo de volta ao seu <li>, sem id repetido."""
    assert not estado["aberto"] and estado["epoca"] is None and estado["hash"] == "", estado
    assert estado["foco"] == foco, estado
    assert estado["na_lista"] == estado["artigos"] == estado["epocas"] and estado["repetidos"] == [], estado


def test_historia_arrasto_rola_e_nao_abre(abrir):
    """Foco 2: arrastar 200 px sobre um cartao rola a faixa e nao abre o modal; um clique que anda menos de 6 px abre."""
    with abrir(HISTORIA, reduced_motion="reduce") as pagina:
        faixa = pagina.locator("ol.nn-linha-tempo")
        medidas = faixa.evaluate("f => ({ x: getComputedStyle(f).overflowX, snap: getComputedStyle(f).scrollSnapType, rola: f.scrollWidth > f.clientWidth })")
        assert medidas == {"x": "auto", "snap": "x mandatory", "rola": True}, medidas
        alvo = _cartao(pagina, pagina.evaluate(_EPOCAS_E_MARCOS)[1]["id"])
        alvo.scroll_into_view_if_needed()
        caixa = alvo.bounding_box()
        x, y = caixa["x"] + caixa["width"] / 2, caixa["y"] + caixa["height"] / 2
        pagina.mouse.move(x, y)
        pagina.mouse.down()
        for passo in range(1, 21):
            pagina.mouse.move(x - 10 * passo, y)
        durante = faixa.evaluate("f => ({ rolagem: f.scrollLeft, classe: f.classList.contains('nn-arrastando') })")
        pagina.mouse.up()
        assert abs(durante["rolagem"] - 200) <= 2 and durante["classe"], durante
        estado = _estado(pagina)
        assert not estado["aberto"] and estado["hash"] == "" and estado["na_lista"] == estado["epocas"], estado
        assert faixa.evaluate("f => f.classList.contains('nn-arrastando')") is False
        assert faixa.evaluate("f => f.scrollLeft") > 0  # soltou e a faixa ficou rolada (presa num cartao pelo snap)
        # depois do arrasto, o proximo clique vale; um tremor de 3 px ainda e clique
        alvo = _cartao(pagina, pagina.evaluate(_EPOCAS_E_MARCOS)[2]["id"])
        alvo.scroll_into_view_if_needed()
        caixa = alvo.bounding_box()
        x, y = caixa["x"] + caixa["width"] / 2, caixa["y"] + caixa["height"] / 2
        pagina.mouse.move(x, y)
        pagina.mouse.down()
        pagina.mouse.move(x + 3, y)
        pagina.mouse.up()
        assert _estado(pagina)["aberto"]


def test_historia_botao_solto_fora_da_faixa_encerra_o_arrasto(abrir):
    """Apertar num cartao, sair da faixa (andando so 2 px de lado, sem captura ainda) e soltar fora: o arrasto acaba.
    Passar o mouse depois, sem botao, nao rola a faixa nem liga o estado de arrasto."""
    with abrir(HISTORIA, reduced_motion="reduce") as pagina:
        faixa = pagina.locator("ol.nn-linha-tempo")
        alvo = _cartao(pagina, pagina.evaluate(_EPOCAS_E_MARCOS)[1]["id"])
        alvo.scroll_into_view_if_needed()
        caixa = alvo.bounding_box()
        x, y = caixa["x"] + caixa["width"] / 2, caixa["y"] + caixa["height"] / 2
        # um ponto da janela fora da faixa: abaixo dela, se couber na janela; senao, acima (a altura da faixa e do que
        # vem antes dela muda com o conteudo, entao o ponto e medido, nao fixo)
        borda = faixa.bounding_box()
        altura = pagina.viewport_size["height"]
        y_fora = borda["y"] + borda["height"] + 20 if borda["y"] + borda["height"] + 20 < altura else borda["y"] - 20
        assert 0 < y_fora < altura and not borda["y"] <= y_fora <= borda["y"] + borda["height"], (y_fora, borda)
        pagina.mouse.move(x, y)
        pagina.mouse.down()
        pagina.mouse.move(x + 2, y_fora, steps=10)
        pagina.mouse.up()
        antes = faixa.evaluate("f => f.scrollLeft")
        pagina.mouse.move(x, y)
        pagina.mouse.move(x - 150, y, steps=15)
        depois = faixa.evaluate("f => ({ rolagem: f.scrollLeft, classe: f.classList.contains('nn-arrastando') })")
        assert depois == {"rolagem": antes, "classe": False}, depois
        assert not _estado(pagina)["aberto"]
        # e o botao solto fora com o arrasto ja em curso (mais de 6 px, com captura) tambem encerra
        pagina.mouse.move(x, y)
        pagina.mouse.down()
        pagina.mouse.move(x - 60, y_fora, steps=10)
        pagina.mouse.up()
        antes = faixa.evaluate("f => f.scrollLeft")
        pagina.mouse.move(x - 200, y, steps=15)
        depois = faixa.evaluate("f => ({ rolagem: f.scrollLeft, classe: f.classList.contains('nn-arrastando') })")
        assert depois == {"rolagem": antes, "classe": False}, depois


def test_historia_clique_abre_modal_e_esc_devolve_foco(abrir):
    """O cartao abre a epoca no modal (o artigo e movido, nao copiado); X, Esc e clique fora fecham, devolvem o artigo e
    o foco. Com o modal Ampliar ligado ao primeiro dialog da pagina, o fechar apagava o artigo."""
    with abrir(HISTORIA, reduced_motion="reduce") as pagina:
        epoca = pagina.evaluate(_EPOCAS_E_MARCOS)[1]["id"]
        for fechar in ("Escape", "x", "fora"):
            _cartao(pagina, epoca).click()
            estado = _estado(pagina)
            assert estado["aberto"] and estado["epoca"] == epoca and estado["hash"] == f"#{epoca}", estado
            assert estado["rotulo"] == f"t-{epoca}" and estado["foco"] == "modal", estado
            assert estado["na_lista"] == estado["epocas"] - 1 and estado["artigos"] == estado["epocas"], estado
            assert estado["repetidos"] == [], estado
            assert pagina.locator(f"{MODAL_HISTORIA} .nn-epoca-texto").is_visible()
            if fechar == "Escape":
                pagina.keyboard.press("Escape")
            elif fechar == "x":
                pagina.locator(f"{MODAL_HISTORIA} .nn-modal-fechar").click()
            else:
                caixa = pagina.locator(MODAL_HISTORIA).bounding_box()
                assert caixa["x"] > 20  # no desktop o modal nao ocupa a largura toda
                pagina.mouse.click(caixa["x"] / 2, 400)
            _esperar_fechar(pagina)
            _fechado_e_no_lugar(_estado(pagina), epoca)
            assert not pagina.locator("li.nn-epoca .nn-epoca-conteudo").first.is_visible()  # com JS, fora da lista


def test_historia_teclado_setas_e_enter(abrir):
    """Setas e Home/End movem o foco entre os cartoes; Enter abre; os botoes nas pontas rolam um cartao."""
    with abrir(HISTORIA, reduced_motion="reduce") as pagina:
        ids = [e["id"] for e in pagina.evaluate(_EPOCAS_E_MARCOS)]
        _cartao(pagina, ids[0]).focus()
        for tecla, esperado in (("ArrowRight", ids[1]), ("ArrowRight", ids[2]), ("ArrowLeft", ids[1]),
                                ("End", ids[-1]), ("Home", ids[0]), ("ArrowLeft", ids[0])):
            pagina.keyboard.press(tecla)
            assert _estado(pagina)["foco"] == esperado, tecla
        pagina.keyboard.press("End")
        assert pagina.locator("ol.nn-linha-tempo").evaluate("f => f.scrollLeft") > 0  # o cartao focado veio a vista
        pagina.keyboard.press("ArrowLeft")
        pagina.keyboard.press("Enter")
        estado = _estado(pagina)
        assert estado["aberto"] and estado["epoca"] == ids[-2], estado
        pagina.keyboard.press("Escape")
        _esperar_fechar(pagina)
        _fechado_e_no_lugar(_estado(pagina), ids[-2])
        # os botoes nas pontas: ‹ sem destino no comeco, › rola um cartao
        faixa = pagina.locator("ol.nn-linha-tempo")
        faixa.evaluate("f => { f.scrollLeft = 0; }")
        anterior, proximo = pagina.locator(".nn-faixa-anterior"), pagina.locator(".nn-faixa-proxima")
        assert anterior.is_visible() and proximo.is_visible()
        pagina.wait_for_function("() => document.querySelector('.nn-faixa-anterior').getAttribute('aria-disabled') === 'true'")
        passo = pagina.evaluate("""() => {
          const f = document.querySelector('ol.nn-linha-tempo');
          return f.querySelector('li.nn-epoca').getBoundingClientRect().width + parseFloat(getComputedStyle(f).columnGap);
        }""")
        proximo.click()
        pagina.wait_for_function("() => document.querySelector('ol.nn-linha-tempo').scrollLeft > 0")
        assert abs(faixa.evaluate("f => f.scrollLeft") - passo) <= 2
        assert anterior.get_attribute("aria-disabled") == "false"
        anterior.click()
        pagina.wait_for_function("() => document.querySelector('ol.nn-linha-tempo').scrollLeft === 0")


def test_historia_lista_vertical_setas_para_cima_e_para_baixo(abrir):
    """Ate 900 px a lista e vertical: alem de <- e ->, as setas para cima e para baixo passam o foco entre os cartoes."""
    with abrir(HISTORIA, largura=CELULAR, reduced_motion="reduce") as pagina:
        ids = [e["id"] for e in pagina.evaluate(_EPOCAS_E_MARCOS)]
        _cartao(pagina, ids[0]).focus()
        for tecla, esperado in (("ArrowDown", ids[1]), ("ArrowDown", ids[2]), ("ArrowUp", ids[1]),
                                ("ArrowRight", ids[2]), ("ArrowLeft", ids[1]), ("ArrowUp", ids[0]), ("ArrowUp", ids[0])):
            pagina.keyboard.press(tecla)
            assert _estado(pagina)["foco"] == esperado, tecla
    with abrir(HISTORIA, reduced_motion="reduce") as pagina:  # na faixa horizontal, para baixo continua rolando a pagina
        ids = [e["id"] for e in pagina.evaluate(_EPOCAS_E_MARCOS)]
        _cartao(pagina, ids[0]).focus()
        pagina.keyboard.press("ArrowDown")
        assert _estado(pagina)["foco"] == ids[0]


def test_historia_endereco_abre_epoca(abrir):
    """`#<id da epoca>` abre a epoca; `#<ano de um marco>` (ou `#m<ano>`) abre a epoca dele, rolada ate o marco."""
    with abrir(HISTORIA, java_script_enabled=False) as pagina:
        epocas = pagina.evaluate(_EPOCAS_E_MARCOS)
    ids = {e["id"] for e in epocas}
    epoca = epocas[1]
    marco = next(m for m in epocas[1]["marcos"] if m not in ids)  # o do dossie: 1763, a capital vai para o Rio
    with abrir(f"{HISTORIA}#{epoca['id']}", reduced_motion="reduce") as pagina:
        estado = _estado(pagina)
        assert estado["aberto"] and estado["epoca"] == epoca["id"] and estado["hash"] == f"#{epoca['id']}", estado
        assert pagina.locator(MODAL_HISTORIA).evaluate("d => d.scrollTop") == 0
    for endereco in (marco, f"m{marco}"):
        with abrir(f"{HISTORIA}#{endereco}", reduced_motion="reduce") as pagina:
            estado = _estado(pagina)
            assert estado["aberto"] and estado["epoca"] == epoca["id"], (endereco, estado)
            dentro = pagina.evaluate(f"""() => {{
              const d = document.querySelector('dialog.nn-modal-historia').getBoundingClientRect();
              const m = document.getElementById('m{marco}');
              const c = m.getBoundingClientRect();
              return {{ visivel: c.top >= d.top && c.top < d.bottom - 40, marcado: m.classList.contains('nn-marco-alvo'), rolou: document.querySelector('dialog.nn-modal-historia').scrollTop > 0 }};
            }}""")
            assert dentro == {"visivel": True, "marcado": True, "rolou": True}, (endereco, dentro)
            # fechar uma epoca aberta pelo endereco limpa o endereco sem sair da pagina
            pagina.keyboard.press("Escape")
            _esperar_fechar(pagina)
            _fechado_e_no_lugar(_estado(pagina), epoca["id"])
            assert pagina.url.endswith(HISTORIA)


@pytest.mark.parametrize("fragmento", ["9999", "abc", "m9999", "titulo-principal", "%E0%A4%A", "t-1530"])
def test_historia_endereco_invalido_nao_quebra(abrir, fragmento):
    """Foco 1: endereco que nao e epoca nem marco abre a pagina normal, sem modal e sem erro (o `with` confere)."""
    with abrir(f"{HISTORIA}#{fragmento}") as pagina:
        estado = _estado(pagina)
        assert not estado["aberto"] and estado["epoca"] is None and estado["na_lista"] == estado["epocas"], estado
        assert pagina.evaluate("() => document.documentElement.classList.contains('nn-js')")


def test_historia_proxima_tres_vezes_e_um_voltar_fecha(abrir):
    """Foco 3: o cartao abre com pushState, anterior/proxima trocam com replaceState; um voltar fecha o modal."""
    with abrir(HISTORIA, reduced_motion="reduce") as pagina:
        ids = [e["id"] for e in pagina.evaluate(_EPOCAS_E_MARCOS)]
        antes = _estado(pagina)["historico"]
        _cartao(pagina, ids[0]).click()
        for i in range(1, 4):
            pagina.locator(f"{MODAL_HISTORIA} a.nn-epoca-proxima").click()
            estado = _estado(pagina)
            assert estado["aberto"] and estado["epoca"] == ids[i] and estado["hash"] == f"#{ids[i]}", estado
            assert estado["rotulo"] == f"t-{ids[i]}" and estado["repetidos"] == [], estado
            assert estado["na_lista"] == estado["epocas"] - 1, estado  # a epoca anterior voltou ao seu lugar
            assert pagina.locator(MODAL_HISTORIA).evaluate("d => d.scrollTop") == 0
        pagina.locator(f"{MODAL_HISTORIA} a.nn-epoca-anterior").click()
        assert _estado(pagina)["epoca"] == ids[2]
        assert _estado(pagina)["historico"] == antes + 1  # uma entrada so: a do cartao
        pagina.go_back()
        _esperar_fechar(pagina)
        _fechado_e_no_lugar(_estado(pagina), ids[2])
        assert pagina.url.endswith(HISTORIA)
        pagina.go_forward()  # e o avancar reabre a epoca do endereco
        pagina.wait_for_function("() => document.querySelector('dialog.nn-modal-historia').open")
        assert _estado(pagina)["epoca"] == ids[2]


def test_historia_marco_abre_epoca_no_marco(abrir):
    with abrir(HISTORIA, reduced_motion="reduce") as pagina:
        epocas = pagina.evaluate(_EPOCAS_E_MARCOS)
        epoca = epocas[2]
        marco = epoca["marcos"][-1]
        link = pagina.locator(f'a.nn-marco[data-marco="{marco}"]')
        link.scroll_into_view_if_needed()
        link.click()
        estado = _estado(pagina)
        assert estado["aberto"] and estado["epoca"] == epoca["id"] and estado["hash"] == f"#m{marco}", estado
        assert pagina.evaluate(f"""() => {{
          const d = document.querySelector('dialog.nn-modal-historia').getBoundingClientRect();
          const c = document.getElementById('m{marco}').getBoundingClientRect();
          return c.top >= d.top && c.top < d.bottom - 40;
        }}""")
        pagina.keyboard.press("Escape")
        _esperar_fechar(pagina)
        _fechado_e_no_lugar(_estado(pagina), epoca["id"])  # o foco volta ao cartao da epoca do marco


def test_historia_sem_js_mostra_todas_as_epocas(abrir):
    with abrir(HISTORIA, java_script_enabled=False) as pagina:
        assert not pagina.evaluate("() => document.documentElement.classList.contains('nn-js')")
        artigos = pagina.locator("li.nn-epoca > article.nn-epoca-conteudo")
        assert artigos.count() == pagina.locator("li.nn-epoca").count() >= 2
        assert pagina.locator("li.nn-epoca > article.nn-epoca-conteudo:visible").count() == artigos.count()
        assert pagina.locator(".nn-epoca-texto:visible").count() == artigos.count()
        assert pagina.locator(".nn-faixa-anterior, .nn-faixa-proxima").count() == 0
        # sem JS a lista e vertical, uma epoca embaixo da outra
        assert pagina.locator("ol.nn-linha-tempo").evaluate("f => getComputedStyle(f).overflowX") == "visible"
        topos = pagina.locator("li.nn-epoca").evaluate_all("ls => ls.map((l) => l.getBoundingClientRect().top)")
        assert topos == sorted(topos) and len(set(topos)) == len(topos)


def test_historia_390_vertical_sem_estouro(abrir):
    with abrir(HISTORIA, largura=CELULAR, reduced_motion="reduce") as pagina:
        faixa = pagina.locator("ol.nn-linha-tempo")
        assert faixa.evaluate("f => getComputedStyle(f).overflowX") == "visible"
        caixas = pagina.locator("li.nn-epoca").evaluate_all("ls => ls.map((l) => { const c = l.getBoundingClientRect(); return [c.top, c.bottom]; })")
        assert all(b[0] >= a[1] for a, b in zip(caixas, caixas[1:]))  # uma embaixo da outra
        assert pagina.locator("li.nn-epoca .nn-epoca-conteudo:visible").count() == 0  # o conteudo vai para o modal
        assert not pagina.locator(".nn-faixa-anterior").is_visible() and not pagina.locator(".nn-faixa-proxima").is_visible()
        assert _estouro(pagina) == {}
        ids = [e["id"] for e in pagina.evaluate(_EPOCAS_E_MARCOS)]
        _cartao(pagina, ids[-1]).click()
        medidas = pagina.locator(MODAL_HISTORIA).evaluate("""d => {
          const c = d.getBoundingClientRect();
          const fora = [...d.querySelectorAll('*')].filter((e) => e.getBoundingClientRect().right > c.right + 1).map((e) => e.className);
          return { largura: c.width, altura: c.height, rola: d.scrollWidth > d.clientWidth, fora: fora.slice(0, 4) };
        }""")
        assert medidas == {"largura": CELULAR, "altura": 800, "rola": False, "fora": []}, medidas  # tela cheia


def test_historia_imagem_quebrada_mostra_alt(abrir):
    """Foco 5. A miniatura real da 1a epoca com imagem carrega, o cartao e medido, o src vira um arquivo que nao existe e
    o cartao tem de manter altura e largura (a caixa 21:9 vem do width/height e do aspect-ratio); no modal, a imagem do
    topo, com o src trocado do mesmo jeito, mostra o texto alternativo. O 404 provocado sai da lista de erros da pagina;
    qualquer outro erro conta."""
    quebrada = "/historia/nao-existe-de-proposito.webp"
    with abrir(HISTORIA, reduced_motion="reduce") as pagina:
        epoca = pagina.evaluate("() => document.querySelector('li.nn-epoca:has(img.nn-epoca-miniatura)').id")
        cartao = _cartao(pagina, epoca)
        cartao.scroll_into_view_if_needed()
        mini = pagina.locator(f"[id='{epoca}'] img.nn-epoca-miniatura")
        mini.evaluate("i => i.decode()")
        assert mini.evaluate("i => i.naturalWidth") > 0
        com_imagem = cartao.bounding_box()
        mini.evaluate("(i, q) => { i.src = q; }", quebrada)
        pagina.wait_for_function("(i) => i.complete && i.naturalWidth === 0", arg=mini.element_handle())
        quebrado = cartao.bounding_box()
        assert all(abs(com_imagem[k] - quebrado[k]) <= 1 for k in ("width", "height")), (com_imagem, quebrado)
        caixa = mini.bounding_box()
        assert caixa["height"] > 60 and abs(caixa["width"] * 9 / 21 - caixa["height"]) <= 1, caixa  # a caixa 21:9 fica
        # a imagem do topo do artigo (escondido ate o modal abrir) recebe o mesmo arquivo inexistente antes de carregar
        pagina.locator(f"[id='{epoca}'] img.nn-epoca-imagem").evaluate("(i, q) => { i.src = q; }", quebrada)
        cartao.click()
        imagem = pagina.locator(f"{MODAL_HISTORIA} img.nn-epoca-imagem")
        pagina.wait_for_function("() => { const i = document.querySelector('dialog img.nn-epoca-imagem'); return i.complete && i.naturalWidth === 0; }")
        caixa = imagem.bounding_box()
        assert caixa["width"] > 100 and abs(caixa["width"] * 9 / 21 - caixa["height"]) <= 1, caixa
        # o texto alternativo aparece: o recorte da imagem quebrada tem tinta (pixels bem mais escuros que o papel)
        recorte = np.array(Image.open(io.BytesIO(imagem.screenshot())).convert("L")).astype(float)
        assert (recorte < recorte.max() - 80).mean() > 0.01, "a imagem quebrada nao mostrou o texto alternativo"
        pagina.erros[:] = [e for e in pagina.erros if "nao-existe-de-proposito" not in e]


def test_historia_imagens_de_marco_so_com_o_modal_aberto(abrir):
    """As imagens dos marcos ficam no artigo, que so vai ao modal: com a pagina aberta nenhuma e baixada; aberta a
    epoca, a do marco carrega (lazy) quando chega perto da tela, com a caixa 21:9 do width/height."""
    with abrir(HISTORIA, reduced_motion="reduce") as pagina:
        fontes = pagina.evaluate("() => [...document.querySelectorAll('img.nn-marco-imagem')].map((i) => i.src)")
        assert fontes, "nenhum marco com imagem no historia.yaml"
        baixadas = lambda: {r for r in pagina.evaluate("() => performance.getEntriesByType('resource').map((r) => r.name)")}
        assert not set(fontes) & baixadas()
        epoca = pagina.evaluate("() => document.querySelector('img.nn-marco-imagem').closest('li.nn-epoca').id")
        _cartao(pagina, epoca).click()
        imagem = pagina.locator(f"{MODAL_HISTORIA} img.nn-marco-imagem").first
        imagem.scroll_into_view_if_needed()
        pagina.wait_for_function("(i) => i.complete && i.naturalWidth > 0", arg=imagem.element_handle())
        caixa = imagem.bounding_box()
        assert caixa["width"] > 100 and abs(caixa["width"] * 9 / 21 - caixa["height"]) <= 1, caixa
        assert imagem.evaluate("i => i.src") in baixadas()


def test_historia_peso_abaixo_de_1mb(abrir):
    with abrir(HISTORIA) as pagina:
        pagina.evaluate("() => document.fonts.ready")
        recursos = pagina.evaluate(
            """() => [performance.getEntriesByType('navigation')[0], ...performance.getEntriesByType('resource')]
                 .map((r) => ({ nome: r.name, bytes: r.transferSize }))"""
        )
        assert not _estado(pagina)["aberto"]
    assert len(recursos) >= 4 and all(r["bytes"] > 0 for r in recursos), recursos
    assert sum(r["bytes"] for r in recursos) <= LIMITE_DA_HISTORIA, sorted(recursos, key=lambda r: -r["bytes"])[:3]


@pytest.mark.parametrize("esquema", ["light", "dark"])
def test_axe_historia(abrir, esquema):
    with abrir(HISTORIA, color_scheme=esquema, reduced_motion="reduce") as pagina:
        assert _violacoes_do_axe(pagina) == []
        ids = [e["id"] for e in pagina.evaluate(_EPOCAS_E_MARCOS)]
        for epoca in (ids[0], ids[-1]):
            _cartao(pagina, epoca).click()
            assert _estado(pagina)["aberto"]
            assert _violacoes_do_axe(pagina) == [], epoca
            pagina.keyboard.press("Escape")
            _esperar_fechar(pagina)


# --- Explorar ---


def _pontos_do_destaque(pagina) -> list[list]:
    return pagina.evaluate(
        """() => {
          const linhas = JSON.parse(document.querySelector('#explorar-vista .nn-graf-largo svg').getAttribute('data-pontos'));
          return linhas.find((l) => l.destaque).pontos;
        }"""
    )


def test_explorar_troca_indicador_e_territorio(abrir, site_gerado):
    with abrir("/explorar/") as pagina:
        titulo_antes = pagina.locator("#explorar-titulo").inner_text()
        svg_antes = pagina.locator("#explorar-vista .nn-graf-largo svg").evaluate("s => s.outerHTML")
        assert "PIB per capita" in titulo_antes and "Nordeste" in titulo_antes
        pagina.select_option("#sel-expl-ind", "gini")
        pagina.select_option("#sel-expl-terr", "BA")
        pagina.wait_for_function("() => document.getElementById('explorar-titulo').textContent.startsWith('Índice de Gini: Bahia')")
        titulo = pagina.locator("#explorar-titulo").inner_text()
        assert titulo != titulo_antes and "Gini" in titulo and "Bahia" in titulo and "PIB" not in titulo
        svg = pagina.locator("#explorar-vista .nn-graf-largo svg").evaluate("s => s.outerHTML")
        assert svg != svg_antes
        esperado = json.loads((site_gerado / "explorar" / "dados" / "gini.json").read_text(encoding="utf-8"))["BA"]
        assert esperado and _pontos_do_destaque(pagina) == esperado  # o desenho vem dos pontos da base, sem retoque
        assert pagina.url.endswith("?indicador=gini&territorio=BA")  # o endereco guarda a escolha


# --- cards ---


def test_card_tem_link_de_download(abrir, rotas):
    cards = [r for r in rotas if r.startswith("/cards/") and r != "/cards/"]
    assert "/cards/renda_rs/" in cards
    for rota in cards:
        with abrir(rota) as pagina:
            link = pagina.locator("a.nn-baixar")
            assert link.count() == 1 and link.is_visible(), rota
            assert link.get_attribute("href") == rota.rstrip("/") + ".png", rota
            assert link.get_attribute("download") is not None, rota
            assert link.inner_text().strip(), rota


# --- o desenho que o site.js refaz no navegador e o do Python (Ruling S-T) ---


def _arvore(svg: str) -> tuple:
    """O SVG como arvore comparavel, sem data-* e sem os ids em si: (tag, atributos ordenados, texto, filhos, resto).

    Os ids do Python vem de um hash e os do navegador de um contador, entao cada id vira a ordem em que aparece e as
    referencias a ele (aria-labelledby, url(#...)) apontam para essa ordem: quem aponta para quem continua conferido.
    """
    raiz = ET.fromstring(svg)
    ids = {no.attrib["id"]: f"#{i}" for i, no in enumerate(n for n in raiz.iter() if "id" in n.attrib)}
    trocar = re.compile("|".join(map(re.escape, ids)) or r"(?!)")

    def ler(no):
        atributos = tuple(sorted(
            (chave, trocar.sub(lambda m: ids[m[0]], valor))
            for chave, valor in no.attrib.items() if chave != "id" and not chave.startswith("data-")
        ))
        return (no.tag.split("}")[-1], atributos, (no.text or "").strip(), tuple(ler(f) for f in no), (no.tail or "").strip())

    return ler(raiz)


def _primeira_diferenca(a: tuple, b: tuple, caminho: str = "svg") -> str | None:
    if a[:3] != b[:3] or a[4] != b[4]:
        return f"{caminho}: {a[:3]} != {b[:3]}"
    if len(a[3]) != len(b[3]):
        return f"{caminho}: {len(a[3])} filhos != {len(b[3])}"
    for i, (x, y) in enumerate(zip(a[3], b[3])):
        if diferenca := _primeira_diferenca(x, y, f"{caminho}/{x[0]}[{i}]"):
            return diferenca
    return None


_SERIALIZAR = """() => [...document.querySelectorAll('#explorar-vista .nn-graf-largo svg, #explorar-vista .nn-graf-estreito svg')]
  .map((s) => new XMLSerializer().serializeToString(s))"""


def test_explorar_redesenhado_no_navegador_igual_ao_do_python(abrir):
    dados = DadosSite.carregar(Caminhos(raiz=RAIZ))
    textos = carregar_conteudo(RAIZ / "metadados" / "site").textos
    diferentes, comparados, sem_grafico = [], 0, 0
    with abrir("/explorar/") as pagina:
        pagina.select_option("#sel-expl-ind", "gini")  # sai da vista inicial, que ja vem desenhada no HTML
        pagina.select_option("#sel-expl-terr", "BA")
        for indicador in INDICADORES_EXPLORAR:
            for territorio, _, _ in TERRITORIOS:
                pagina.select_option("#sel-expl-ind", indicador.chave)
                pagina.select_option("#sel-expl-terr", territorio)
                esperado_html = vista_explorar_em_html(dados, textos, indicador.chave, territorio)
                esperados = re.findall(r"<svg\b.*?</svg>", esperado_html, flags=re.S)
                pagina.wait_for_function(
                    "(t) => document.getElementById('explorar-titulo').textContent.includes(t) && !document.getElementById('explorar-vista').hasAttribute('aria-busy')",
                    arg=f"{indicador.nome}: {next(n for i, n, _ in TERRITORIOS if i == territorio)} (",
                )
                obtidos = pagina.evaluate(_SERIALIZAR)
                if not esperados:  # territorio sem dado: a vista e so o aviso, nos dois lados
                    sem_grafico += 1
                    if obtidos:
                        diferentes.append(f"{indicador.chave}/{territorio}: o Python nao desenha e o navegador desenhou")
                    continue
                comparados += 1
                if len(esperados) != 2 or len(obtidos) != 2:  # a vista tem sempre dois graficos: o largo e o estreito
                    diferentes.append(f"{indicador.chave}/{territorio}: {len(esperados)} graficos no Python e {len(obtidos)} no navegador")
                    continue
                for largura, (no_navegador, do_python) in zip(("largo", "estreito"), zip(obtidos, esperados)):
                    if diferenca := _primeira_diferenca(_arvore(no_navegador), _arvore(do_python)):
                        diferentes.append(f"{indicador.chave}/{territorio} ({largura}): {diferenca}")
    assert comparados >= 6 * 3 and sem_grafico >= 1  # a amostra e grande e inclui territorio sem dado
    assert diferentes == []


# --- pista de rolagem do mapa de calor no celular (Ruling S-T) ---


def test_mapa_de_calor_no_celular_avisa_que_rola_de_lado(abrir):
    frase = carregar_conteudo(RAIZ / "metadados" / "site").textos["estados"]["rolagem"]
    with abrir("/estados/", largura=CELULAR) as pagina:
        caixa = pagina.locator(".nn-vista:visible .nn-mapa-caixa")
        assert caixa.evaluate("c => c.scrollWidth > c.clientWidth")  # rola de verdade
        assert pagina.locator(".nn-vista:visible .nn-rolagem").inner_text().strip() == frase
        assert caixa.evaluate("c => getComputedStyle(c).maskImage") != "none"  # esmaece na borda direita
        caixa.evaluate("c => { c.scrollLeft = c.scrollWidth; }")
        pagina.wait_for_function("() => document.querySelector('.nn-vista:not([hidden]) .nn-mapa-caixa').classList.contains('nn-no-fim')")
        assert caixa.evaluate("c => getComputedStyle(c).maskImage") == "none"  # no fim, nada a esmaecer
        caixa.evaluate("c => { c.scrollLeft = 0; }")
        pagina.wait_for_function("() => !document.querySelector('.nn-vista:not([hidden]) .nn-mapa-caixa').classList.contains('nn-no-fim')")
    with abrir("/estados/", largura=DESKTOP) as pagina:  # no desktop o mapa cabe: sem frase e sem esmaecimento
        assert not pagina.locator(".nn-vista:visible .nn-rolagem").is_visible()
        assert pagina.locator(".nn-vista:visible .nn-mapa-caixa").evaluate("c => getComputedStyle(c).maskImage") == "none"
