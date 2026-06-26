"""
COVID DASHBOARD - STREAMLIT + SNOWFLAKE
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from snowflake.snowpark import Session
from datetime import datetime

# ============================================================================
# CONFIGURAÇÃO DA PÁGINA
# ============================================================================

st.set_page_config(
    page_title="COVID Analytics Dashboard",
    page_icon="🦠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CONFIGURAÇÃO DE CONEXÃO
# ============================================================================

connection_parameters = {
    "user": st.secrets["snowflake"]["user"],
    "password": st.secrets["snowflake"]["password"],
    "account": st.secrets["snowflake"]["account"],
    "warehouse": st.secrets["snowflake"]["warehouse"],
    "database": "TEST_DB",
    "schema": "PUBLIC",
    "role": st.secrets["snowflake"]["role"]
}

# ============================================================================
# DATASET
# ============================================================================

CSV_URL = "https://raw.githubusercontent.com/owid/covid-19-data/master/public/data/owid-covid-data.csv"

# ============================================================================
# SIDEBAR
# ============================================================================

st.sidebar.title("⚙️ Controle")

if st.sidebar.button("■ Carregar Dados no Snowflake"):

    with st.spinner("Baixando e preparando dados..."):

        # ----------------------------
        # 1. Carregar CSV
        # ----------------------------
        df = pd.read_csv(CSV_URL)

        # ----------------------------
        # 2. Filtragem (reduz volume)
        # ----------------------------
        paises = [
            "Brazil", "United States", "India",
            "France", "Vietnam", "China"
        ]

        df = df[df["location"].isin(paises)]
        df = df[df["date"] >= "2020-01-01"]

        # ----------------------------
        # 3. Limpeza básica
        # ----------------------------
        df = df.dropna(subset=["total_cases", "total_deaths"])

        # ----------------------------
        # 4. Conectar Snowflake (Snowpark)
        # ----------------------------
        session = Session.builder.configs(connection_parameters).create()

        # ----------------------------
        # 5. Upload para Snowflake
        # ----------------------------
        session.write_pandas(
        df,
            table_name="COVID_DATA",
            auto_create_table=True,
            overwrite=True
        )

        st.success(f"✅ Dados carregados com sucesso! {len(df)} linhas inseridas.")

if st.sidebar.button("■ Carregar Dashboard"):

    session = Session.builder.configs(connection_parameters).create()

    df = session.table("COVID_DATA").to_pandas()

    st.session_state["df"] = df

    st.success(" Dashboard carregado do Snowflake!")

# ============================================================================
# MAIN APP
# ============================================================================

st.title(" COVID Analytics Dashboard")
st.markdown("Análise global de dados COVID-19 com Snowflake + Streamlit")

# ============================================================================
# VERIFICAÇÃO DE DADOS
# ============================================================================

if "df" not in st.session_state:
    st.warning("Carregue os dados primeiro na sidebar.")
    st.stop()

df = st.session_state["df"]

# ============================================================================
# FILTROS
# ============================================================================

paises = st.multiselect(
    "Selecione os países",
    options=df["location"].unique(),
    default=list(df["location"].unique())
)

df = df[df["location"].isin(paises)]

# ============================================================================
# KPIs
# ============================================================================

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total de Casos", f"{df['total_cases'].max():,.0f}")

with col2:
    st.metric("Total de Óbitos", f"{df['total_deaths'].max():,.0f}")

with col3:
    st.metric("Países Analisados", df["location"].nunique())

st.markdown("---")

# ============================================================================
# TABS
# ============================================================================

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 Evolução",
    "⚰️ Óbitos",
    "💉 Vacinação",
    "🌍 População x Casos (Dispersao)",
    "📊 Dados Brutos"
])
# ============================================================================
# 1. EVOLUÇÃO DE CASOS
# ============================================================================

with tab1:

    st.subheader(" Evolução de Casos Novos")

    df_line = df.groupby(["date", "location"])["new_cases"].sum().reset_index()

    fig = px.line(
        df_line,
        x="date",
        y="new_cases",
        color="location",
        title="Casos novos ao longo do tempo"
    )

    st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# 2. ÓBITOS POR PAÍS
# ============================================================================

with tab2:

    st.subheader(" Total de Óbitos por País")

    df_deaths = df.groupby("location")["total_deaths"].max().reset_index()

    fig = px.bar(
        df_deaths,
        x="location",
        y="total_deaths",
        title="Total de mortes por país",
        color="total_deaths"
    )

    st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# 3. VACINAÇÃO
# ============================================================================

with tab3:

    st.subheader(" Vacinação (último registro)")

    df_latest = df.sort_values("date").groupby("location").tail(1)

    fig = px.pie(
        df_latest,
        names="location",
        values="people_fully_vaccinated",
        title="Proporção de vacinados (dose completa)"
    )

    st.plotly_chart(fig, use_container_width=True)

# ============================================================================
# 4. População x Casos
# ============================================================================

df_latest = (
    df.sort_values("date")
      .groupby("location")
      .tail(1)
)

with tab4:

    st.subheader("🌍 Relação entre População e Total de Casos")

    fig = px.scatter(
        df_latest,
        x="population",
        y="total_cases",
        color="location",
        size="total_deaths",
        hover_name="location",
        hover_data={
            "population": ":,.0f",
            "total_cases": ":,.0f",
            "total_deaths": ":,.0f"
        },
        labels={
            "population": "População",
            "total_cases": "Total de Casos",
            "total_deaths": "Total de Óbitos"
        },
        title="População x Total de Casos por País"
    )

    fig.update_layout(height=600)

    st.plotly_chart(fig, use_container_width=True)


# ============================================================================
# 5. DADOS BRUTOS
# ============================================================================

with tab5:

    st.subheader(" Dados Brutos")

    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label=" Baixar CSV",
        data=csv,
        file_name=f"covid_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )