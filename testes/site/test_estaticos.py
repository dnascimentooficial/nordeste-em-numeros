"""Estilo, script, fontes e .htaccess do site: identidade visual, Content-Security-Policy e movimento opcional."""

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from nordeste.caminhos import Caminhos
from nordeste.site import gerar, graficos
from nordeste.site.dados import DadosSite
from nordeste.site.formatacao import numero
from nordeste.site.gerar import gerar_site

from auxiliares import RAIZ, Arvore

SITE = "https://nordeste.dnascimento.com.br"
HTACCESS = [
    "RewriteEngine On",
    r"RewriteCond %{HTTP_HOST} !^nordeste\.dnascimento\.com\.br$ [NC]",
    "RewriteRule ^(.*)$ https://nordeste.dnascimento.com.br/$1 [R=301,L]",
    "RewriteCond %{HTTPS} off",
    "RewriteRule ^(.*)$ https://nordeste.dnascimento.com.br/$1 [R=301,L]",
    "Header always set Content-Security-Policy \"default-src 'self'; img-src 'self' data:; style-src 'self'; "
    "script-src 'self' https://cloud.umami.is; "
    "connect-src 'self' https://cloud.umami.is https://*.umami.is https://*.umami.dev; "
    "font-src 'self'; frame-ancestors 'none'; base-uri 'self'\"",
    'Header always set X-Content-Type-Options "nosniff"',
    'Header always set Referrer-Policy "strict-origin-when-cross-origin"',
    'Header always set X-Frame-Options "DENY"',
    'Header always set Strict-Transport-Security "max-age=31536000"',
    "AddDefaultCharset UTF-8",
    "AddCharset UTF-8 .css .js .json .csv .svg .txt",
    '<FilesMatch "\\.(html|css|js|json|csv)$">',  # sem cache longo: a Hostinger guardou um 404 do estilo.css
    'Header set Cache-Control "no-cache"',
    "</FilesMatch>",
    '<FilesMatch "\\.(png|webp|woff2)$">',
    'Header set Cache-Control "max-age=86400"',
    "</FilesMatch>",
]
CORES = ("#ea2e00", "#c42600", "#080808", "#f5f4ef", "#ffffff")
# elementos que carregam um recurso pela URL; <a> e so link (as fontes oficiais sao links e podem ser externos)
CARREGAM = {"link": "href", "script": "src", "img": "src", "source": "src", "iframe": "src", "video": "src",
            "audio": "src", "embed": "src", "object": "data", "image": "href", "use": "href"}
# o unico recurso de fora: o script da medicao de audiencia (gerar.MEDICAO), que a CSP libera pelo nome
SCRIPT_DA_MEDICAO = "https://cloud.umami.is/script.js"
NAMESPACE_SVG = "http://www.w3.org/2000/svg"  # nome, nao recurso: o site.js cria elementos SVG com ele
MOVIMENTO = re.compile(r"^(animation|transition)(-[a-z-]+)?$|^view-transition-name$|^scroll-behavior$")
SEM_REDUCAO = "@media (prefers-reduced-motion: no-preference)"


@pytest.fixture(scope="module")
def saida(tmp_path_factory) -> Path:
    destino = tmp_path_factory.mktemp("site") / "saida"
    gerar_site(Caminhos(raiz=RAIZ), destino, imagens=False)
    return destino


def _arquivos(saida: Path, extensao: str) -> list[Path]:
    return sorted(saida.rglob(f"*{extensao}"))


def _sem_comentarios(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _regras(css: str) -> list[tuple[tuple[str, ...], str]]:
    """(cabecalhos dos blocos que envolvem, declaracao) de cada declaracao do CSS; at-rules vazias como `@x { }`
    entram com declaracao vazia, para o teste ver onde ficam."""
    achadas, pilha, atual = [], [], ""
    for caractere in _sem_comentarios(css):
        if caractere == "{":
            pilha.append(" ".join(atual.split()))
            atual = ""
            achadas.append((tuple(pilha), ""))
        elif caractere == "}":
            if atual.strip():
                achadas.append((tuple(pilha), atual.strip()))
            pilha.pop()
            atual = ""
        elif caractere == ";":
            achadas.append((tuple(pilha), atual.strip()))
            atual = ""
        else:
            atual += caractere
    assert not pilha, "chaves desbalanceadas no CSS"
    return achadas


def _proprio(url: str) -> bool:
    return not re.match(r"^(?:[a-z][a-z0-9+.-]*:|//)", url, re.I) or url.startswith(SITE + "/")


# --- .htaccess ---


def test_htaccess_redireciona_e_tem_cabecalhos(saida):
    linhas = [l for l in (saida / ".htaccess").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert linhas == HTACCESS


# --- Content-Security-Policy: nada de fora e nada inline ---


def test_nenhum_recurso_externo(saida):
    paginas = _arquivos(saida, ".html")
    assert len(paginas) > 6
    for pagina in paginas:
        arvore = Arvore(pagina.read_text(encoding="utf-8"))
        for elemento in arvore.elementos:
            if elemento["tag"] == "a":
                continue
            for nome in {CARREGAM.get(elemento["tag"]), "src", "srcset", "poster"} - {None}:
                valor = elemento["attrs"].get(nome)
                if valor is None:
                    continue
                urls = [v.split()[0] for v in valor.split(",") if v.strip()] if nome == "srcset" else [valor]
                for url in urls:
                    if elemento["tag"] == "script" and url == SCRIPT_DA_MEDICAO:
                        continue
                    assert _proprio(url), (pagina.name, elemento["tag"], url)
        for estilo in arvore.achar("link", rel="stylesheet"):
            assert estilo["attrs"]["href"].startswith("/"), pagina
    for css in _arquivos(saida, ".css"):
        texto = _sem_comentarios(css.read_text(encoding="utf-8"))
        assert "@import" not in texto, css
        for url in re.findall(r"url\(\s*['\"]?([^'\")]+)", texto):
            assert url.startswith("/") or url.startswith("#"), (css.name, url)
    for js in _arquivos(saida, ".js"):
        texto = js.read_text(encoding="utf-8").replace(NAMESPACE_SVG, "")
        assert not re.search(r"https?://|//[a-z0-9-]+\.[a-z]", texto, re.I), js.name
        assert "import(" not in texto and "importScripts" not in texto, js.name


def test_sem_style_ou_script_inline(saida):
    for pagina in _arquivos(saida, ".html"):
        texto = pagina.read_text(encoding="utf-8")
        arvore = Arvore(texto)
        assert not arvore.achar("style"), pagina
        for elemento in arvore.elementos:
            assert "style" not in elemento["attrs"], (pagina, elemento["tag"])
            assert not [a for a in elemento["attrs"] if a.startswith("on")], (pagina, elemento["tag"])
            assert not (elemento["attrs"].get("href") or "").lower().startswith("javascript:"), pagina
        for script in arvore.achar("script"):
            if script["attrs"].get("type") == "application/ld+json":  # dado, nao e executado (Ruling S-D)
                continue
            src = script["attrs"].get("src", "")
            assert (src.startswith("/") or src == SCRIPT_DA_MEDICAO) and not Arvore.texto(script), pagina
    js = (saida / "site.js").read_text(encoding="utf-8")
    # o CSSOM (`elemento.style.propriedade = ...`, o anel do voltar ao topo) a CSP deixa; o atributo style, nao
    sem_cssom = re.sub(r"\.style\.[a-zA-Z]+ = ", "", js)
    assert re.findall(r"\.style\.([a-zA-Z]+) = ", js) and not re.findall(r"\.style\.(?:cssText|setProperty)", js)
    js = sem_cssom
    for proibido in (".style", "setAttribute('style'", 'setAttribute("style"', "cssText", "innerHTML", "outerHTML",
                     "insertAdjacentHTML", "document.write", "eval(", "new Function", "setTimeout('", 'setTimeout("'):
        assert proibido not in js, proibido


def test_paginas_usam_os_estaticos_gerados(saida):
    for pagina in _arquivos(saida, ".html"):
        arvore = Arvore(pagina.read_text(encoding="utf-8"))
        locais = [e["attrs"]["href"] for e in arvore.achar("link", rel="stylesheet")]
        locais += [e["attrs"]["src"] for e in arvore.achar("script") if e["attrs"].get("src", SCRIPT_DA_MEDICAO) != SCRIPT_DA_MEDICAO]
        for local in locais:  # cada estatico vem com ?v= e os 8 primeiros do sha256 do arquivo publicado
            caminho, _, versao = local.partition("?v=")
            assert versao == hashlib.sha256((saida / caminho.lstrip("/")).read_bytes()).hexdigest()[:8], local
        locais = [local.partition("?")[0] for local in locais]
        # a pagina Como chegamos tem ainda o nn-js.js, sem defer e antes do estilo (ver o teste abaixo)
        historia = pagina.parent.name in ("como-chegamos", "how-we-got-here")  # a mesma pagina em ingles
        esperados = ["/estilo.css", "/nn-js.js", "/site.js"] if historia else ["/estilo.css", "/site.js"]
        assert sorted(locais) == esperados, pagina
        for local in locais:
            assert (saida / local.lstrip("/")).is_file(), local


def test_nn_js_so_na_pagina_como_chegamos_e_antes_do_estilo(saida):
    """A classe nn-js tem de estar no <html> antes do primeiro desenho: o script e externo (a CSP nao admite inline),
    pequeno, sem defer nem async, e vem no <head> antes do estilo.css. As outras paginas nao o pedem."""
    script = (saida / "nn-js.js").read_text(encoding="utf-8")
    assert script.strip() == 'document.documentElement.classList.add("nn-js");'
    for pagina in _arquivos(saida, ".html"):
        texto = pagina.read_text(encoding="utf-8")
        pede = '<script src="/nn-js.js?v=' in texto
        assert pede == (pagina.parent.name in ("como-chegamos", "how-we-got-here")), pagina
        if pede:
            arvore = Arvore(texto)
            [tag] = [s for s in arvore.achar("script") if s["attrs"].get("src", "").startswith("/nn-js.js?v=")]
            assert "defer" not in tag["attrs"] and "async" not in tag["attrs"] and "type" not in tag["attrs"]
            assert texto.index('<script src="/nn-js.js?v=') < texto.index('<link rel="stylesheet"') < texto.index("</head>")
            assert texto.index("<head>") < texto.index('<script src="/nn-js.js?v=')
    # a classe nao vem mais do site.js (depois do primeiro desenho seria tarde): so o remove, quando nao ha <dialog>
    assert "classList.add('nn-js')" not in (saida / "site.js").read_text(encoding="utf-8")


# --- identidade visual ---


def test_cores_e_fontes_da_identidade(saida):
    css = (saida / "estilo.css").read_text(encoding="utf-8")
    for cor in CORES:
        assert cor in css.lower(), cor
    faces = re.findall(r"@font-face\s*\{([^}]*)\}", _sem_comentarios(css))
    familias = {}
    for face in faces:
        familia = re.search(r"font-family:\s*['\"]?([^;'\"]+)", face).group(1)
        familias[familia] = face
        assert re.search(r"font-display:\s*swap", face), familia
        urls = re.findall(r"url\(\s*['\"]?([^'\")]+)", face)
        assert urls and all(u.endswith(".woff2") for u in urls), familia
        for url in urls:
            fonte = saida / url.lstrip("/")
            assert fonte.read_bytes()[:4] == b"wOF2", url
            licenca = fonte.parent / "OFL.txt"
            assert "SIL Open Font License" in licenca.read_text(encoding="utf-8"), url
    assert set(familias) == {"Manrope", "DM Sans", "EB Garamond"}



# --- pagina Como chegamos: a serifada so nela ---

SERIFADA = "EB Garamond"
PASTA_SERIFADA = RAIZ / "src" / "nordeste" / "site" / "estaticos" / "fontes" / "eb-garamond"


def _seletores(cabecalho: str) -> list[str]:
    return [s.strip() for s in cabecalho.split(",") if s.strip()]


def _sob_a_historia(seletor: str) -> bool:
    """O seletor so casa dentro de `.nn-historia` (a classe do <main> da pagina Como chegamos).

    Os `:not(...)` saem antes: o que esta dentro deles exclui elementos, nao situa o seletor (`:not(.a .nn-historia) h1`
    casa em qualquer pagina). `.nn-historia-foo` nao conta: depois do nome vem algo que nao e parte de um identificador.
    """
    sem_negacao = re.sub(r":not\((?:[^()]|\([^()]*\))*\)", "", seletor)
    return bool(re.search(r"(^|[\s>+~])\.nn-historia(?![\w-])", sem_negacao))


@pytest.mark.parametrize("seletor, esperado", [
    (".nn-historia h1", True),
    (".nn-js .nn-historia .nn-faixa", True),
    (".nn-historia", True),
    (".nn-historia-foo h1", False),
    (".nn-historia-foo", False),
    (":not(.a .nn-historia) h1", False),
    (":not(.nn-historia) h1", False),
    ("h1:not(.a .nn-historia)", False),
    (".nn-historia h1:not(.x)", True),
    (".nn-historia :not(.a .b) h1", True),
])
def test_o_auxiliar_sob_a_historia_nao_deixa_passar_seletor_solto(seletor, esperado):
    assert _sob_a_historia(seletor) is esperado, seletor


def test_fonte_serifada_so_na_pagina_de_historia(saida):
    css = (saida / "estilo.css").read_text(encoding="utf-8")
    regras = _regras(css)
    faces = [d for c, d in regras if c and c[-1] == "@font-face" and d.startswith("font-family")]
    assert any(SERIFADA in d for d in faces)
    # variaveis que levam a serifada: valem como o nome dela
    variaveis = {d.split(":", 1)[0].strip() for c, d in regras if d.startswith("--") and SERIFADA in d}
    usos = []
    for cabecalhos, declaracao in regras:
        if not cabecalhos or cabecalhos[-1] == "@font-face" or ":" not in declaracao:
            continue
        propriedade, valor = (x.strip() for x in declaracao.split(":", 1))
        if SERIFADA in valor or any(f"var({v}" in valor for v in variaveis):
            usos.append((cabecalhos[-1], propriedade))
            for seletor in _seletores(cabecalhos[-1]):
                assert _sob_a_historia(seletor), (seletor, declaracao)
    assert any(p in ("font-family", "font") for _, p in usos), usos  # e ela e usada (titulos da pagina)
    assert {":root", "body", "html", ".nn"}.isdisjoint(s for c, _ in usos for s in _seletores(c))


def test_licenca_cita_as_tres_fontes_da_ofl():
    """O LICENSE.md diz que tudo fora das excecoes e CC BY 4.0: toda fonte com OFL.txt tem de estar entre as excecoes."""
    licenca = " ".join((RAIZ / "LICENSE.md").read_text(encoding="utf-8").split())
    fontes = sorted(p.parent.name for p in (RAIZ / "src" / "nordeste" / "site" / "estaticos" / "fontes").glob("*/OFL.txt"))
    assert fontes == ["dm-sans", "eb-garamond", "manrope"]
    assert "Fontes Manrope, DM Sans e EB Garamond (`src/nordeste/site/estaticos/fontes/`): SIL Open Font License 1.1" in licenca


def test_ebgaramond_local_com_licenca(saida):
    for pasta in (PASTA_SERIFADA, saida / "fontes" / "eb-garamond"):
        fonte, licenca = pasta / "EBGaramond.woff2", pasta / "OFL.txt"
        assert fonte.read_bytes()[:4] == b"wOF2", fonte
        assert 5_000 < fonte.stat().st_size < 80_000, fonte.stat().st_size  # so o subconjunto latino, um peso
        texto = licenca.read_text(encoding="utf-8")
        assert "SIL Open Font License" in texto and "EB Garamond" in texto, licenca
    css = _sem_comentarios((saida / "estilo.css").read_text(encoding="utf-8"))
    face = next(f for f in re.findall(r"@font-face\s*\{([^}]*)\}", css) if SERIFADA in f)
    assert re.findall(r"url\(\s*['\"]?([^'\")]+)", face) == ["/fontes/eb-garamond/EBGaramond.woff2"]
    assert re.search(r"font-weight:\s*500\s*;", face)  # um peso so: os titulos nao pedem negrito sintetico
    assert all(u.startswith("/") for u in re.findall(r"url\(\s*['\"]?([^'\")]+)", css))  # nada externo
    # as variaveis da pagina, nos dois temas
    raizes = [(c, d) for c, d in _regras(css) if c and c[-1] == ":root"]
    for nome in ("--nn-papel-antigo", "--nn-sepia"):
        assert any(len(c) == 1 and d.startswith(nome + ":") for c, d in raizes), nome
        assert any(c[0].startswith("@media (prefers-color-scheme: dark)") and d.startswith(nome + ":") for c, d in raizes), nome


def test_movimento_so_sem_reduced_motion(saida):
    css = (saida / "estilo.css").read_text(encoding="utf-8")
    regras = _regras(css)
    animadas = 0
    for cabecalhos, declaracao in regras:
        dentro = SEM_REDUCAO in cabecalhos
        bloco = cabecalhos[-1] if cabecalhos else ""
        if bloco.startswith(("@keyframes", "@view-transition")) or bloco.startswith("::view-transition"):
            assert dentro, bloco
        propriedade = declaracao.split(":", 1)[0].strip().lower() if ":" in declaracao else ""
        if MOVIMENTO.match(propriedade):
            assert dentro, (cabecalhos, declaracao)
            animadas += 1
    assert animadas, "o site tem movimento (com prefers-reduced-motion: no-preference)"
    assert any(c[-1] == "@view-transition" and d.replace(" ", "") == "navigation:auto" for c, d in regras)
    js = (saida / "site.js").read_text(encoding="utf-8")
    assert "matchMedia('(prefers-reduced-motion: no-preference)')" in js
    assert "IntersectionObserver" in js


# --- foto da abertura (Ruling S-U) e modal Ampliar (Ruling S-W) ---


def _luminancia(rgb: tuple[float, float, float]) -> float:
    canais = [c / 255 for c in rgb]
    lineares = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canais]
    return 0.2126 * lineares[0] + 0.7152 * lineares[1] + 0.0722 * lineares[2]


def _contraste(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    claro, escuro = sorted((_luminancia(a), _luminancia(b)), reverse=True)
    return (claro + 0.05) / (escuro + 0.05)


def _declaracoes(css: str, seletor: str) -> dict[str, str]:
    """propriedade -> valor das regras cujo seletor e exatamente `seletor` (sem at-rule em volta)."""
    achadas = {}
    for cabecalhos, declaracao in _regras(css):
        if cabecalhos == (seletor,) and ":" in declaracao:
            propriedade, valor = declaracao.split(":", 1)
            achadas[propriedade.strip()] = " ".join(valor.split())
    return achadas


def _regra_em(css: str, cabecalho: tuple[str, ...], seletor: str) -> dict[str, str]:
    """propriedade -> valor do `seletor` dentro das at-rules `cabecalho` (por exemplo, o @media dele)."""
    achadas = {}
    for cabecalhos, declaracao in _regras(css):
        if cabecalhos == (*cabecalho, seletor) and ":" in declaracao:
            propriedade, valor = declaracao.split(":", 1)
            achadas[propriedade.strip()] = " ".join(valor.split())
    return achadas


# a composicao da abertura (foto-abertura.webp, 1500x844): o Farol da Barra (torre e forte) vai de x 39,5% a 58,6% da
# largura e o sol fica em x ~95,7% (medidos na imagem original, 1672x941)


def test_css_da_abertura_em_secao_cheia_com_a_foto_inteira(saida):
    css = (saida / "estilo.css").read_text(encoding="utf-8")
    css = re.sub(r"\?v=[0-9a-f]{8}", "", css)  # as imagens vem com ?v= (conferido em test_imagens_do_css_versionadas)
    # a foto e o ::before (local: a CSP e default-src 'self'), a composicao inteira por baixo de um veu uniforme de 30%
    # (ate 40%, se o contraste pedir), sem degradê e sem o recorte da metade direita; nada de <img>
    foto = _declaracoes(css, ".nn-hero-com-foto::before")
    assert 'url("/foto-abertura.webp")' in foto["background-image"] and foto["background-size"].endswith("cover")
    assert foto["inset"] == "0" and "width" not in foto and "--nn-foto-fusao" not in foto["background-image"]
    camada = re.fullmatch(r'linear-gradient\(rgba\(8, 8, 8, ([0-9.]+)\), rgba\(8, 8, 8, ([0-9.]+)\)\), url\("/foto-abertura.webp"\)',
                          foto["background-image"])
    assert camada and camada[1] == camada[2] and 0.3 <= float(camada[1]) <= 0.4, foto["background-image"]
    assert "90deg" not in foto["background-image"] and "180deg" not in foto["background-image"]
    # o circulo decorativo se aposentou: nenhum ::after na abertura
    assert not [c for c, _ in _regras(css) if c and ".nn-hero" in c[-1] and "::after" in c[-1]]
    # secao cheia: na largura da tela, subindo por baixo do menu, com o texto na largura padrao
    hero = _declaracoes(css, ".nn-hero, .nn-capa")
    assert hero["width"] == "100vw" and hero["margin-left"] == "calc(50% - 50vw)", hero
    assert hero["margin-top"] == "calc(-1 * (var(--nn-topo-alt) + 28px))" and hero["padding-inline"] == "var(--nn-borda-cheia)"
    assert re.search(r"body \{[^}]*overflow-x: clip", css)
    # o titulo com sombra difusa, o destaque no laranja claro com sombra mais forte e o paragrafo na caixa de vidro
    assert "text-shadow" in _declaracoes(css, ".nn-hero-com-foto .nn-hero-titulo")
    destaque = _declaracoes(css, ".nn-hero-com-foto .nn-hero-titulo .nn-destaque")
    assert destaque["color"].startswith("#ff5a1f") and destaque["text-shadow"].count("rgba(0, 0, 0,") >= 2
    vidro = _declaracoes(css, ".nn .nn-hero-com-foto .nn-hero-intro")
    assert vidro["background"] == "rgba(8, 8, 8, 0.42)" and vidro["backdrop-filter"] == "blur(3px)"
    # a foto so existe por CSS e movimento so sem reducao
    assert not any("nn-hero-com-foto" in cabecalhos[-1] and "animation" in d for cabecalhos, d in _regras(css) if cabecalhos)


def test_css_das_capas_tem_uma_classe_por_imagem_do_gerador(saida):
    """Cada imagem de CAPAS (e a foto da abertura) tem a sua classe no estilo.css, com o arquivo certo no fundo; o
    degradê escuro fica a esquerda no computador e sobe de baixo no celular."""
    css = (saida / "estilo.css").read_text(encoding="utf-8")
    css = re.sub(r"\?v=[0-9a-f]{8}", "", css)  # as imagens vem com ?v= (conferido em test_imagens_do_css_versionadas)
    for arquivo in [a for a in gerar.CAPAS.values() if a]:
        regra = _declaracoes(css, "." + gerar.classe_da_capa(arquivo))
        assert regra.get("--nn-capa-foto") == f'url("/historia/{arquivo}")', arquivo
        assert (gerar.PASTA_ESTATICOS / "historia" / arquivo).is_file(), arquivo
    assert _declaracoes(css, "." + gerar.CLASSE_DA_CAPA_DA_FOTO)["--nn-capa-foto"] == 'url("/foto-abertura.webp")'
    capa = _declaracoes(css, ".nn-capa")
    assert capa["--nn-capa-veu"].startswith("linear-gradient(90deg, #080808 0%")
    assert capa["background-image"] == "var(--nn-capa-veu), var(--nn-capa-base), var(--nn-capa-foto, none)"
    assert _regra_em(css, ("@media (max-width: 1099px)",), ".nn-capa")["--nn-capa-veu"].startswith("linear-gradient(0deg, #080808")


def test_modal_do_css_e_as_cores_da_faixa(saida):
    css = (saida / "estilo.css").read_text(encoding="utf-8")
    modal = _declaracoes(css, ".nn-modal")
    assert modal["padding"] == "0" and modal["background"] == "var(--nn-painel)"
    cheia = [(c, d) for c, d in _regras(css) if "max-width: 560px" in c[0] and c[-1] == ".nn-modal" and d.startswith("width")]
    assert cheia and cheia[0][1] == "width: 100vw"  # no celular o modal ocupa a tela toda
    assert any(c[-1] == ".nn-modal-gire" and d == "display: block" and "orientation: portrait" in c[0] for c, d in _regras(css))
    assert _declaracoes(css, ".nn-faixa-abertura")["background"] == "var(--nn-papel)"
    # a abertura do modal anima so sem reducao de movimento (test_movimento_so_sem_reduced_motion confere o resto)
    assert any(SEM_REDUCAO in c and c[-1].startswith(".nn-modal") and d.startswith("animation") for c, d in _regras(css))


def test_texto_branco_pequeno_so_sobre_o_laranja_escuro(saida):
    """Ruling S-S: #ea2e00 com texto branco da 4,3:1; aba ativa, botao pressionado e Baixar usam #c42600 (>= 4,5:1)."""
    css = (saida / "estilo.css").read_text(encoding="utf-8")
    assert _contraste((255, 255, 255), (0xEA, 0x2E, 0x00)) < 4.5 <= _contraste((255, 255, 255), (0xC4, 0x26, 0x00))
    assert re.search(r"--nn-laranja-escuro:\s*#c42600", css)
    for seletor in ('.nn-botao[aria-pressed="true"]', ".nn .nn-baixar", ".nn .nn-topo-botao", ".nn .nn-saidas .nn-saida-card"):
        assert _declaracoes(css, seletor)["background"] == "var(--nn-laranja-escuro)", seletor
    grupos: dict[tuple, dict[str, str]] = {}
    for cabecalhos, declaracao in _regras(css):
        if ":" in declaracao:
            propriedade, valor = declaracao.split(":", 1)
            grupos.setdefault(cabecalhos, {})[propriedade.strip()] = " ".join(valor.split())
    vivos = ("var(--nn-laranja)", "#ea2e00")
    # o voltar ao topo e o unico no laranja vivo: nao tem texto, so o icone (grafico pede 3:1, e o branco da 4,3:1)
    assert [c[-1] for c, g in grupos.items() if g.get("background") in vivos and g.get("color") == "var(--nn-branco)"] == [".nn-voltar"]


def test_modal_reserva_o_espaco_da_barra_e_o_zoom_so_com_ponteiro_fino(saida):
    """Ruling S-Z: com o modal aberto a barra de rolagem some e o espaco dela fica; cursor zoom-in so com mouse."""
    css = (saida / "estilo.css").read_text(encoding="utf-8")
    aberto = _declaracoes(css, "html:has(.nn-modal[open])")
    assert aberto["overflow"] == "hidden" and aberto["scrollbar-gutter"] == "stable"
    cursores = [c for c, d in _regras(css) if d.startswith("cursor: zoom-in")]
    assert cursores and all("@media (pointer: fine)" in c[0] and c[-1] == ".nn-clicavel" for c in cursores)


def test_mapa_de_calor_avisa_a_rolagem_so_onde_ele_rola(saida):
    css = (saida / "estilo.css").read_text(encoding="utf-8")
    assert _declaracoes(css, ".nn-rolagem")["display"] == "none"
    estreito = [(c, d) for c, d in _regras(css) if c[0] == "@media (max-width: 640px)"]
    assert (("@media (max-width: 640px)", ".nn-rolagem"), "display: block") in estreito
    assert any(c[-1] == ".nn-mapa-caixa" and d.startswith("mask-image: linear-gradient(to right") for c, d in estreito)
    assert any(c[-1] == ".nn-mapa-caixa.nn-no-fim" and d == "mask-image: none" for c, d in estreito)
    assert _declaracoes(css, ".nn-mapa")["min-width"] == "560px"  # abaixo de ~640 px ele rola


# --- o desenho do site.js segue o do Python ---


def test_constantes_do_desenho_iguais_no_script(saida):
    js = (saida / "site.js").read_text(encoding="utf-8")
    for nome in ("ANO_INICIAL", "ANO_FINAL", "LARGURA_CARACTERE", "AFASTAMENTO_ROTULOS", "LARGURA_ESTREITA"):
        achado = re.search(rf"\b{nome} = ([0-9.]+)", js)
        assert achado and float(achado.group(1)) == getattr(graficos, nome), nome


def test_explorar_tem_os_ganchos_do_script(saida):
    arvore = Arvore((saida / "explorar" / "index.html").read_text(encoding="utf-8"))
    cartao = arvore.achar("article", id="explorar-grafico")[0]["attrs"]
    dados = DadosSite.carregar(Caminhos(raiz=RAIZ))
    faixas = json.loads(cartao["data-governos"])
    assert faixas == json.loads(graficos.faixas_em_json(dados.governos))
    assert faixas and all(isinstance(n, str) and i < f and isinstance(x, bool) for n, i, f, x in faixas)
    assert [i for _, i, _, _ in faixas] == sorted(i for _, i, _, _ in faixas)
    assert cartao["data-sem-periodo"] and cartao["data-erro"] and cartao["data-tabela"]
    zoom = arvore.achar("div", id="explorar-zoom")[0]["attrs"]
    assert "hidden" in zoom  # sem JavaScript o painel de zoom nao aparece; o site.js monta os controles
    for texto in ("data-de", "data-ate", "data-inicio", "data-fim", "data-ampliar", "data-todo", "aria-label"):
        assert zoom[texto], texto
    for id_ in ("sel-expl-terr", "sel-expl-terr2"):
        assert all(o["attrs"].get("data-etiqueta") for o in _opcoes(arvore, id_) if o["attrs"]["value"])


def _opcoes(arvore: Arvore, id_select: str) -> list[dict]:
    """As <option> do <select> de id dado, na ordem."""
    i = arvore.elementos.index(arvore.achar("select", id=id_select)[0])
    opcoes = []
    for elemento in arvore.elementos[i + 1:]:
        if elemento["tag"] != "option":
            break
        opcoes.append(elemento)
    return opcoes


@pytest.mark.skipif(shutil.which("node") is None, reason="sem Node.js para rodar o site.js")
def test_numeros_do_script_iguais_aos_do_python(saida):
    casos = [(43.25, 1), (2.5, 0), (3.5, 0), (-0.04, 1), (1234567.891, 2), (0.125, 2), (2.675, 2), (25000, 0),
             (0.7125, 3), (99.95, 1), (-12.25, 1), (1e-9, 0), (186521.5, 0)]
    programa = (
        "const NN = require(process.argv[1]);"
        f"const casos = {json.dumps(casos)};"
        "console.log(JSON.stringify(casos.map(([v, c]) => NN.numero(v, c))));"
    )
    feito = subprocess.run(["node", "-e", programa, str(saida / "site.js")], capture_output=True, text=True, check=True)
    assert json.loads(feito.stdout) == [numero(v, c) for v, c in casos]


def test_imagens_do_css_versionadas(saida):
    """Cada imagem que o estilo.css publicado pede leva ?v= com o sha256 do arquivo: trocar a foto da abertura sem trocar
    o nome nao pode deixar o navegador com a antiga (cache de um dia das imagens). As fontes ficam sem ?v= (preload)."""
    css = (saida / "estilo.css").read_text(encoding="utf-8")
    imagens = re.findall(r'url\("/([^"]+\.(?:webp|png|jpe?g)[^"]*)"\)', css)
    assert imagens and any(i.startswith("foto-abertura.webp") for i in imagens)
    for endereco in imagens:
        caminho, _, versao = endereco.partition("?v=")
        assert versao == hashlib.sha256((saida / caminho).read_bytes()).hexdigest()[:8], endereco
    assert re.findall(r'url\("/fontes/[^"?]+\.woff2"\)', css)
