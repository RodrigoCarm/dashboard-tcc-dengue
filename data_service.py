from datetime import date
from typing import Any

import pandas as pd

from base import BaseArquivo
from cache_system.cache import CacheConfig


cache = CacheConfig()

ARQUIVO_CACHE_KEY = "arquivo_dados"
DADOS_CACHE_KEY = "dados_processados"
FILTROS_CACHE_KEY = "filtros_ativos"


COLUNAS_NUMERICAS = [
    "SE", "casos_est", "casos_est_min", "casos_est_max", "casos", "p_rt1",
    "p_inc100k", "nivel", "Rt", "pop", "tempmin", "tempmed", "tempmax",
    "umidmin", "umidmed", "umidmax", "receptivo", "transmissao", "nivel_inc",
    "notif_accum_year",
]


def carregar_arquivo_cache() -> pd.DataFrame:
    df = cache.get_cache(ARQUIVO_CACHE_KEY)
    if df is None:
        base = BaseArquivo()
        df = base.carregar_arquivo()
        cache.set_cache(ARQUIVO_CACHE_KEY, df)
    return df.copy()


def preparar_dados(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    if "data_iniSE" in df.columns and "data_ini_SE" not in df.columns:
        df = df.rename(columns={"data_iniSE": "data_ini_SE"})

    df["data_ini_SE"] = pd.to_datetime(df["data_ini_SE"], errors="coerce")

    for coluna in COLUNAS_NUMERICAS:
        if coluna in df.columns:
            df[coluna] = pd.to_numeric(df[coluna], errors="coerce")

    df = df.sort_values("data_ini_SE").reset_index(drop=True)

    df["ano"] = df["data_ini_SE"].dt.year
    df["mes_num"] = df["data_ini_SE"].dt.month
    df["mes"] = df["data_ini_SE"].dt.strftime("%m/%Y")
    df["semana_label"] = df["data_ini_SE"].dt.strftime("%d/%m/%Y")

    mapa_nivel = {
        1: "1 - Verde",
        2: "2 - Amarelo",
        3: "3 - Laranja",
        4: "4 - Vermelho",
    }
    df["nivel_alerta"] = df["nivel"].map(mapa_nivel).fillna("Sem classificação")

    mapa_inc = {
        0: "Abaixo do limiar pré-epidêmico",
        1: "Acima do pré-epidêmico",
        2: "Acima do limiar epidêmico",
    }
    df["nivel_inc_desc"] = df["nivel_inc"].map(mapa_inc).fillna("Sem classificação")

    mapa_receptivo = {
        0: "Desfavorável",
        1: "Favorável",
        2: "Favorável por 2 semanas",
        3: "Favorável por 3+ semanas",
    }
    df["receptivo_desc"] = df["receptivo"].map(mapa_receptivo).fillna("Sem classificação")

    mapa_transmissao = {
        0: "Nenhuma evidência",
        1: "Possível",
        2: "Provável",
        3: "Altamente provável",
    }
    df["transmissao_desc"] = df["transmissao"].map(mapa_transmissao).fillna("Sem classificação")

    return df


def carregar_dados() -> pd.DataFrame:
    df = cache.get_cache(DADOS_CACHE_KEY)
    if df is None:
        df = preparar_dados(carregar_arquivo_cache())
        cache.set_cache(DADOS_CACHE_KEY, df)
    return df.copy()


def _to_date(valor: str | date | None, padrao: date) -> date:
    if valor is None:
        return padrao
    if isinstance(valor, date):
        return valor
    data = pd.to_datetime(valor, errors="coerce")
    if pd.isna(data):
        return padrao
    return data.date()


def obter_metadados() -> dict[str, Any]:
    df = carregar_dados()
    niveis = sorted(df["nivel_alerta"].dropna().unique().tolist())
    municipio = (
        df["municipio_nome"].dropna().iloc[0]
        if "municipio_nome" in df.columns and not df["municipio_nome"].dropna().empty
        else "Ji-Paraná"
    )
    return {
        "min_data": df["data_ini_SE"].min().date().isoformat(),
        "max_data": df["data_ini_SE"].max().date().isoformat(),
        "niveis_alerta": niveis,
        "municipio": municipio,
    }


def filtros_padrao() -> dict[str, Any]:
    metadados = obter_metadados()
    return {
        "data_ini": metadados["min_data"],
        "data_fim": metadados["max_data"],
        "niveis_alerta": metadados["niveis_alerta"],
        "somente_rt_maior_1": False,
    }


def registrar_filtros(
    data_ini: str | date | None = None,
    data_fim: str | date | None = None,
    niveis_alerta: list[str] | None = None,
    somente_rt_maior_1: bool = False,
) -> dict[str, Any]:
    padrao = filtros_padrao()
    data_ini_valor = _to_date(data_ini, date.fromisoformat(padrao["data_ini"]))
    data_fim_valor = _to_date(data_fim, date.fromisoformat(padrao["data_fim"]))
    if data_ini_valor > data_fim_valor:
        data_ini_valor, data_fim_valor = data_fim_valor, data_ini_valor

    filtros = {
        "data_ini": data_ini_valor.isoformat(),
        "data_fim": data_fim_valor.isoformat(),
        "niveis_alerta": niveis_alerta if niveis_alerta is not None else padrao["niveis_alerta"],
        "somente_rt_maior_1": somente_rt_maior_1,
    }
    cache.set_cache(FILTROS_CACHE_KEY, filtros)
    return filtros


def obter_filtros() -> dict[str, Any]:
    filtros = cache.get_cache(FILTROS_CACHE_KEY)
    if filtros is None:
        filtros = filtros_padrao()
        cache.set_cache(FILTROS_CACHE_KEY, filtros)
    return filtros


def obter_dados_filtrados() -> pd.DataFrame:
    df = carregar_dados()
    filtros = obter_filtros()
    data_ini = date.fromisoformat(filtros["data_ini"])
    data_fim = date.fromisoformat(filtros["data_fim"])

    mask = (
        (df["data_ini_SE"].dt.date >= data_ini)
        & (df["data_ini_SE"].dt.date <= data_fim)
        & (df["nivel_alerta"].isin(filtros["niveis_alerta"]))
    )

    if filtros["somente_rt_maior_1"]:
        mask &= df["Rt"] > 1

    return df.loc[mask].copy()


def calcular_resumo(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {
            "total_casos": 0,
            "pop": None,
            "semana_pico": None,
            "semanas_vermelhas": 0,
            "casos_vermelho": 0,
            "incidencia_max": None,
            "rt_max": None,
            "semanas_rt_maior_1": 0,
            "semanas_epidemicas": 0,
            "maior_incidencia_habitantes": None,
        }

    total_casos = df["casos"].sum()
    pop = df["pop"].dropna().max() if "pop" in df.columns else None
    semana_pico = df.loc[df["casos"].idxmax()]
    casos_vermelho = df.loc[df["nivel"] == 4, "casos"].sum() if "nivel" in df.columns else 0
    maior_incidencia_habitantes = None

    if pop and pd.notna(pop):
        maior_incidencia_habitantes = int(semana_pico["casos"]) / int(pop) * 100

    return {
        "total_casos": serializar_valor(total_casos),
        "pop": serializar_valor(pop),
        "semana_pico": serializar_linha(semana_pico),
        "semanas_vermelhas": int((df["nivel"] == 4).sum()) if "nivel" in df.columns else 0,
        "casos_vermelho": serializar_valor(casos_vermelho),
        "incidencia_max": serializar_valor(df["p_inc100k"].max()) if "p_inc100k" in df.columns else None,
        "rt_max": serializar_valor(df["Rt"].max()) if "Rt" in df.columns else None,
        "semanas_rt_maior_1": int((df["Rt"] > 1).sum()) if "Rt" in df.columns else 0,
        "semanas_epidemicas": int((df["nivel_inc"] == 2).sum()) if "nivel_inc" in df.columns else 0,
        "maior_incidencia_habitantes": serializar_valor(maior_incidencia_habitantes),
    }


def casos_por_mes(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["ano", "mes_num", "mes", "casos"])
    return (
        df.groupby(["ano", "mes_num", "mes"], as_index=False)["casos"]
        .sum()
        .sort_values(["ano", "mes_num"])
    )


def dados_melt(df: pd.DataFrame, colunas: list[str], var_name: str, value_name: str) -> pd.DataFrame:
    colunas_validas = [coluna for coluna in colunas if coluna in df.columns]
    if df.empty or not colunas_validas:
        return pd.DataFrame(columns=["data_ini_SE", var_name, value_name])
    return df.melt(
        id_vars="data_ini_SE",
        value_vars=colunas_validas,
        var_name=var_name,
        value_name=value_name,
    )


def obter_destaques() -> dict[str, Any]:
    df = obter_dados_filtrados()
    resumo = calcular_resumo(df)
    casos_mes = casos_por_mes(df)
    casos_mes_top = None if casos_mes.empty else serializar_linha(casos_mes.sort_values("casos", ascending=False).head(1).iloc[0])
    total_casos = resumo["total_casos"]
    perc_vermelho = (resumo["casos_vermelho"] / total_casos * 100) if total_casos else 0

    return {
        "municipio": obter_metadados()["municipio"],
        "total_casos": serializar_valor(total_casos),
        "casos_mes_top": casos_mes_top,
        "semana_pico": resumo["semana_pico"],
        "casos_vermelho": serializar_valor(resumo["casos_vermelho"]),
        "perc_vermelho": serializar_valor(perc_vermelho),
    }


def serializar_valor(valor):
    if isinstance(valor, pd.Timestamp):
        return valor.isoformat()
    if pd.isna(valor):
        return None
    if hasattr(valor, "item"):
        return valor.item()
    return valor


def serializar_linha(linha: pd.Series) -> dict[str, Any]:
    return {coluna: serializar_valor(valor) for coluna, valor in linha.to_dict().items()}


def serializar_dataframe(df: pd.DataFrame) -> list[dict[str, Any]]:
    return [
        {coluna: serializar_valor(valor) for coluna, valor in linha.items()}
        for linha in df.to_dict(orient="records")
    ]
