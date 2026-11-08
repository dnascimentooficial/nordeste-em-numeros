"""Idiomas do site: o portugues (o original, na raiz) e o ingles (em /en/), gerados pelo mesmo comando `site`.

O conteudo em ingles e uma camada sobre o portugues: `metadados/site/en/<arquivo>.yaml` repete a estrutura do arquivo
em portugues (mesmas chaves, mesmas listas) com so os textos de leitura traduzidos. A carga junta as duas: o que falta
na traducao (chave, item de lista, texto) fica em portugues, e o relatorio do gerador lista o que faltou; traducao
faltando nunca derruba a geracao. Os marcadores de dado (`{id.campo:formato}`) e os de modelo (`[n]`, `[epocas]`...)
tem de ser os mesmos do texto em portugues, texto a texto: diferente, e ErroConteudo.

O idioma da geracao em curso fica numa variavel de contexto (`em_idioma`): a formatacao de numeros e datas e os rotulos
fixos do codigo (interface.py) o leem sem que cada funcao precise recebe-lo.
"""

import contextvars
import dataclasses
import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import yaml

IDIOMAS = ("pt", "en")
PADRAO = "pt"
PASTA_DA_TRADUCAO = {"en": "en"}  # em metadados/site/
PREFIXO = {"pt": "", "en": "/en"}  # das rotas
LANG = {"pt": "pt-BR", "en": "en"}  # <html lang>, hreflang
OG_LOCALE = {"pt": "pt_BR", "en": "en_US"}
ARQUIVOS_TRADUZIDOS = ("textos", "perguntas", "destaques", "cards", "historia", "inovacao", "fichas")

# a rota de cada pagina em cada idioma (chave da pagina -> caminho); o card e /cards/<id>/ e /en/cards/<id>/
ROTAS = {
    "pt": {
        "index": "/", "como-chegamos": "/como-chegamos/", "inovacao": "/inovacao/", "estados": "/estados/",
        "explorar": "/explorar/", "cards": "/cards/", "sobre": "/sobre/", "dados": "/dados/",
    },
    "en": {
        "index": "/en/", "como-chegamos": "/en/how-we-got-here/", "inovacao": "/en/innovation/", "estados": "/en/states/",
        "explorar": "/en/explore/", "cards": "/en/cards/", "sobre": "/en/about/", "dados": "/en/data/",
    },
}

# chaves cujo valor nunca e traduzido: ids, condicoes, arquivos e enderecos. O valor delas vem sempre do portugues,
# mesmo que a traducao traga outro.
NAO_TRADUZIR = frozenset({"id", "condicao", "arquivo", "url", "licenca"})
# chaves que, com um identificador (uma palavra so, sem espaco), apontam para a selecao dos dados ou para outra parte
# do conteudo (`card: pibpc`, `grafico: renda`, `tipo: serie`); com texto de leitura (`saidas.card`), sao traduzidas
SE_IDENTIFICADOR = frozenset({
    "indicador", "territorio", "referencia", "tipo", "sub", "etapa", "rede", "serie", "card", "grafico", "mapa",
    "destaque", "destaque_populacao",
})
IDENTIFICADOR = re.compile(r"[A-Za-z0-9_.\-]+")


def _fixo(chave: object, valor: object) -> bool:
    """O valor dessa chave fica sempre o do portugues."""
    if isinstance(valor, (dict, list)):
        return False
    return chave in NAO_TRADUZIR or (chave in SE_IDENTIFICADOR and isinstance(valor, str)
                                     and IDENTIFICADOR.fullmatch(valor) is not None)


MARCADOR = re.compile(r"\{[^{}]*\}|\[[a-z_]+\]")

_atual: contextvars.ContextVar[str] = contextvars.ContextVar("idioma", default=PADRAO)


class ErroTraducao(ValueError):
    """Traducao que muda um marcador de dado ou de modelo."""


def idioma_atual() -> str:
    return _atual.get()


@contextmanager
def em_idioma(idioma: str) -> Iterator[None]:
    """Tudo dentro do `with` formata numeros, datas e rotulos no idioma dado."""
    if idioma not in IDIOMAS:
        raise ValueError(f"idioma desconhecido: {idioma!r} (valem {IDIOMAS})")
    marca = _atual.set(idioma)
    try:
        yield
    finally:
        _atual.reset(marca)


def rota(chave: str, idioma: str | None = None) -> str:
    return ROTAS[idioma or idioma_atual()][chave]


def rota_do_card(id_: str, idioma: str | None = None) -> str:
    return f"{ROTAS[idioma or idioma_atual()]['cards']}{id_}/"


def arquivo_da_rota(caminho: str) -> str:
    """`/` -> `index.html`, `/en/states/` -> `en/states/index.html`."""
    return f"{caminho.strip('/')}/index.html".lstrip("/")


def outra_rota(caminho: str, idioma: str) -> str:
    """A mesma pagina no outro idioma: `/inovacao/` -> `/en/innovation/`, `/en/cards/pobreza/` -> `/cards/pobreza/`."""
    de = next(i for i in IDIOMAS if i != idioma)
    for chave, original in sorted(ROTAS[de].items(), key=lambda par: -len(par[1])):
        if caminho == original:
            return ROTAS[idioma][chave]
        if chave == "cards" and caminho.startswith(original):
            return ROTAS[idioma]["cards"] + caminho[len(original):]
    raise KeyError(f"rota sem par no outro idioma: {caminho!r}")


# --- camada de traducao ---

def marcadores(texto: str) -> list[str]:
    return sorted(MARCADOR.findall(texto))


def _com_traducao(original: object, traducao: object, onde: str) -> object:
    """O original com os textos da traducao por cima (regras no docstring do modulo)."""
    if traducao is None:
        return original
    if isinstance(original, dict):
        if not isinstance(traducao, dict):
            return original
        return {
            chave: valor if _fixo(chave, valor) else _com_traducao(valor, traducao.get(chave), f"{onde}.{chave}")
            for chave, valor in original.items()
        }
    if isinstance(original, list):
        if not isinstance(traducao, list):
            return original
        pares = _pares(original, traducao)
        return [_com_traducao(item, par, f"{onde}[{i}]") for i, (item, par) in enumerate(pares)]
    if isinstance(original, str):
        if not isinstance(traducao, str) or not traducao.strip():
            return original
        if marcadores(original) != marcadores(traducao):
            raise ErroTraducao(
                f"{onde}: a tradução muda os marcadores ({marcadores(original)} -> {marcadores(traducao)}): {traducao!r}"
            )
        return traducao
    return original  # numero, booleano: sempre o do original


def _pares(original: list, traducao: list) -> list[tuple[object, object]]:
    """Cada item do original com o seu na traducao: pelo `id` quando os itens tem id, senao pela posicao."""
    if all(isinstance(i, dict) and "id" in i for i in original):
        por_id = {t.get("id"): t for t in traducao if isinstance(t, dict)}
        return [(item, por_id.get(item["id"])) for item in original]
    return [(item, traducao[i] if i < len(traducao) else None) for i, item in enumerate(original)]


def faltas(original: object, traducao: object, onde: str = "") -> list[str]:
    """Os caminhos dos textos sem traducao (e os que a traducao traz a mais, marcados `+`)."""
    if isinstance(original, dict):
        if not isinstance(traducao, dict):
            return [onde or "."] if _tem_texto(original) else []
        achadas = []
        for chave, valor in original.items():
            if _fixo(chave, valor):
                continue
            caminho = f"{onde}.{chave}" if onde else str(chave)
            achadas += faltas(valor, traducao.get(chave), caminho)
        achadas += [f"+{onde}.{c}" if onde else f"+{c}" for c in traducao if c not in original]
        return achadas
    if isinstance(original, list):
        if not isinstance(traducao, list):
            return [onde] if _tem_texto(original) else []
        achadas = []
        for i, (item, par) in enumerate(_pares(original, traducao)):
            achadas += faltas(item, par, f"{onde}[{i}]")
        if len(traducao) > len(original):
            achadas.append(f"+{onde}[{len(original)}:]")
        return achadas
    if isinstance(original, str):
        return [] if isinstance(traducao, str) and traducao.strip() else [onde]
    return []


def _tem_texto(obj: object) -> bool:
    if isinstance(obj, str):
        return True
    if isinstance(obj, dict):
        return any(_tem_texto(v) for k, v in obj.items() if not _fixo(k, v))
    if isinstance(obj, list):
        return any(_tem_texto(v) for v in obj)
    return False


def ler_traducao(pasta: Path, nome: str, idioma: str) -> object:
    """O YAML da traducao (`metadados/site/en/<nome>.yaml`), ou None se nao existe ou o idioma e o original."""
    if idioma == PADRAO:
        return None
    caminho = pasta / PASTA_DA_TRADUCAO[idioma] / f"{nome}.yaml"
    if not caminho.is_file():
        return None
    try:
        return yaml.safe_load(caminho.read_text(encoding="utf-8"))
    except yaml.YAMLError as erro:
        raise ErroTraducao(f"{caminho}: não foi possível ler ({erro}).") from erro


def traduzir(original: object, pasta: Path, nome: str, idioma: str) -> object:
    """`original` (o YAML em portugues ja lido) com a traducao por cima; no idioma original, ele mesmo."""
    if idioma == PADRAO:
        return original
    return _com_traducao(original, ler_traducao(pasta, nome, idioma), f"{PASTA_DA_TRADUCAO[idioma]}/{nome}.yaml")


def traducoes_faltando(pasta: Path, idioma: str = "en") -> list[str]:
    """`en/textos.yaml: menu.inicio`: cada texto que cai no portugues por falta de traducao, arquivo a arquivo (so dos
    arquivos em portugues que existem)."""
    achadas = []
    for nome in ARQUIVOS_TRADUZIDOS:
        caminho = pasta / f"{nome}.yaml"
        if nome == "fichas":
            achadas += _fichas_faltando(pasta, idioma)
            continue
        if not caminho.is_file():
            continue
        original = yaml.safe_load(caminho.read_text(encoding="utf-8"))
        traducao = ler_traducao(pasta, nome, idioma)
        prefixo = f"{PASTA_DA_TRADUCAO[idioma]}/{nome}.yaml"
        if traducao is None:
            achadas.append(f"{prefixo}: (arquivo inteiro)")
            continue
        achadas += [f"{prefixo}: {c}" for c in faltas(original, traducao)]
    return achadas


# --- fichas dos indicadores (metadados/indicadores): so os campos que o site mostra ---

CAMPOS_DA_FICHA = ("nome", "orgao")
CAMPOS_DA_SERIE = ("fonte", "base_origem")


def fichas_no_idioma(fichas: dict, pasta: Path, idioma: str) -> dict:
    """As fichas com nome, orgao e fonte e base de origem de cada serie de `<idioma>/fichas.yaml` (por id da ficha e
    da serie); o que falta fica em portugues."""
    traducao = ler_traducao(pasta, "fichas", idioma) or {}
    traduzidas = {}
    for id_, ficha in fichas.items():
        dela = traducao.get(id_) or {}
        series = dela.get("series") or {}
        traduzidas[id_] = dataclasses.replace(
            ficha,
            **{c: dela[c] for c in CAMPOS_DA_FICHA if isinstance(dela.get(c), str) and dela[c].strip()},
            series=tuple(
                dataclasses.replace(s, **{
                    c: (series.get(s.id) or {})[c] for c in CAMPOS_DA_SERIE
                    if isinstance((series.get(s.id) or {}).get(c), str) and series[s.id][c].strip()
                })
                for s in ficha.series
            ),
        )
    return traduzidas


def _fichas_faltando(pasta: Path, idioma: str) -> list[str]:
    """Os campos mostrados de cada ficha (metadados/indicadores, vizinha de metadados/site) sem traducao."""
    traducao = ler_traducao(pasta, "fichas", idioma) or {}
    prefixo = f"{PASTA_DA_TRADUCAO[idioma]}/fichas.yaml"
    achadas = []
    for arquivo in sorted((pasta.parent / "indicadores").glob("*.yaml")):
        ficha = yaml.safe_load(arquivo.read_text(encoding="utf-8")) or {}
        id_ = ficha.get("id", arquivo.stem)
        dela = traducao.get(id_) or {}
        achadas += [f"{prefixo}: {id_}.nome"] if not dela.get("nome") else []
        series = dela.get("series") or {}
        for serie in ficha.get("series") or []:
            for campo in CAMPOS_DA_SERIE:
                if not (series.get(serie.get("id")) or {}).get(campo):
                    achadas.append(f"{prefixo}: {id_}.series.{serie.get('id')}.{campo}")
    return achadas
