"""Conteudo historico da pagina "Como chegamos ate aqui": epocas, marcos, numeros com tipo e fonte, e os censos.

Excecao a regra "nenhum numero digitado em YAML": aqui os numeros historicos ficam em `historia.yaml`, cada um com
`tipo` e `fonte`. A parcela da populacao nunca e digitada: o gerador a calcula de `historia/censos.csv`.
Toda recusa levanta ErroConteudo com o caminho do campo (ex. `epocas[2].numeros[0].fonte`).
"""

import csv
from dataclasses import dataclass
from pathlib import Path

import yaml

from nordeste.site.conteudo import ErroConteudo
from nordeste.site.dados import Ponto

TIPOS = {"oficial": "dado oficial", "historiador": "estimativa de historiador", "interpretacao": "interpretação"}
LICENCAS = ("dominio-publico", "ilustracao-do-autor", "cc-by")
LICENCA_QUE_EXIGE_URL = "cc-by"  # a pagina da imagem com a licenca precisa estar a vista
PALAVRAS_MINIMAS = 150
PALAVRAS_MAXIMAS = 300

_COLUNAS_DOS_CENSOS = ("ano", "populacao_nordeste", "populacao_brasil", "fonte")


@dataclass(frozen=True)
class Marco:
    ano: int
    titulo: str
    texto: str


@dataclass(frozen=True)
class NumeroHistorico:
    valor: str  # texto exibido, ex. "46,7%"
    legenda: str
    tipo: str
    fonte: str


@dataclass(frozen=True)
class ImagemHistorica:
    arquivo: str
    titulo: str
    autor: str
    data: str
    licenca: str
    alt: str
    url: str | None


@dataclass(frozen=True)
class Epoca:
    id: str
    inicio: int
    fim: int
    nome: str
    resumo: str
    texto: str
    marcos: tuple[Marco, ...]
    numeros: tuple[NumeroHistorico, ...]
    o_que_ficou: str
    fontes: tuple[dict, ...]
    imagem: ImagemHistorica | None


@dataclass(frozen=True)
class Historia:
    provisoria: bool
    abertura: dict
    epocas: tuple[Epoca, ...]
    fecho: dict
    censos: tuple[tuple[int, int, int, str], ...]  # (ano, populacao do Nordeste, populacao do Brasil, fonte)


# --- validacao dos campos ---

def _mapa(obj: object, onde: str, obrigatorias: tuple[str, ...], opcionais: tuple[str, ...] = ()) -> dict:
    """Mapa com todas as chaves obrigatorias e nenhuma fora das permitidas; a chave que falta e citada pelo caminho."""
    if not isinstance(obj, dict):
        raise ErroConteudo(f"{onde}: esperava um mapa, veio {type(obj).__name__}.")
    for chave in obrigatorias:
        if chave not in obj:
            raise ErroConteudo(f"{onde}.{chave}: campo obrigatorio ausente.")
    sobram = sorted(obj.keys() - set(obrigatorias) - set(opcionais), key=str)
    if sobram:
        raise ErroConteudo(f"{onde}: chaves desconhecidas {sobram}.")
    return obj


def _texto(obj: object, onde: str) -> str:
    if not isinstance(obj, str) or not obj.strip():
        raise ErroConteudo(f"{onde}: esperava um texto nao vazio, veio {obj!r}.")
    return obj


def _inteiro(obj: object, onde: str) -> int:
    if isinstance(obj, bool) or not isinstance(obj, int):
        raise ErroConteudo(f"{onde}: esperava um ano inteiro, veio {obj!r}.")
    return obj


def _lista(obj: object, onde: str) -> list:
    if not isinstance(obj, list) or not obj:
        raise ErroConteudo(f"{onde}: esperava uma lista com ao menos um item.")
    return obj


def _validar_abertura(abertura: object) -> dict:
    _mapa(abertura, "abertura", ("titulo", "subtitulo", "legenda", "nota_estados", "texto"))
    for chave, valor in abertura.items():
        _texto(valor, f"abertura.{chave}")
    return abertura


def _validar_fecho(fecho: object) -> dict:
    _mapa(fecho, "fecho", ("titulo", "texto", "links"))
    _texto(fecho["titulo"], "fecho.titulo")
    _texto(fecho["texto"], "fecho.texto")
    for i, link in enumerate(_lista(fecho["links"], "fecho.links")):
        onde = f"fecho.links[{i}]"
        _mapa(link, onde, ("texto", "url"))
        _texto(link["texto"], f"{onde}.texto")
        _texto(link["url"], f"{onde}.url")
    return fecho


def _validar_marco(marco: object, onde: str, epoca: dict) -> Marco:
    _mapa(marco, onde, ("ano", "titulo", "texto"))
    ano = _inteiro(marco["ano"], f"{onde}.ano")
    if not epoca["inicio"] <= ano <= epoca["fim"]:
        raise ErroConteudo(f"{onde}.ano: {ano} fora do periodo da epoca ({epoca['inicio']} a {epoca['fim']}).")
    return Marco(ano, _texto(marco["titulo"], f"{onde}.titulo"), _texto(marco["texto"], f"{onde}.texto"))


def _validar_numero(numero: object, onde: str) -> NumeroHistorico:
    _mapa(numero, onde, ("valor", "legenda", "tipo", "fonte"))
    tipo = numero["tipo"]
    if tipo not in TIPOS:
        raise ErroConteudo(f"{onde}.tipo: {tipo!r} fora de {tuple(TIPOS)}.")
    if tipo == "interpretacao":
        raise ErroConteudo(f"{onde}.tipo: 'interpretacao' so aparece no campo o_que_ficou, nao em numeros.")
    return NumeroHistorico(
        _texto(numero["valor"], f"{onde}.valor"), _texto(numero["legenda"], f"{onde}.legenda"), tipo,
        _texto(numero["fonte"], f"{onde}.fonte"),
    )


def _validar_fonte(fonte: object, onde: str) -> dict:
    _mapa(fonte, onde, ("texto",), ("url",))
    _texto(fonte["texto"], f"{onde}.texto")
    if fonte.get("url") is not None:
        _texto(fonte["url"], f"{onde}.url")
    return dict(fonte)


def _validar_imagem(imagem: object, onde: str) -> ImagemHistorica:
    _mapa(imagem, onde, ("arquivo", "titulo", "autor", "data", "licenca", "alt"), ("url",))
    campos = {c: _texto(imagem[c], f"{onde}.{c}") for c in ("arquivo", "titulo", "autor", "data", "licenca", "alt")}
    if campos["licenca"] not in LICENCAS:
        raise ErroConteudo(f"{onde}.licenca: {campos['licenca']!r} fora de {LICENCAS}.")
    url = imagem.get("url")
    if campos["licenca"] == LICENCA_QUE_EXIGE_URL and url is None:
        raise ErroConteudo(f"{onde}.url: obrigatoria para a licenca {LICENCA_QUE_EXIGE_URL!r} (pagina da imagem com a licenca).")
    return ImagemHistorica(**campos, url=None if url is None else _texto(url, f"{onde}.url"))


def _validar_epoca(epoca: object, onde: str, provisoria: bool) -> Epoca:
    _mapa(
        epoca, onde,
        ("id", "inicio", "fim", "nome", "resumo", "texto", "marcos", "numeros", "o_que_ficou", "fontes"), ("imagem",),
    )
    id_ = epoca["id"]
    if isinstance(id_, int) and not isinstance(id_, bool):
        id_ = str(id_)
    id_ = _texto(id_, f"{onde}.id")
    inicio, fim = _inteiro(epoca["inicio"], f"{onde}.inicio"), _inteiro(epoca["fim"], f"{onde}.fim")
    if fim <= inicio:
        raise ErroConteudo(f"{onde}.fim: {fim} nao e depois do inicio ({inicio}).")
    texto = _texto(epoca["texto"], f"{onde}.texto")
    palavras = len(texto.split())
    if not PALAVRAS_MINIMAS <= palavras <= PALAVRAS_MAXIMAS:
        raise ErroConteudo(f"{onde}.texto: {palavras} palavras, fora de {PALAVRAS_MINIMAS} a {PALAVRAS_MAXIMAS}.")
    marcos = [_validar_marco(m, f"{onde}.marcos[{i}]", epoca) for i, m in enumerate(_lista(epoca["marcos"], f"{onde}.marcos"))]
    numeros = [_validar_numero(n, f"{onde}.numeros[{i}]") for i, n in enumerate(_lista(epoca["numeros"], f"{onde}.numeros"))]
    fontes = [_validar_fonte(f, f"{onde}.fontes[{i}]") for i, f in enumerate(_lista(epoca["fontes"], f"{onde}.fontes"))]
    if epoca.get("imagem") is not None:
        imagem = _validar_imagem(epoca["imagem"], f"{onde}.imagem")
    elif provisoria:
        imagem = None
    else:
        raise ErroConteudo(f"{onde}.imagem: obrigatoria quando provisoria e falso.")
    return Epoca(
        id=id_, inicio=inicio, fim=fim,
        nome=_texto(epoca["nome"], f"{onde}.nome"), resumo=_texto(epoca["resumo"], f"{onde}.resumo"),
        texto=texto, marcos=tuple(sorted(marcos, key=lambda m: m.ano)), numeros=tuple(numeros),
        o_que_ficou=_texto(epoca["o_que_ficou"], f"{onde}.o_que_ficou"), fontes=tuple(fontes), imagem=imagem,
    )


# --- censos ---

def _ler_censos(pasta: Path) -> tuple[tuple[int, int, int, str], ...]:
    caminho = pasta / "historia" / "censos.csv"
    try:
        with caminho.open(encoding="utf-8", newline="") as arquivo:
            leitor = csv.DictReader(arquivo)
            if tuple(leitor.fieldnames or ()) != _COLUNAS_DOS_CENSOS:
                raise ErroConteudo(f"censos.csv: colunas devem ser {_COLUNAS_DOS_CENSOS}, vieram {leitor.fieldnames}.")
            linhas = list(leitor)
    except OSError as erro:
        raise ErroConteudo(f"{caminho}: nao foi possivel ler censos.csv ({erro}).") from erro
    if not linhas:
        raise ErroConteudo("censos.csv: sem nenhum censo.")
    censos = []
    for n, linha in enumerate(linhas, start=2):  # a linha 1 e o cabecalho
        onde = f"censos.csv, linha {n}"
        try:
            ano, nordeste, brasil = (int(linha[c]) for c in _COLUNAS_DOS_CENSOS[:3])
        except (TypeError, ValueError) as erro:
            raise ErroConteudo(f"{onde}: ano e populacoes devem ser inteiros ({dict(linha)}).") from erro
        if nordeste <= 0 or brasil <= 0:
            raise ErroConteudo(f"{onde} (ano {ano}): populacoes devem ser positivas.")
        if nordeste > brasil:
            raise ErroConteudo(f"{onde} (ano {ano}): populacao_nordeste ({nordeste}) maior que populacao_brasil ({brasil}).")
        censos.append((ano, nordeste, brasil, _texto(linha["fonte"], f"{onde}.fonte")))
    anos = [c[0] for c in censos]
    repetidos = sorted({a for a in anos if anos.count(a) > 1})
    if repetidos:
        raise ErroConteudo(f"censos.csv: ano repetido {repetidos}.")
    return tuple(sorted(censos))


# --- carga ---

def carregar_historia(pasta: Path) -> Historia | None:
    """Le e valida `historia.yaml` e `historia/censos.csv` de `pasta` (metadados/site); None sem `historia.yaml`."""
    caminho = pasta / "historia.yaml"
    if not caminho.exists():
        return None
    try:
        bruto = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as erro:
        raise ErroConteudo(f"{caminho}: nao foi possivel ler historia.yaml ({erro}).") from erro
    _mapa(bruto, "historia.yaml", ("provisoria", "abertura", "epocas", "fecho"))
    provisoria = bruto["provisoria"]
    if not isinstance(provisoria, bool):
        raise ErroConteudo(f"provisoria: esperava verdadeiro ou falso, veio {provisoria!r}.")
    abertura = _validar_abertura(bruto["abertura"])
    epocas = [_validar_epoca(e, f"epocas[{i}]", provisoria) for i, e in enumerate(_lista(bruto["epocas"], "epocas"))]
    vistos: set[str] = set()
    for i, epoca in enumerate(epocas):
        if epoca.id in vistos:
            raise ErroConteudo(f"epocas[{i}].id: id repetido {epoca.id!r}.")
        vistos.add(epoca.id)
    fecho = _validar_fecho(bruto["fecho"])
    return Historia(
        provisoria=provisoria, abertura=abertura, epocas=tuple(sorted(epocas, key=lambda e: e.inicio)), fecho=fecho,
        censos=_ler_censos(pasta),
    )


def parcela_do_nordeste(historia: Historia) -> list[Ponto]:
    """Parcela do Nordeste na populacao do Brasil em cada censo, em %, uma casa (serie "censo")."""
    return [Ponto(ano, round(100 * nordeste / brasil, 1), "censo") for ano, nordeste, brasil, _ in historia.censos]
