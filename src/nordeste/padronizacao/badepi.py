"""Padronizador dos microdados de patentes da BADEPI (INPI): pedidos de residentes por UF do primeiro depositante.

O coletor `arquivo` guarda do zip da BADEPI (`badepiv12_ptn.zip`, 123 MB) so os dois CSV usados, com os bytes
comprimidos do original: `..._deposito.csv` (um pedido por linha: NO_PEDIDO, ANO = ano da data de entrada no INPI, ...)
e `..._depositante.csv` (um depositante por linha: NO_PEDIDO, NO_ORDEM, CD_PAIS_PFPJ, CD_UF_PFPJ, ...). Texto em
Latin-1, separador `;`, cabecalho na primeira linha. Os dois sao lidos em fluxo, sem carregar o CSV na memoria.

Regra do dicionario da BADEPI: "o requerente que aparece em primeira ordem no pedido determina a origem do pedido".
Residente e o pedido cujo depositante de ordem 1 tem pais `BR`; a UF e a desse depositante. Quando o arquivo traz mais
de uma linha de ordem 1 para o mesmo pedido (6.329 pedidos na versao 12, 30 deles com pais, UF ou tipo de pessoa
diferentes), vale a primeira, na ordem do arquivo, que traz o pais. Pedido de residente sem UF valida fica fora das UFs e,
portanto, do Brasil, que e a soma das 27 UFs (como as regioes).

Tipo do pedido (o dicionario nao documenta a numeracao; ver a ficha): no formato antigo, o prefixo do numero (`PI`,
`MU`); no formato de 12 digitos (desde 2012), os dois primeiros digitos (`naturezas`). So entram os prefixos e as
naturezas declarados na ficha.

Confere os nomes das colunas, o ano (inteiro dentro da serie: ano novo, como o de uma versao nova da base, e erro ate o
`fim` subir) e a presenca dos dois membros. Qualquer desvio e ErroLayout.
"""

import csv
import io
import zipfile
from collections import Counter

import pandas as pd

from nordeste.coletores.arquivo import ler_pacote
from nordeste.esquema import COLUNAS_BASE, normalizar_base
from nordeste.fichas import Ficha, Serie
from nordeste.padronizacao.erros import ErroLayout
from nordeste.padronizacao.geocapes import REGIAO_DA_UF, TERRITORIO_DA_UF

COLUNAS_DEPOSITO = ("NO_PEDIDO", "ANO")
COLUNAS_DEPOSITANTE = ("NO_PEDIDO", "NO_ORDEM", "CD_PAIS_PFPJ", "CD_UF_PFPJ")


def _leitor(zip_: zipfile.ZipFile, membro: str, colunas: tuple[str, ...], onde: str):
    """(indices das colunas, leitor das linhas seguintes) de um membro CSV do zip reduzido."""
    try:
        bruto = zip_.open(membro)
    except KeyError:
        raise ErroLayout(f"{onde}: falta {membro} no arquivo coletado") from None
    linhas = csv.reader(io.TextIOWrapper(bruto, encoding="latin-1", newline=""), delimiter=";")
    cabecalho = [c.strip() for c in next(linhas, [])]
    faltam = [c for c in colunas if c not in cabecalho]
    if faltam:
        raise ErroLayout(f"{onde}: {membro} sem as colunas {', '.join(faltam)} (cabeçalho: {cabecalho})")
    return [cabecalho.index(c) for c in colunas], linhas


def tipo_do_pedido(numero: str, prefixos: tuple[str, ...], naturezas: tuple[str, ...]) -> bool:
    """O pedido e de um dos tipos contados? Formato antigo pelo prefixo; o de 12 digitos pela natureza."""
    if len(numero) == 12 and numero.isdigit():
        return numero[:2] in naturezas
    return any(numero.startswith(p) for p in prefixos)


def contar_residentes(conteudo: bytes, serie: Serie, onde: str) -> dict[int, Counter]:
    """{ano: Counter(sigla da UF: pedidos)} dos pedidos de residentes dos tipos da ficha, de `inicio` a `fim`."""
    p = serie.parametros
    partes = p.get("partes") or []
    membros = {parte.get("arquivo_no_zip") for parte in partes}
    deposito = next((m for m in membros if m and m.endswith("_deposito.csv")), None)
    depositante = next((m for m in membros if m and m.endswith("_depositante.csv")), None)
    if not deposito or not depositante or len({parte["url"] for parte in partes}) != 1:
        raise ErroLayout(f"{onde}: a ficha deve declarar os membros _deposito.csv e _depositante.csv de uma URL")
    prefixos, naturezas = tuple(p.get("prefixos", ())), tuple(str(n) for n in p.get("naturezas", ()))
    if not prefixos or not naturezas:
        raise ErroLayout(f"{onde}: a ficha deve declarar os prefixos e as naturezas contados")
    try:
        zip_ = zipfile.ZipFile(io.BytesIO(ler_pacote(conteudo)[partes[0]["url"]]))
    except (ValueError, KeyError, zipfile.BadZipFile) as erro:
        raise ErroLayout(f"{onde}: arquivo coletado ilegível ({erro})") from erro
    with zip_:
        vistos: set[str] = set()
        uf_do_residente: dict[str, str] = {}
        (i_pedido, i_ordem, i_pais, i_uf), linhas = _leitor(zip_, depositante, COLUNAS_DEPOSITANTE, onde)
        for linha in linhas:
            if len(linha) <= max(i_pedido, i_ordem, i_pais, i_uf) or linha[i_ordem].strip() != "1":
                continue
            pedido, pais = linha[i_pedido].strip(), linha[i_pais].strip()
            if pedido in vistos or not pais:
                continue  # vale a primeira linha de ordem 1 que traz o pais; linha sem pais nao identifica a origem
            vistos.add(pedido)
            if pais == "BR":
                uf_do_residente[pedido] = linha[i_uf].strip()
        del vistos
        fim = serie.fim if serie.fim is not None else 9999
        contagens: dict[int, Counter] = {ano: Counter() for ano in range(serie.inicio, (serie.fim or serie.inicio) + 1)}
        (i_pedido, i_ano), linhas = _leitor(zip_, deposito, COLUNAS_DEPOSITO, onde)
        for numero, linha in enumerate(linhas, start=2):
            if len(linha) <= max(i_pedido, i_ano):
                raise ErroLayout(f"{onde}: {deposito}, linha {numero} com colunas de menos")
            texto_ano = linha[i_ano].strip()
            if not (texto_ano.isdigit() and len(texto_ano) == 4):
                raise ErroLayout(f"{onde}: {deposito}, linha {numero}: ano {texto_ano!r}")
            ano = int(texto_ano)
            if not serie.inicio <= ano <= fim:
                raise ErroLayout(
                    f"{onde}: pedido de {ano}, fora da série ({serie.inicio} a {serie.fim}); versão nova da BADEPI? "
                    "Reveja o fim da série na ficha")
            pedido = linha[i_pedido].strip()
            uf = uf_do_residente.get(pedido)
            if uf in REGIAO_DA_UF and tipo_do_pedido(pedido, prefixos, naturezas):
                contagens.setdefault(ano, Counter())[uf] += 1
    vazios = [ano for ano, c in contagens.items() if not c]
    if vazios:
        raise ErroLayout(f"{onde}: nenhum pedido de residente em {vazios}")
    return contagens


def padronizar_badepi(
    conteudo: bytes, ficha: Ficha, serie: Serie, coleta_id: str, territorios: pd.DataFrame,
) -> pd.DataFrame:
    """Linhas da base: Brasil e regioes (soma das UFs) e as nove UFs do Nordeste, por ano, todas `observado`."""
    onde = f"BADEPI {ficha.id}/{serie.id}"
    conhecidos = set(territorios["territorio_id"])
    registros = []
    for ano, por_uf in contar_residentes(conteudo, serie, onde).items():
        valores = {"BR": sum(por_uf[uf] for uf in REGIAO_DA_UF)}
        for uf, regiao in REGIAO_DA_UF.items():
            valores[regiao] = valores.get(regiao, 0) + por_uf[uf]
        valores |= {territorio: por_uf[uf] for uf, territorio in TERRITORIO_DA_UF.items()}
        registros += [{
            "indicador_id": ficha.id, "subindicador": "", "etapa": "", "rede": "", "territorio_id": territorio,
            "ano": ano, "valor": float(valor), "tipo_dado": "observado", "serie_id": serie.id, "coleta_id": coleta_id,
            "nota": "",
        } for territorio, valor in valores.items() if territorio in conhecidos]
    return normalizar_base(pd.DataFrame(registros, columns=COLUNAS_BASE))
