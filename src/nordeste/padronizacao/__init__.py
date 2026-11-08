"""Padronizadores: convertem o arquivo bruto de uma coleta para o formato da base."""

import numpy as np
import pandas as pd

from nordeste.caminhos import Caminhos
from nordeste.coletores.registro import Coleta
from nordeste.esquema import COLUNAS_BASE, normalizar_base
from nordeste.fichas import Ficha, Serie
from nordeste.padronizacao.badepi import padronizar_badepi
from nordeste.padronizacao.cetic import padronizar_cetic
from nordeste.padronizacao.erros import ErroLayout
from nordeste.padronizacao.geocapes import padronizar_geocapes
from nordeste.padronizacao.ibid import padronizar_ibid
from nordeste.padronizacao.ipeadata import padronizar_ipeadata
from nordeste.padronizacao.mcti import padronizar_mcti
from nordeste.padronizacao.pintec import padronizar_pintec
from nordeste.padronizacao.planilha import padronizar_planilha
from nordeste.padronizacao.sidra import padronizar_sidra
from nordeste.territorios import territorios_do_nordeste

NOTA_SEM_PESQUISA = "ano sem pesquisa (Censo)"

__all__ = ["ErroLayout", "padronizar"]

_PADRONIZADORES = {
    "sidra": padronizar_sidra,
    "planilha": padronizar_planilha,
    "ipeadata": padronizar_ipeadata,
    "ibid": padronizar_ibid,
    "cetic": padronizar_cetic,
    "geocapes": padronizar_geocapes,
    "badepi": padronizar_badepi,
    "mcti": padronizar_mcti,
    "pintec": padronizar_pintec,
}


def padronizar(
    ficha: Ficha, serie: Serie, coleta: Coleta, caminhos: Caminhos, territorios: pd.DataFrame,
) -> pd.DataFrame:
    """Padroniza o arquivo bruto da coleta, marca os anos de estimativa oficial e os anos sem pesquisa.

    O padronizador vem de parametros["padronizador"] ou, na falta, do coletor da serie. Ele recebe a tabela de
    territorios sem as UFs de fora do Nordeste, a nao ser que a serie peca `todas_as_ufs: true`.
    Anos de parametros["anos_estimativa"] viram estimativa_oficial; linhas indisponiveis
    continuam indisponiveis (valor nulo <=> indisponivel). Os anos de serie.anos_sem_publicacao (dentro de
    inicio..fim) ganham uma linha indisponivel para cada grupo e territorio da serie que a fonte nao trouxe
    nesse ano; valor da fonte nunca e sobrescrito.
    """
    nome = serie.parametros.get("padronizador", serie.coletor)
    if nome not in _PADRONIZADORES:
        raise ErroLayout(f"padronizador desconhecido em {ficha.id}/{serie.id}: {nome}")
    conteudo = (caminhos.raiz / coleta.arquivo).read_bytes()
    if not serie.parametros.get("todas_as_ufs"):
        territorios = territorios_do_nordeste(territorios)
    df = _PADRONIZADORES[nome](conteudo, ficha, serie, coleta.coleta_id, territorios)
    estimados = df["ano"].isin(serie.parametros.get("anos_estimativa", [])) & (
        df["tipo_dado"] != "indisponivel")
    df.loc[estimados, "tipo_dado"] = "estimativa_oficial"
    df = _com_anos_parciais(df, serie)
    return _com_anos_sem_pesquisa(df, serie, coleta.coleta_id)


def _com_anos_parciais(df: pd.DataFrame, serie: Serie) -> pd.DataFrame:
    """`anos_parciais` (com `nota_dos_anos_parciais`): anos que a fonte ainda pode completar; o valor fica como veio e
    a nota da ficha vai para as linhas desses anos (depois da nota da fonte, se houver)."""
    anos = serie.parametros.get("anos_parciais", [])
    if not anos:
        return df
    nota = serie.parametros.get("nota_dos_anos_parciais")
    if not isinstance(nota, str) or not nota.strip():
        raise ErroLayout(f"{serie.id}: anos_parciais exige nota_dos_anos_parciais (texto não vazio)")
    parciais = df["ano"].isin(anos) & (df["tipo_dado"] != "indisponivel")
    df = df.copy()
    df.loc[parciais, "nota"] = [f"{n}; {nota}" if n else nota for n in df.loc[parciais, "nota"]]
    return df


def _com_anos_sem_pesquisa(df: pd.DataFrame, serie: Serie, coleta_id: str) -> pd.DataFrame:
    anos = [a for a in serie.anos_sem_publicacao if a >= serie.inicio and (serie.fim is None or a <= serie.fim)]
    if not anos or df.empty:
        return df
    chave = ["indicador_id", "subindicador", "etapa", "rede", "territorio_id", "serie_id"]
    novas = df[chave].drop_duplicates().merge(pd.DataFrame({"ano": anos}), how="cross")
    novas = novas.merge(df[[*chave, "ano"]], how="left", on=[*chave, "ano"], indicator=True)
    novas = novas[novas["_merge"] == "left_only"].drop(columns="_merge")
    if novas.empty:
        return df
    novas = novas.assign(valor=np.nan, tipo_dado="indisponivel", coleta_id=coleta_id, nota=NOTA_SEM_PESQUISA)
    return normalizar_base(pd.concat([df, novas[COLUNAS_BASE]], ignore_index=True))
