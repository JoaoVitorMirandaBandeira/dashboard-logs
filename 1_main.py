import streamlit as stl
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta


@stl.cache_data
def load_document(path_document):
    df = pd.read_csv(path_document, sep=',')
    date_cols = ['created_at', 'updated_at']
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
    for col in ["client","candidate","portal","description","category","process_selective","stage","step","situation","component"]:
        if col in df.columns:
            df[col] = df[col].fillna('N/A')

    return df
stl.set_page_config(
    page_title="Logs",
    layout="wide"
)
# path_document = stl.sidebar.file_uploader(label="Carregue seu arquivo CSV de logs", type=["csv"])
path_document = "./logsv2.csv"
if path_document is None:
    stl.info("Por favor, carregue um arquivo CSV para começar.")
    stl.stop()

df_original = load_document(path_document)

if df_original is None:
    stl.stop()

stl.sidebar.title("Filtros")

# Filtro de clientes
clients = ["Todos"] + sorted(df_original['client'].unique())
selected_clients = stl.sidebar.multiselect(
    label="Cliente",
    options=clients,
    default=["Todos"]
)
# Filtros de datas
min_date = df_original['created_at'].min().date()
max_date = df_original['created_at'].max().date()
default_start_date = max_date - timedelta(days=7)
date_range = stl.sidebar.date_input(
    label="Periodo",
    value=(default_start_date, max_date),
    max_value=max_date,
    min_value=min_date
)
# Filtro de categoria
categories = ["Todos"] + sorted(df_original['category'].unique())
selected_categories = stl.sidebar.multiselect(
    label="Categoria",
    options=categories,
    default=["Todos"]
)
# Filtro de situações
situations = ["Todos"] + sorted(df_original['situation'].unique())
selected_situations = stl.sidebar.multiselect(
    label="Situação",
    options=situations,
    default=["Todos"]
)

stl.sidebar.info("Dica: O carregamento inicial pode demorar, mas os filtros serão rápidos devido ao cache.")
stl.sidebar.markdown("Desenvolvido por [João Vitor](https://github.com/JoaoVitorMirandaBandeira)")

# Filtrar o data frame
df_filtered = df_original.copy()
if len(date_range) == 2:
    start_date, end_date = date_range
    start_datetime = pd.to_datetime(start_date)
    end_datetime = pd.to_datetime(end_date) + timedelta(days=1)
    df_filtered = df_filtered[
        (df_filtered['created_at'] >= start_datetime) & (df_filtered['created_at'] < end_datetime)
    ]
else:
    stl.stop()
if "Todos" not in selected_clients:
    df_filtered = df_filtered[df_filtered['client'].isin(selected_clients)]
if "Todos" not in selected_categories:
    df_filtered = df_filtered[df_filtered['category'].isin(selected_categories)]
if "Todos" not in selected_situations:
    df_filtered = df_filtered[df_filtered['situation'].isin(selected_situations)]
if df_filtered.empty:
    stl.warning("Nenhum dado encontrado para os filtros selecionados.")
    stl.stop()

# Indicadores

stl.title("Dashboard de Monitoramento de Logs de Erro")
stl.markdown("### Indicadores")

count_total = df_filtered.shape[0]
count_client = df_filtered['client'].nunique()
count_category = df_filtered['category'].nunique()
count_situation = df_filtered['situation'].nunique()
count_candidate = df_filtered[df_filtered['candidate'] != "N/A"]['candidate'].nunique()
erros_today = df_filtered[df_filtered['created_at'].dt.date == datetime.today().date()].shape[0]
col1, col2, col3, col4, col5 = stl.columns(5)
col1.metric(label="Total de logs", value=count_total)
col2.metric(label="Total de clientes", value=count_client)
col3.metric(label="Total de categorias", value=count_category)
col4.metric(label="Total de situações", value=count_situation)
col5.metric(label="Total de candidatos", value=count_candidate)



stl.header("Análise Visual dos Erros")
col_a, col_b = stl.columns(2)

with col_a:
    # Erros ao longo do tempo 
    stl.subheader("Erros ao longo do tempo")
    erros_over_time = df_filtered.set_index('created_at').resample('D').size().reset_index(name='count')
    fig_time = px.line(erros_over_time, x='created_at', y='count', title="Tendência de Erros Diários", markers=True)
    fig_time.update_layout(xaxis_title="Data", yaxis_title="Número de Erros")
    stl.plotly_chart(fig_time, use_container_width=True)

    # Erros por Componente
    stl.subheader("Top components com erros")
    df_plot = df_filtered[df_filtered['component'] != "N/A"]
    erros_by_component = df_plot['component'].value_counts().nlargest(10).reset_index()
    erros_by_component.columns = ['component', 'count']  # Renomear colunas
    erros_by_component = erros_by_component.sort_values(by='count', ascending=False)
    px_fig = px.bar(erros_by_component, x='count', y='component', orientation='h',height=500)
    stl.plotly_chart(px_fig, use_container_width=True)
    #stl.bar_chart(erros_by_component, x='component', y='count',x_label="Contagem", y_label="Componente", stack="layered", horizontal=True, height=500)

    # Erros por descricao
    stl.subheader("Top 15 erros por descrição")
    erros_by_description = df_filtered[df_filtered['description'] != 'N/A']['description'].value_counts().nlargest(15).reset_index()
    erros_by_description.columns = ['description', 'count']  # Renomear colunas
    erros_by_description = erros_by_description.sort_values(by='count', ascending=False)
    px_fig = px.pie(erros_by_description, values='count', names='description')
    stl.plotly_chart(px_fig, use_container_width=True)

with col_b:
    stl.subheader("Erros por Categoria)")
    errors_by_category = df_filtered['category'].value_counts().reset_index()
    errors_by_category.columns = ['category', 'count']

    # Gráfico de Pizza (opcional, pode comentar se preferir só a lista/botões)
    fig_category = px.pie(errors_by_category, values='count', names='category')
    stl.plotly_chart(fig_category, use_container_width=True)

    # Top Cliente com erro 
    stl.subheader("Top 10 Clientes com Erros")
    erros_by_client = df_filtered['client'].value_counts().nlargest(10).reset_index()
    erros_by_client.columns = ['client', 'count']  # Renomear colunas
    erros_by_client = erros_by_client.sort_values(by='count', ascending=True)
    px_fig = px.bar(erros_by_client, x='count', y='client', orientation='h',height=500)
    stl.plotly_chart(px_fig, use_container_width=True)
    #stl.bar_chart(erros_by_client, x='client', y='count',x_label="Contagem", y_label="Cliente", stack="layered", horizontal=True, height=500)

    # Top 20 candidatos que sofreram com erros
    df_filtered = df_filtered[df_filtered['candidate'] != "N/A"]
    errors_by_cand_client = df_filtered.groupby(['candidate', 'client']).size().reset_index(name='count')
    erros_by_candidate = errors_by_cand_client['candidate'].value_counts().nlargest(20).reset_index()
    errors_by_cand_client['diplay'] = errors_by_cand_client['candidate'] + " (" + errors_by_cand_client['client'] + ")"
    errors_by_cand_client = errors_by_cand_client.sort_values(by='count', ascending=False)
    errors_by_cand_client = errors_by_cand_client.head(20).sort_values(by='count', ascending=True)
    px_fig = px.bar(errors_by_cand_client, x='count', y='diplay', orientation='h', height=500)
    stl.plotly_chart(px_fig, use_container_width=True)


stl.header("Detalhes dos Logs de Erro (Visão Geral)")
stl.dataframe(df_filtered.sort_values(by='created_at', ascending=False))