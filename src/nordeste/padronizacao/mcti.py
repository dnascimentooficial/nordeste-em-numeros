"""Padronizador das tabelas CSV dos Indicadores Nacionais de CT&I do MCTI (site legado, antigo.mctic.gov.br).

Layout conferido nas tabelas 2.3.3 (dispendio dos governos estaduais em C&T) e 2.3.5 (em P&D), baixadas em 2026-11-03:

- texto em Latin-1, separador `;`, numeros com ponto de milhar e virgula decimal e `-` para zero; linhas vazias (so
  `;`) antes, entre e depois da tabela;
- uma linha com o numero da tabela (`Tabela 2.3.3`), o titulo (com os anos, `2000-2019`) e a unidade
  (`em milhões de R$ correntes`);
- o cabecalho comeca por `Grandes Regiões / Unidades da Federação` e traz um ano por coluna (2.3.3) ou um ano a cada
  tres colunas (2.3.5), com os rotulos de cada coluna do ano na linha de baixo (`P&D`, `Orçamento executado(1)`,
  `Pós-graduação(2)`);
- uma linha por territorio: `Total` (o Brasil), as cinco regioes e as 27 UFs, pelo nome; depois, fonte e notas.

Cada parte da serie (`parametros.partes`) diz a `url`, a `tabela`, um trecho do `titulo`, o `subindicador` e, nas
tabelas com varias colunas por ano, a `coluna` (rotulo da linha de baixo do cabecalho). Tabela, titulo, unidade, anos
(os da serie, todos), territorios e numeros sao conferidos; qualquer desvio e ErroLayout. Entram o Brasil, as regioes e
as UFs da tabela de territorios, com o valor publicado (o Nordeste e o publicado pelo MCTI, nao a soma das UFs).
"""

import csv
import io

import pandas as pd

from nordeste.coletores.arquivo import ler_pacote
from nordeste.esquema import COLUNAS_BASE, normalizar_base
from nordeste.fichas import Ficha, Serie
from nordeste.padronizacao.erros import ErroLayout
from nordeste.padronizacao.planilha import numero_br
from nordeste.territorios import normalizar_nome, territorio_por_nome

CABECALHO = "Grandes Regiões / Unidades da Federação"
UNIDADE = "em milhões de R$ correntes"
REGIOES = ("Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste")
UFS = (
    "Acre", "Alagoas", "Amapá", "Amazonas", "Bahia", "Ceará", "Distrito Federal", "Espírito Santo", "Goiás",
    "Maranhão", "Mato Grosso", "Mato Grosso do Sul", "Minas Gerais", "Pará", "Paraíba", "Paraná", "Pernambuco",
    "Piauí", "Rio de Janeiro", "Rio Grande do Norte", "Rio Grande do Sul", "Rondônia", "Roraima", "Santa Catarina",
    "São Paulo", "Sergipe", "Tocantins",
)
_NOMES = {normalizar_nome(n): n for n in ("Total", *REGIOES, *UFS)}


def _linhas(conteudo: bytes, onde: str) -> list[list[str]]:
    try:
        texto = conteudo.decode("latin-1")
    except UnicodeDecodeError as erro:  # latin-1 decodifica qualquer byte; fica pela simetria com os outros leitores
        raise ErroLayout(f"{onde}: arquivo ilegível ({erro})") from erro
    if texto.lstrip().startswith("<"):
        raise ErroLayout(f"{onde}: veio uma página HTML no lugar do CSV")
    return [[c.strip() for c in linha] for linha in csv.reader(io.StringIO(texto), delimiter=";")]


def _numero(texto: str, onde: str) -> float:
    if texto.strip() == "-":
        return 0.0  # convencao da tabela: "-" e zero (UF sem dispendio ou sem pos-graduacao estadual)
    try:
        numero = numero_br(texto)
    except ValueError as erro:
        raise ErroLayout(f"{onde}: {erro}") from None
    if numero is None or numero < 0:
        raise ErroLayout(f"{onde}: esperava número não negativo, achou {texto!r}")
    return numero


def _colunas_dos_anos(cabecalho: list[str], abaixo: list[str], coluna: str | None, onde: str) -> dict[int, int]:
    """{ano: indice da coluna}: a do proprio ano ou, com `coluna`, a do bloco do ano cujo rotulo de baixo e esse."""
    inicios = {int(c): i for i, c in enumerate(cabecalho) if i and c.isdigit() and len(c) == 4}
    if not inicios:
        raise ErroLayout(f"{onde}: o cabeçalho não traz os anos")
    if coluna is None:
        return inicios
    resultado = {}
    ordem = sorted(inicios.values()) + [len(cabecalho)]
    for ano, inicio in inicios.items():
        fim = ordem[ordem.index(inicio) + 1]
        achadas = [i for i in range(inicio, max(fim, inicio + 1)) if i < len(abaixo) and abaixo[i] == coluna]
        if len(achadas) != 1:
            raise ErroLayout(f"{onde}: o bloco de {ano} não tem uma coluna {coluna!r} (rótulos: {abaixo[inicio:fim]})")
        resultado[ano] = achadas[0]
    return resultado


def ler_tabela_mcti(conteudo: bytes, parte: dict, serie: Serie, onde: str) -> dict[str, dict[int, float]]:
    """{nome do territorio: {ano: valor}} do Brasil (`Total`), das cinco regioes e das 27 UFs."""
    linhas = _linhas(conteudo, onde)
    texto = [" ".join(c for c in linha if c) for linha in linhas]
    if not any(t == parte["tabela"] or t.startswith(parte["tabela"] + " ") for t in texto):
        raise ErroLayout(f"{onde}: não achei a linha {parte['tabela']!r}")
    titulo = next((t for t in texto if parte["titulo"] in t), None)
    if titulo is None:
        raise ErroLayout(f"{onde}: não achei o título com {parte['titulo']!r}")
    fim = serie.fim if serie.fim is not None else serie.inicio
    if f"{serie.inicio}-{fim}" not in titulo:
        raise ErroLayout(f"{onde}: o título não cobre {serie.inicio}-{fim}: {titulo!r}")
    if not any(UNIDADE in t for t in texto):
        raise ErroLayout(f"{onde}: a unidade mudou (esperava {UNIDADE!r})")
    posicao = next((i for i, linha in enumerate(linhas) if linha and linha[0] == CABECALHO), None)
    if posicao is None or posicao + 1 >= len(linhas):
        raise ErroLayout(f"{onde}: não achei o cabeçalho {CABECALHO!r}")
    colunas = _colunas_dos_anos(linhas[posicao], linhas[posicao + 1], parte.get("coluna"), onde)
    esperados = list(range(serie.inicio, fim + 1))
    if sorted(colunas) != esperados:
        raise ErroLayout(f"{onde}: anos {sorted(colunas)} diferentes dos da série ({serie.inicio} a {fim})")
    valores: dict[str, dict[int, float]] = {}
    for numero, linha in enumerate(linhas[posicao + 1:], start=posicao + 2):
        nome = _NOMES.get(normalizar_nome(linha[0])) if linha else None
        if nome is None:
            continue
        if nome in valores:
            raise ErroLayout(f"{onde}, linha {numero}: {nome} repetido")
        valores[nome] = {
            ano: _numero(linha[c] if c < len(linha) else "", f"{onde}, linha {numero} ({nome}, {ano})")
            for ano, c in colunas.items()
        }
    faltam = [n for n in ("Total", *REGIOES, *UFS) if n not in valores]
    if faltam:
        raise ErroLayout(f"{onde}: faltam as linhas de {', '.join(faltam)}")
    return valores


def padronizar_mcti(
    conteudo: bytes, ficha: Ficha, serie: Serie, coleta_id: str, territorios: pd.DataFrame,
) -> pd.DataFrame:
    """Linhas da base: Brasil, regioes e UFs da tabela de territorios, por subindicador (um por parte) e ano."""
    try:
        arquivos = ler_pacote(conteudo)
    except ValueError as erro:
        raise ErroLayout(f"MCTI {ficha.id}/{serie.id}: {erro}") from erro
    registros = []
    for posicao, parte in enumerate(serie.parametros["partes"], start=1):
        onde = f"MCTI {ficha.id}/{serie.id}, parte {posicao} ({parte.get('tabela')})"
        faltam = [c for c in ("url", "tabela", "titulo", "subindicador") if not parte.get(c)]
        if faltam:
            raise ErroLayout(f"{onde}: a parte não declara {', '.join(faltam)}")
        if parte["url"] not in arquivos:
            raise ErroLayout(f"{onde}: {parte['url']} ausente do pacote coletado")
        for nome, por_ano in ler_tabela_mcti(arquivos[parte["url"]], parte, serie, onde).items():
            territorio = "BR" if nome == "Total" else territorio_por_nome(territorios, nome)
            if territorio is None:
                continue
            for ano, valor in por_ano.items():
                registros.append({
                    "indicador_id": ficha.id, "subindicador": parte["subindicador"], "etapa": "", "rede": "",
                    "territorio_id": territorio, "ano": ano, "valor": valor, "tipo_dado": "observado",
                    "serie_id": serie.id, "coleta_id": coleta_id, "nota": "",
                })
    return normalizar_base(pd.DataFrame(registros, columns=COLUNAS_BASE))
