"""Conteudo da pagina Inovacao (metadados/site/inovacao.yaml): capa, placar, capitulos com a regua de leitura e o
capitulo de texto sobre o ecossistema.

Mesmas regras do Inicio: nenhum numero de dado e digitado (marcadores `{id.campo:formato}` preenchidos pela base, com
os destaques declarados no proprio arquivo), e cada veredito tem uma condicao que, falsa, o tira da pagina e do placar.
O capitulo sem graficos (`texto: true`) traz a etiqueta do que ele e e, em vez de graficos, paragrafos e/ou blocos
(titulo, numeros em destaque, paragrafos, tabela e a fonte do bloco): fatos datados de fora da base, sem marcador.
"""

from pathlib import Path

import yaml

from nordeste.site.idioma import PADRAO, ErroTraducao, traduzir
from nordeste.site.conteudo import (
    ErroConteudo, _exigir_chaves, _validar_destaques, _validar_grafico, _validar_textos_e_condicoes,
)

ARQUIVO = "inovacao.yaml"
_CHAVES = {"obrigatorias": {"destaques", "capa", "placar", "regua", "capitulos"}, "opcionais": set()}
_CHAVES_DO_CAPITULO = {
    "obrigatorias": {"id", "rotulo", "titulo", "lide", "graficos", "fecho", "fonte"},
    "opcionais": {"explicacao", "alerta", "regua", "posicoes"},
}
_CHAVES_DO_TEXTO = {
    "obrigatorias": {"id", "rotulo", "titulo", "texto", "etiqueta"},
    "opcionais": {"paragrafos", "blocos", "fonte", "fecho"},
}
_CHAVES_DO_BLOCO = {"obrigatorias": {"titulo", "fonte"}, "opcionais": {"destaques", "paragrafos", "tabela"}}
_CHAVES_DO_NUMERO = {"obrigatorias": {"valor", "rotulo"}, "opcionais": {"ano"}}
_CHAVES_DA_TABELA = {"obrigatorias": {"titulo", "colunas", "linhas"}, "opcionais": set()}


def _lista_de_textos(valor: object) -> bool:
    return isinstance(valor, list) and bool(valor) and all(isinstance(p, str) and p for p in valor)


def _validar_capitulo_de_texto(capitulo: dict) -> None:
    onde = f"{ARQUIVO}, capítulo {capitulo.get('id')}"
    _exigir_chaves(capitulo, _CHAVES_DO_TEXTO, onde)
    if "paragrafos" not in capitulo and "blocos" not in capitulo:
        raise ErroConteudo(f"{onde}: o capítulo de texto precisa de paragrafos ou blocos.")
    for campo in ("paragrafos", "fonte"):
        if campo in capitulo and not _lista_de_textos(capitulo[campo]):
            raise ErroConteudo(f"{onde}: {campo} é uma lista de textos.")
    if "fecho" in capitulo and not (isinstance(capitulo["fecho"], str) and capitulo["fecho"]):
        raise ErroConteudo(f"{onde}: fecho é um texto.")
    blocos = capitulo.get("blocos", [])
    if not isinstance(blocos, list) or ("blocos" in capitulo and not blocos):
        raise ErroConteudo(f"{onde}: blocos é uma lista com ao menos um bloco.")
    textos = list(capitulo.get("paragrafos", [])) + [capitulo.get("fecho", "")]
    for n, bloco in enumerate(blocos, start=1):
        ondeb = f"{onde}, bloco {n}"
        _exigir_chaves(bloco, _CHAVES_DO_BLOCO, ondeb)
        if "paragrafos" in bloco and not _lista_de_textos(bloco["paragrafos"]):
            raise ErroConteudo(f"{ondeb}: paragrafos é uma lista de textos.")
        for numero in bloco.get("destaques", []):
            _exigir_chaves(numero, _CHAVES_DO_NUMERO, f"{ondeb}, destaque")
            textos += [str(v) for v in numero.values()]
        if "tabela" in bloco:
            tabela = bloco["tabela"]
            _exigir_chaves(tabela, _CHAVES_DA_TABELA, f"{ondeb}, tabela")
            if any(not isinstance(l, list) or len(l) != len(tabela["colunas"]) for l in tabela["linhas"]):
                raise ErroConteudo(f"{ondeb}, tabela: cada linha tem uma célula por coluna.")
            textos += [str(c) for l in tabela["linhas"] for c in l]
        textos += [bloco["titulo"], bloco["fonte"]] + list(bloco.get("paragrafos", []))
    if any("{" in t or "}" in t for t in textos):
        raise ErroConteudo(f"{onde}: o capítulo de texto não usa marcador de dado.")
_CHAVES_DA_REGUA = {"obrigatorias": {"rotulo", "destaque"}, "opcionais": set()}
_CHAVES_DAS_POSICOES = {"obrigatorias": {"titulo", "indicador", "nota"}, "opcionais": set()}


def _validar_capitulo(capitulo: object, destaques: dict) -> None:
    if isinstance(capitulo, dict) and capitulo.get("texto") is True:
        _validar_capitulo_de_texto(capitulo)
        return
    onde = f"{ARQUIVO}, capítulo {capitulo.get('id') if isinstance(capitulo, dict) else capitulo!r}"
    _exigir_chaves(capitulo, _CHAVES_DO_CAPITULO, onde)
    _exigir_chaves(capitulo["fecho"], {"obrigatorias": {"texto", "condicao"}, "opcionais": set()}, f"{onde}, fecho")
    if not isinstance(capitulo["graficos"], list) or not capitulo["graficos"]:
        raise ErroConteudo(f"{onde}: graficos deve ser uma lista com ao menos um gráfico.")
    for grafico in capitulo["graficos"]:
        _validar_grafico(grafico, f"{onde}, gráfico")
    for item in capitulo.get("regua", []):
        _exigir_chaves(item, _CHAVES_DA_REGUA, f"{onde}, régua")
        if item["destaque"] not in destaques or destaques[item["destaque"]]["tipo"] != "fatia":
            raise ErroConteudo(f"{onde}, régua: {item['destaque']!r} não é destaque do tipo fatia.")
    if "posicoes" in capitulo:
        _exigir_chaves(capitulo["posicoes"], _CHAVES_DAS_POSICOES, f"{onde}, posições")


def carregar_inovacao(pasta: Path, idioma: str = PADRAO) -> dict | None:
    """Le e valida inovacao.yaml; None se o arquivo nao existe (a pagina nao e gerada)."""
    caminho = pasta / ARQUIVO
    if not caminho.exists():
        return None
    try:
        conteudo = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as erro:
        raise ErroConteudo(f"{caminho}: não foi possível ler ({erro}).") from erro
    try:
        conteudo = traduzir(conteudo, pasta, "inovacao", idioma)
    except ErroTraducao as erro:
        raise ErroConteudo(str(erro)) from erro
    _exigir_chaves(conteudo, _CHAVES, ARQUIVO)
    _validar_destaques(conteudo["destaques"])
    regua = conteudo["regua"]
    _exigir_chaves(regua, {"obrigatorias": {"titulo", "populacao", "destaque_populacao", "nota"}, "opcionais": set()},
                   f"{ARQUIVO}, regua")
    if conteudo["destaques"].get(regua["destaque_populacao"], {}).get("tipo") != "fatia":
        raise ErroConteudo(f"{ARQUIVO}: regua.destaque_populacao deve ser um destaque do tipo fatia.")
    if not isinstance(conteudo["capitulos"], list) or not conteudo["capitulos"]:
        raise ErroConteudo(f"{ARQUIVO}: capitulos deve ser uma lista com ao menos um capítulo.")
    ids = [c.get("id") for c in conteudo["capitulos"] if isinstance(c, dict)]
    if len(set(ids)) != len(ids):
        raise ErroConteudo(f"{ARQUIVO}: id de capítulo repetido.")
    for capitulo in conteudo["capitulos"]:
        _validar_capitulo(capitulo, conteudo["destaques"])
    _validar_textos_e_condicoes(
        {k: v for k, v in conteudo.items() if k != "destaques"}, set(conteudo["destaques"]), ARQUIVO)
    return conteudo
