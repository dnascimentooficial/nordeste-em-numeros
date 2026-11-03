"""Conteudo da pagina Inovacao (metadados/site/inovacao.yaml): capa, placar, capitulos com a regua de leitura e o
capitulo de texto sobre o ecossistema.

Mesmas regras do Inicio: nenhum numero de dado e digitado (marcadores `{id.campo:formato}` preenchidos pela base, com
os destaques declarados no proprio arquivo), e cada veredito tem uma condicao que, falsa, o tira da pagina e do placar.
O capitulo sem graficos (`texto: true`) traz so paragrafos com a etiqueta do que ele e; nele nao ha marcador.
"""

from pathlib import Path

import yaml

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
    "obrigatorias": {"id", "rotulo", "titulo", "texto", "etiqueta", "paragrafos", "fonte"},
    "opcionais": set(),
}
_CHAVES_DA_REGUA = {"obrigatorias": {"rotulo", "destaque"}, "opcionais": set()}
_CHAVES_DAS_POSICOES = {"obrigatorias": {"titulo", "indicador", "nota"}, "opcionais": set()}


def _validar_capitulo(capitulo: object, destaques: dict) -> None:
    if isinstance(capitulo, dict) and capitulo.get("texto") is True:
        _exigir_chaves(capitulo, _CHAVES_DO_TEXTO, f"{ARQUIVO}, capítulo {capitulo.get('id')}")
        for campo in ("paragrafos", "fonte"):
            if not isinstance(capitulo[campo], list) or not all(isinstance(p, str) and p for p in capitulo[campo]):
                raise ErroConteudo(f"{ARQUIVO}, capítulo {capitulo['id']}: {campo} é uma lista de textos.")
        if any("{" in p or "}" in p for p in capitulo["paragrafos"]):
            raise ErroConteudo(f"{ARQUIVO}, capítulo {capitulo['id']}: o capítulo de texto não usa marcador de dado.")
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


def carregar_inovacao(pasta: Path) -> dict | None:
    """Le e valida inovacao.yaml; None se o arquivo nao existe (a pagina nao e gerada)."""
    caminho = pasta / ARQUIVO
    if not caminho.exists():
        return None
    try:
        conteudo = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as erro:
        raise ErroConteudo(f"{caminho}: não foi possível ler ({erro}).") from erro
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
