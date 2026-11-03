"""Conteudo historico da pagina "Como chegamos ate aqui": epocas, marcos, numeros com tipo e fonte, e os censos.

Excecao a regra "nenhum numero digitado em YAML": aqui os numeros historicos ficam em `historia.yaml`, cada um com
`tipo` e `fonte`. A parcela da populacao nunca e digitada: o gerador a calcula de `historia/censos.csv`.
Toda recusa levanta ErroConteudo com o caminho do campo (ex. `epocas[2].numeros[0].fonte`); quando o id da epoca ja e
conhecido, o caminho vem seguido dele (ex. `epocas[2].numeros[0].fonte (epoca 1654): ...`).
"""

import csv
import datetime
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from nordeste.site.conteudo import ErroConteudo
from nordeste.site.dados import Ponto

TIPOS = {"oficial": "dado oficial", "historiador": "estimativa de historiador", "interpretacao": "interpretação"}
LICENCAS = ("dominio-publico", "ilustracao-do-autor", "cc-by")
ROTULO_DA_LICENCA = {"dominio-publico": "domínio público", "ilustracao-do-autor": "ilustração do autor", "cc-by": "CC BY"}
LICENCA_QUE_EXIGE_URL = "cc-by"  # a pagina da imagem com a licenca precisa estar a vista
PALAVRAS_MINIMAS = 150
PALAVRAS_MAXIMAS = 300
MARCOS_POR_EPOCA = (2, 4)  # spec, secao 5
NUMEROS_POR_EPOCA = (1, 3)
# o modelo _epoca.html poe o ponto depois do titulo do marco e da fonte do numero ("<b>{{ m.titulo }}.</b>",
# "Fonte: {{ n.fonte }}."): com pontuacao no fim do campo sairia ".." ou "?."
PONTUACAO_FINAL = (".", "?", "!")
# o id da epoca vira o id do HTML e o endereco `#<id>`: o ano em que ela comeca, com quatro digitos. Assim nunca bate com o
# id de um marco (`m<ano>`) nem com os ids fixos da pagina (`conteudo`, `titulo-principal`, `t-<id>`, `g-censos`...)
FORMATO_DO_ID = re.compile(r"[0-9]{4}")
# imagens (WebP em estaticos/historia/, recortadas em 21:9): a da epoca vai no cartao e no topo do artigo; a do marco,
# opcional, so quando ha imagem livre do proprio fato, carrega so com o modal aberto
PESO_MAXIMO_DA_EPOCA = 150_000
PESO_MAXIMO_DO_MARCO = 80_000
PESO_MAXIMO_DO_CARTAO = 25_000  # a miniatura do cartao, arquivo proprio (as 8 da faixa cabem no 1 MB da pagina)
PROPORCAO = (21, 9)
SUFIXO_DO_CARTAO = "-cartao"

_COLUNAS_DOS_CENSOS = ("ano", "populacao_nordeste", "populacao_brasil", "fonte")


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
class Marco:
    ano: int
    titulo: str
    texto: str
    imagem: ImagemHistorica | None = None  # opcional sempre: marco sem imagem livre do fato fica so com texto


@dataclass(frozen=True)
class NumeroHistorico:
    valor: str  # texto exibido, ex. "46,7%"
    legenda: str
    tipo: str
    fonte: str


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
    if isinstance(obj, (int, float, datetime.date)) and not isinstance(obj, bool):
        campo = onde.rsplit(".", 1)[-1]
        raise ErroConteudo(f'{onde}: o YAML leu {obj!r} como numero ou data; escreva entre aspas ({campo}: "{obj}").')
    if not isinstance(obj, str) or not obj.strip():
        raise ErroConteudo(f"{onde}: esperava um texto nao vazio, veio {obj!r}.")
    return obj


def _url(obj: object, onde: str) -> str:
    texto = _texto(obj, onde)
    if not texto.startswith(("http://", "https://")):
        raise ErroConteudo(f"{onde}: a url deve comecar com http:// ou https://, veio {texto!r}.")
    return texto


def _sem_pontuacao_final(texto: str, onde: str) -> str:
    if texto.rstrip().endswith(PONTUACAO_FINAL):
        raise ErroConteudo(f"{onde}: termina em {texto.rstrip()[-1]!r}; escreva sem pontuacao final (o modelo poe o ponto).")
    return texto


def _quantos(itens: list, onde: str, faixa: tuple[int, int], nome: str) -> list:
    minimo, maximo = faixa
    if not minimo <= len(itens) <= maximo:
        raise ErroConteudo(f"{onde}: {len(itens)} {nome}, fora de {minimo} a {maximo} por epoca.")
    return itens


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
    _mapa(marco, onde, ("ano", "titulo", "texto"), ("imagem",))
    ano = _inteiro(marco["ano"], f"{onde}.ano")
    if not epoca["inicio"] <= ano <= epoca["fim"]:
        raise ErroConteudo(f"{onde}.ano: {ano} fora do periodo da epoca ({epoca['inicio']} a {epoca['fim']}).")
    titulo = _sem_pontuacao_final(_texto(marco["titulo"], f"{onde}.titulo"), f"{onde}.titulo")
    imagem = None if marco.get("imagem") is None else _validar_imagem(marco["imagem"], f"{onde}.imagem")
    return Marco(ano, titulo, _texto(marco["texto"], f"{onde}.texto"), imagem)


def _validar_numero(numero: object, onde: str) -> NumeroHistorico:
    _mapa(numero, onde, ("valor", "legenda", "tipo", "fonte"))
    tipo = numero["tipo"]
    if tipo not in TIPOS:
        raise ErroConteudo(f"{onde}.tipo: {tipo!r} fora de {tuple(TIPOS)}.")
    if tipo == "interpretacao":
        raise ErroConteudo(f"{onde}.tipo: 'interpretacao' so aparece no campo o_que_ficou, nao em numeros.")
    return NumeroHistorico(
        _texto(numero["valor"], f"{onde}.valor"), _texto(numero["legenda"], f"{onde}.legenda"), tipo,
        _sem_pontuacao_final(_texto(numero["fonte"], f"{onde}.fonte"), f"{onde}.fonte"),
    )


def _validar_fonte(fonte: object, onde: str) -> dict:
    _mapa(fonte, onde, ("texto",), ("url",))
    _texto(fonte["texto"], f"{onde}.texto")
    if fonte.get("url") is not None:
        _url(fonte["url"], f"{onde}.url")
    return dict(fonte)


def _validar_imagem(imagem: object, onde: str) -> ImagemHistorica:
    _mapa(imagem, onde, ("arquivo", "titulo", "autor", "data", "licenca", "alt"), ("url",))
    campos = {c: _texto(imagem[c], f"{onde}.{c}") for c in ("arquivo", "titulo", "autor", "data", "licenca", "alt")}
    if campos["licenca"] not in LICENCAS:
        raise ErroConteudo(f"{onde}.licenca: {campos['licenca']!r} fora de {LICENCAS}.")
    url = imagem.get("url")
    if campos["licenca"] == LICENCA_QUE_EXIGE_URL and url is None:
        raise ErroConteudo(f"{onde}.url: obrigatoria para a licenca {LICENCA_QUE_EXIGE_URL!r} (pagina da imagem com a licenca).")
    return ImagemHistorica(**campos, url=None if url is None else _url(url, f"{onde}.url"))


def _validar_epoca(epoca: object, onde: str, provisoria: bool) -> Epoca:
    try:
        return _validar_campos_da_epoca(epoca, onde, provisoria)
    except ErroConteudo as erro:
        # o caminho do campo diz a posicao na lista; o id diz a epoca sem precisar contar as entradas do YAML
        id_ = epoca.get("id") if isinstance(epoca, dict) else None
        mensagem = str(erro)
        if isinstance(id_, (str, int)) and not isinstance(id_, bool) and str(id_).strip() and not mensagem.startswith(f"{onde}.id"):
            caminho, dois_pontos, resto = mensagem.partition(": ")
            raise ErroConteudo(f"{caminho} (epoca {str(id_).strip()}){dois_pontos}{resto}") from erro
        raise


def _validar_campos_da_epoca(epoca: object, onde: str, provisoria: bool) -> Epoca:
    _mapa(
        epoca, onde,
        ("id", "inicio", "fim", "nome", "resumo", "texto", "marcos", "numeros", "o_que_ficou", "fontes"), ("imagem",),
    )
    id_ = epoca["id"]
    if isinstance(id_, int) and not isinstance(id_, bool):
        id_ = str(id_)
    id_ = _texto(id_, f"{onde}.id")
    if not FORMATO_DO_ID.fullmatch(id_):
        raise ErroConteudo(f"{onde}.id: {id_!r} fora do formato; esperava o ano em que a epoca comeca, com quatro digitos (ex. '1654').")
    inicio, fim = _inteiro(epoca["inicio"], f"{onde}.inicio"), _inteiro(epoca["fim"], f"{onde}.fim")
    if fim <= inicio:
        raise ErroConteudo(f"{onde}.fim: {fim} nao e depois do inicio ({inicio}).")
    texto = _texto(epoca["texto"], f"{onde}.texto")
    palavras = len(texto.split())
    if not PALAVRAS_MINIMAS <= palavras <= PALAVRAS_MAXIMAS:
        raise ErroConteudo(f"{onde}.texto: {palavras} palavras, fora de {PALAVRAS_MINIMAS} a {PALAVRAS_MAXIMAS}.")
    lista_de_marcos = _quantos(_lista(epoca["marcos"], f"{onde}.marcos"), f"{onde}.marcos", MARCOS_POR_EPOCA, "marcos")
    lista_de_numeros = _quantos(_lista(epoca["numeros"], f"{onde}.numeros"), f"{onde}.numeros", NUMEROS_POR_EPOCA, "numeros")
    marcos = [_validar_marco(m, f"{onde}.marcos[{i}]", epoca) for i, m in enumerate(lista_de_marcos)]
    numeros = [_validar_numero(n, f"{onde}.numeros[{i}]") for i, n in enumerate(lista_de_numeros)]
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


# --- medidas das imagens ---

def arquivo_do_cartao(arquivo: str) -> str:
    """A miniatura do cartao de uma epoca, por convencao: `1530.webp` -> `1530-cartao.webp` (mesmo recorte, reduzido)."""
    base, ponto, extensao = arquivo.rpartition(".")
    return f"{base}{SUFIXO_DO_CARTAO}{ponto}{extensao}" if ponto else f"{arquivo}{SUFIXO_DO_CARTAO}"


def medidas_da_webp(caminho: Path) -> tuple[int, int]:
    """(largura, altura) lidas do cabecalho da WebP (VP8, VP8L ou VP8X), sem depender do Pillow no gerador."""
    try:
        cabecalho = caminho.read_bytes()[:30]
    except OSError as erro:
        raise ErroConteudo(f"{caminho}: nao foi possivel ler a imagem ({erro}).") from erro
    if len(cabecalho) == 30 and cabecalho[:4] == b"RIFF" and cabecalho[8:12] == b"WEBP":
        bloco = cabecalho[12:16]
        if bloco == b"VP8 " and cabecalho[23:26] == b"\x9d\x01\x2a":
            return (int.from_bytes(cabecalho[26:28], "little") & 0x3FFF, int.from_bytes(cabecalho[28:30], "little") & 0x3FFF)
        if bloco == b"VP8L" and cabecalho[20] == 0x2F:
            bits = int.from_bytes(cabecalho[21:25], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
        if bloco == b"VP8X":
            return int.from_bytes(cabecalho[24:27], "little") + 1, int.from_bytes(cabecalho[27:30], "little") + 1
    raise ErroConteudo(f"{caminho}: nao e uma imagem WebP.")


# --- censos ---

def _ler_censos(pasta: Path) -> tuple[tuple[int, int, int, str], ...]:
    caminho = pasta / "historia" / "censos.csv"
    try:
        with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
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
        if ano <= 0:
            raise ErroConteudo(f"{onde}: ano deve ser positivo, veio {ano}.")
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
    marcos_vistos: dict[int, int] = {}  # cada marco vira id="m<ano>" na pagina: o ano nao se repete entre epocas
    for i, epoca in enumerate(epocas):
        for marco in epoca.marcos:
            if marco.ano in marcos_vistos:
                raise ErroConteudo(
                    f"epocas[{i}].marcos (epoca {epoca.id}): ano {marco.ano} repetido "
                    f"(ja e marco de epocas[{marcos_vistos[marco.ano]}], epoca {epocas[marcos_vistos[marco.ano]].id})."
                )
            marcos_vistos[marco.ano] = i
    fecho = _validar_fecho(bruto["fecho"])
    return Historia(
        provisoria=provisoria, abertura=abertura, epocas=tuple(sorted(epocas, key=lambda e: e.inicio)), fecho=fecho,
        censos=_ler_censos(pasta),
    )


def parcela_do_nordeste(historia: Historia) -> list[Ponto]:
    """Parcela do Nordeste na populacao do Brasil em cada censo, em %, uma casa (serie "censo")."""
    return [Ponto(ano, round(100 * nordeste / brasil, 1), "censo") for ano, nordeste, brasil, _ in historia.censos]
