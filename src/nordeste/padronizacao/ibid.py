"""Padronizador da serie historica do IBID (INPI): uma aba por ano, um territorio por linha.

Layout da planilha `ibid-serie-historica.xlsx`, conferido no arquivo de 2025:

- abas `IBID <ano>`: A1 traz o ano, C1 o rotulo `IBID - Geral` e a linha 3 os rotulos dos subindices (D a L). Da linha 4
  em diante vem um territorio por linha: nome (A), sigla do INPI (B), indice geral (C), `IBID - Contexto` (D), cinco
  pilares (E a I), `IBID - Resultado` (J) e dois pilares (K e L). Primeiro as 27 UFs, depois as regioes e o Brasil;
- ao lado das regioes, nas colunas N e O, a tabela de pesos (UF e PIB per capita em R$ 10 mil) com que o INPI agrega
  as UFs em regioes e Brasil. Nao e territorio nem indice: fica de fora, e por isso so as colunas A a L sao lidas;
- aba `IBID_série hist`: a posicao de cada UF no ranking do indice geral, ano a ano. Serve de conferencia: a posicao
  calculada com os valores lidos na coluna C tem de ser a publicada. Coluna trocada nao passa despercebida.

A sigla do INPI nao e a do projeto (Sergipe e Sudeste sao ambos `SE`; o Sul e `SU`), entao o par nome e sigla e
conferido contra a tabela abaixo e o territorio da base sai do nome. Qualquer desvio (aba, rotulo, territorio que
falta, sobra ou repete, celula vazia ou fora de 0 a 1, posicao que nao bate) e ErroLayout com o lugar exato: o
consolidar deixa a serie pendente e a publicacao mantem as linhas ja publicadas.
"""

import io
import math
import numbers
import re
import warnings

import pandas as pd

from nordeste.esquema import COLUNAS_BASE, normalizar_base
from nordeste.fichas import Ficha, Serie
from nordeste.padronizacao.erros import ErroLayout
from nordeste.territorios import normalizar_nome, territorio_por_nome

ABA_DO_ANO = re.compile(r"IBID (\d{4})")
ABA_DAS_POSICOES = "IBID_série hist"
ROTULO_GERAL = "IBID - Geral"  # em C1
ROTULOS_DA_LINHA_3 = (  # D3 a L3
    "IBID - Contexto", "Instituições", "Capital humano", "Infraestrutura", "Economia", "Negócios",
    "IBID - Resultado", "Conhecimento e tecnologia", "Economia criativa",
)
COLUNAS = {"geral": 2, "contexto": 3, "resultado": 9}  # subindicador -> coluna (0 = A)
_PRIMEIRA_LINHA = 3  # linha 4 da planilha
_ULTIMA_COLUNA = 12  # colunas A a L; M em diante (pesos) fica de fora

UFS_DO_INPI = {
    "AC": "Acre", "AL": "Alagoas", "AM": "Amazonas", "AP": "Amapá", "BA": "Bahia", "CE": "Ceará",
    "DF": "Distrito Federal", "ES": "Espírito Santo", "GO": "Goiás", "MA": "Maranhão", "MG": "Minas Gerais",
    "MS": "Mato Grosso do Sul", "MT": "Mato Grosso", "PA": "Pará", "PB": "Paraíba", "PE": "Pernambuco",
    "PI": "Piauí", "PR": "Paraná", "RJ": "Rio de Janeiro", "RN": "Rio Grande do Norte", "RO": "Rondônia",
    "RR": "Roraima", "RS": "Rio Grande do Sul", "SC": "Santa Catarina", "SE": "Sergipe", "SP": "São Paulo",
    "TO": "Tocantins",
}
AGREGADOS_DO_INPI = {
    "Norte": "NO", "Nordeste": "NE", "Sudeste": "SE", "Sul": "SU", "Centro-Oeste": "CO", "Brasil": "BR",
}
_PARES = {
    **{(normalizar_nome(nome), sigla): ("uf", sigla) for sigla, nome in UFS_DO_INPI.items()},
    **{(normalizar_nome(nome), sigla): ("agregado", nome) for nome, sigla in AGREGADOS_DO_INPI.items()},
}


def _vazia(celula) -> bool:
    return celula is None or (isinstance(celula, float) and math.isnan(celula)) or (
        isinstance(celula, str) and not celula.strip())


def _numero(celula) -> bool:
    return isinstance(celula, numbers.Real) and not isinstance(celula, bool) and not math.isnan(celula)


def _texto(celula) -> str:
    return celula.strip() if isinstance(celula, str) else ""


def _celula(grade: list[list], linha: int, coluna: int):
    if linha >= len(grade) or coluna >= len(grade[linha]):
        return None
    return grade[linha][coluna]


def _endereco(linha: int, coluna: int) -> str:
    return f"{chr(ord('A') + coluna)}{linha + 1}"


def ler_abas(conteudo: bytes) -> dict[str, list[list]]:
    """Todas as abas do xlsx como grades de celulas (None no lugar de celula vazia)."""
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Cannot parse header or footer", category=UserWarning)
            abas = pd.read_excel(io.BytesIO(conteudo), sheet_name=None, header=None, dtype=object, engine="openpyxl")
    except Exception as erro:
        raise ErroLayout(f"IBID: planilha ilegível ({erro})") from erro
    return {
        nome: [[None if _vazia(c) else c for c in linha] for linha in tabela.itertuples(index=False, name=None)]
        for nome, tabela in abas.items()
    }


def _abas_dos_anos(abas: dict[str, list[list]], serie: Serie) -> dict[int, str]:
    """{ano: aba} de `inicio` a `fim` da serie; aba que falta ou ano novo fora da cobertura e erro."""
    achadas = {int(m.group(1)): nome for nome in abas if (m := ABA_DO_ANO.fullmatch(nome.strip()))}
    fim = serie.fim if serie.fim is not None else max(achadas, default=serie.inicio)
    esperados = range(serie.inicio, fim + 1)
    faltam = [a for a in esperados if a not in achadas]
    if faltam:
        raise ErroLayout(
            f"IBID: faltam as abas {', '.join(f'IBID {a}' for a in faltam)} (abas do arquivo: {', '.join(abas)})")
    fora = sorted(a for a in achadas if a not in esperados)
    if fora:
        raise ErroLayout(
            f"IBID: abas fora da cobertura da série ({serie.inicio} a {fim}): "
            f"{', '.join(achadas[a] for a in fora)}. Edição nova: suba o fim da série na ficha")
    return {a: achadas[a] for a in esperados}


def _conferir_cabecalho(grade: list[list], aba: str, ano: int) -> None:
    esperado = {(0, 0): ano, (0, 2): ROTULO_GERAL}
    esperado |= {(2, 3 + i): rotulo for i, rotulo in enumerate(ROTULOS_DA_LINHA_3)}
    for (linha, coluna), valor in esperado.items():
        achado = _celula(grade, linha, coluna)
        igual = achado == valor if isinstance(valor, int) else _texto(achado) == valor
        if not igual:
            raise ErroLayout(
                f"IBID, aba {aba}: esperava {valor!r} em {_endereco(linha, coluna)}, achou {achado!r} "
                "(a planilha mudou de layout)")


def _linhas_da_aba(grade: list[list], aba: str) -> dict[tuple[str, str], list]:
    """{(tipo, chave): linha} das 27 UFs, das cinco regioes e do Brasil; qualquer outra linha com numero e erro."""
    achadas: dict[tuple[str, str], list] = {}
    for posicao in range(_PRIMEIRA_LINHA, len(grade)):
        linha = (grade[posicao] + [None] * _ULTIMA_COLUNA)[:_ULTIMA_COLUNA]
        nome, sigla = _texto(linha[0]), _texto(linha[1])
        tem_numero = any(not _vazia(c) for c in linha[2:])
        if not nome and not sigla and not tem_numero:
            continue  # linha em branco (ou so a tabela de pesos, nas colunas N e O)
        territorio = _PARES.get((normalizar_nome(nome), sigla))
        if territorio is None:
            raise ErroLayout(
                f"IBID, aba {aba}, linha {posicao + 1}: território não reconhecido {linha[0]!r}/{linha[1]!r}")
        if territorio in achadas:
            raise ErroLayout(f"IBID, aba {aba}, linha {posicao + 1}: {nome} repetido")
        achadas[territorio] = linha
    esperados = [("uf", s) for s in UFS_DO_INPI] + [("agregado", n) for n in AGREGADOS_DO_INPI]
    faltam = [UFS_DO_INPI.get(c, c) for t, c in esperados if (t, c) not in achadas]
    if faltam:
        raise ErroLayout(f"IBID, aba {aba}: faltam as linhas de {', '.join(faltam)}")
    return achadas


def _indice(linha: list, coluna: int, aba: str, nome: str) -> float:
    celula = linha[coluna]
    if not _numero(celula) or not 0 <= celula <= 1:
        raise ErroLayout(
            f"IBID, aba {aba}, {nome}, coluna {chr(ord('A') + coluna)}: esperava índice de 0 a 1, achou {celula!r}")
    return float(celula)


def _posicoes_publicadas(abas: dict[str, list[list]]) -> dict[int, dict[str, int]]:
    """{ano: {sigla: posicao}} da aba de posicoes no ranking do indice geral."""
    grade = abas.get(ABA_DAS_POSICOES)
    if grade is None:
        raise ErroLayout(f"IBID: falta a aba {ABA_DAS_POSICOES!r}, que confere a coluna do índice geral")
    cabecalho = next((i for i, linha in enumerate(grade) if linha and _texto(linha[0]) == "UF"), None)
    if cabecalho is None:
        raise ErroLayout(f"IBID, aba {ABA_DAS_POSICOES}: não achei a linha de cabeçalho (UF e os anos)")
    anos = {c: int(v) for c, v in enumerate(grade[cabecalho]) if c and _numero(v) and float(v).is_integer()}
    posicoes: dict[int, dict[str, int]] = {ano: {} for ano in anos.values()}
    for linha in grade[cabecalho + 1:]:
        sigla = _texto(linha[0]) if linha else ""
        if sigla not in UFS_DO_INPI:
            continue
        for coluna, ano in anos.items():
            if coluna < len(linha) and _numero(linha[coluna]):
                posicoes[ano][sigla] = int(linha[coluna])
    return posicoes


def posicoes_calculadas(geral_das_ufs: dict[str, float]) -> dict[str, int]:
    """Posicao de cada UF no ranking do indice geral: 1 mais o numero de UFs com indice maior."""
    return {uf: 1 + sum(outro > valor for outro in geral_das_ufs.values()) for uf, valor in geral_das_ufs.items()}


def _conferir_posicoes(ano: int, geral_das_ufs: dict[str, float], publicadas: dict[int, dict[str, int]]) -> None:
    do_ano = publicadas.get(ano, {})
    if set(do_ano) != set(UFS_DO_INPI):
        faltam = sorted(set(UFS_DO_INPI) - set(do_ano))
        raise ErroLayout(f"IBID, aba {ABA_DAS_POSICOES}: {ano} sem a posição de {', '.join(faltam)}")
    divergentes = [
        f"{uf} {calculada}º (publicada {do_ano[uf]}º)"
        for uf, calculada in posicoes_calculadas(geral_das_ufs).items() if calculada != do_ano[uf]
    ]
    if divergentes:
        raise ErroLayout(
            f"IBID {ano}: a posição calculada com a coluna C não é a publicada em {ABA_DAS_POSICOES}: "
            f"{', '.join(divergentes[:5])}; a coluna do índice geral pode ter mudado")


def ler_ibid(conteudo: bytes, serie: Serie) -> dict[int, dict[str, dict[str, float]]]:
    """{ano: {territorio do INPI: {subindicador: valor}}}, com as 27 UFs (pela sigla) e os agregados (pelo nome).

    Confere abas, cabecalhos, territorios, valores de 0 a 1 e a posicao de cada UF no ranking publicado.
    """
    abas = ler_abas(conteudo)
    publicadas = _posicoes_publicadas(abas)
    resultado: dict[int, dict[str, dict[str, float]]] = {}
    for ano, aba in _abas_dos_anos(abas, serie).items():
        grade = abas[aba]
        _conferir_cabecalho(grade, aba, ano)
        do_ano = {}
        for (tipo, chave), linha in _linhas_da_aba(grade, aba).items():
            nome = UFS_DO_INPI[chave] if tipo == "uf" else chave
            do_ano[chave] = {sub: _indice(linha, coluna, aba, nome) for sub, coluna in COLUNAS.items()}
        _conferir_posicoes(ano, {uf: do_ano[uf]["geral"] for uf in UFS_DO_INPI}, publicadas)
        resultado[ano] = do_ano
    return resultado


def _linha(ficha: Ficha, serie: Serie, coleta_id: str, territorio: str, ano: int, valor: float, sub: str = "") -> dict:
    return {
        "indicador_id": ficha.id, "subindicador": sub, "etapa": "", "rede": "", "territorio_id": territorio,
        "ano": ano, "valor": valor, "tipo_dado": "observado", "serie_id": serie.id, "coleta_id": coleta_id, "nota": "",
    }


def _padronizar_posicoes(
    conteudo: bytes, ficha: Ficha, serie: Serie, coleta_id: str, territorios: pd.DataFrame,
) -> pd.DataFrame:
    """`medida: posicao`: a posicao nacional de cada UF no ranking do indice geral (1 a 27, aba de posicoes), uma
    linha por UF da tabela de territorios e ano. A leitura e a mesma do indice: so sai a posicao que confere com a
    calculada pela coluna C. Brasil e regioes nao tem posicao."""
    publicadas = _posicoes_publicadas(ler_abas(conteudo))
    registros = []
    for ano in ler_ibid(conteudo, serie):
        for sigla, posicao in publicadas[ano].items():
            territorio = territorio_por_nome(territorios, UFS_DO_INPI[sigla])
            if territorio is not None:
                registros.append(_linha(ficha, serie, coleta_id, territorio, ano, float(posicao)))
    return normalizar_base(pd.DataFrame(registros, columns=COLUNAS_BASE))


def padronizar_ibid(
    conteudo: bytes, ficha: Ficha, serie: Serie, coleta_id: str, territorios: pd.DataFrame,
) -> pd.DataFrame:
    """Linhas da base: Brasil, regioes e as UFs da tabela de territorios (as demais UFs sao lidas e conferidas, mas
    nao entram), uma por ano e subindicador (`geral`, `contexto` e `resultado`), todas `observado`. Com
    `parametros.medida: posicao`, a posicao nacional de cada UF no ranking (ver `_padronizar_posicoes`)."""
    medida = serie.parametros.get("medida", "indice")
    if medida == "posicao":
        return _padronizar_posicoes(conteudo, ficha, serie, coleta_id, territorios)
    if medida != "indice":
        raise ErroLayout(f"IBID: medida desconhecida {medida!r} em {ficha.id}/{serie.id} (use indice ou posicao)")
    por_nome = {**UFS_DO_INPI, **{nome: nome for nome in AGREGADOS_DO_INPI}}
    registros = []
    for ano, do_ano in ler_ibid(conteudo, serie).items():
        for chave, valores in do_ano.items():
            territorio = territorio_por_nome(territorios, por_nome[chave])
            if territorio is None:
                continue
            for subindicador, valor in valores.items():
                registros.append({
                    "indicador_id": ficha.id, "subindicador": subindicador, "etapa": "", "rede": "",
                    "territorio_id": territorio, "ano": ano, "valor": valor, "tipo_dado": "observado",
                    "serie_id": serie.id, "coleta_id": coleta_id, "nota": "",
                })
    return normalizar_base(pd.DataFrame(registros, columns=COLUNAS_BASE))
