"""Página inicial editorial: placar das perguntas, resposta primeiro em cada pergunta, saídas, legenda com as siglas dos
governos, menu lateral e capítulos (plano docs/plans/2026-11-03-inicio-intuitivo.md, tarefas 1 a 7)."""

import re
from pathlib import Path

import pandas as pd
import pytest
import yaml

from nordeste.caminhos import Caminhos
from nordeste.site import gerar
from nordeste.site.conteudo import ErroConteudo, carregar_conteudo
from nordeste.site.gerar import gerar_site

from auxiliares import RAIZ, Arvore, alterar_base, copiar_base

CARDS_DAS_PERGUNTAS = {  # a tabela do plano (tarefa 4)
    "renda-per-capita": "pibpc", "economia": "vol", "escola": "ideb", "trabalho": "desoc", "idhm": "idhm",
    "pobreza": "pobreza",
}


def _ler(saida: Path, pagina: str = "index.html") -> str:
    return (saida / pagina).read_text(encoding="utf-8")


def _artigo(html: str, id_: str) -> str:
    inicio = re.search(rf'<article class="nn-capitulo[^"]*" id="q-{id_}">', html).start()
    return html[inicio:html.index("</article>", inicio)]


def _subir_a_pobreza(base: pd.DataFrame) -> pd.DataFrame:
    """A pobreza do Nordeste termina acima do que começou: o fecho e o card da pobreza saem (a pergunta fica)."""
    pobreza = base[(base["indicador_id"] == "pobreza") & (base["territorio_id"] == "NE") & (base["valor"] != "")]
    base.loc[pobreza["ano"].astype(int).idxmax(), "valor"] = "99.0"
    return base


def _sem_pobreza_do_nordeste(base: pd.DataFrame) -> pd.DataFrame:
    """O lide da pobreza cita um destaque que some: a pergunta sai inteira."""
    return base[~((base["indicador_id"] == "pobreza") & (base["territorio_id"] == "NE"))]


@pytest.fixture(scope="module")
def conteudo():
    return carregar_conteudo(RAIZ / "metadados" / "site")


@pytest.fixture(scope="module")
def gerado(tmp_path_factory) -> Path:
    saida = tmp_path_factory.mktemp("site") / "saida"
    gerar_site(Caminhos(raiz=RAIZ), saida, imagens=False)
    return saida


def _gerar_com(tmp_path_factory, alterar) -> tuple[Path, gerar.RelatorioSite]:
    raiz = copiar_base(tmp_path_factory.mktemp("repo") / "repo")
    alterar_base(raiz, alterar)
    saida = tmp_path_factory.mktemp("site") / "saida"
    return saida, gerar_site(Caminhos(raiz=raiz), saida, imagens=False)


@pytest.fixture(scope="module")
def sem_fecho(tmp_path_factory):
    return _gerar_com(tmp_path_factory, _subir_a_pobreza)


@pytest.fixture(scope="module")
def sem_pergunta(tmp_path_factory):
    return _gerar_com(tmp_path_factory, _sem_pobreza_do_nordeste)


# --- tarefa 2: placar ---


def _placar(html: str) -> list[dict]:
    trecho = html[html.index('<ol class="nn-placar-lista">'):html.index("</ol>", html.index('<ol class="nn-placar-lista">'))]
    linhas = []
    for li in re.findall(r"<li>.*?</li>", trecho, flags=re.S):
        arvore = Arvore(li)
        veredito = arvore.achar(classe="nn-placar-veredito")[0]
        linhas.append({
            "href": arvore.achar("a")[0]["attrs"]["href"],
            "numero": Arvore.texto(arvore.achar(classe="nn-placar-num")[0]),
            "tema": Arvore.texto(arvore.achar(classe="nn-placar-tema")[0]),
            "mito": Arvore.texto(arvore.achar(classe="nn-so-leitor")[0]),
            "veredito": Arvore.texto(veredito),
            "sem_veredito": "nn-placar-sem-veredito" in veredito["attrs"]["class"].split(),
        })
    return linhas


def test_placar_tem_uma_linha_por_pergunta_na_ordem_com_o_veredito_do_fecho(gerado, conteudo):
    html = _ler(gerado)
    arvore = Arvore(html)
    placar = arvore.achar("section", classe="nn-placar")
    assert len(placar) == 1
    assert Arvore.texto(arvore.achar("h2", id="titulo-placar")[0]) == conteudo.textos["placar"]["titulo"]
    # depois da faixa de numeros e antes das perguntas
    assert html.index("nn-faixa-abertura") < html.index('class="nn-card nn-placar"') < html.index('id="resumo"')
    linhas = _placar(html)
    artigos = [a["attrs"]["id"] for a in arvore.achar("article", classe="nn-capitulo")]
    assert [l["href"] for l in linhas] == [f"#{i}" for i in artigos] == [f"#q-{p['id']}" for p in conteudo.perguntas]
    assert [l["numero"] for l in linhas] == [f"{i:02d}" for i in range(1, len(linhas) + 1)]
    for linha, p in zip(linhas, conteudo.perguntas):
        assert arvore.achar(id=linha["href"][1:])  # cada link leva a um id que existe
        fecho = Arvore.texto(Arvore(_artigo(html, p["id"])).achar("p", classe="nn-fecho")[0]).removeprefix("No frigir dos ovos: ")
        assert linha["veredito"] == fecho[0].upper() + fecho[1:] and not linha["sem_veredito"]
        assert linha["tema"] == p["rotulo"]
        # a frase feita, sem o "Será?", para quem ouve a pagina
        assert linha["mito"] and "Será?" not in linha["mito"] and linha["mito"] in Arvore.texto(Arvore(_artigo(html, p["id"])).achar("h2")[0])


def test_placar_sem_fecho_mostra_ver_a_resposta(sem_fecho, conteudo):
    saida, relatorio = sem_fecho
    assert "pobreza" in relatorio.fechos_suprimidos
    linhas = {l["href"]: l for l in _placar(_ler(saida))}
    assert linhas["#q-pobreza"]["veredito"] == conteudo.textos["placar"]["sem_veredito"] == "Ver a resposta"
    assert linhas["#q-pobreza"]["sem_veredito"]
    pobreza = next(p for p in conteudo.perguntas if p["id"] == "pobreza")
    assert pobreza["fecho"]["texto"][1:] not in _ler(saida)  # nem no placar, nem no bloco
    assert sum(not l["sem_veredito"] for l in linhas.values()) == len(conteudo.perguntas) - 1


def test_pergunta_que_saiu_inteira_some_do_placar_e_do_menu_lateral(sem_pergunta, conteudo):
    saida, _ = sem_pergunta
    html = _ler(saida)
    arvore = Arvore(html)
    assert not arvore.achar("article", id="q-pobreza")
    assert "#q-pobreza" not in html  # nenhum link quebrado: nem no placar, nem no menu lateral
    assert len(_placar(html)) == len(conteudo.perguntas) - 1
    ids = {e["attrs"]["id"] for e in arvore.elementos if "id" in e["attrs"]}
    assert all(a["attrs"]["href"][1:] in ids for a in arvore.achar("a") if a["attrs"].get("href", "").startswith("#q-"))


# --- tarefa 3: a resposta primeiro em cada pergunta ---


def test_primeiro_grafico_fora_dos_details_e_os_outros_dentro(gerado, conteudo):
    html = _ler(gerado)
    rotulos = conteudo.textos["perguntas_rotulos"]
    for p in conteudo.perguntas:
        artigo = _artigo(html, p["id"])
        corpo = artigo[artigo.index('<div class="nn-pergunta-corpo">'):artigo.index("<details")]
        assert len(re.findall(r'<div class="nn-grafico">', corpo)) == 1, p["id"]  # o primeiro grafico, a vista
        assert f'id="{p["graficos"][0]["id"].replace("_", "-")}"' in corpo
        mais = re.search(r'<details class="nn-mais-graficos">(.*?)</details>', artigo, flags=re.S)
        resto = p["graficos"][1:]
        if not resto:
            assert mais is None, p["id"]
            continue
        assert len(re.findall(r'<div class="nn-grafico">', mais[1])) == len(resto)
        resumo = Arvore.texto(Arvore(mais[1]).achar("summary")[0])
        esperado = rotulos["mais_um_grafico"] if len(resto) == 1 else rotulos["mais_graficos"].replace("[n]", str(len(resto)))
        assert resumo == esperado and re.fullmatch(r"Ver mais \d+ gráficos?", resumo)


def test_fonte_e_alerta_ficam_em_fonte_e_metodo(gerado, conteudo):
    html = _ler(gerado)
    for p in conteudo.perguntas:
        artigo = _artigo(html, p["id"])
        fonte = re.search(r'<details class="nn-fonte-metodo">(.*?)</details>', artigo, flags=re.S)
        assert fonte and Arvore.texto(Arvore(fonte[1]).achar("summary")[0]) == "Fonte e método"
        assert artigo.count('class="nn-fonte"') == 1 and 'class="nn-fonte"' in fonte[1]
        assert ("nn-alerta" in artigo) == ("alerta" in p)
        if "alerta" in p:
            assert "nn-alerta" in fonte[1] and artigo.count("nn-alerta") == 1


def test_nenhum_texto_das_perguntas_sumiu(gerado, conteudo):
    """Tudo o que a pergunta tinha continua no bloco (a vista ou dentro de um <details>): lide, explicacao, fecho,
    alerta, fontes, titulos e subtitulos dos graficos e cada linha da tabela dos numeros."""
    html = _ler(gerado)
    from nordeste.site.conteudo import calcular_destaques, preencher
    from nordeste.site.dados import DadosSite
    destaques = calcular_destaques(DadosSite.carregar(Caminhos(raiz=RAIZ)), conteudo)
    for p in conteudo.perguntas:
        texto = Arvore.texto(Arvore(_artigo(html, p["id"])).elementos[0])
        partes = [p["lide"], p.get("explicacao"), p["fecho"]["texto"], p.get("alerta"), *p["fonte"]]
        partes += [g.get(c) for g in p["graficos"] for c in ("titulo", "subtitulo")]
        for parte in filter(None, partes):
            assert " ".join(preencher(parte, destaques).split()) in texto, (p["id"], parte)
        assert len(Arvore(_artigo(html, p["id"])).achar("tr")) > len(p["graficos"])


def test_templates_do_ampliado_ficam_fora_dos_details(gerado):
    html = _ler(gerado)
    fim_das_perguntas = html.index("</section>", html.rindex('<article class="nn-capitulo'))
    templates = re.findall(r'<template class="nn-ampliado" id="(nn-ampliado-[^"]+)"', html)
    assert templates and html.index("<template") > fim_das_perguntas
    botoes = re.findall(r'data-ampliado="(nn-ampliado-[^"]+)"', html)
    assert sorted(botoes) == sorted(templates)  # cada Ampliar, inclusive os de dentro dos <details>, tem o seu


# --- tarefa 4: saidas ---


def test_cada_pergunta_tem_o_card_da_tabela_do_plano(conteudo):
    assert {p["id"]: p.get("card") for p in conteudo.perguntas} == CARDS_DAS_PERGUNTAS


def test_saidas_levam_a_paginas_geradas(gerado, conteudo):
    html = _ler(gerado)
    textos = conteudo.textos["saidas"]
    for p in conteudo.perguntas:
        nav = re.search(r'<nav class="nn-saidas"[^>]*>(.*?)</nav>', _artigo(html, p["id"]), flags=re.S)
        assert nav, p["id"]
        links = [(a["attrs"]["href"], Arvore.texto(a)) for a in Arvore(nav[1]).achar("a")]
        assert links == [(f"/cards/{CARDS_DAS_PERGUNTAS[p['id']]}/", textos["card"]), ("/estados/", textos["estados"]),
                         ("/explorar/", textos["explorar"])]
        for href, _ in links:
            assert (gerado / href.strip("/") / "index.html").is_file(), href
    rotulos = re.findall(r'<nav class="nn-saidas" aria-label="([^"]+)"', html)
    assert len(set(rotulos)) == len(conteudo.perguntas)  # um nome por pergunta, sem landmark repetido


def test_card_suprimido_tira_o_botao_em_vez_de_levar_a_404(sem_fecho):
    saida, relatorio = sem_fecho
    assert "pobreza" in relatorio.cards_suprimidos and not (saida / "cards" / "pobreza").exists()
    html = _ler(saida)
    assert "/cards/pobreza/" not in html
    nav = re.search(r'<nav class="nn-saidas"[^>]*>(.*?)</nav>', _artigo(html, "pobreza"), flags=re.S)[1]
    assert [a["attrs"]["href"] for a in Arvore(nav).achar("a")] == ["/estados/", "/explorar/"]


def test_card_inexistente_em_perguntas_yaml_e_erro_de_conteudo(tmp_path):
    raiz = copiar_base(tmp_path / "repo")
    arquivo = raiz / "metadados" / "site" / "perguntas.yaml"
    texto = arquivo.read_text(encoding="utf-8")
    assert texto.count("  card: vol\n") == 1
    arquivo.write_text(texto.replace("  card: vol\n", "  card: nao-existe\n"), encoding="utf-8")
    with pytest.raises(ErroConteudo, match=r"pergunta economia: card 'nao-existe' nao esta em cards.yaml"):
        gerar_site(Caminhos(raiz=raiz), tmp_path / "saida", imagens=False)


# --- tarefa 5: legenda com as siglas dos governos ---


def test_legenda_das_perguntas_traz_as_siglas_do_csv_de_governos(gerado):
    governos = pd.read_csv(RAIZ / "metadados" / "governos.csv", dtype=str)
    apelidos = list(dict.fromkeys(governos.loc[governos["interino"] == "não", "apelido"]))
    esperado = " · ".join(f"{a[0]} = {a}" for a in apelidos)
    assert esperado == "F = FHC · L = Lula · D = Dilma · T = Temer · B = Bolsonaro"
    html = _ler(gerado)
    legenda = re.search(r'<div class="nn-folha">\s*<div class="nn-legenda"[^>]*>(.*?)</div>', html, flags=re.S)[1]
    siglas = Arvore(legenda).achar(classe="nn-legenda-siglas")
    assert len(siglas) == 1 and Arvore.texto(siglas[0]) == f"Siglas dos governos nos gráficos: {esperado}"
    # a legenda do modal (nos <template>) segue sem as siglas
    assert html.count("nn-legenda-siglas") == 1


# --- tarefa 6: chamada "Como chegamos" depois das perguntas ---


def test_chamada_vem_depois_das_perguntas(gerado):
    html = _ler(gerado)
    fim_das_perguntas = html.index("</section>", html.rindex('<article class="nn-capitulo'))
    assert fim_das_perguntas < html.index('<section class="nn-chamada-historia"')


# --- tarefa 7: capitulos, menu lateral e folha ---


def test_capitulos_numerados_sem_cartao_e_os_pares_invertidos(gerado, conteudo):
    html = _ler(gerado)
    arvore = Arvore(html)
    artigos = arvore.achar("article", classe="nn-capitulo")
    assert len(artigos) == len(conteudo.perguntas)
    for n, (artigo, p) in enumerate(zip(artigos, conteudo.perguntas), 1):
        classes = artigo["attrs"]["class"].split()
        assert "nn-card" not in classes
        assert ("nn-capitulo-invertido" in classes) == (n % 2 == 0), p["id"]
        eyebrow = Arvore(_artigo(html, p["id"])).achar("p", classe="nn-eyebrow")[0]
        assert Arvore.texto(eyebrow) == f"{n:02d} / {p['rotulo']}"
    # a folha guarda a legenda e os capitulos; o menu lateral vem antes dela, no #resumo
    resumo = html[html.index('id="resumo"'):]
    assert resumo.index('<nav class="nn-indice"') < resumo.index('<div class="nn-folha">') < resumo.index('class="nn-legenda"')


def test_menu_lateral_tem_um_link_por_pergunta_na_ordem(gerado, conteudo):
    html = _ler(gerado)
    nav = re.search(r'<nav class="nn-indice" aria-label="([^"]+)">(.*?)</nav>', html, flags=re.S)
    assert nav[1] == conteudo.textos["perguntas_rotulos"]["indice"]
    links = Arvore(nav[2]).achar("a")
    assert [a["attrs"]["href"] for a in links] == [f"#q-{p['id']}" for p in conteudo.perguntas]
    for a, p in zip(re.findall(r"<a .*?</a>", nav[2], flags=re.S), conteudo.perguntas):
        item = Arvore(a)
        assert Arvore.texto(item.achar("b")[0]) == p["rotulo"]
        assert "Será?" not in Arvore.texto(item.achar("small")[0])
    assert "aria-current" not in nav[2]  # quem marca a pergunta em leitura e o site.js; sem ele, nada fica marcado


def test_rotulo_de_mais_graficos_sem_o_marcador_e_erro_de_conteudo(tmp_path):
    raiz = copiar_base(tmp_path / "repo")
    arquivo = raiz / "metadados" / "site" / "textos.yaml"
    textos = yaml.safe_load(arquivo.read_text(encoding="utf-8"))
    textos["perguntas_rotulos"]["mais_graficos"] = "Ver mais gráficos"
    arquivo.write_text(yaml.safe_dump(textos, allow_unicode=True, sort_keys=False), encoding="utf-8")
    with pytest.raises(ErroConteudo, match="mais_graficos"):
        gerar_site(Caminhos(raiz=raiz), tmp_path / "saida", imagens=False)


@pytest.mark.parametrize("chave", ["placar", "perguntas_rotulos", "saidas"])
def test_textos_novos_do_inicio_sao_exigidos(tmp_path, chave):
    raiz = copiar_base(tmp_path / "repo")
    arquivo = raiz / "metadados" / "site" / "textos.yaml"
    textos = yaml.safe_load(arquivo.read_text(encoding="utf-8"))
    del textos[chave]
    arquivo.write_text(yaml.safe_dump(textos, allow_unicode=True, sort_keys=False), encoding="utf-8")
    with pytest.raises(ErroConteudo, match=f"falta a seção textos.{chave}|falta textos.{chave}"):
        gerar_site(Caminhos(raiz=raiz), tmp_path / "saida", imagens=False)
