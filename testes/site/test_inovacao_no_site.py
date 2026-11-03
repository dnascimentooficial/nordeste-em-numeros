"""Página Inovação: gera do inovacao.yaml com a base publicada, números iguais aos da base, placar que segue os
vereditos (e as condições), régua de leitura com a população tirada da base, menu com o cartão novo e o IBID por posição
em Estados."""

import re
from pathlib import Path

import pandas as pd
import pytest

from nordeste.caminhos import Caminhos
from nordeste.site.conteudo import fatia_do_brasil
from nordeste.site.dados import DadosSite
from nordeste.site.explorar import INDICADORES_ESTADOS, UFS, vista_estados
from nordeste.site.formatacao import numero
from nordeste.site.gerar import CAPAS, gerar_site
from nordeste.site.inovacao import carregar_inovacao

from auxiliares import RAIZ, Arvore, alterar_base, copiar_base

PAGINA = "inovacao/index.html"


@pytest.fixture(scope="module")
def dados() -> DadosSite:
    return DadosSite.carregar(Caminhos(raiz=RAIZ))


@pytest.fixture(scope="module")
def conteudo() -> dict:
    return carregar_inovacao(RAIZ / "metadados" / "site")


@pytest.fixture(scope="module")
def gerado(tmp_path_factory):
    saida = tmp_path_factory.mktemp("site") / "saida"
    return saida, gerar_site(Caminhos(raiz=RAIZ), saida, imagens=False)


def _ler(saida: Path, pagina: str = PAGINA) -> str:
    return (saida / pagina).read_text(encoding="utf-8")


def _artigo(html: str, id_: str) -> str:
    inicio = html.index(f'id="q-{id_}"')
    return html[inicio:html.index("</article>", inicio)]


def _placar(html: str) -> list[dict]:
    trecho = html[html.index('<ol class="nn-placar-lista">'):html.index("</ol>", html.index('<ol class="nn-placar-lista">'))]
    linhas = []
    for li in re.findall(r"<li>.*?</li>", trecho, flags=re.S):
        arvore = Arvore(li)
        veredito = arvore.achar(classe="nn-placar-veredito")[0]
        linhas.append({"href": arvore.achar("a")[0]["attrs"]["href"], "veredito": Arvore.texto(veredito),
                       "sem": "nn-placar-sem-veredito" in veredito["attrs"]["class"].split()})
    return linhas


# --- a pagina ---

def test_pagina_gera_com_capa_placar_capitulos_e_menu_lateral(gerado, conteudo):
    saida, relatorio = gerado
    assert PAGINA in relatorio.paginas
    assert not [s for s in relatorio.fechos_suprimidos if s.startswith("inovacao:")]
    html = _ler(saida)
    arvore = Arvore(html)
    assert arvore.achar("section", classe="nn-capa")[0]["attrs"]["class"].split()[-1] == "nn-capa-" + CAPAS["inovacao"][:-5]
    assert Arvore.texto(arvore.achar("h1")[0]) == conteudo["capa"]["titulo"]
    assert "Imagem:" in Arvore.texto(arvore.achar(classe="nn-capa-credito")[0])  # credito da imagem na capa
    capitulos = [a["attrs"]["id"] for a in arvore.achar("article", classe="nn-capitulo")]
    assert capitulos == [f"q-{c['id']}" for c in conteudo["capitulos"]]
    indice = [a["attrs"]["href"] for a in arvore.achar("nav", classe="nn-indice")[0:1] for a in Arvore(
        html[html.index('<nav class="nn-indice"'):html.index("</nav>", html.index('<nav class="nn-indice"'))]).achar("a")]
    assert indice == [f"#{c}" for c in capitulos]
    assert html.index('class="nn-capa') < html.index('class="nn-card nn-placar"') < html.index('id="resumo"')
    assert len(arvore.achar("nav", classe="nn-saidas")) == len(capitulos)


def test_placar_tem_os_vereditos_dos_capitulos_com_numeros(gerado, conteudo):
    saida, _ = gerado
    html = _ler(saida)
    com_numeros = [c for c in conteudo["capitulos"] if not c.get("texto")]
    linhas = _placar(html)
    assert [l["href"] for l in linhas] == [f"#q-{c['id']}" for c in com_numeros]
    for linha, c in zip(linhas, com_numeros):
        fecho = Arvore.texto(Arvore(_artigo(html, c["id"])).achar("p", classe="nn-fecho")[0])
        fecho = fecho.removeprefix(conteudo["placar"]["fecho"] + " ")
        assert not linha["sem"] and linha["veredito"] == fecho[0].upper() + fecho[1:]
    assert "q-ecossistema" not in "".join(l["href"] for l in linhas)  # o capitulo de texto nao tem veredito


def test_os_numeros_do_texto_saem_da_base(gerado, dados):
    saida, _ = gerado
    texto = Arvore(_ler(saida)).texto_visivel()
    doutores = {p.ano: p.valor for p in dados.serie("doutores_titulados", "NE", serie="sem_filtro_de_nota")}
    brasil = {p.ano: p.valor for p in dados.serie("doutores_titulados", "BR", serie="sem_filtro_de_nota")}
    assert f"{numero(doutores[2024], 0)} em 2024, {numero(doutores[2024] / brasil[2024] * 100, 1)}% do Brasil" in texto
    assert "4.328 em 2024, 16,7% do Brasil" in texto
    patentes = {p.ano: p.valor for p in dados.serie("patentes_residentes", "NE")}
    assert f"Em 2025, foram {numero(patentes[2025], 0)}, 14,2%" in texto and patentes[2025] == 1352
    assert "4.278 empresas que inovaram entre as 12.654 do Nordeste, 33,8%. No Brasil, 33,9%" in texto
    assert "foram de 57.243 para 75.113 em 2024: 9,8% dos empregos do setor no Brasil" in texto
    assert "de 4,9% em 2000 para 11,9% em 2019" in texto
    assert "Em 2014, 37% dos domicílios do Nordeste" in texto and "Em 2025, eram 84%, e o Brasil, 86%" in texto


def test_regua_poe_a_populacao_do_mesmo_ano_tirada_da_base(gerado, dados):
    saida, _ = gerado
    html = _ler(saida)
    populacao = {p.ano: p.valor for p in fatia_do_brasil(dados, "populacao", "NE")}
    for capitulo, rotulo, ano in (("conhecimento", "Doutores titulados", 2024), ("inovacao", "Pedidos de patente", 2025),
                                  ("trabalho", "Empregos em TI", 2024), ("conhecimento", "Gasto estadual em C&T", 2019)):
        regua = Arvore(_artigo(html, capitulo)).achar("section", classe="nn-leitura")
        assert regua, capitulo
        texto = Arvore.texto(regua[0])
        assert f"{rotulo}" in texto and f"({ano})" in texto
        assert f"PopulaçãodoNordeste({ano}){numero(populacao[ano], 1)}%" in texto.replace(" ", ""), (capitulo, texto)


def test_posicoes_do_ibid_saem_da_ficha_de_posicao(gerado, dados):
    saida, _ = gerado
    tabela = Arvore(_artigo(_ler(saida), "inovacao")).achar("section", classe="nn-posicoes")[0]
    linhas = [Arvore.texto(tr) for tr in Arvore(re.search(r"<tbody>.*?</tbody>", _ler(saida), flags=re.S)[0]).achar("tr")]
    texto = Arvore.texto(tabela).replace(" ", "")
    assert "Piauí21º18º" in texto and "Paraíba18º15º" in texto and "RiodoNorte13º12º" in texto.replace("Grande", "")
    assert linhas  # a tabela tem corpo
    assert texto.index("Norte13º") < texto.index("Maranhão")  # do mais bem colocado ao ultimo


def test_ecossistema_e_so_texto_com_a_etiqueta(gerado, conteudo):
    saida, _ = gerado
    artigo = _artigo(_ler(saida), "ecossistema")
    arvore = Arvore(artigo)
    assert Arvore.texto(arvore.achar(classe="nn-etiqueta")[0]) == "Índice de associação setorial, não é estatística oficial"
    assert "<svg" not in artigo.replace('class="nn-icone"', "")
    texto = Arvore.texto(arvore.achar("article")[0]) if arvore.achar("article") else " ".join(arvore.visivel)
    for trecho in ("26º em 2021", "1º em 2025", "100 pontos", "oito estados", "Piauí e Pernambuco",
                   "Rio Grande do Norte e Alagoas", "541 empresas e 24 mil profissionais em 2025, segundo o próprio Porto Digital",
                   "113 iniciativas", "13 de outubro de 2025"):
        assert trecho in " ".join(texto.split()), trecho
    assert "19 no Nordeste" not in texto and " 19 " not in texto


def test_graficos_alem_do_principal_ficam_recolhidos(gerado, conteudo):
    saida, _ = gerado
    html = _ler(saida)
    for c in conteudo["capitulos"]:
        if c.get("texto"):
            continue
        artigo = _artigo(html, c["id"])
        principal = c["graficos"][0]["id"].replace("_", "-")
        assert artigo.index(f'id="{principal}"') < artigo.index('class="nn-pergunta-texto"')
        for g in c["graficos"][1:]:
            gid = g["id"].replace("_", "-")
            assert artigo.index('<details class="nn-mais-graficos">') < artigo.index(f'id="{gid}"'), gid


# --- vereditos com condicao ---

@pytest.fixture(scope="module")
def sem_veredito(tmp_path_factory):
    """Patentes do Nordeste em 2025 com metade do Brasil: a fatia passa da populacao e o veredito do cap. 3 cai."""
    raiz = copiar_base(tmp_path_factory.mktemp("repo") / "repo")

    def inflar(base: pd.DataFrame) -> pd.DataFrame:
        alvo = (base.indicador_id == "patentes_residentes") & (base.territorio_id == "NE") & (base.ano == "2025")
        base.loc[alvo, "valor"] = "5000.0"
        return base
    alterar_base(raiz, inflar)
    saida = tmp_path_factory.mktemp("site") / "saida"
    return saida, gerar_site(Caminhos(raiz=raiz), saida, imagens=False)


def test_veredito_cuja_condicao_falha_sai_da_pagina_e_do_placar(sem_veredito, conteudo):
    saida, relatorio = sem_veredito
    assert "inovacao:inovacao" in relatorio.fechos_suprimidos
    html = _ler(saida)
    linhas = {l["href"]: l for l in _placar(html)}
    assert linhas["#q-inovacao"]["sem"] and linhas["#q-inovacao"]["veredito"] == conteudo["placar"]["sem_veredito"]
    assert not Arvore(_artigo(html, "inovacao")).achar("p", classe="nn-fecho")
    assert not linhas["#q-conectividade"]["sem"]


# --- menu e Estados ---

def test_menu_tem_o_cartao_da_inovacao_no_grupo_historias(gerado):
    saida, _ = gerado
    html = _ler(saida, "index.html")
    cabecalho = re.search(r"<header\b.*?</header>", html, flags=re.S)[0]
    grupos = re.findall(r'<details class="nn-menu-grupo".*?</details>', cabecalho, flags=re.S)
    historias = Arvore(grupos[0])
    assert Arvore.texto(historias.achar("summary")[0]) == "Histórias"
    assert [a["attrs"]["href"] for a in historias.achar("a")] == ["/como-chegamos/", "/inovacao/", "/cards/"]
    assert "Inovação" in Arvore.texto(historias.achar("a", href="/inovacao/")[0])
    na_pagina = Arvore(re.search(r"<header\b.*?</header>", _ler(saida), flags=re.S)[0])
    assert na_pagina.achar("a", href="/inovacao/", aria_current="page")


def test_estados_mostra_o_ibid_pela_posicao_com_a_nota(gerado, dados):
    saida, _ = gerado
    arvore = Arvore(_ler(saida, "estados/index.html"))
    ind = next(i for i in INDICADORES_ESTADOS if i.chave == "ibid")
    assert ind.indicador_id == "ibid_posicao" and not ind.maior_melhor
    vista = vista_estados(dados, ind)
    ultimo = vista["ano_do_ranking"]
    posicoes = {uf: next(p.valor for p in dados.serie("ibid_posicao", uf) if p.ano == ultimo) for uf in UFS}
    assert [r["valor"] for r in vista["ranking"]] == [f"{int(v)}º no país" for v in sorted(posicoes.values())]
    assert vista["ranking"][0]["posicao"] == "1º Rio Grande do Norte" and vista["ranking"][0]["valor"] == "12º no país"
    bloco = arvore.achar("div", classe="nn-vista", data_vista="ibid")[0]
    assert "posição de cada estado entre as 27" in Arvore.texto(bloco)
    piaui = next(l for l in vista["linhas"] if l["uf"] == "PI")
    assert piaui["celulas"][0]["titulo"] == "Piauí, 2014: 21º no país"
    assert piaui["celulas"][0]["classe"] < piaui["celulas"][-1]["classe"]  # 21º -> 18º: a celula de 2025 e mais escura
