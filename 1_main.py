import streamlit as stl
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

stl.markdown("""
<style>
.small-divider {
    border-top: 1px solid rgba(250, 250, 250, 0.1);
    margin-top: 5px !important;
    margin-bottom: 10px !important;
}
.cache-info {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 14px;
    background: rgba(250, 250, 250, 0.04);
    border: 1px solid rgba(250, 250, 250, 0.08);
    border-radius: 8px;
    font-size: 0.85em;
    color: #9ca3af;
}
.cache-info .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #22c55e;
    flex-shrink: 0;
}
.cache-info .label {
    color: #6b7280;
    font-weight: 600;
    letter-spacing: 0.02em;
    text-transform: uppercase;
    font-size: 0.78em;
}
.cache-info .value {
    color: #9d9d9d;
    font-variant-numeric: tabular-nums;
}
.cache-info .age {
    margin-left: auto;
    color: #6b7280;
    font-size: 0.85em;
}
</style>
""", unsafe_allow_html=True)

API_URL = "https://conectortotvs.apprbs.com.br/api/log-center/list-log"
JSON_DATA_KEY = "data"


def _clean_logs_df(df):
    for col in ['created_at', 'updated_at']:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], format='%d/%m/%Y às %H:%M:%S', errors='coerce')

    for col in ["client", "candidate", "portal", "description", "category",
                "process_selective", "stage", "step", "situation", "component"]:
        if col in df.columns:
            df[col] = df[col].fillna('N/A')
    return df


@stl.cache_data(ttl=3600, show_spinner="Carregando logs dos últimos 4 dias...")
def fetch_logs():
    api_key = stl.secrets['api_key']
    headers = {"x-api-key": api_key}
    payload = {
        "page": 1,
        "perPage": 20000,
        "filter": {}
    }
    response = requests.post(API_URL, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    records = response.json().get(JSON_DATA_KEY, [])
    df = pd.DataFrame.from_records(records)
    sp_time = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-3)))
    return _clean_logs_df(df), sp_time.replace(tzinfo=None)


stl.set_page_config(
    page_title="Logs",
    layout="wide"
)

df_original, cached_at = fetch_logs()

if df_original is None or df_original.empty:
    stl.warning("Nenhum dado retornado pela API de logs.")
    stl.stop()


df = df_original.copy()
stl.sidebar.title("Filtros")

# Filtro de clientes
clients = ["Todos"] + sorted(df['client'].dropna().unique().tolist())
selected_clients = stl.sidebar.multiselect(
    label="Cliente",
    options=clients,
    default=["Todos"]
)

invert_filter = stl.sidebar.checkbox(
    label="Inverter filtro",
    key="invert_client_filter",
    value=False
)
stl.sidebar.markdown('<hr class="small-divider">', unsafe_allow_html=True)
if "Todos" not in selected_clients:
    if invert_filter:
        df = df[~df['client'].isin(selected_clients)]
    else:
        df = df[df['client'].isin(selected_clients)]

description = ["Todos"] + sorted(df['description'].dropna().astype(str).unique().tolist())
selected_description = stl.sidebar.multiselect(
    label="Descrição",
    options=description,
    default=["Todos"]
)
invert_filter_description = stl.sidebar.checkbox(
    label="Inverter filtro",
    key="invert_description_filter",
    value=False
)
stl.sidebar.markdown('<hr class="small-divider">', unsafe_allow_html=True)
if "Todos" not in selected_description:
    if invert_filter_description:
        df = df[~df['description'].isin(selected_description)]
    else:
        df = df[df['description'].isin(selected_description)]

# Filtro de categoria
categories = ["Todos"] + sorted(df['category'].dropna().unique().tolist())
selected_categories = stl.sidebar.multiselect(
    label="Categoria",
    options=categories,
    default=["Todos"]
)
invert_filter_description = stl.sidebar.checkbox(
    label="Inverter filtro",
    key="invert_category_filter",
    value=False
)
stl.sidebar.markdown('<hr class="small-divider">', unsafe_allow_html=True)
if "Todos" not in selected_categories:
    if invert_filter_description:
        df = df[~df['category'].isin(selected_categories)]
    else:
        df = df[df['category'].isin(selected_categories)]

# Filtro de situações
situations = ["Todos"] + sorted(df['situation'].dropna().unique().tolist())
selected_situations = stl.sidebar.multiselect(
    label="Situação",
    options=situations,
    default=["Todos"]
)

if "Todos" not in selected_situations:
    df = df[df['situation'].isin(selected_situations)]

# Filtros de datas
min_date = df['created_at'].min().date()
max_date = df['created_at'].max().date()
default_start_date = min_date
date_range = stl.sidebar.date_input(
    label="Periodo",
    value=(default_start_date, max_date),
    max_value=max_date,
    min_value=min_date
)

stl.sidebar.info("Dica: O carregamento inicial pode demorar, mas os filtros serão rápidos devido ao cache.")
stl.sidebar.markdown("Desenvolvido por [João Vitor](https://github.com/JoaoVitorMirandaBandeira)")

# Filtrar o data frame
df_filtered = df.copy()
if len(date_range) == 2:
    start_date, end_date = date_range
    start_datetime = pd.to_datetime(start_date)
    end_datetime = pd.to_datetime(end_date) + timedelta(days=1)
    df_filtered = df_filtered[
        (df_filtered['created_at'] >= start_datetime) & (df_filtered['created_at'] < end_datetime)
    ]
else:
    stl.stop()

if df_filtered.empty:
    stl.warning("Nenhum dado encontrado para os filtros selecionados.")
    stl.stop()

# Indicadores

stl.title("Dashboard de Monitoramento de Logs de Erro")

cache_age_delta = datetime.now() - cached_at
cache_age_mins = int(cache_age_delta.total_seconds() // 60)
if cache_age_mins < 1:
    cache_age_str = "agora mesmo"
elif cache_age_mins < 60:
    cache_age_str = f"há {cache_age_mins} min"
else:
    cache_age_h = cache_age_mins // 60
    cache_age_m = cache_age_mins % 60
    cache_age_str = f"há {cache_age_h}h{cache_age_m:02d}min"

col_btn, col_cache = stl.columns([1, 2.5])
with col_btn:
    if stl.button("🔄 Recarregar logs", help="Limpa o cache e busca novos dados da API", use_container_width=True):
        stl.cache_data.clear()
        stl.rerun()
col_cache.markdown(
    f"""
    <div class="cache-info">
        <span class="dot"></span>
        <span class="label">Cache</span>
        <span class="value">{cached_at.strftime('%d/%m/%Y %H:%M:%S')}</span>
        <span class="age">({cache_age_str})</span>
    </div>
    """,
    unsafe_allow_html=True
)

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
    erros_over_time = df_filtered.set_index('created_at').resample('h').size().reset_index(name='count')
    fig_time = px.line(erros_over_time, x='created_at', y='count', title="Tendência de Erros Diários", markers=True)
    fig_time.update_layout(xaxis_title="Data", yaxis_title="Número de Erros")
    stl.plotly_chart(fig_time, use_container_width=True)

    # Erros por Componente
    stl.subheader("Top components com erros")
    df_plot = df_filtered[df_filtered['component'] != "N/A"]
    df_plot_new = df_plot
    df_plot_new['component'] = df_plot_new['component'] + " (" + df_plot_new['client'] + ")"
    erros_by_component = df_plot_new['component'].value_counts().nlargest(10).reset_index()
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