"""Autoria no cabecalho e no rodape: o titulo e o "por Julio Diogenes", o bloco "Desenvolvido por" com a foto (ou as
iniciais), o modal "Sobre o autor" e a secao #autor de Sobre, tudo a partir da chave `autor` de textos.yaml."""

import re
from pathlib import Path

import pytest
import yaml
from PIL import Image

from nordeste.caminhos import Caminhos
from nordeste.site.conteudo import ErroConteudo
from nordeste.site.gerar import URL_DO_AUTOR, gerar_site

from auxiliares import RAIZ, Arvore, copiar_base, estaticos_com_arquivos

PAGINAS = (
    "index.html", "como-chegamos/index.html", "estados/index.html", "explorar/index.html", "cards/index.html",
    "sobre/index.html", "dados/index.html",
)
MOTIVACAO = (
    "Fiz este estudo por raiva, e também por orgulho. Raiva de um discurso que repete que o Nordeste está do mesmo "
    "jeito, apaga a história da região e ignora o que estados e municípios fizeram e deixaram de fazer. Orgulho de "
    "uma região que mudou mais do que se diz, ainda que falte muito chão. Então fui conferir nos dados oficiais, de "
    "2000 para cá, e na história, da Colônia até hoje. Aqui ninguém ganha passe livre: município, estado e União "
    "dividem a conta. Cada número tem fonte e cálculo à vista, para quem quiser rebater ou entender."
)
QUEM_SOU = (
    "Diretor executivo do Laboratório Urbano Vivo de Vitória (LUV). Há mais de 17 anos, ajudo profissionais, empresas "
    "e governos a transformar problemas complexos em decisões executáveis, com estratégia, inovação, inteligência "
    "artificial e políticas públicas."
)
MAIS = "Mais sobre o meu trabalho em dnascimento.com.br"
FORMACAO = [
    "Especialização em Direito da Infraestrutura, Governança e Regulação, PUC Minas (em curso, 2026–2027)",
    "Bacharelado em Engenharia da Computação, Uniamérica (2022–2026)",
    "Especialização em Análise de Dados, EBAC – Escola Britânica de Artes Criativas e Tecnologia (2022)",
    "Design, com ênfase em Gestão de Marca, Universidade Potiguar (2009–2012)",
]
FORMACAO_VAZIA = "Formação e trajetória completas em dnascimento.com.br"
ESTATICOS = RAIZ / "src" / "nordeste" / "site" / "estaticos"
FOTO_DO_REPOSITORIO = ESTATICOS / "autor.webp"
MARCAS_DO_REPOSITORIO = (ESTATICOS / "marca-autor-clara.webp", ESTATICOS / "marca-autor-escura.webp")


@pytest.fixture(scope="module")
def gerado(tmp_path_factory) -> Path:
    saida = tmp_path_factory.mktemp("site") / "saida"
    gerar_site(Caminhos(raiz=RAIZ), saida, imagens=False)
    return saida


def _html(saida: Path, pagina: str) -> str:
    return (saida / pagina).read_text(encoding="utf-8")


def _trecho(html: str, tag: str) -> tuple[str, Arvore]:
    achado = re.search(rf"<{tag}\b.*?</{tag}>", html, flags=re.S)
    assert achado, tag
    return achado[0], Arvore(achado[0])


def _webp(destino: Path, tamanho: tuple[int, int]) -> None:
    Image.new("RGB", tamanho, (120, 120, 120)).save(destino, "WEBP")


def _com_textos_alterados(tmp_path: Path, alterar) -> Path:
    raiz = copiar_base(tmp_path / "repo")
    arquivo = raiz / "metadados" / "site" / "textos.yaml"
    textos = yaml.safe_load(arquivo.read_text(encoding="utf-8"))
    alterar(textos)
    arquivo.write_text(yaml.safe_dump(textos, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return raiz


# --- cabecalho ---


@pytest.mark.parametrize("pagina", PAGINAS)
def test_cabecalho_tem_titulo_autor_separador_e_menu(gerado, pagina):
    html, _ = _trecho(_html(gerado, pagina), "header")
    arvore = Arvore(html)
    marca = arvore.achar("a", classe="nn-marca")
    assert len(marca) == 1 and marca[0]["attrs"]["href"] == "/" and Arvore.texto(marca[0]) == "Nordeste em Números"
    autoria = arvore.achar(classe="nn-autoria")
    assert len(autoria) == 1 and Arvore.texto(autoria[0]) == "por Júlio Diógenes"
    nome = [e for e in arvore.achar("a") if e["attrs"].get("href") == URL_DO_AUTOR]
    assert len(nome) == 1 and Arvore.texto(nome[0]) == "Júlio Diógenes"
    assert [Arvore.texto(e) for e in arvore.achar("strong")] == ["Júlio Diógenes"]
    assert len(arvore.achar(classe="nn-topo-linha")) == 1
    # a ordem: primeira linha (titulo e autor), separador, menu
    assert html.index("nn-marca") < html.index("nn-autoria") < html.index("nn-topo-linha") < html.index("nn-menu")


@pytest.mark.parametrize("pagina", PAGINAS)
def test_cabecalho_tem_o_menu_inteiro_com_uma_pagina_atual_e_sem_o_link_solto(gerado, pagina):
    _, arvore = _trecho(_html(gerado, pagina), "header")
    menu = arvore.achar("nav", classe="nn-menu")
    assert len(menu) == 1 and menu[0]["attrs"]["aria-label"] == "Páginas do site"
    itens = [e for e in arvore.achar("a") if e["attrs"].get("href", "").startswith("/") and "nn-marca" not in e["attrs"].get("class", "")]
    assert [e["attrs"]["href"] for e in itens] == [
        "/", "/como-chegamos/", "/estados/", "/explorar/", "/cards/", "/sobre/", "/dados/"
    ]
    atuais = [e for e in itens if e["attrs"].get("aria-current") == "page"]
    rota = "/" if pagina == "index.html" else "/" + pagina.removesuffix("index.html")
    assert [e["attrs"]["href"] for e in atuais] == [rota]
    assert not [e for e in arvore.achar("a") if Arvore.texto(e) == "dnascimento.com.br"]
    assert not arvore.achar("a", classe="nn-hero-site")


def test_paginas_de_card_tambem_tem_o_cabecalho_novo(gerado):
    card = next((gerado / "cards").glob("*/index.html"))
    _, arvore = _trecho(card.read_text(encoding="utf-8"), "header")
    assert arvore.achar(classe="nn-autoria") and arvore.achar(classe="nn-topo-linha")


# --- rodape: bloco de autoria ---


@pytest.mark.parametrize("pagina", PAGINAS)
def test_rodape_mantem_o_que_ja_tinha_e_ganha_o_bloco_de_autoria(gerado, pagina):
    html = _html(gerado, pagina)
    _, rodape = _trecho(html, "footer")
    texto = Arvore.texto(rodape.elementos[0])
    assert re.search(r"publicados em \d{1,2}º? de \w+ de \d{4}", texto) and "sha256 da base:" in texto
    assert "CC BY 4.0" in texto and "Imagem: Júlio Diógenes" in texto
    # as duas linhas antigas, que o bloco de autoria passou a cobrir, sairam do rodape
    assert "Nordeste em Números" not in texto
    assert not [a for a in rodape.achar("a") if Arvore.texto(a) == "dnascimento.com.br"]
    assert not rodape.achar("strong") or [Arvore.texto(s) for s in rodape.achar("strong")] == ["Júlio Diógenes"]
    gatilho = rodape.achar("a", classe="nn-autor-abrir")
    assert len(gatilho) == 1
    assert gatilho[0]["attrs"]["href"] == "/sobre/#autor"  # sem JavaScript, o clique leva a secao de Sobre
    assert gatilho[0]["attrs"]["aria-haspopup"] == "dialog"
    assert Arvore.texto(gatilho[0]) == "Desenvolvido por Júlio Diógenes"  # a foto ou as iniciais nao tem texto proprio
    assert [Arvore.texto(e) for e in rodape.achar("strong", classe="nn-autor-nome")] == ["Júlio Diógenes"]


def test_com_a_foto_do_pacote_o_circulo_leva_o_retrato_320_por_320(gerado):
    assert FOTO_DO_REPOSITORIO.is_file()
    with Image.open(FOTO_DO_REPOSITORIO) as foto:
        assert foto.format == "WEBP" and foto.size == (320, 320)
    assert FOTO_DO_REPOSITORIO.stat().st_size <= 100_000
    for pagina in PAGINAS:
        _, rodape = _trecho(_html(gerado, pagina), "footer")
        circulo = rodape.achar(classe="nn-autor-circulo")
        assert len(circulo) == 1 and Arvore.texto(circulo[0]) == "", pagina  # sem iniciais quando ha foto
        imagens = rodape.achar("img", src="/autor.webp")
        assert len(imagens) == 1 and imagens[0]["attrs"]["alt"] == "Júlio Diógenes", pagina
        assert (imagens[0]["attrs"]["width"], imagens[0]["attrs"]["height"]) == ("320", "320")
    assert (gerado / "autor.webp").read_bytes() == FOTO_DO_REPOSITORIO.read_bytes()


def test_sem_foto_do_autor_o_circulo_mostra_as_iniciais(tmp_path, monkeypatch):
    estaticos = estaticos_com_arquivos(tmp_path, monkeypatch)
    (estaticos / "autor.webp").unlink()
    saida = tmp_path / "saida"
    gerar_site(Caminhos(raiz=copiar_base(tmp_path / "repo")), saida, imagens=False)
    for pagina in PAGINAS:
        _, rodape = _trecho(_html(saida, pagina), "footer")
        circulo = rodape.achar(classe="nn-autor-circulo")
        assert len(circulo) == 1 and Arvore.texto(circulo[0]) == "JD" and circulo[0]["attrs"]["aria-hidden"] == "true"
        assert not rodape.achar("img", src="/autor.webp"), pagina
    assert not (saida / "autor.webp").exists()


def test_com_autor_webp_o_circulo_leva_a_foto_com_largura_e_altura(tmp_path, monkeypatch):
    estaticos = estaticos_com_arquivos(tmp_path, monkeypatch)
    _webp(estaticos / "autor.webp", (120, 150))
    saida = tmp_path / "saida"
    gerar_site(Caminhos(raiz=copiar_base(tmp_path / "repo")), saida, imagens=False)
    for pagina in PAGINAS:
        _, rodape = _trecho(_html(saida, pagina), "footer")
        imagens = rodape.achar("img", src="/autor.webp")
        assert len(imagens) == 1, pagina
        atributos = imagens[0]["attrs"]
        assert atributos["src"] == "/autor.webp" and atributos["alt"] == "Júlio Diógenes"
        assert (atributos["width"], atributos["height"]) == ("120", "150")
        assert "style" not in atributos
        assert "JD" not in Arvore.texto(rodape.achar(classe="nn-autor-circulo")[0])
    assert (saida / "autor.webp").read_bytes() == (estaticos / "autor.webp").read_bytes()


def test_autor_webp_que_nao_e_webp_ou_pesa_demais_e_recusado(tmp_path, monkeypatch):
    estaticos = estaticos_com_arquivos(tmp_path, monkeypatch)
    (estaticos / "autor.webp").write_bytes(b"isto nao e uma imagem")
    with pytest.raises(ErroConteudo, match="autor.webp"):
        gerar_site(Caminhos(raiz=copiar_base(tmp_path / "a")), tmp_path / "saida", imagens=False)
    _webp(estaticos / "autor.webp", (56, 56))
    with (estaticos / "autor.webp").open("ab") as arquivo:
        arquivo.write(bytes(150_000))
    with pytest.raises(ErroConteudo, match="autor.webp.*KB"):
        gerar_site(Caminhos(raiz=copiar_base(tmp_path / "b")), tmp_path / "saida", imagens=False)


def test_marca_do_autor_no_rodape_e_a_versao_clara_e_a_marca_do_pacote_tem_o_tamanho_certo(gerado):
    for arquivo in MARCAS_DO_REPOSITORIO:
        with Image.open(arquivo) as marca:
            assert marca.format == "WEBP" and marca.size == (462, 154), arquivo.name
    for pagina in PAGINAS:
        _, rodape = _trecho(_html(gerado, pagina), "footer")
        marca = rodape.achar("img", classe="nn-autor-marca")
        assert len(marca) == 1, pagina
        atributos = marca[0]["attrs"]
        # o rodape e preto nos dois temas: so a versao branca se enxerga nele; o nome ja esta no texto ao lado
        assert atributos["src"] == "/marca-autor-clara.webp" and atributos["alt"] == ""
        assert (atributos["width"], atributos["height"]) == ("462", "154") and "style" not in atributos
    for arquivo in MARCAS_DO_REPOSITORIO:
        assert (gerado / arquivo.name).read_bytes() == arquivo.read_bytes()


@pytest.mark.parametrize(
    "apagar",
    [("marca-autor-clara.webp",), ("marca-autor-escura.webp",), ("marca-autor-clara.webp", "marca-autor-escura.webp")],
)
def test_marca_do_autor_so_aparece_se_as_duas_versoes_existirem(tmp_path, monkeypatch, apagar):
    estaticos = estaticos_com_arquivos(tmp_path, monkeypatch)
    for nome in apagar:
        (estaticos / nome).unlink()
    saida = tmp_path / "saida"
    gerar_site(Caminhos(raiz=copiar_base(tmp_path / "repo")), saida, imagens=False)
    for pagina in PAGINAS:
        arvore = Arvore(_html(saida, pagina))
        assert not arvore.achar(classe="nn-autor-marca") and not arvore.achar("picture"), pagina


def test_marca_com_tamanhos_diferentes_ou_que_nao_e_webp_e_recusada(tmp_path, monkeypatch):
    estaticos = estaticos_com_arquivos(tmp_path, monkeypatch)
    _webp(estaticos / "marca-autor-clara.webp", (462, 154))
    _webp(estaticos / "marca-autor-escura.webp", (400, 100))
    with pytest.raises(ErroConteudo, match="mesmo tamanho"):
        gerar_site(Caminhos(raiz=copiar_base(tmp_path / "a")), tmp_path / "saida", imagens=False)
    (estaticos / "marca-autor-escura.webp").write_bytes(b"isto nao e uma imagem")
    with pytest.raises(ErroConteudo, match="marca-autor-escura.webp"):
        gerar_site(Caminhos(raiz=copiar_base(tmp_path / "b")), tmp_path / "saida", imagens=False)


# --- modal e secao de Sobre ---


@pytest.mark.parametrize("pagina", PAGINAS)
def test_dialog_sobre_o_autor_tem_as_tres_secoes_e_nasce_fechado(gerado, pagina):
    html = _html(gerado, pagina)
    achados = [d for d in re.findall(r"<dialog\b.*?</dialog>", html, flags=re.S) if "nn-modal-autor" in d]
    assert len(achados) == 1
    arvore = Arvore(achados[0])
    dialogo = arvore.achar("dialog")[0]["attrs"]
    assert dialogo["class"] == "nn-modal nn-modal-autor" and "open" not in dialogo
    titulo = arvore.achar("h2")[0]
    assert dialogo["aria-labelledby"] == titulo["attrs"]["id"] and Arvore.texto(titulo) == "Sobre o autor"
    assert [Arvore.texto(h) for h in arvore.achar("h3")] == ["Quem sou", "Por que fiz este estudo", "Formação"]
    visivel = arvore.texto_visivel()
    assert QUEM_SOU in visivel and MAIS in visivel and MOTIVACAO in visivel
    assert [Arvore.texto(li) for li in arvore.achar("li")] == FORMACAO
    assert FORMACAO_VAZIA not in visivel  # com a lista, a frase de trajetoria nao aparece
    assert {e["attrs"]["href"] for e in arvore.achar("a")} == {URL_DO_AUTOR}
    assert [Arvore.texto(a) for a in arvore.achar("a")] == ["dnascimento.com.br"]  # o link do "Mais sobre o meu trabalho"
    marca = arvore.achar("picture")
    assert len(marca) == 1  # a marca do modal segue o tema: a branca no escuro, a escura no claro
    assert [e["attrs"]["srcset"] for e in arvore.achar("source")] == ["/marca-autor-clara.webp"]
    assert arvore.achar("source")[0]["attrs"]["media"] == "(prefers-color-scheme: dark)"
    imagem = arvore.achar("img")
    assert len(imagem) == 1 and imagem[0]["attrs"]["src"] == "/marca-autor-escura.webp"
    assert imagem[0]["attrs"]["alt"] == "Júlio Diógenes"
    assert [Arvore.texto(b) for b in arvore.achar("button", classe="nn-modal-fechar")] == ["Fechar ×"]
    assert not arvore.achar(id="autor")  # o id #autor e da secao de Sobre, nao do modal


def test_sobre_tem_a_secao_autor_com_o_mesmo_conteudo_do_modal(gerado):
    html = _html(gerado, "sobre/index.html")
    arvore = Arvore(html)
    secoes = arvore.achar(id="autor")
    assert len(secoes) == 1 and secoes[0]["tag"] == "article"
    secao = re.search(r'<article[^>]*id="autor".*?</article>', html, flags=re.S)[0]
    modal = next(d for d in re.findall(r"<dialog\b.*?</dialog>", html, flags=re.S) if "nn-modal-autor" in d)
    texto_da_secao = Arvore(secao).texto_visivel()
    assert MOTIVACAO in texto_da_secao and QUEM_SOU in texto_da_secao and MAIS in texto_da_secao
    assert [Arvore.texto(li) for li in Arvore(secao).achar("li")] == FORMACAO
    ids = [e["attrs"]["id"] for e in arvore.achar() if "id" in e["attrs"]]
    assert len(ids) == len(set(ids)), "ids repetidos entre o modal e a secao"
    for titulo in ("Sobre o autor", "Quem sou", "Por que fiz este estudo", "Formação"):
        assert titulo in texto_da_secao and titulo in Arvore(modal).texto_visivel()
    assert secoes[0]["attrs"]["aria-labelledby"] in ids


def test_so_sobre_tem_a_secao_autor(gerado):
    for pagina in PAGINAS:
        assert bool(Arvore(_html(gerado, pagina)).achar(id="autor")) is (pagina == "sobre/index.html"), pagina


def test_o_texto_vem_do_yaml_e_nao_do_modelo(tmp_path):
    novo = "Texto de teste da motivação, trocado só no yaml."

    def trocar(textos):
        textos["autor"]["motivacao"]["texto"] = novo

    saida = tmp_path / "saida"
    gerar_site(Caminhos(raiz=_com_textos_alterados(tmp_path, trocar)), saida, imagens=False)
    for pagina in ("index.html", "sobre/index.html"):
        visivel = Arvore(_html(saida, pagina)).texto_visivel()
        assert novo in visivel and "Fiz este estudo por raiva" not in visivel, pagina


def test_formacao_com_itens_lista_os_itens_e_some_com_a_frase_de_trajetoria(tmp_path):
    def com_itens(textos):
        textos["autor"]["formacao"] = ["Item um de teste", "Item dois de teste"]

    saida = tmp_path / "saida"
    gerar_site(Caminhos(raiz=_com_textos_alterados(tmp_path, com_itens)), saida, imagens=False)
    html = _html(saida, "sobre/index.html")
    secao = re.search(r'<article[^>]*id="autor".*?</article>', html, flags=re.S)[0]
    arvore = Arvore(secao)
    assert [Arvore.texto(li) for li in arvore.achar("li")] == ["Item um de teste", "Item dois de teste"]
    assert FORMACAO_VAZIA not in arvore.texto_visivel()


@pytest.mark.parametrize("valor", ["ausente", None, []])
def test_formacao_ausente_nula_ou_vazia_mostra_a_frase_de_trajetoria_com_link(tmp_path, valor):
    def ajustar(textos):
        if valor == "ausente":
            textos["autor"].pop("formacao", None)
        else:
            textos["autor"]["formacao"] = valor

    saida = tmp_path / "saida"
    gerar_site(Caminhos(raiz=_com_textos_alterados(tmp_path, ajustar)), saida, imagens=False)
    secao = re.search(r'<article[^>]*id="autor".*?</article>', _html(saida, "sobre/index.html"), flags=re.S)[0]
    arvore = Arvore(secao)
    assert FORMACAO_VAZIA in arvore.texto_visivel() and not arvore.achar("li")
    assert [Arvore.texto(a) for a in arvore.achar("a")] == ["dnascimento.com.br", "dnascimento.com.br"]
    assert {a["attrs"]["href"] for a in arvore.achar("a")} == {URL_DO_AUTOR}


# --- validacao de textos.yaml ---


@pytest.mark.parametrize(
    "caminho",
    [
        ("autor",), ("autor", "nome"), ("autor", "titulo"), ("autor", "fechar"), ("autor", "link"),
        ("autor", "quem_sou"), ("autor", "quem_sou", "texto"), ("autor", "quem_sou", "mais"), ("autor", "motivacao"),
        ("autor", "motivacao", "titulo"), ("autor", "motivacao", "texto"), ("autor", "formacao_titulo"),
        ("autor", "formacao_vazia"),
    ],
)
def test_textos_sem_a_chave_do_autor_falha_com_mensagem_clara(tmp_path, caminho):
    def tirar(textos):
        pai = textos
        for chave in caminho[:-1]:
            pai = pai[chave]
        del pai[caminho[-1]]

    raiz = _com_textos_alterados(tmp_path, tirar)
    esperado = ".".join(("textos", *caminho))
    with pytest.raises(ErroConteudo, match=rf"textos\.yaml: falta {re.escape(esperado)}\."):
        gerar_site(Caminhos(raiz=raiz), tmp_path / "saida", imagens=False)


@pytest.mark.parametrize(
    "alterar, mensagem",
    [
        (lambda t: t["autor"]["motivacao"].update(texto="  "), "autor.motivacao.texto"),
        (lambda t: t["autor"].update(formacao="um texto solto"), "autor.formacao"),
        (lambda t: t["autor"].update(formacao=["ok", ""]), "autor.formacao"),
        (lambda t: t["autor"]["quem_sou"].update(mais="Sem o endereço do site."), "autor.link"),
        (lambda t: t["autor"]["quem_sou"].update(texto=""), "autor.quem_sou.texto"),
        (lambda t: t["autor"].update(formacao_vazia="Sem o endereço do site."), "autor.link"),
    ],
)
def test_textos_do_autor_invalidos_falham_com_mensagem_clara(tmp_path, alterar, mensagem):
    raiz = _com_textos_alterados(tmp_path, alterar)
    with pytest.raises(ErroConteudo, match=re.escape(mensagem)):
        gerar_site(Caminhos(raiz=raiz), tmp_path / "saida", imagens=False)


# --- licenca da foto e da marca do autor ---


@pytest.mark.parametrize("arquivo", [FOTO_DO_REPOSITORIO, *MARCAS_DO_REPOSITORIO], ids=lambda a: a.name)
def test_se_um_arquivo_do_autor_existir_o_license_cita_a_excecao(arquivo):
    """Foto e marca sao do autor, nao da CC BY 4.0: existindo o arquivo, o LICENSE.md tem de dizer isso."""
    licenca = (RAIZ / "LICENSE.md").read_text(encoding="utf-8")
    if arquivo.exists():
        caminho = f"src/nordeste/site/estaticos/{arquivo.name}"
        assert caminho in licenca, f"{arquivo.name} existe, mas o LICENSE.md nao o cita"
        trecho = licenca.split(caminho, 1)[1].split("\n- ", 1)[0]
        trecho = " ".join(trecho.split())
        assert "© Júlio Diógenes, todos os direitos reservados" in trecho
        assert re.search(r"não (está|estão) cobertas? pela CC BY 4\.0", trecho)
