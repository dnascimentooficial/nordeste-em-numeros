"""Padronizador das tabelas regionais da PINTEC (IBGE): empresas industriais, total e as que implementaram inovacao.

Uma parte por edicao (`parametros.partes`: `url`, `ano` e, conforme o arquivo, `arquivo_no_zip` e `aba`), todas em .xls.
A tabela e a 2.2 de 2003 a 2017 ("Empresas [...], total e as que implementaram inovações [...], segundo Grandes Regiões
e Unidades da Federação selecionadas - período <anos>") e a 1 em 2000 ("Empresas, total e as que implementaram
inovações e/ou com projetos, por Regiões e Unidade da Federação - 1998-2000"). Layout conferido nas sete edicoes:

- o titulo, nas primeiras linhas, traz o periodo da edicao (`periodo` da parte, como `2015-2017`);
- uma linha do cabecalho tem `Total` na coluna B e `Que implementaram inovações` na C;
- uma linha por territorio, rotulo na coluna A: `Brasil`, as regioes (em 2000, `Região Nordeste`; e o Sudeste vem
  sem Sao Paulo, `Região Sudeste (excl. SP)`, que nao entra) e as UFs selecionadas; total na coluna B e as que
  implementaram na C. Os numeros sao estimativas da amostra expandida, com casas decimais.

`medida: contagens` grava as duas contagens (subindicadores `total` e `inovadoras`); `medida: taxa` grava a taxa de
inovacao, inovadoras / total x 100, com as duas contagens publicadas da mesma linha (a conta que o IBGE chama de taxa de
inovacao), e a nota diz isso. Entram o Brasil e as regioes; as poucas UFs selecionadas ficam de fora. Qualquer desvio e
ErroLayout.
"""

import io
import math
import numbers
import warnings
import zipfile

import pandas as pd

from nordeste.coletores.arquivo import ler_pacote
from nordeste.esquema import COLUNAS_BASE, normalizar_base
from nordeste.fichas import Ficha, Serie
from nordeste.padronizacao.erros import ErroLayout
from nordeste.territorios import normalizar_nome

TERRITORIOS = {
    "brasil": "BR", "norte": "N", "nordeste": "NE", "sudeste": "SE", "sul": "S", "centro-oeste": "CO",
    "regiao norte": "N", "regiao nordeste": "NE", "regiao sul": "S", "regiao centro-oeste": "CO",
}
NOTA_DA_TAXA = "taxa calculada pelo projeto: empresas que implementaram inovação ÷ total de empresas, contagens da mesma tabela"


def _grade(conteudo: bytes, aba: str | None, onde: str) -> list[list]:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            tabela = pd.read_excel(io.BytesIO(conteudo), sheet_name=aba if aba else 0, header=None, dtype=object,
                                   engine="xlrd")
    except Exception as erro:  # noqa: BLE001 - qualquer falha de leitura e layout inesperado
        raise ErroLayout(f"{onde}: planilha ilegível ({erro})") from erro
    return [list(linha) for linha in tabela.itertuples(index=False, name=None)]


def _texto(celula) -> str:
    return " ".join(celula.split()) if isinstance(celula, str) else ""


def _numero(celula, onde: str) -> float:
    if not isinstance(celula, numbers.Real) or isinstance(celula, bool) or math.isnan(celula) or celula < 0:
        raise ErroLayout(f"{onde}: esperava número não negativo, achou {celula!r}")
    return float(celula)


def ler_edicao(conteudo: bytes, parte: dict, onde: str) -> dict[str, tuple[float, float]]:
    """{territorio: (total, inovadoras)} do Brasil e das regioes publicadas na tabela da edicao."""
    if parte.get("arquivo_no_zip"):
        try:
            with zipfile.ZipFile(io.BytesIO(conteudo)) as zip_:
                conteudo = zip_.read(parte["arquivo_no_zip"])
        except (zipfile.BadZipFile, KeyError) as erro:
            raise ErroLayout(f"{onde}: {parte['arquivo_no_zip']} ausente ou zip ilegível ({erro})") from erro
    grade = _grade(conteudo, parte.get("aba"), onde)
    topo = " ".join(_texto(c) for linha in grade[:4] for c in linha)
    if "Empresas" not in topo or "implementaram inova" not in topo or parte["periodo"] not in topo:
        raise ErroLayout(f"{onde}: o título não é o da tabela de empresas inovadoras de {parte['periodo']}: {topo[:200]!r}")
    cabecalho = next((i for i, linha in enumerate(grade[:12]) if len(linha) > 2 and _texto(linha[1]) == "Total"
                      and _texto(linha[2]).startswith("Que implementaram inovaç")), None)
    if cabecalho is None:
        raise ErroLayout(f"{onde}: não achei o cabeçalho com Total (B) e Que implementaram inovações (C)")
    valores: dict[str, tuple[float, float]] = {}
    for numero, linha in enumerate(grade[cabecalho + 1:], start=cabecalho + 2):
        territorio = TERRITORIOS.get(normalizar_nome(_texto(linha[0]))) if linha else None
        if territorio is None:
            continue
        if territorio in valores:
            raise ErroLayout(f"{onde}, linha {numero}: {territorio} repetido")
        total = _numero(linha[1], f"{onde}, linha {numero}, total")
        inovadoras = _numero(linha[2], f"{onde}, linha {numero}, inovadoras")
        if inovadoras > total or total == 0:
            raise ErroLayout(f"{onde}, linha {numero}: {inovadoras} inovadoras de {total} empresas")
        valores[territorio] = (total, inovadoras)
    if not {"BR", "NE"} <= set(valores):
        raise ErroLayout(f"{onde}: faltam o Brasil ou o Nordeste (achei {sorted(valores)})")
    return valores


def padronizar_pintec(
    conteudo: bytes, ficha: Ficha, serie: Serie, coleta_id: str, territorios: pd.DataFrame,
) -> pd.DataFrame:
    medida = serie.parametros.get("medida")
    if medida not in ("contagens", "taxa"):
        raise ErroLayout(f"PINTEC {ficha.id}/{serie.id}: medida deve ser contagens ou taxa, veio {medida!r}")
    try:
        arquivos = ler_pacote(conteudo)
    except ValueError as erro:
        raise ErroLayout(f"PINTEC {ficha.id}/{serie.id}: {erro}") from erro
    registros = []
    for parte in serie.parametros["partes"]:
        onde = f"PINTEC {ficha.id}/{serie.id}, edição {parte.get('ano')}"
        if not (serie.inicio <= parte.get("ano", 0) <= (serie.fim or 9999)) or not parte.get("periodo"):
            raise ErroLayout(f"{onde}: a parte precisa de ano dentro da série e do período da edição")
        if parte["url"] not in arquivos:
            raise ErroLayout(f"{onde}: {parte['url']} ausente do pacote coletado")
        for territorio, (total, inovadoras) in ler_edicao(arquivos[parte["url"]], parte, onde).items():
            if medida == "taxa":
                pares = [("", inovadoras / total * 100, NOTA_DA_TAXA)]
            else:
                pares = [("total", total, ""), ("inovadoras", inovadoras, "")]
            registros += [{
                "indicador_id": ficha.id, "subindicador": sub, "etapa": "", "rede": "", "territorio_id": territorio,
                "ano": parte["ano"], "valor": valor, "tipo_dado": "observado", "serie_id": serie.id,
                "coleta_id": coleta_id, "nota": nota,
            } for sub, valor, nota in pares]
    return normalizar_base(pd.DataFrame(registros, columns=COLUNAS_BASE))
