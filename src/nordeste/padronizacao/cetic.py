"""Padronizador das tabelas HTML da TIC Domicilios (Cetic.br): uma pagina por ano, Brasil e regioes numa tabela.

A pagina `https://cetic.br/pt/tics/domicilios/<ano>/domicilios/<tabela>/` traz a tabela com o titulo
(`A4 - DOMICÍLIOS COM ACESSO À INTERNET`; ate 2015, `A4 - PROPORÇÃO DE DOMICÍLIOS ...`), um cabecalho com as respostas
(`Percentual (%)`, `Sim`, `Não` e, conforme o ano, `Não sabe` e `Não respondeu`) e uma linha por recorte: o total do
pais (`Total`, `TOTAL` ou `TOTAL BRASIL`), as cinco regioes e outros recortes (area, renda, classe). A primeira celula
de cada grupo leva o nome do grupo (`REGIÃO`, `REGIÕES DO PAÍS`), por isso o rotulo da linha e a celula logo antes
dos valores. Logo abaixo da tabela, o rodape: a fonte ou a base e o periodo de coleta, sempre com o ano da pesquisa, e,
em 2020, "(Edição COVID-19 - Metodologia adaptada)" depois de "TIC Domicílios 2020".

Cada parte da serie (`parametros.partes`: `url` e `ano`) e uma pagina, guardada pelo coletor `arquivo` num pacote.
Tabela, titulo, cabecalho, total, regioes, valor de 0 a 100 e ano no rodape sao conferidos; qualquer desvio e
ErroLayout. A edicao com metodologia propria (texto entre parenteses depois de "TIC Domicílios <ano>" no rodape) vai
para a `nota` das linhas daquele ano, tirada da pagina, nunca escrita na ficha.
"""

import re
from html.parser import HTMLParser

import pandas as pd

from nordeste.coletores.arquivo import ler_pacote
from nordeste.esquema import COLUNAS_BASE, normalizar_base
from nordeste.fichas import Ficha, Serie
from nordeste.padronizacao.erros import ErroLayout
from nordeste.padronizacao.planilha import numero_br
from nordeste.territorios import normalizar_nome

ROTULOS_DO_TOTAL = frozenset({"total", "total brasil"})
REGIOES = {"norte": "N", "nordeste": "NE", "sudeste": "SE", "sul": "S", "centro-oeste": "CO"}
_EDICAO = re.compile(r"TIC Domic[ií]lios\s+(\d{4})\s*\(([^)]+)\)")
_RODAPE = 1500  # texto logo depois da tabela: notas, fonte (ou base e periodo de coleta), com o ano
# Nota de rodape de 2006 a 2013: o acesso contado e so o do computador ("Considerado somente o acesso a internet via
# computador..." ate 2010; "Excluindo-se o acesso via telefone celular no domicilio" de 2011 a 2013).
_SO_COMPUTADOR = re.compile(
    r"(Considerado somente o acesso [^.]*computador[^.]*\([^)]*\)\.|Excluindo-se o acesso via telefone celular[^.]*\.)",
    re.IGNORECASE)


class _Tabela(HTMLParser):
    """Linhas (celulas como texto) e texto da primeira tabela da pagina, e o texto da pagina depois dela."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.linhas: list[list[str]] = []
        self.texto_da_tabela: list[str] = []
        self.depois: list[str] = []
        self._nivel = 0
        self._fechada = False
        self._linha: list[str] | None = None
        self._celula: list[str] | None = None

    def handle_starttag(self, tag, attrs):
        if self._fechada:
            return
        if tag == "table":
            self._nivel += 1
        elif self._nivel and tag == "tr":
            self._linha = []
        elif self._nivel and tag in ("td", "th") and self._linha is not None:
            self._celula = []

    def handle_endtag(self, tag):
        if self._fechada:
            return
        if tag in ("td", "th") and self._celula is not None:
            self._linha.append(" ".join("".join(self._celula).split()))
            self._celula = None
        elif tag == "tr" and self._linha is not None:
            self.linhas.append(self._linha)
            self._linha = None
        elif tag == "table" and self._nivel:
            self._nivel -= 1
            self._fechada = self._nivel == 0

    def handle_data(self, data):
        if self._fechada:
            self.depois.append(data)
            return
        if self._nivel:
            self.texto_da_tabela.append(data)
        if self._celula is not None:
            self._celula.append(data)


def _rotulo(texto: str) -> str:
    return normalizar_nome(" ".join(texto.split()))


def ler_pagina(conteudo: bytes, tabela: str, ano: int, onde: str) -> tuple[dict[str, float], list[str]]:
    """({territorio_id: percentual de "Sim"}, notas) de uma pagina da TIC Domicilios.

    As notas sao tiradas do rodape: a restricao ao acesso por computador, quando houver, e a edicao com metodologia
    propria (2020).
    """
    try:
        html = conteudo.decode("utf-8")
    except UnicodeDecodeError as erro:
        raise ErroLayout(f"Cetic {onde}: página ilegível ({erro})") from erro
    pagina = _Tabela()
    pagina.feed(html)
    pagina.close()
    if not pagina.linhas:
        raise ErroLayout(f"Cetic {onde}: a página não tem tabela")
    titulo = _rotulo(" ".join(pagina.texto_da_tabela))
    if f"{tabela.lower()} -" not in titulo or "acesso a internet" not in titulo:
        raise ErroLayout(f"Cetic {onde}: a tabela não é a {tabela} de acesso à internet ({titulo[:80]!r})")

    cabecalho = next((l for l in pagina.linhas if l and _rotulo(l[0]).startswith("percentual")), None)
    if cabecalho is None or len(cabecalho) < 3 or _rotulo(cabecalho[1]) != "sim":
        raise ErroLayout(f"Cetic {onde}: cabeçalho fora do esperado (Percentual, Sim, Não...): {cabecalho!r}")
    respostas = len(cabecalho) - 1

    valores: dict[str, float] = {}
    for linha in pagina.linhas:
        if len(linha) <= respostas or linha is cabecalho:
            continue
        rotulo = _rotulo(linha[-respostas - 1])
        territorio = "BR" if rotulo in ROTULOS_DO_TOTAL else REGIOES.get(rotulo)
        if territorio is None:
            continue
        if territorio in valores:
            raise ErroLayout(f"Cetic {onde}: a linha {linha[-respostas - 1]!r} aparece mais de uma vez")
        celula = linha[-respostas]
        try:
            valor = numero_br(celula)
        except ValueError:
            valor = None
        if valor is None or not 0 <= valor <= 100:
            raise ErroLayout(f"Cetic {onde}: {linha[-respostas - 1]}, coluna Sim: esperava percentual, achou {celula!r}")
        valores[territorio] = valor
    faltam = [t for t in ("BR", *REGIOES.values()) if t not in valores]
    if faltam:
        raise ErroLayout(f"Cetic {onde}: faltam as linhas de {', '.join(faltam)}")

    rodape = " ".join("".join(pagina.depois).split())[:_RODAPE]
    if str(ano) not in rodape:
        raise ErroLayout(f"Cetic {onde}: o rodapé da tabela não cita {ano} ({rodape[:120]!r})")
    notas = [re.sub(r"\s+\.", ".", m.group(1)) for m in _SO_COMPUTADOR.finditer(rodape)][:1]
    notas += [m.group(2).strip() for m in _EDICAO.finditer(rodape) if int(m.group(1)) == ano]
    return valores, notas


def padronizar_cetic(
    conteudo: bytes, ficha: Ficha, serie: Serie, coleta_id: str, territorios: pd.DataFrame,
) -> pd.DataFrame:
    """Linhas da base, uma por ano e territorio (Brasil e regioes), todas `observado`.

    `parametros.so_computador` (true ou false) diz se a serie conta so o acesso por computador; a nota de rodape de
    cada pagina tem de concordar, senao a definicao mudou e e ErroLayout. `parametros.nota`, se houver, abre a nota de
    todas as linhas da serie (ex.: so areas urbanas); seguem as notas tiradas da pagina, com o prefixo "Cetic.br:".
    """
    parametros = serie.parametros
    partes = parametros.get("partes")
    if not isinstance(partes, list) or not partes:
        raise ErroLayout(f"Cetic {ficha.id}/{serie.id}: partes deve ser a lista de páginas (url e ano)")
    try:
        paginas = ler_pacote(conteudo)
    except ValueError as erro:
        raise ErroLayout(f"Cetic {ficha.id}/{serie.id}: {erro}") from erro
    conhecidos = set(territorios["territorio_id"])
    nota_da_serie = parametros.get("nota", "")
    so_computador = parametros.get("so_computador")
    if not isinstance(so_computador, bool):
        raise ErroLayout(f"Cetic {ficha.id}/{serie.id}: parametros.so_computador deve ser true ou false")
    registros = []
    for parte in partes:
        url, ano = parte.get("url"), parte.get("ano")
        onde = f"{ficha.id}/{serie.id}, {ano} ({url})"
        if url not in paginas:
            raise ErroLayout(f"Cetic {onde}: página ausente do pacote coletado")
        valores, notas = ler_pagina(paginas[url], parametros.get("tabela", "A4"), ano, onde)
        restrita = any(_SO_COMPUTADOR.fullmatch(n) for n in notas)
        if restrita != so_computador:
            raise ErroLayout(
                f"Cetic {onde}: a série declara so_computador: {str(so_computador).lower()}, mas o rodapé "
                f"{'traz' if restrita else 'não traz'} a restrição ao acesso por computador; a definição mudou")
        nota = "; ".join([nota_da_serie] * bool(nota_da_serie) + [f"Cetic.br: {n}" for n in notas])
        for territorio, valor in valores.items():
            if territorio not in conhecidos:
                continue
            registros.append({
                "indicador_id": ficha.id, "subindicador": "", "etapa": "", "rede": "", "territorio_id": territorio,
                "ano": ano, "valor": valor, "tipo_dado": "observado", "serie_id": serie.id, "coleta_id": coleta_id,
                "nota": nota,
            })
    df = normalizar_base(pd.DataFrame(registros, columns=COLUNAS_BASE))
    if df.duplicated(["territorio_id", "ano"]).any():
        raise ErroLayout(f"Cetic {ficha.id}/{serie.id}: ano repetido nas partes")
    return df
