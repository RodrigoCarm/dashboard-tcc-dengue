
import os
from datetime import date

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st
from plotly.subplots import make_subplots

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
API_URL = os.getenv("DENGUE_API_URL", "http://127.0.0.1:8000")


def chamar_api(metodo: str, caminho: str, **kwargs):
    try:
        resposta = requests.request(metodo, f"{API_URL}{caminho}", timeout=15, **kwargs)
        resposta.raise_for_status()
        return resposta.json()
    except requests.RequestException as exc:
        st.error(f"Não foi possível conectar na API FastAPI em {API_URL}. Detalhes: {exc}")
        st.stop()


def registros_para_dataframe(registros: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(registros)
    if "data_ini_SE" in df.columns:
        df["data_ini_SE"] = pd.to_datetime(df["data_ini_SE"], errors="coerce")
    return df


def carregar_dataframe_endpoint(caminho: str) -> pd.DataFrame:
    payload = chamar_api("GET", caminho)
    return registros_para_dataframe(payload.get("dados", []))


@st.cache_data(ttl=60)
def carregar_metadados() -> dict:
    return chamar_api("GET", "/metadados")


def registrar_filtros_api(data_ini: date, data_fim: date, niveis_alerta: list[str], somente_rt_maior_1: bool):
    return chamar_api(
        "POST",
        "/filtros",
        json={
            "data_ini": data_ini.isoformat(),
            "data_fim": data_fim.isoformat(),
            "niveis_alerta": niveis_alerta,
            "somente_rt_maior_1": somente_rt_maior_1,
        },
    )


def formatar_numero(valor, casas=0):
    if pd.isna(valor):
        return "-"
    if casas == 0:
        return f"{valor:,.0f}".replace(",", ".")
    return f"{valor:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


# =========================
# Entrada dos dados
# =========================
st.title("Análise dos casos de dengue - Ji-Paraná")
st.caption("Análise semanal dos casos de dengue, incidência, alerta, Rt, transmissão e clima.")

metadados = carregar_metadados()


# =========================
# Filtros
# =========================
st.sidebar.header("Filtros")

min_data = date.fromisoformat(metadados["min_data"])
max_data = date.fromisoformat(metadados["max_data"])

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

niveis_disponiveis = metadados["niveis_alerta"]
niveis_selecionados = st.sidebar.multiselect(
    "Nível de alerta",
    options=niveis_disponiveis,
    default=niveis_disponiveis,
)

somente_rt_maior_1 = st.sidebar.checkbox("Mostrar somente semanas com Rt > 1", value=False)

registrar_filtros_api(data_ini, data_fim, niveis_selecionados, somente_rt_maior_1)
df = carregar_dataframe_endpoint("/dados/filtrados")

if df.empty:
    st.warning("Nenhum registro encontrado para os filtros selecionados.")
    st.stop()

municipio = metadados.get("municipio", "Ji-Paraná")
resumo = chamar_api("GET", "/indicadores")



############ -> INICIO DOS INDICADORES
st.subheader("Indicadores principais")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Total de casos", formatar_numero(resumo["total_casos"]))
col2.metric("População estimada", formatar_numero(resumo["pop"]))

semana_pico = resumo["semana_pico"]
if semana_pico is not None:
    col3.metric(
        "Semana de pico",
        pd.to_datetime(semana_pico["data_ini_SE"]).strftime("%d/%m/%Y"),
        delta=f"{formatar_numero(semana_pico['casos'])} casos",
    )
else:
    col3.metric("Semana de pico", "-")

col4.metric("Maior incidência/Habitantes", f"{formatar_numero(resumo['maior_incidencia_habitantes'], 2)}%")

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

df_casos = carregar_dataframe_endpoint("/graficos/casos-incidencia")
fig_casos = make_subplots(specs=[[{"secondary_y": True}]])

fig_casos.add_trace(
    go.Bar(
        x=df_casos["data_ini_SE"],
        y=df_casos["casos"],
        name="Casos notificados",
        hovertemplate="Semana: %{x|%d/%m/%Y}<br>Casos: %{y}<extra></extra>",
    ),
    secondary_y=False,
)

fig_casos.add_trace(
    go.Scatter(
        x=df_casos["data_ini_SE"],
        y=df_casos["p_inc100k"],
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

casos_mes = carregar_dataframe_endpoint("/graficos/casos-mes")

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
st.info(
    """
    O nível de alerta do **InfoDengue** resume a situação de transmissão no município a cada semana.
    A classificação considera condições climáticas favoráveis, presença de casos, crescimento da
    transmissão pelo Rt e incidência acima do padrão histórico.

    **Verde:** clima desfavorável e baixa atividade viral.  
    **Amarelo:** clima favorável e presença de pelo menos um caso.  
    **Laranja:** incidência em crescimento, com Rt > 1 por pelo menos duas semanas consecutivas.  
    **Vermelho:** incidência alta em relação ao histórico do município.
    """
)

df_alerta = carregar_dataframe_endpoint("/graficos/nivel-alerta")

fig_alerta = px.scatter(
    df_alerta,
    x="data_ini_SE",
    y="nivel",
    size="casos",
    color="nivel_alerta",
    category_orders={
        "nivel_alerta": ["1 - Verde", "2 - Amarelo", "3 - Laranja", "4 - Vermelho"],
    },
    color_discrete_map={
        "1 - Verde": "#2ca02c",
        "2 - Amarelo": "#f2c94c",
        "3 - Laranja": "#f2994a",
        "4 - Vermelho": "#d62728",
    },
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
    st.caption("O Rt mede a tendência de transmissão da dengue, indicando quantos novos casos, em média, cada caso infectado pode gerar na população.")
    df_rt = carregar_dataframe_endpoint("/graficos/rt")
    fig_rt = px.line(
        df_rt,
        x="data_ini_SE",
        y="Rt",
        markers=True,
        labels={"data_ini_SE": "Semana", "Rt": "Rt"},
    )
    fig_rt.add_hline(y=1, line_dash="dash", annotation_text="Rt = 1")
    fig_rt.update_layout(height=380)
    st.plotly_chart(fig_rt, width="stretch")

with col_prt:
    st.subheader("Probabilidade de transmissão em crescimento")
    st.caption(
        "Este gráfico mostra a probabilidade de o Rt estar acima de 1, "
        "ou seja, o grau de confiança de que a transmissão está crescendo (p_rt1)."
    )
    df_prt = carregar_dataframe_endpoint("/graficos/probabilidade-rt")
    fig_prt = px.line(
        df_prt,
        x="data_ini_SE",
        y="p_rt1",
        markers=True,
        labels={"data_ini_SE": "Semana", "p_rt1": "Probabilidade de Rt > 1"},
    )
    fig_prt.add_hline(y=0.95, line_dash="dash", annotation_text="Critério 0,95")
    fig_prt.update_layout(height=380)
    st.plotly_chart(fig_prt, width="stretch")


# =========================
# Gráfico 5: clima e transmissão
# =========================
st.subheader("Clima, receptividade e transmissão")

col_clima, col_umidade = st.columns(2)

with col_clima:
    df_temperatura = carregar_dataframe_endpoint("/graficos/temperatura")
    fig_temp = px.line(
        df_temperatura,
        x="data_ini_SE",
        y="Temperatura",
        color="Indicador",
        markers=True,
        title="Evolução semanal da temperatura",
        labels={"data_ini_SE": "Semana", "Temperatura": "Temperatura semanal", "Indicador": "Indicador"},
    )
    fig_temp.update_layout(height=380)
    st.plotly_chart(fig_temp, width="stretch")

with col_umidade:
    df_umidade = carregar_dataframe_endpoint("/graficos/umidade")
    fig_umidade = px.line(
        df_umidade,
        x="data_ini_SE",
        y="Umidade",
        color="Indicador",
        markers=True,
        title="Evolução semanal da Umidade",
        labels={"data_ini_SE": "Semana", "Umidade": "Umidade semanal", "Indicador": "Indicador"},
    )
    fig_umidade.update_layout(height=380)
    st.plotly_chart(fig_umidade, width="stretch")


st.subheader("Evolução semanal dos casos, clima e Rt")
st.caption(
    "As barras mostram os casos notificados no ano analisado, enquanto as linhas "
    "apresentam a temperatura média, a umidade média e o Rt por semana."
)

fig_clima_rt = go.Figure()
df_clima_rt = carregar_dataframe_endpoint("/graficos/clima-rt")

fig_clima_rt.add_trace(
    go.Bar(
        x=df_clima_rt["data_ini_SE"],
        y=df_clima_rt["casos"],
        name="Casos notificados",
        marker_color="rgba(125, 190, 240, 0.34)",
        hovertemplate="Semana: %{x|%d/%m/%Y}<br>Casos: %{y}<extra></extra>",
        yaxis="y",
    )
)

fig_clima_rt.add_trace(
    go.Scatter(
        x=df_clima_rt["data_ini_SE"],
        y=df_clima_rt["tempmed"],
        name="Temperatura média",
        mode="lines+markers",
        line=dict(color="#f2994a", width=2),
        marker=dict(size=6),
        hovertemplate="Semana: %{x|%d/%m/%Y}<br>Temperatura média: %{y:.2f} °C<extra></extra>",
        yaxis="y2",
    )
)

fig_clima_rt.add_trace(
    go.Scatter(
        x=df_clima_rt["data_ini_SE"],
        y=df_clima_rt["umidmed"],
        name="Umidade média",
        mode="lines+markers",
        line=dict(color="#27ae60", width=2),
        marker=dict(size=6),
        hovertemplate="Semana: %{x|%d/%m/%Y}<br>Umidade média: %{y:.2f}%<extra></extra>",
        yaxis="y2",
    )
)

fig_clima_rt.add_trace(
    go.Scatter(
        x=df_clima_rt["data_ini_SE"],
        y=df_clima_rt["Rt"],
        name="Rt",
        mode="lines+markers",
        line=dict(color="#eb5757", width=2),
        marker=dict(size=6),
        hovertemplate="Semana: %{x|%d/%m/%Y}<br>Rt: %{y:.2f}<extra></extra>",
        yaxis="y3",
    )
)

fig_clima_rt.add_shape(
    type="line",
    xref="paper",
    x0=0,
    x1=0.86,
    yref="y3",
    y0=1,
    y1=1,
    line=dict(color="#eb5757", dash="dash", width=1),
)

fig_clima_rt.update_layout(
    height=470,
    hovermode="x unified",
    legend_title="Indicador",
    xaxis=dict(
        domain=[0, 0.86],
        title="Semana epidemiológica",
    ),
    yaxis=dict(
        title="Casos notificados",
        rangemode="tozero",
    ),
    yaxis2=dict(
        title="Temperatura (°C) / Umidade (%)",
        anchor="x",
        overlaying="y",
        side="right",
        showgrid=False,
    ),
    yaxis3=dict(
        title="Rt",
        anchor="free",
        overlaying="y",
        side="right",
        position=0.98,
        rangemode="tozero",
        showgrid=False,
    ),
    barmode="overlay",
)

st.plotly_chart(fig_clima_rt, width="stretch")


# =========================
# Destaques automáticos
# =========================
st.subheader("Leitura automática dos principais achados")

destaques = chamar_api("GET", "/destaques")
casos_mes_top = destaques["casos_mes_top"]
semana_pico_destaque = destaques["semana_pico"]

st.info(
    f"""
    **{municipio}** registrou **{formatar_numero(destaques['total_casos'])} casos** no período filtrado.  
    O mês com mais casos foi **{casos_mes_top['mes']}**, com **{formatar_numero(casos_mes_top['casos'])} casos**.  
    A semana de pico começou em **{pd.to_datetime(semana_pico_destaque['data_ini_SE']).strftime('%d/%m/%Y')}**, com **{formatar_numero(semana_pico_destaque['casos'])} casos**.  
    As semanas em alerta vermelho concentraram **{formatar_numero(destaques['casos_vermelho'])} casos**, equivalente a **{formatar_numero(destaques['perc_vermelho'], 1)}%** dos casos filtrados.
    """
)


# =========================
# Tabela e download
# =========================
st.subheader("Base analítica")

payload_tabela = chamar_api("GET", "/tabela")
df_tabela = registros_para_dataframe(payload_tabela.get("dados", []))

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
st.dataframe(
    df_tabela,
    width="stretch",
    hide_index=True,
)

