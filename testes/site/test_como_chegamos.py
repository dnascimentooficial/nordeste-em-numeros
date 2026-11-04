"""Pagina "Como chegamos ate aqui": gerada do historia.yaml (de teste) e dos censos, com a abertura, a linha do tempo,
o conteudo de cada modal no HTML, o menu, o OpenGraph e os creditos das imagens em Sobre."""

import json
import re
import shutil
from pathlib import Path

import pytest
import yaml
from PIL import Image

from nordeste.caminhos import Caminhos
from nordeste.cli import main
from nordeste.site import gerar
from nordeste.site.conteudo import ErroConteudo
from nordeste.site.gerar import RelatorioSite, gerar_site
from nordeste.site.historia import TIPOS

from auxiliares import Arvore, copiar_base, dialogos_da_pagina, imagens_da_pagina

SITE = "https://nordeste.dnascimento.com.br"
PAGINA = "como-chegamos/index.html"
# 1872 e 2022 com os valores do dossie (46,7% e 26,9%); 1950 so para a serie ter um ponto no meio
CENSOS = (
    "ano,populacao_nordeste,populacao_brasil,fonte\n"
    "1872,4638560,9930478,Censo de teste A\n"
    "1950,17973413,51944397,Censo de teste B\n"
    "2022,54658515,203080756,Censo de teste C\n"
)
IMAGENS = (
    {"licenca": "dominio-publico", "url": None, "rotulo": "domínio público"},
    {"licenca": "cc-by", "url": "https://commons.wikimedia.org/wiki/File:Teste.jpg", "rotulo": "CC BY"},
    {"licenca": "ilustracao-do-autor", "url": None, "rotulo": "ilustração do autor"},
)
MEDIDAS_DA_EPOCA = (420, 180)  # 21:9, gravadas no width e no height do HTML
MEDIDAS_DO_MARCO = (210, 90)
MEDIDAS_DO_CARTAO = (140, 60)  # a miniatura do cartao: arquivo proprio, <epoca>-cartao.webp
# imagem de marco so nos marcos A das epocas 0 (dominio publico) e 1 (CC BY, com url); os outros ficam so com texto
IMAGENS_DE_MARCO = {0: IMAGENS[0], 1: IMAGENS[1]}


def _epoca(i: int, com_imagem: bool = True) -> dict:
    inicio = 1600 + 100 * i
    epoca = {
        "id": str(inicio),
        "inicio": inicio,
        "fim": inicio + 100,
        "nome": f"Época de teste {i}",
        "resumo": f"Resumo da época {i}.",
        "texto": " ".join([f"palavra{i}"] * 200),
        "marcos": [
            {"ano": inicio + 10, "titulo": f"Marco A{i}", "texto": f"Texto do marco A{i}."},
            {"ano": inicio + 50, "titulo": f"Marco B{i}", "texto": f"Texto do marco B{i}."},
        ],
        "numeros": [
            {"valor": f"{i + 1}0 engenhos", "legenda": f"Legenda oficial {i}", "tipo": "oficial", "fonte": f"IBGE, tabela {i}"},
            {"valor": f"{i + 2} mil", "legenda": f"Legenda historiador {i}", "tipo": "historiador", "fonte": f"Autor {i}, Obra {i}, p. 1{i}"},
        ],
        "o_que_ficou": f"O que ficou da época {i}.",
        "fontes": [{"texto": f"Obra impressa {i}"}, {"texto": f"Obra on-line {i}", "url": f"https://exemplo.org/obra-{i}"}],
    }
    if com_imagem:
        imagem = IMAGENS[i % len(IMAGENS)]
        epoca["imagem"] = {
            "arquivo": f"epoca-{inicio}.webp", "titulo": f"Título da imagem {i}", "autor": f"Autor da imagem {i}",
            "data": f"{inicio + 40}", "licenca": imagem["licenca"], "alt": f"Cena da época {i}", "url": imagem["url"],
        }
        if i in IMAGENS_DE_MARCO:
            licenca = IMAGENS_DE_MARCO[i]
            epoca["marcos"][0]["imagem"] = {
                "arquivo": f"marco-{inicio + 10}.webp", "titulo": f"Gravura do marco A{i}", "autor": f"Gravador {i}",
                "data": f"{inicio + 12}", "licenca": licenca["licenca"], "alt": f"Cena do marco A{i}", "url": licenca["url"],
            }
    return epoca


def _webp(caminho: Path, medidas: tuple[int, int]) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", medidas, (140, 100, 60)).save(caminho, "WEBP", quality=60)


@pytest.fixture(scope="module", autouse=True)
def _estaticos_com_imagens(tmp_path_factory):
    """Os estaticos do pacote com as WebP do historia.yaml de teste em historia/ (o gerador le delas width e height)."""
    estaticos = tmp_path_factory.mktemp("estaticos") / "estaticos"
    shutil.copytree(gerar.PASTA_ESTATICOS, estaticos, ignore=shutil.ignore_patterns("historia"))
    for i in range(3):
        inicio = 1600 + 100 * i
        _webp(estaticos / "historia" / f"epoca-{inicio}.webp", MEDIDAS_DA_EPOCA)
        _webp(estaticos / "historia" / f"epoca-{inicio}-cartao.webp", MEDIDAS_DO_CARTAO)
        if i in IMAGENS_DE_MARCO:
            _webp(estaticos / "historia" / f"marco-{inicio + 10}.webp", MEDIDAS_DO_MARCO)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(gerar, "PASTA_ESTATICOS", estaticos)
        yield estaticos


def _historia(provisoria: bool = False, com_imagem: bool = True) -> dict:
    return {
        "provisoria": provisoria,
        "abertura": {
            "titulo": "Como chegamos até aqui",
            "subtitulo": "Subtítulo da abertura de teste.",
            "legenda": "Legenda do gráfico de teste.",
            "nota_estados": "Nota dos estados de teste.",
            "texto": "Texto da abertura de teste.",
        },
        "epocas": [_epoca(i, com_imagem) for i in range(3)],
        "fecho": {
            "titulo": "E de 2000 para cá?",
            "texto": "Texto do fecho de teste.",
            "links": [{"texto": "Início", "url": "../"}, {"texto": "Cards", "url": "../cards/"}],
        },
    }


def _base(raiz: Path, historia: dict | None, censos: str = CENSOS) -> Path:
    copiar_base(raiz)
    pasta = raiz / "metadados" / "site"
    (pasta / "historia.yaml").unlink(missing_ok=True)
    if historia is not None:
        (pasta / "historia").mkdir(exist_ok=True)
        (pasta / "historia.yaml").write_text(yaml.safe_dump(historia, allow_unicode=True, sort_keys=False), encoding="utf-8")
        (pasta / "historia" / "censos.csv").write_text(censos, encoding="utf-8")
    return raiz


def _ler(saida: Path, pagina: str = PAGINA) -> str:
    return (saida / pagina).read_text(encoding="utf-8")


def _trecho(html: str, abre: str, fecha: str) -> str:
    inicio = html.index(abre)
    return html[inicio:html.index(fecha, inicio)]


def _epoca_html(html: str, id_: str) -> str:
    """Da abertura do <li> da epoca ao fim do artigo dela (inclusive)."""
    return _trecho(html, f'<li class="nn-epoca" id="{id_}">', "</article>") + "</article>"


def _menu(html: str) -> list[tuple[str, str]]:
    """(endereco, nome) de cada link da barra do menu: os links soltos e os cartoes dos grupos (pelo titulo)."""
    nav = _trecho(html, '<nav class="nn-menu"', "</nav>")
    pares = []
    for a in re.findall(r"<a\b[^>]*>.*?</a>", nav, flags=re.S):
        arvore = Arvore(a)
        titulo = arvore.achar(classe="nn-menu-cartao-titulo")
        pares.append((arvore.achar("a")[0]["attrs"]["href"], Arvore.texto(titulo[0] if titulo else arvore.achar("a")[0])))
    return pares


@pytest.fixture(scope="module")
def gerado(tmp_path_factory) -> tuple[Path, RelatorioSite]:
    raiz = _base(tmp_path_factory.mktemp("base"), _historia())
    saida = tmp_path_factory.mktemp("site") / "saida"
    return saida, gerar_site(Caminhos(raiz=raiz), saida, imagens=False)


def test_pagina_gerada_no_menu_entre_inicio_e_estados(gerado):
    saida, relatorio = gerado
    assert PAGINA in relatorio.paginas and (saida / PAGINA).is_file()
    assert relatorio.historia_provisoria is False
    assert relatorio.paginas.index(PAGINA) == relatorio.paginas.index("index.html") + 1
    for pagina in ("index.html", PAGINA, "sobre/index.html", "cards/pobreza/index.html"):
        menu = _menu(_ler(saida, pagina))
        assert menu[:4] == [("/", "Início"), ("/como-chegamos/", "Como chegamos até aqui"), ("/inovacao/", "Inovação"),
                            ("/cards/", "Cards para compartilhar")], pagina
    arvore = Arvore(_ler(saida))
    atual = [e for e in arvore.achar("a") if e["attrs"].get("aria-current") == "page"]
    assert [e["attrs"]["href"] for e in atual] == ["/como-chegamos/"] * 2  # na barra e na gaveta
    assert len(arvore.achar("main", classe="nn-historia")) == 1
    assert arvore.achar("main")[0]["attrs"]["id"] == "conteudo"  # o link "Ir para o conteúdo" continua valendo


def test_abertura_mostra_parcelas_calculadas(gerado):
    saida, _ = gerado
    html = _ler(saida)
    arvore = Arvore(html)
    secao = arvore.achar("section", classe="nn-hist-abertura")
    assert len(secao) == 1
    numero = Arvore.texto(arvore.achar(classe="nn-hist-numero")[0])
    assert "46,7%" in numero and "1872" in numero and "26,9%" in numero and "2022" in numero
    # o titulo e o subtitulo sobem para a capa; a abertura fica com a conta dos censos, o texto e o grafico
    capa = Arvore.texto(arvore.achar("section", classe="nn-capa")[0])
    assert "Como chegamos até aqui" in capa and "Subtítulo da abertura de teste." in capa
    abertura = Arvore.texto(secao[0])
    for texto in ("A conta dos censos", "Legenda do gráfico de teste.", "Nota dos estados de teste.",
                  "Texto da abertura de teste."):
        assert texto in abertura
    # a coluna da esquerda: 1872 · 46,7%, a etiqueta da queda (calculada dos censos), 2022 · 26,9% "no Censo de 2022"
    parcelas = [Arvore.texto(p) for p in arvore.achar("p", classe="nn-hist-parcela")]
    assert parcelas == ["1872 46,7% dos brasileiros viviam no Nordeste", "2022 26,9% no Censo de 2022"]
    assert [Arvore.texto(e) for e in arvore.achar(classe="nn-hist-etiqueta")] == ["−19,8 pontos em 150 anos"]
    # a fonte e a nota num paragrafo so, embaixo do grafico; os numeros dos censos no pe do bloco
    legenda = Arvore.texto(arvore.achar("figcaption", classe="nn-hist-legenda")[0])
    assert legenda == "Legenda do gráfico de teste. Nota dos estados de teste."
    assert html.index('class="nn-hist-grafico"') < html.index('class="nn-hist-pe"') < html.index("Ver os números dos censos")
    # o grafico dos censos nas duas larguras, dentro da abertura, com os tres censos e a linha emendada
    trecho = _trecho(html, '<section class="nn-hist-abertura nn-hist-bloco"', "</section>")
    svgs = Arvore(trecho).achar("svg")
    assert [s["attrs"]["viewbox"] for s in svgs] == ["0 0 720 300", "0 0 360 240"]
    for svg in svgs:
        assert svg["attrs"]["data-eixo"] == "1872 2023"
        pontos = json.loads(svg["attrs"]["data-pontos"])
        assert [p[:2] for p in pontos[0]["pontos"]] == [[1872, 46.7], [1950, 34.6], [2022, 26.9]]
        assert svg["attrs"]["data-sufixo"] == "%" and svg["attrs"]["data-casas"] == "1"
    assert len(Arvore(trecho).achar("path")) == 2  # uma linha por largura
    # as pontas maiores (o primeiro e o ultimo censo) e o rotulo do primeiro ponto, em cada largura
    pontas = Arvore(trecho).achar("circle", classe="nn-ponta")
    assert len(pontas) == 4 and {c["attrs"]["r"] for c in pontas} == {"5"}
    assert [Arvore.texto(t) for t in Arvore(trecho).achar("text", classe="nn-ponta-rotulo")] == ["1872 · 46,7%"] * 2
    assert not [r for r in Arvore(trecho).achar("rect") if "nn-faixa" in r["attrs"].get("class", "")]
    # a tabela que a descricao acessivel promete: um censo por linha, com as populacoes e a fonte
    linhas = [Arvore.texto(tr) for tr in Arvore(trecho).achar("tr")][1:]
    assert len(linhas) == 3
    assert "1872" in linhas[0] and "46,7%" in linhas[0] and "4.638.560" in linhas[0] and "Censo de teste A" in linhas[0]
    assert "2022" in linhas[2] and "26,9%" in linhas[2] and "203.080.756" in linhas[2]


def test_abertura_muda_com_os_censos(tmp_path):
    outros = CENSOS.replace("1872,4638560,9930478", "1872,5000000,10000000")
    saida = tmp_path / "saida"
    gerar_site(Caminhos(raiz=_base(tmp_path / "base", _historia(), outros)), saida, imagens=False)
    numero = Arvore.texto(Arvore(_ler(saida)).achar(classe="nn-hist-numero")[0])
    assert "50,0%" in numero and "46,7%" not in numero
    assert "−23,1 pontos em 150 anos" in numero  # a etiqueta tambem sai dos censos, nunca digitada


def test_cada_epoca_tem_artigo_completo(gerado):
    saida, _ = gerado
    html = _ler(saida)
    historia = _historia()
    assert len(Arvore(html).achar("ol", classe="nn-linha-tempo")) == 1
    assert [e["attrs"]["id"] for e in Arvore(html).achar("li", classe="nn-epoca")] == ["1600", "1700", "1800"]
    for i, epoca in enumerate(historia["epocas"]):
        trecho = _epoca_html(html, epoca["id"])
        arvore = Arvore(trecho)
        botao = arvore.achar("button", classe="nn-epoca-abrir")
        assert len(botao) == 1 and botao[0]["attrs"]["data-epoca"] == epoca["id"]
        assert botao[0]["attrs"]["type"] == "button"
        assert "aria-haspopup" not in botao[0]["attrs"]  # sem JavaScript o cartao nao abre nada: o site.js poe o aviso
        cartao = Arvore.texto(botao[0])
        assert f"{epoca['inicio']}–{epoca['fim']}" in cartao and epoca["nome"] in cartao
        img_cartao = [e for e in arvore.achar("img") if any(e is f for f in _filhos(arvore, botao[0]))]
        assert len(img_cartao) == 1
        assert img_cartao[0]["attrs"]["loading"] == "lazy"
        # o cartao usa a miniatura propria (o arquivo grande so vai no artigo, que fica escondido ate o modal)
        assert img_cartao[0]["attrs"]["src"] == f"/historia/epoca-{epoca['inicio']}-cartao.webp"
        # width e height do arquivo: a caixa 21:9 existe antes de a imagem chegar (sem salto de layout)
        assert (img_cartao[0]["attrs"]["width"], img_cartao[0]["attrs"]["height"]) == tuple(map(str, MEDIDAS_DO_CARTAO))
        # a miniatura e decorativa: a descricao fica so na imagem do artigo, para o leitor de tela nao ler a cena duas
        # vezes e o nome do botao comecar pelo periodo e pelo nome da epoca
        assert img_cartao[0]["attrs"]["alt"] == ""

        artigo = _trecho(trecho, '<article class="nn-epoca-conteudo"', "</article>")
        arv = Arvore(artigo)
        texto = Arvore.texto(arv.elementos[0])
        # 1. imagem destaque no topo, com credito (autor, titulo, data, licenca; link quando ha url)
        img = arv.achar("img", classe="nn-epoca-imagem")
        assert len(img) == 1 and img[0]["attrs"]["alt"] == epoca["imagem"]["alt"]
        assert img[0]["attrs"]["loading"] == "lazy"
        assert (img[0]["attrs"]["width"], img[0]["attrs"]["height"]) == tuple(map(str, MEDIDAS_DA_EPOCA))
        assert img[0]["attrs"]["src"] == f"/historia/{epoca['imagem']['arquivo']}"
        credito = Arvore.texto(arv.achar(classe="nn-epoca-credito")[0])
        imagem = IMAGENS[i % len(IMAGENS)]
        for parte in (epoca["imagem"]["autor"], epoca["imagem"]["titulo"], epoca["imagem"]["data"], imagem["rotulo"]):
            assert parte in credito, (epoca["id"], parte)
        if imagem["url"]:
            assert imagem["url"] in [a["attrs"]["href"] for a in arv.achar("a")]
        # 2 a 7: resumo, texto, marcos, numeros com etiqueta, o que ficou, fontes
        assert Arvore.texto(arv.achar(classe="nn-epoca-resumo")[0]) == epoca["resumo"]
        assert epoca["texto"] in Arvore.texto(arv.achar(classe="nn-epoca-texto")[0])
        for marco in epoca["marcos"]:
            item = arv.achar(id=f"m{marco['ano']}")
            assert len(item) == 1
            assert all(p in Arvore.texto(item[0]) for p in (str(marco["ano"]), marco["titulo"], marco["texto"]))
        etiquetas = arv.achar("span", classe="nn-tipo")
        assert len(etiquetas) == len(epoca["numeros"]) + 1  # mais a de "interpretação", no "O que ficou disso"
        for numero, etiqueta in zip(epoca["numeros"], etiquetas):
            assert etiqueta["attrs"]["class"].split() == ["nn-tipo", f"nn-tipo-{numero['tipo']}"]
            assert etiqueta["attrs"]["title"] == numero["fonte"]
            assert Arvore.texto(etiqueta) == TIPOS[numero["tipo"]]
            assert numero["valor"] in texto and numero["legenda"] in texto and numero["fonte"] in texto
        ficou = Arvore.texto(arv.achar(classe="nn-epoca-ficou")[0])
        assert "O que ficou disso" in ficou and epoca["o_que_ficou"] in ficou and TIPOS["interpretacao"] in ficou
        assert etiquetas[-1]["attrs"]["class"].split() == ["nn-tipo", "nn-tipo-interpretacao"]
        fontes = Arvore.texto(arv.achar(classe="nn-epoca-fontes")[0])
        assert all(f["texto"] in fontes for f in epoca["fontes"])
        assert "https://exemplo.org/obra-" + str(i) in [a["attrs"]["href"] for a in arv.achar("a")]
        # a ordem da spec (secao 5, itens 1 a 8), com a imagem destaque no topo: acima do periodo e do titulo
        marcas = ["nn-epoca-figura", "<img", "nn-epoca-credito", "nn-epoca-data", "nn-epoca-titulo", "nn-epoca-resumo",
                  "nn-epoca-texto", "nn-epoca-marcos", "nn-epoca-numeros", "nn-epoca-ficou", "nn-epoca-fontes",
                  "nn-epoca-nav"]
        posicoes = [artigo.index(m) for m in marcas]
        assert posicoes == sorted(posicoes), epoca["id"]
        assert arv.elementos[1]["attrs"].get("class") == "nn-epoca-figura"  # o primeiro filho do artigo


def _filhos(arvore: Arvore, pai: dict) -> list[dict]:
    """Os elementos depois de `pai` ate o fim dele (o HTMLParser nao guarda a arvore: usa a ordem e o texto)."""
    inicio = arvore.elementos.index(pai)
    filhos = []
    for e in arvore.elementos[inicio + 1:]:
        if e["tag"] == "article" or e["attrs"].get("class") == "nn-marcos-linha":
            break
        filhos.append(e)
    return filhos


def test_primeira_e_ultima_epoca_sem_botao_sem_destino(gerado):
    saida, _ = gerado
    html = _ler(saida)
    ids = ["1600", "1700", "1800"]
    for i, id_ in enumerate(ids):
        nav = Arvore(_trecho(_epoca_html(html, id_), '<nav class="nn-epoca-nav"', "</nav>"))
        anterior = nav.achar("a", classe="nn-epoca-anterior")
        proxima = nav.achar("a", classe="nn-epoca-proxima")
        if i == 0:
            assert anterior == []
        else:
            assert [(a["attrs"]["href"], a["attrs"]["data-epoca"]) for a in anterior] == [(f"#{ids[i - 1]}", ids[i - 1])]
            assert Arvore.texto(anterior[0]) == "← época anterior"
        if i == len(ids) - 1:
            assert proxima == []
        else:
            assert [(a["attrs"]["href"], a["attrs"]["data-epoca"]) for a in proxima] == [(f"#{ids[i + 1]}", ids[i + 1])]
            assert Arvore.texto(proxima[0]) == "próxima época →"
    # os textos dos botoes nao aparecem fora da navegacao da epoca que tem destino
    assert html.count("← época anterior") == 2 and html.count("próxima época →") == 2


def test_marcos_apontam_para_a_epoca_certa(gerado):
    saida, _ = gerado
    html = _ler(saida)
    todos = Arvore(html).achar("a", classe="nn-marco")
    assert len(todos) == 6
    for epoca in _historia()["epocas"]:
        trecho = _epoca_html(html, epoca["id"])
        linha = _trecho(trecho, "<li", "<article")  # os marcos da linha do tempo, fora do artigo
        marcos = Arvore(linha).achar("a", classe="nn-marco")
        assert [m["attrs"]["data-marco"] for m in marcos] == [str(m["ano"]) for m in epoca["marcos"]]
        for marco, a in zip(epoca["marcos"], marcos):
            assert a["attrs"]["href"] == f"#m{marco['ano']}"
            assert a["attrs"]["data-epoca"] == epoca["id"]
            assert str(marco["ano"]) in Arvore.texto(a)
            artigo = _trecho(trecho, '<article class="nn-epoca-conteudo"', "</article>")
            assert f'id="m{marco["ano"]}"' in artigo
    ids = [e["attrs"]["id"] for e in Arvore(html).elementos if "id" in e["attrs"]]
    assert len(ids) == len(set(ids))


def test_um_unico_dialog_vazio_no_fim(gerado):
    saida, _ = gerado
    html = _ler(saida)
    arvore = Arvore(html)
    dialogos = dialogos_da_pagina(arvore)  # o "Sobre o autor", de toda pagina, tem teste proprio (test_autoria.py)
    assert len(dialogos) == 1
    assert dialogos[0]["attrs"]["class"].split() == ["nn-modal", "nn-modal-historia"]
    assert "aria-labelledby" not in dialogos[0]["attrs"]  # o site.js o liga ao titulo da epoca aberta (nao ha titulo aqui)
    dialogo = _trecho(html, "<dialog", "</dialog>")
    assert "nn-epoca-conteudo" not in dialogo and "nn-modal-fechar" in dialogo and "nn-modal-corpo" in dialogo
    assert html.index("<dialog") > html.index('<ol class="nn-linha-tempo"')
    fecho = arvore.achar("section", classe="nn-hist-fecho")
    assert len(fecho) == 1
    assert "E de 2000 para cá?" in Arvore.texto(fecho[0])
    assert [a["attrs"]["href"] for a in Arvore(_trecho(html, '<section class="nn-hist-fecho nn-hist-bloco"', "</section>")).achar("a")] == ["../", "../cards/"]


def test_pagina_sem_style_script_inline_nem_recurso_externo(gerado):
    saida, _ = gerado
    arvore = Arvore(_ler(saida))
    assert not arvore.achar("style")
    for e in arvore.elementos:
        assert "style" not in e["attrs"], e["tag"]
        assert not [a for a in e["attrs"] if a.startswith("on")], e["tag"]
        if e["tag"] in ("img", "script", "link") and (e["attrs"].get("src") or e["attrs"].get("href")):
            url = e["attrs"].get("src") or e["attrs"]["href"]
            assert url.startswith("/") or url.startswith(SITE), url
    for script in arvore.achar("script"):
        assert script["attrs"].get("src", "").partition("?")[0] in ("/nn-js.js", "/site.js") and not Arvore.texto(script)
    visivel = arvore.texto_visivel()
    assert not re.search(r"\b(nan|none|undefined|null)\b", visivel, flags=re.IGNORECASE)
    assert "{" not in visivel and "Prévia" not in visivel
    assert not arvore.achar("meta", name="robots")



def test_so_a_pagina_de_historia_pre_carrega_a_serifada(gerado):
    """A EB Garamond (titulos desta pagina) vem pre-carregada so aqui; as outras paginas nem a citam no HTML."""
    saida, relatorio = gerado
    previas = [e["attrs"] for e in Arvore(_ler(saida)).achar("link", rel="preload")]
    assert previas == [{"rel": "preload", "href": "/fontes/eb-garamond/EBGaramond.woff2", "as": "font",
                        "type": "font/woff2", "crossorigin": None}]
    for pagina in relatorio.paginas:
        if pagina not in (PAGINA, "en/how-we-got-here/index.html"):  # a mesma pagina em ingles tambem a pre-carrega
            assert "EBGaramond" not in _ler(saida, pagina), pagina


def test_provisoria_nao_gera_pagina_nem_menu(tmp_path):
    raiz = _base(tmp_path / "base", _historia(provisoria=True, com_imagem=False))
    saida = tmp_path / "saida"
    relatorio = gerar_site(Caminhos(raiz=raiz), saida, imagens=False)
    assert relatorio.historia_provisoria is True
    assert PAGINA not in relatorio.paginas and not (saida / "como-chegamos").exists()
    for pagina in ("index.html", "sobre/index.html"):
        assert "/como-chegamos/" not in [href for href, _ in _menu(_ler(saida, pagina))]
        assert "como-chegamos" not in _ler(saida, pagina)
    assert json.loads(gerar.relatorio_em_json(relatorio))["historia_provisoria"] is True


def test_sem_historia_yaml_nao_ha_pagina(tmp_path):
    saida = tmp_path / "saida"
    relatorio = gerar_site(Caminhos(raiz=_base(tmp_path / "base", None)), saida, imagens=False)
    assert relatorio.historia_provisoria is False and PAGINA not in relatorio.paginas
    assert "/como-chegamos/" not in _ler(saida, "index.html")


def test_incluir_provisoria_gera_previa_com_aviso_e_noindex(tmp_path):
    raiz = _base(tmp_path / "base", _historia(provisoria=True, com_imagem=False))
    saida = tmp_path / "saida"
    relatorio = gerar_site(Caminhos(raiz=raiz), saida, imagens=False, incluir_provisoria=True)
    assert relatorio.historia_provisoria is True and PAGINA in relatorio.paginas
    html = _ler(saida)
    arvore = Arvore(html)
    aviso = arvore.achar(classe="nn-hist-previa")
    assert len(aviso) == 1 and "Prévia: texto provisório" in Arvore.texto(aviso[0])
    assert [m["attrs"]["content"] for m in arvore.achar("meta", name="robots")] == ["noindex"]
    assert ("/como-chegamos/", "Como chegamos até aqui") in _menu(_ler(saida, "index.html"))
    assert not Arvore(_ler(saida, "index.html")).achar("meta", name="robots")  # so a pagina previa sai do indice
    # epoca sem imagem (so possivel com provisoria): cartao e artigo sem <img>, sem credito, e o resto inteiro
    assert not imagens_da_pagina(arvore) and not arvore.achar(classe="nn-epoca-credito")
    assert len(arvore.achar("button", classe="nn-epoca-abrir")) == 3
    assert len(arvore.achar("article", classe="nn-epoca-conteudo")) == 3
    assert not Arvore(_ler(saida, "sobre/index.html")).achar(id="sobre-imagens")


def test_cli_incluir_provisoria(tmp_path):
    raiz = _base(tmp_path / "base", _historia(provisoria=True, com_imagem=False))
    assert main(["--raiz", str(raiz), "site", "--saida", str(tmp_path / "sem"), "--sem-imagens"]) == 0
    assert not (tmp_path / "sem" / PAGINA).exists()
    assert main(["--raiz", str(raiz), "site", "--saida", str(tmp_path / "com"), "--sem-imagens",
                 "--incluir-provisoria"]) == 0
    assert "Prévia: texto provisório" in _ler(tmp_path / "com")


def test_creditos_das_imagens_em_sobre(gerado):
    saida, _ = gerado
    html = _ler(saida, "sobre/index.html")
    arvore = Arvore(html)
    secao = arvore.achar(id="sobre-imagens")
    assert len(secao) == 1
    itens = [Arvore.texto(li) for li in arvore.achar("li", classe="nn-credito-imagem")]
    # cada epoca e, logo depois dela, cada marco com imagem
    esperados = []
    for i, epoca in enumerate(_historia()["epocas"]):
        esperados.append((epoca["nome"], epoca["imagem"], IMAGENS[i]["rotulo"]))
        for marco in epoca["marcos"]:
            if "imagem" in marco:
                esperados.append((f"{epoca['nome']}, marco de {marco['ano']}", marco["imagem"], IMAGENS_DE_MARCO[i]["rotulo"]))
    assert len(itens) == len(esperados) == 5
    for item, (rotulo, imagem, licenca) in zip(itens, esperados):
        assert item.startswith(f"{rotulo}:"), item
        assert all(p in item for p in (imagem["autor"], imagem["titulo"], imagem["data"], licenca)), item
    assert IMAGENS[1]["url"] in [a["attrs"].get("href") for a in arvore.achar("a")]
    assert "/como-chegamos/" in [a["attrs"].get("href") for a in Arvore(_trecho(html, 'id="sobre-imagens"', "</article>")).achar("a")]


def test_pagina_tem_og_e_canonical_proprios(gerado):
    saida, _ = gerado
    arvore = Arvore(_ler(saida))
    url = f"{SITE}/como-chegamos/"
    assert [e["attrs"]["href"] for e in arvore.achar("link", rel="canonical")] == [url]
    metas = {(m["attrs"].get("property") or m["attrs"].get("name")): m["attrs"]["content"] for m in arvore.achar("meta") if "content" in m["attrs"]}
    assert metas["og:url"] == url
    assert metas["og:image"].startswith(f"{SITE}/compartilhar.jpg?v=")  # a ilustracao do site inteiro
    titulo = Arvore.texto(arvore.achar("title")[0])
    assert titulo == metas["og:title"] == "Como chegamos até aqui · Nordeste em Números"
    assert metas["og:description"] == metas["description"] != ""


def test_imagem_og_da_pagina_pelo_mesmo_caminho_das_outras(tmp_path, monkeypatch):
    fotografados = {}

    def renderizar_falso(alvos, raiz):
        for alvo in alvos:
            fotografados[alvo.png.relative_to(raiz).as_posix()] = alvo.html.read_text(encoding="utf-8")
            alvo.png.parent.mkdir(parents=True, exist_ok=True)
            alvo.png.write_bytes(b"png")

    monkeypatch.setattr(gerar, "renderizar", renderizar_falso)
    saida = tmp_path / "saida"
    gerar_site(Caminhos(raiz=_base(tmp_path / "base", _historia())), saida, imagens=True)
    assert "og/como-chegamos.png" in fotografados
    titulo = Arvore(fotografados["og/como-chegamos.png"]).achar("h1", classe="nn-og-titulo")[0]
    assert Arvore.texto(titulo) == "Como chegamos até aqui"
    assert "og/como-chegamos.png" in json.loads((saida / gerar.MANIFESTO_DE_IMAGENS).read_text(encoding="utf-8"))


def test_marco_com_imagem_livre_mostra_a_imagem_no_artigo(gerado):
    saida, _ = gerado
    html = _ler(saida)
    for i, epoca in enumerate(_historia()["epocas"]):
        artigo = Arvore(_trecho(_epoca_html(html, epoca["id"]), '<article class="nn-epoca-conteudo"', "</article>"))
        for marco in epoca["marcos"]:
            item = _trecho(_epoca_html(html, epoca["id"]), f'<li id="m{marco["ano"]}"', "</li>")
            arv = Arvore(item)
            if "imagem" not in marco:
                assert not arv.achar("img") and not arv.achar(classe="nn-marco-credito")  # so texto, sem ilustracao
                continue
            imagem, licenca = marco["imagem"], IMAGENS_DE_MARCO[i]
            img = arv.achar("img", classe="nn-marco-imagem")
            assert len(img) == 1
            attrs = img[0]["attrs"]
            assert attrs["src"] == f"/historia/{imagem['arquivo']}" and attrs["alt"] == imagem["alt"]
            # so carrega quando o modal abre: lazy e dentro do artigo (que fica escondido ate ir para o modal)
            assert attrs["loading"] == "lazy"
            assert (attrs["width"], attrs["height"]) == tuple(map(str, MEDIDAS_DO_MARCO))
            credito = Arvore.texto(arv.achar(classe="nn-marco-credito")[0])
            assert all(p in credito for p in (imagem["autor"], imagem["data"], licenca["rotulo"])), credito
            if licenca["url"]:
                assert licenca["url"] in [a["attrs"]["href"] for a in arv.achar("a")]
            # o texto do marco vem antes da imagem
            assert item.index(marco["texto"]) < item.index("nn-marco-figura")
        # nenhuma imagem de marco fora do artigo (a linha do tempo so tem a miniatura da epoca)
        linha = Arvore(_trecho(_epoca_html(html, epoca["id"]), "<li", "<article"))
        assert not linha.achar("img", classe="nn-marco-imagem")
        assert len(artigo.achar("img", classe="nn-marco-imagem")) == (1 if i in IMAGENS_DE_MARCO else 0)


def test_imagens_copiadas_so_com_a_pagina(gerado, tmp_path):
    saida, _ = gerado
    assert sorted(p.name for p in (saida / "historia").iterdir()) == [
        "epoca-1600-cartao.webp", "epoca-1600.webp", "epoca-1700-cartao.webp", "epoca-1700.webp",
        "epoca-1800-cartao.webp", "epoca-1800.webp", "marco-1610.webp", "marco-1710.webp",
    ]
    raiz = _base(tmp_path / "base", _historia(provisoria=True, com_imagem=False))
    gerar_site(Caminhos(raiz=raiz), tmp_path / "sem", imagens=False)
    assert not (tmp_path / "sem" / PAGINA).exists() and not (tmp_path / "sem" / "historia").exists()


@pytest.mark.parametrize("defeito", ["falta", "pesada", "proporcao", "sem-cartao", "cartao-pesado", "cartao-fora"])
def test_recusa_imagem_ausente_pesada_ou_fora_de_21_por_9(tmp_path, monkeypatch, _estaticos_com_imagens, defeito):
    estaticos = tmp_path / "estaticos"
    shutil.copytree(_estaticos_com_imagens, estaticos)
    monkeypatch.setattr(gerar, "PASTA_ESTATICOS", estaticos)
    nome = {"pesada": "marco-1710.webp", "falta": "epoca-1700.webp", "proporcao": "epoca-1700.webp"}.get(
        defeito, "epoca-1700-cartao.webp")
    alvo = estaticos / "historia" / nome
    if defeito in ("falta", "sem-cartao"):
        alvo.unlink()
    elif defeito == "pesada":  # marco ate 80 000 bytes
        Image.effect_noise((900, 386), 100).convert("RGB").save(alvo, "WEBP", quality=100)
        assert alvo.stat().st_size > 80_000
    elif defeito == "cartao-pesado":  # cartao ate 25 000 bytes
        Image.effect_noise((700, 300), 100).convert("RGB").save(alvo, "WEBP", quality=100)
        assert alvo.stat().st_size > 25_000
    else:
        _webp(alvo, (400, 300))
    with pytest.raises(ErroConteudo, match=alvo.name) as erro:
        gerar_site(Caminhos(raiz=_base(tmp_path / "base", _historia())), tmp_path / "saida", imagens=False)
    if defeito == "sem-cartao":  # a mensagem diz que falta a miniatura do cartao daquela epoca
        assert "cartão" in str(erro.value) and "epoca-1700.webp" in str(erro.value)


# --- a chamada para a pagina no Inicio: o bloco depois da faixa de numeros, com o titulo dos censos e o credito da 1530 ---

def _historia_com_a_epoca_1530() -> dict:
    historia = _historia()
    historia["epocas"][0]["id"] = "1530"  # a epoca cuja imagem e credito a chamada usa
    historia["epocas"][0]["imagem"]["url"] = "https://commons.wikimedia.org/wiki/File:Teste-1530.jpg"
    return historia


@pytest.fixture(scope="module")
def com_chamada(tmp_path_factory) -> Path:
    raiz = _base(tmp_path_factory.mktemp("base"), _historia_com_a_epoca_1530())
    saida = tmp_path_factory.mktemp("site") / "saida"
    gerar_site(Caminhos(raiz=raiz), saida, imagens=False)
    return saida


def test_chamada_no_inicio_depois_das_perguntas_com_o_titulo_dos_censos(com_chamada):
    html = _ler(com_chamada, "index.html")
    arvore = Arvore(html)
    chamada = arvore.achar("section", classe="nn-chamada-historia")
    assert len(chamada) == 1
    # depois das perguntas (e antes dos <template> dos graficos ampliados), nao mais logo depois da faixa
    fim_das_perguntas = html.index("</section>", html.rindex('<article class="nn-capitulo'))
    assert html.index('id="resumo"') < fim_das_perguntas < html.index('<section class="nn-chamada-historia"') < html.index("<template")
    # os mesmos numeros da abertura da pagina historica (censos.csv de teste: 46,7% em 1872 e 26,9% em 2022)
    titulo = Arvore.texto(arvore.achar("h2", id="titulo-chamada-historia")[0])
    assert titulo == "Em 1872, 46,7% dos brasileiros viviam no Nordeste. Em 2022, 26,9%."
    pagina = Arvore.texto(Arvore(_ler(com_chamada)).achar(classe="nn-hist-numero")[0])
    assert "46,7%" in pagina and "26,9%" in pagina
    texto = Arvore.texto(chamada[0])
    assert "Como chegamos até aqui" in texto and "em oito épocas, com a fonte de cada número." in texto
    assert [a["attrs"]["href"] for a in Arvore(_trecho(html, '<section class="nn-chamada-historia"', "</section>")).achar("a")][0] == "/como-chegamos/"
    assert "Ver a linha do tempo →" in texto


def test_chamada_traz_o_credito_da_imagem_da_epoca_1530_com_link(com_chamada):
    html = _ler(com_chamada, "index.html")
    trecho = _trecho(html, '<p class="nn-chamada-credito"', "</p>")
    links = Arvore(trecho).achar("a")
    assert [l["attrs"]["href"] for l in links] == ["https://commons.wikimedia.org/wiki/File:Teste-1530.jpg"]
    assert "Imagem: " in trecho and "Autor da imagem 0, <cite>Título da imagem 0</cite>, 1640" in trecho
    assert trecho.rstrip().endswith("(domínio público).")
    assert "style=" not in _trecho(html, '<section class="nn-chamada-historia"', "</section>")


def test_chamada_some_sem_a_pagina_historica(tmp_path):
    for nome, historia in (("sem", None), ("provisoria", {**_historia_com_a_epoca_1530(), "provisoria": True})):
        raiz = _base(tmp_path / f"base-{nome}", historia)
        saida = tmp_path / f"saida-{nome}"
        gerar_site(Caminhos(raiz=raiz), saida, imagens=False)
        html = _ler(saida, "index.html")
        assert "nn-chamada-historia" not in html and "/como-chegamos/" not in html, nome


def test_chamada_exige_os_quatro_marcadores_no_titulo(tmp_path):
    chamada = {"eyebrow": "e", "titulo": "Em [ano_inicial], [parcela_inicial].", "texto": "t", "botao": "b", "credito": "c"}
    with pytest.raises(ErroConteudo, match="chamada_historia.titulo"):
        gerar._chamada_da_historia(chamada, None)
