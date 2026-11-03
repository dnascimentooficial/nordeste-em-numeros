"""Padronizador do JSON montado pelo coletor `geocapes` (programas e discentes de pos-graduacao, por UF do programa).

O bruto traz o indicador (id, descricao e o aviso de metodo que o proprio GeoCAPES mostra) e, por ano, as contagens
somadas pelos campos do `sumarizador`: `[{"IDUF": "SP", "REFERENCIAL": 903}, ...]` para programas e
`[{"UF": "SP", "GRAU": "Doutorado", "FLUXO": "Titulado", "REFERENCIAL": 4321}, ...]` para discentes.

Parametros da serie: `indicador`, `descricao`, `campo_uf` (`IDUF` ou `UF`), `aviso` (trecho que o aviso do indicador
tem de conter: a quebra de 2016 para 2017 vem dele) e, opcional, `filtro` ({campo: [valores aceitos]}) com
`dominios` ({campo: [todos os valores conhecidos]}): valor fora do dominio e erro, para que um grau ou situacao novos nao
entrem nem saiam calados. Ano fora da serie, ano que falta, UF desconhecida, contagem que nao e inteiro nao negativo e
linha repetida tambem sao ErroLayout.

UF sem linha no ano conta zero (o GeoCAPES so lista UF com programa). O Nordeste, as outras regioes e o Brasil sao a
soma das UFs: a API nao publica agregado.
"""

import json

import pandas as pd

from nordeste.esquema import COLUNAS_BASE, normalizar_base
from nordeste.fichas import Ficha, Serie
from nordeste.padronizacao.erros import ErroLayout

REGIAO_DA_UF = {
    "AC": "N", "AP": "N", "AM": "N", "PA": "N", "RO": "N", "RR": "N", "TO": "N",
    "MA": "NE", "PI": "NE", "CE": "NE", "RN": "NE", "PB": "NE", "PE": "NE", "AL": "NE", "SE": "NE", "BA": "NE",
    "ES": "SE", "MG": "SE", "RJ": "SE", "SP": "SE",
    "PR": "S", "RS": "S", "SC": "S",
    "DF": "CO", "GO": "CO", "MS": "CO", "MT": "CO",
}
TERRITORIO_DA_UF = {uf: ("SE_UF" if uf == "SE" else uf) for uf, regiao in REGIAO_DA_UF.items() if regiao == "NE"}


def contagens_por_uf(conteudo: bytes, serie: Serie, onde: str) -> dict[int, dict[str, int]]:
    """{ano: {sigla da UF: contagem}} com as 27 UFs (zero onde o ano nao traz a UF), de `inicio` a `fim` da serie."""
    p = serie.parametros
    try:
        bruto = json.loads(conteudo)
        indicador, anos = bruto["indicador"], bruto["anos"]
    except (ValueError, KeyError, TypeError) as erro:
        raise ErroLayout(f"{onde}: JSON ilegível ou sem indicador e anos ({erro!r})") from erro
    if indicador.get("id") != p["indicador"] or indicador.get("descricao") != p["descricao"]:
        raise ErroLayout(f"{onde}: indicador {indicador.get('id')!r} {indicador.get('descricao')!r} não é o da ficha")
    if p["aviso"] not in (indicador.get("mensagem") or ""):
        raise ErroLayout(f"{onde}: o aviso do indicador mudou: {indicador.get('mensagem')!r}")
    if bruto.get("sumarizador") != p["sumarizador"]:
        raise ErroLayout(f"{onde}: sumarizador {bruto.get('sumarizador')!r}, esperava {p['sumarizador']!r}")
    esperados = [str(a) for a in range(serie.inicio, (serie.fim or serie.inicio) + 1)]
    if sorted(anos) != esperados:
        raise ErroLayout(f"{onde}: anos {sorted(anos)}, esperava {esperados[0]} a {esperados[-1]}")
    campo_uf, filtro, dominios = p["campo_uf"], p.get("filtro", {}), p.get("dominios", {})
    campos = [c.strip().upper() for c in p["sumarizador"].split(",")]
    resultado: dict[int, dict[str, int]] = {}
    for ano in esperados:
        contagens = dict.fromkeys(REGIAO_DA_UF, 0)
        vistos = set()
        for item in anos[ano].get("dados", []) if isinstance(anos[ano], dict) else []:
            if set(item) != {*campos, "REFERENCIAL"}:
                raise ErroLayout(f"{onde}, {ano}: campos {sorted(item)}, esperava {sorted([*campos, 'REFERENCIAL'])}")
            chave = tuple(item[c] for c in campos)
            if chave in vistos:
                raise ErroLayout(f"{onde}, {ano}: linha repetida {chave}")
            vistos.add(chave)
            uf, valor = item[campo_uf], item["REFERENCIAL"]
            if uf not in REGIAO_DA_UF:
                raise ErroLayout(f"{onde}, {ano}: UF desconhecida {uf!r}")
            if not isinstance(valor, int) or isinstance(valor, bool) or valor < 0:
                raise ErroLayout(f"{onde}, {ano}: contagem inválida {valor!r} ({chave})")
            for campo, conhecidos in dominios.items():
                if item[campo] not in conhecidos:
                    raise ErroLayout(f"{onde}, {ano}: {campo} {item[campo]!r} fora dos valores conhecidos {conhecidos}")
            if all(item[campo] in aceitos for campo, aceitos in filtro.items()):
                contagens[uf] += valor
        if not vistos:
            raise ErroLayout(f"{onde}, {ano}: sem contagens")
        resultado[int(ano)] = contagens
    return resultado


def padronizar_geocapes(
    conteudo: bytes, ficha: Ficha, serie: Serie, coleta_id: str, territorios: pd.DataFrame,
) -> pd.DataFrame:
    """Linhas da base: Brasil e regioes (somas das UFs) e as nove UFs do Nordeste, por ano, todas `observado`."""
    onde = f"GeoCAPES {ficha.id}/{serie.id}"
    registros = []
    for ano, contagens in contagens_por_uf(conteudo, serie, onde).items():
        valores = {"BR": sum(contagens.values())}
        for uf, regiao in REGIAO_DA_UF.items():
            valores[regiao] = valores.get(regiao, 0) + contagens[uf]
        valores |= {territorio: contagens[uf] for uf, territorio in TERRITORIO_DA_UF.items()}
        for territorio, valor in valores.items():
            if territorio not in set(territorios["territorio_id"]):
                continue
            registros.append({
                "indicador_id": ficha.id, "subindicador": "", "etapa": "", "rede": "", "territorio_id": territorio,
                "ano": ano, "valor": float(valor), "tipo_dado": "observado", "serie_id": serie.id,
                "coleta_id": coleta_id, "nota": "",
            })
    return normalizar_base(pd.DataFrame(registros, columns=COLUNAS_BASE))
