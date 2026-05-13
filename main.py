
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from base import BaseArquivo

# =========================
# Configuração da página
# =========================
st.set_page_config(
    page_title="Dashboard Dengue - Ji-Paraná",
    page_icon="🦟",
    layout="wide",
)


# =========================
# Funções auxiliares
# =========================
@st.cache_data
def carregar_dados() -> pd.DataFrame:
    """
    Carrega a base CSV do InfoDengue/alerta dengue.
    A base enviada está separada por vírgula.
    """
    base = BaseArquivo()    
    df = base.carregar_arquivo()

    # Padroniza o nome da coluna de data, pois no dicionário aparece como data_ini_SE,
    # mas no arquivo veio como data_iniSE.
    if "data_iniSE" in df.columns and "data_ini_SE" not in df.columns:
        df = df.rename(columns={"data_iniSE": "data_ini_SE"})

    df["data_ini_SE"] = pd.to_datetime(df["data_ini_SE"], errors="coerce")

    # Garante que as principais colunas numéricas estejam como número.
    colunas_numericas = [
        "SE", "casos_est", "casos_est_min", "casos_est_max", "casos", "p_rt1",
        "p_inc100k", "nivel", "Rt", "pop", "tempmin", "tempmed", "tempmax",
        "umidmin", "umidmed", "umidmax", "receptivo", "transmissao", "nivel_inc",
        "notif_accum_year",
    ]

    for coluna in colunas_numericas:
        if coluna in df.columns:
            df[coluna] = pd.to_numeric(df[coluna], errors="coerce")

    # Ordena cronologicamente.
    df = df.sort_values("data_ini_SE").reset_index(drop=True)

    # Campos derivados para análise.
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


def formatar_numero(valor, casas=0):
    if pd.isna(valor):
        return "-"
    if casas == 0:
        return f"{valor:,.0f}".replace(",", ".")
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def calcular_resumo(df: pd.DataFrame) -> dict:
    total_casos = df["casos"].sum()
    pop = df["pop"].dropna().max() if "pop" in df.columns else None

    semana_pico = df.loc[df["casos"].idxmax()] if not df.empty else None
    semanas_vermelhas = int((df["nivel"] == 4).sum()) if "nivel" in df.columns else 0
    casos_vermelho = df.loc[df["nivel"] == 4, "casos"].sum() if "nivel" in df.columns else 0

    incidencia_max = df["p_inc100k"].max() if "p_inc100k" in df.columns else None
    rt_max = df["Rt"].max() if "Rt" in df.columns else None
    semanas_rt_maior_1 = int((df["Rt"] > 1).sum()) if "Rt" in df.columns else 0
    semanas_epidemicas = int((df["nivel_inc"] == 2).sum()) if "nivel_inc" in df.columns else 0

    return {
        "total_casos": total_casos,
        "pop": pop,
        "semana_pico": semana_pico,
        "semanas_vermelhas": semanas_vermelhas,
        "casos_vermelho": casos_vermelho,
        "incidencia_max": incidencia_max,
        "rt_max": rt_max,
        "semanas_rt_maior_1": semanas_rt_maior_1,
        "semanas_epidemicas": semanas_epidemicas,
    }



# =========================
# Entrada dos dados
# =========================
st.title("Dashboard de Dengue - Ji-Paraná")
st.caption("Análise semanal dos casos de dengue, incidência, alerta, Rt, transmissão e clima.")

df_original = carregar_dados()


# =========================
# Filtros
# =========================
st.sidebar.header("Filtros")

min_data = df_original["data_ini_SE"].min().date()
max_data = df_original["data_ini_SE"].max().date()

intervalo_data = st.sidebar.date_input(
    "Período",
    value=(min_data, max_data),
    min_value=min_data,
    max_value=max_data,
)

if isinstance(intervalo_data, tuple) and len(intervalo_data) == 2:
    data_ini, data_fim = intervalo_data
else:
    data_ini, data_fim = min_data, max_data

niveis_disponiveis = sorted(df_original["nivel_alerta"].dropna().unique())
niveis_selecionados = st.sidebar.multiselect(
    "Nível de alerta",
    options=niveis_disponiveis,
    default=niveis_disponiveis,
)

somente_rt_maior_1 = st.sidebar.checkbox("Mostrar somente semanas com Rt > 1", value=False)

mask = (
    (df_original["data_ini_SE"].dt.date >= data_ini)
    & (df_original["data_ini_SE"].dt.date <= data_fim)
    & (df_original["nivel_alerta"].isin(niveis_selecionados))
)

if somente_rt_maior_1:
    mask &= df_original["Rt"] > 1

df = df_original.loc[mask].copy()

if df.empty:
    st.warning("Nenhum registro encontrado para os filtros selecionados.")
    st.stop()

municipio = df_original["municipio_nome"].dropna().iloc[0] if "municipio_nome" in df_original.columns else "Ji-Paraná"
resumo = calcular_resumo(df)



############ -> INICIO DOS INDICADORES
st.subheader("Indicadores principais")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total de casos", formatar_numero(resumo["total_casos"]))
col2.metric("População estimada", formatar_numero(resumo["pop"]))

semana_pico = resumo["semana_pico"]
if semana_pico is not None:
    col3.metric(
        "Semana de pico",
        semana_pico["data_ini_SE"].strftime("%d/%m/%Y"),
        delta=f"{formatar_numero(semana_pico['casos'])} casos",
    )
else:
    col3.metric("Semana de pico", "-")

col4.metric("Maior incidência/Habitantes", f"{formatar_numero(int(semana_pico['casos']) / int(resumo['pop']) * 100, 2)}%")

col5, col6, col7, col8 = st.columns(4)
col5.metric("Semanas em vermelho", formatar_numero(resumo["semanas_vermelhas"]))
col6.metric("Casos em semanas vermelhas", formatar_numero(resumo["casos_vermelho"]))
col7.metric("Maior Rt", formatar_numero(resumo["rt_max"], 2))
col8.metric("Semanas com Rt > 1", formatar_numero(resumo["semanas_rt_maior_1"]))

st.divider()


# =========================
# Gráfico 1: casos e incidência
# =========================
st.subheader("Evolução semanal de casos e incidência")

fig_casos = make_subplots(specs=[[{"secondary_y": True}]])

fig_casos.add_trace(
    go.Bar(
        x=df["data_ini_SE"],
        y=df["casos"],
        name="Casos notificados",
        hovertemplate="Semana: %{x|%d/%m/%Y}<br>Casos: %{y}<extra></extra>",
    ),
    secondary_y=False,
)

fig_casos.add_trace(
    go.Scatter(
        x=df["data_ini_SE"],
        y=df["p_inc100k"],
        name="Incidência por 100 mil",
        mode="lines+markers",
        hovertemplate="Semana: %{x|%d/%m/%Y}<br>Incidência: %{y:.2f}<extra></extra>",
    ),
    secondary_y=True,
)

fig_casos.update_layout(
    height=430,
    xaxis_title="Semana epidemiológica",
    legend_title="Indicador",
    hovermode="x unified",
)
fig_casos.update_yaxes(title_text="Casos", secondary_y=False)
fig_casos.update_yaxes(title_text="Incidência por 100 mil", secondary_y=True)

st.plotly_chart(fig_casos, width="stretch")


# =========================
# Gráfico 2: casos por mês
# =========================
st.subheader("Casos acumulados por mês")

casos_mes = (
    df.groupby(["ano", "mes_num", "mes"], as_index=False)["casos"]
    .sum()
    .sort_values(["ano", "mes_num"])
)

fig_mes = px.bar(
    casos_mes,
    x="mes",
    y="casos",
    text="casos",
    labels={"mes": "Mês", "casos": "Casos"},
)
fig_mes.update_layout(height=380)
fig_mes.update_traces(textposition="outside")
st.plotly_chart(fig_mes, width="stretch")


# =========================
# Gráfico 3: nível de alerta
# =========================
st.subheader("Nível de alerta por semana")

fig_alerta = px.scatter(
    df,
    x="data_ini_SE",
    y="nivel",
    size="casos",
    hover_data={
        "semana_label": True,
        "casos": True,
        "p_inc100k": ":.2f",
        "Rt": ":.2f",
        "nivel_alerta": True,
        "data_ini_SE": False,
    },
    labels={"data_ini_SE": "Semana", "nivel": "Nível de alerta"},
)
fig_alerta.update_yaxes(tickmode="array", tickvals=[1, 2, 3, 4])
fig_alerta.update_layout(height=380)
st.plotly_chart(fig_alerta, width="stretch")


# =========================
# Gráfico 4: Rt e probabilidade Rt > 1
# =========================
col_rt, col_prt = st.columns(2)

with col_rt:
    st.subheader("Rt por semana")
    fig_rt = px.line(
        df,
        x="data_ini_SE",
        y="Rt",
        markers=True,
        labels={"data_ini_SE": "Semana", "Rt": "Rt"},
    )
    fig_rt.add_hline(y=1, line_dash="dash", annotation_text="Rt = 1")
    fig_rt.update_layout(height=380)
    st.plotly_chart(fig_rt, width="stretch")

with col_prt:
    st.subheader("Probabilidade de Rt > 1")
    fig_prt = px.line(
        df,
        x="data_ini_SE",
        y="p_rt1",
        markers=True,
        labels={"data_ini_SE": "Semana", "p_rt1": "p_rt1"},
    )
    fig_prt.add_hline(y=0.95, line_dash="dash", annotation_text="Critério 0,95")
    fig_prt.update_layout(height=380)
    st.plotly_chart(fig_prt, width="stretch")


# =========================
# Gráfico 5: clima e transmissão
# =========================
st.subheader("Clima, receptividade e transmissão")

col_clima, col_trans = st.columns(2)

with col_clima:
    fig_temp = px.line(
        df,
        x="data_ini_SE",
        y=["tempmin", "tempmed", "tempmax"],
        markers=True,
        labels={"data_ini_SE": "Semana", "value": "Temperatura média semanal", "variable": "Indicador"},
    )
    fig_temp.update_layout(height=380)
    st.plotly_chart(fig_temp, width="stretch")

with col_trans:
    transmissao_count = (
        df.groupby("transmissao_desc", as_index=False)
        .agg(semanas=("transmissao", "count"), casos=("casos", "sum"))
        .sort_values("semanas", ascending=False)
    )
    fig_trans = px.bar(
        transmissao_count,
        x="transmissao_desc",
        y="semanas",
        text="semanas",
        hover_data={"casos": True},
        labels={"transmissao_desc": "Evidência de transmissão", "semanas": "Semanas"},
    )
    fig_trans.update_layout(height=380)
    fig_trans.update_traces(textposition="outside")
    st.plotly_chart(fig_trans, width="stretch")


# =========================
# Destaques automáticos
# =========================
st.subheader("Leitura automática dos principais achados")

casos_mes_top = casos_mes.sort_values("casos", ascending=False).head(1).iloc[0]
perc_vermelho = (resumo["casos_vermelho"] / resumo["total_casos"] * 100) if resumo["total_casos"] else 0

st.info(
    f"""
    **{municipio}** registrou **{formatar_numero(resumo['total_casos'])} casos** no período filtrado.  
    O mês com mais casos foi **{casos_mes_top['mes']}**, com **{formatar_numero(casos_mes_top['casos'])} casos**.  
    A semana de pico começou em **{semana_pico['data_ini_SE'].strftime('%d/%m/%Y')}**, com **{formatar_numero(semana_pico['casos'])} casos**.  
    As semanas em alerta vermelho concentraram **{formatar_numero(resumo['casos_vermelho'])} casos**, equivalente a **{formatar_numero(perc_vermelho, 1)}%** dos casos filtrados.
    """
)


# =========================
# Tabela e download
# =========================
st.subheader("Base analítica")

colunas_exibir = [
    "data_ini_SE", "SE", "municipio_nome", "casos", "casos_est", "p_inc100k",
    "nivel_alerta", "Rt", "p_rt1", "nivel_inc_desc", "receptivo_desc",
    "transmissao_desc", "tempmin", "tempmed", "tempmax", "umidmin", "umidmed", "umidmax",
]
colunas_exibir = [c for c in colunas_exibir if c in df.columns]

st.dataframe(
    df[colunas_exibir],
    width="stretch",
    hide_index=True,
)


with st.expander("Dicionário rápido das principais colunas"):
    st.markdown(
        """
        - **data_ini_SE**: primeiro dia da semana epidemiológica.
        - **SE**: semana epidemiológica.
        - **casos**: número de casos notificados por semana.
        - **casos_est**: número estimado de casos por semana usando nowcasting.
        - **p_inc100k**: taxa de incidência estimada por 100 mil habitantes.
        - **nivel**: nível de alerta: 1 verde, 2 amarelo, 3 laranja, 4 vermelho.
        - **Rt**: número reprodutivo estimado dos casos.
        - **p_rt1**: probabilidade de Rt ser maior que 1.
        - **receptivo**: condição climática favorável à transmissão.
        - **transmissao**: evidência de transmissão sustentada.
        - **nivel_inc**: classificação da incidência em relação aos limiares pré-epidêmico e epidêmico.
        """
    )
