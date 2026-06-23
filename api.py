from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel

from data_service import (
    calcular_resumo,
    carregar_dados,
    casos_por_mes,
    dados_melt,
    obter_dados_filtrados,
    obter_destaques,
    obter_metadados,
    registrar_filtros,
    serializar_dataframe,
)


app = FastAPI(title="API Dashboard Dengue - Ji-Paraná")


class FiltrosRequest(BaseModel):
    data_ini: Optional[str] = None
    data_fim: Optional[str] = None
    niveis_alerta: Optional[list[str]] = None
    somente_rt_maior_1: bool = False


@app.get("/")
def health_check():
    return {"status": "online"}


@app.get("/metadados")
def metadados():
    return obter_metadados()


@app.post("/filtros")
def atualizar_filtros(filtros: FiltrosRequest):
    filtros_registrados = registrar_filtros(
        data_ini=filtros.data_ini,
        data_fim=filtros.data_fim,
        niveis_alerta=filtros.niveis_alerta,
        somente_rt_maior_1=filtros.somente_rt_maior_1,
    )
    return {"filtros": filtros_registrados}


@app.get("/dados/original")
def dados_original():
    return {"dados": serializar_dataframe(carregar_dados())}


@app.get("/dados/filtrados")
def dados_filtrados():
    return {"dados": serializar_dataframe(obter_dados_filtrados())}


@app.get("/indicadores")
def indicadores():
    return calcular_resumo(obter_dados_filtrados())


@app.get("/graficos/casos-incidencia")
def grafico_casos_incidencia():
    colunas = ["data_ini_SE", "casos", "p_inc100k"]
    return {"dados": serializar_dataframe(obter_dados_filtrados()[colunas])}


@app.get("/graficos/casos-mes")
def grafico_casos_mes():
    return {"dados": serializar_dataframe(casos_por_mes(obter_dados_filtrados()))}


@app.get("/graficos/nivel-alerta")
def grafico_nivel_alerta():
    colunas = ["data_ini_SE", "nivel", "casos", "nivel_alerta", "semana_label", "p_inc100k", "Rt"]
    return {"dados": serializar_dataframe(obter_dados_filtrados()[colunas])}


@app.get("/graficos/rt")
def grafico_rt():
    colunas = ["data_ini_SE", "Rt"]
    return {"dados": serializar_dataframe(obter_dados_filtrados()[colunas])}


@app.get("/graficos/probabilidade-rt")
def grafico_probabilidade_rt():
    colunas = ["data_ini_SE", "p_rt1"]
    return {"dados": serializar_dataframe(obter_dados_filtrados()[colunas])}


@app.get("/graficos/temperatura")
def grafico_temperatura():
    df = dados_melt(
        obter_dados_filtrados(),
        ["tempmin", "tempmed", "tempmax"],
        "Indicador",
        "Temperatura",
    )
    return {"dados": serializar_dataframe(df)}


@app.get("/graficos/umidade")
def grafico_umidade():
    df = dados_melt(
        obter_dados_filtrados(),
        ["umidmin", "umidmed", "umidmax"],
        "Indicador",
        "Umidade",
    )
    return {"dados": serializar_dataframe(df)}


@app.get("/graficos/clima-rt")
def grafico_clima_rt():
    colunas = ["data_ini_SE", "casos", "tempmed", "umidmed", "Rt"]
    return {"dados": serializar_dataframe(obter_dados_filtrados()[colunas])}


@app.get("/destaques")
def destaques():
    return obter_destaques()


@app.get("/tabela")
def tabela():
    colunas = [
        "data_ini_SE", "SE", "municipio_nome", "casos", "casos_est", "p_inc100k",
        "nivel_alerta", "Rt", "p_rt1", "nivel_inc_desc", "receptivo_desc",
        "transmissao_desc", "tempmin", "tempmed", "tempmax", "umidmin", "umidmed", "umidmax",
    ]
    df = obter_dados_filtrados()
    colunas = [coluna for coluna in colunas if coluna in df.columns]
    return {"dados": serializar_dataframe(df[colunas]), "colunas": colunas}
