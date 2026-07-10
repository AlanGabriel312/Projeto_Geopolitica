# app/streamlit_app.py
import os
from datetime import datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# ==============================================================================
# CONFIGURAÇÃO DE PÁGINA (ESTILO DASHBOARD EXECUTIVO)
# ==============================================================================
st.set_page_config(
    page_title="Dashboard Geopolítico",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==============================================================================
# LEITURA DE DADOS DA CAMADA GOLD (DATA LAKE CONTROLE)
# ==============================================================================
PATH_GOLD_INDIVIDUAL = "./datalake/gold/clipping_geopolitica.parquet"
PATH_GOLD_CONEXOES = "./datalake/gold/coocorrencia_paises.parquet"

@st.cache_data
def carregar_dados_gold():
    """Lê os parquets analíticos da Gold de forma segura e com cache de RAM."""
    if not os.path.exists(PATH_GOLD_INDIVIDUAL) or not os.path.exists(PATH_GOLD_CONEXOES):
        # Exemplo simulado COMPLETO com as 13 linhas originais do seu teste real
        gold_mock = pd.DataFrame({
            "pais": ["ira", "israel", "brasil", "ucrania", "russia", "estados unidos", "libano", "franca", "china", "palestina", "reino unido", "india"],
            "mencoes": [15, 13, 23, 29, 26, 17, 8, 5, 4, 2, 2, 2] 
        })

        # FIXADO: Adicionado todas as 13 linhas que você obteve da análise real
        gold_conexoes_mock = pd.DataFrame({
            "pais_a": [
                "estados unidos", "brasil", "ira", "franca", "brasil", 
                "russia", "china", "ira", "franca", "reino unido", 
                "ira", "israel", "china"
            ],
            "pais_b": [
                "ira", "russia", "ucrania", "russia", "ira", 
                "ucrania", "franca", "russia", "reino unido", "russia", 
                "israel", "libano", "russia"
            ],
            "mencoes_juntos": [4, 3, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1]
        })
        return gold_mock, gold_conexoes_mock, True
    
    # Carregamento oficial de produção (Lê do Data Lake gerado pelo bot)
    gold = pd.read_parquet(PATH_GOLD_INDIVIDUAL)
    gold_conexoes = pd.read_parquet(PATH_GOLD_CONEXOES)
    return gold, gold_conexoes, False


# === FIXADO: Agora as variáveis batem perfeitamente com os passos seguintes ===
gold_data, gold_conexoes_data, modo_demo = carregar_dados_gold()

# Define data de atualização dinâmica com base nas propriedades do arquivo no Linux
if not modo_demo:
    timestamp_mod = os.path.getmtime(PATH_GOLD_INDIVIDUAL)
    data_atualizacao = datetime.fromtimestamp(timestamp_mod).strftime("%d/%m/%Y %H:%M:%S")
else:
    data_atualizacao = datetime.now().strftime("%d/%m/%Y %H:%M:%S")


# ==============================================================================
# INTERFACE VISUAL PRINCIPAL (STREAMLIT LADO DO CLIENTE)
# ==============================================================================
st.title("Dashboard - Análise de Conflitos Geopolíticos")
st.caption("MBA Engenharia de Dados — Artefato Final de Programação para Engenharia de Dados")
st.markdown("---")

# Cards de KPIs e Metadados obrigatórios do contrato (Seção 5)
col_meta1, col_meta2, col_meta3, col_meta4 = st.columns(4)
with col_meta1:
    st.metric(label="⏰ Última Ingestão Realizada", value=data_atualizacao.split()[0], delta=data_atualizacao.split()[1])
with col_meta2:
    status_sistema = "🟢 OPERACIONAL (VPS)" if not modo_demo else "🟡 AMBIENTE DEMO"
    st.metric(label="🖥️ Status do Pipeline", value=status_sistema)
with col_meta3:
    st.metric(label="🚨 Foco Narrativo Dominante", value="Oriente Médio / Eixo")
with col_meta4:
    st.metric(label="🗂️ Camadas Ativas", value="Bronze ➔ Silver ➔ Gold")

# Barra lateral informativa e declarativa (Sidebar)
with st.sidebar:
    st.header("📋 Ficha Técnica")
    st.markdown("**Domínio:** Geopolítica & Notícias")
    st.markdown("**Público-alvo:** Diretores e Analistas de Risco Corporativo")
    st.markdown("""
    **Problema Resolvido:**  
    O monitoramento manual de canais jornalísticos consome tempo valioso de equipes estratégicas.
    
    **Propósito:**  
    Automatizar a captura de pautas globais através da mineração estruturada de transcrições de mídia.
    """)
    st.markdown("---")
    st.success("🎯 **Métrica Principal:** Volume de citações rastreadas por trechos de legenda.")

# ==============================================================================
# ADAPTAÇÃO DA SUA GRADE DE GRÁFICOS DO PLOTLY
# ==============================================================================

# Dicionários de mapeamento estruturados
mapa_nomes = {
    "brasil": "Brazil", "eua": "United States", "estados unidos": "United States",
    "canada": "Canada", "canadá": "Canada", "mexico": "Mexico", "méxico": "Mexico",
    "venezuela": "Venezuela", "argentina": "Argentina", "chile": "Chile", "cuba": "Cuba",
    "colombia": "Colombia", "colômbia": "Colombia",
    "russia": "Russia", "rússia": "Russia", "Rússia": "Russia",
    "ucrania": "Ukraine", "ucrânia": "Ukraine",
    "ira": "Iran", "irã": "Iran", "israel": "Israel", "china": "China",
    "siria": "Syria", "síria": "Syria", "libano": "Lebanon", "líbano": "Lebanon",
    "iemen": "Yemen", "iêmen": "Yemen", "palestina": "Palestine",
    "arabia saudita": "Saudi Arabia", "arábia saudita": "Saudi Arabia", "turquia": "Turkey",
    "taiwan": "Taiwan", "coreia": "North Korea", "coréia": "North Korea",
    "japao": "Japan", "japão": "Japan", "india": "India", "índia": "India",
    "pakistan": "Pakistan", "paquistão": "Pakistan", "afeganistao": "Afghanistan",
    "reino unido": "United Kingdom", "franca": "France", "frança": "France",
    "alemanha": "Germany", "italia": "Italy", "itália": "Italy", "espanha": "Spain",
    "portugal": "Portugal", "egito": "Egypt", "nigeria": "Nigeria", "áfrica do sul": "South Africa"
}

nomes_exibicao = {
    "russia": "Rússia", "ucrania": "Ucrânia", "ira": "Irã", "israel": "Israel",
    "china": "China", "venezuela": "Venezuela", "brasil": "Brasil",
    "estados unidos": "EUA", "libano": "Líbano", "franca": "França",
    "palestina": "Palestina", "reino unido": "Reino Unido", "india": "Índia"
}

blocos_geopoliticos = {
    "russia": "BRICS+", "rússia": "BRICS+", "Rússia": "BRICS+",
    "china": "BRICS+", "brasil": "BRICS+", "india": "BRICS+", "índia": "BRICS+",
    "eua": "OTAN / Ocidente", "estados unidos": "OTAN / Ocidente",
    "canada": "OTAN / Ocidente", "canadá": "OTAN / Ocidente",
    "reino unido": "OTAN / Ocidente", "franca": "OTAN / Ocidente", "frança": "OTAN / Ocidente",
    "alemanha": "OTAN / Ocidente", "italia": "OTAN / Ocidente", "itália": "OTAN / Ocidente",
    "espanha": "OTAN / Ocidente", "portugal": "OTAN / Ocidente",
    "ira": "Oriente Médio / Eixo", "irã": "Oriente Médio / Eixo",
    "israel": "Oriente Médio / Eixo", "palestina": "Oriente Médio / Eixo",
    "libano": "Oriente Médio / Eixo", "líbano": "Oriente Médio / Eixo",
    "siria": "Oriente Médio / Eixo", "síria": "Oriente Médio / Eixo",
    "iemen": "Oriente Médio / Eixo", "iêmen": "Oriente Médio / Eixo",
    "arabia saudita": "Oriente Médio / Eixo", "arábia saudita": "Oriente Médio / Eixo",
    "turquia": "Oriente Médio / Eixo",
    "ucrania": "Leste Europeu (Conflito)", "ucrânia": "Leste Europeu (Conflito)",
    "venezuela": "América Latina (Monitoramento)", "cuba": "América Latina (Monitoramento)"
}

df_individual = gold_data.copy()

# Força o uso da coluna 'mencoes' (quantidade de vezes citadas nos trechos)
metrica_col = "mencoes"
sufixo_label = "vezes"

df_individual["pais_ingles"] = df_individual["pais"].map(mapa_nomes)
df_individual["pais_pt"] = df_individual["pais"].map(nomes_exibicao)
df_individual["pais_pt"] = df_individual["pais_pt"].fillna(df_individual["pais"].str.capitalize())

df_individual["bloco"] = df_individual["pais"].map(blocos_geopoliticos).fillna("Outros / Global")

# Agrupa e soma as citações de termos duplicados (ex: 'russia' e 'rússia')
df_blocos = df_individual.groupby("bloco", as_index=False)[metrica_col].sum()

df_individual = df_individual.dropna(subset=["pais_ingles"])
df_individual = df_individual.groupby(["pais_ingles", "pais_pt"], as_index=False)[metrica_col].sum()
df_individual = df_individual.sort_values(by=metrica_col, ascending=True)

# Processamento da Tabela de Contexto Semântico
df_tabela = gold_conexoes_data.copy()

# Traduz e formata os nomes dos países para a exibição na tabela
df_tabela["País A"] = df_tabela["pais_a"].map(nomes_exibicao).fillna(df_tabela["pais_a"].str.capitalize())
df_tabela["País B"] = df_tabela["pais_b"].map(nomes_exibicao).fillna(df_tabela["pais_b"].str.capitalize())

# Garante que a coluna de contagem tenha o nome bonito para o cabeçalho
if "mencoes_juntos" in df_tabela.columns:
    df_tabela = df_tabela.rename(columns={"mencoes_juntos": "Menções Juntos"})
elif "Ocorrências" in df_tabela.columns:
    df_tabela = df_tabela.rename(columns={"Ocorrências": "Menções Juntos"})

# Seleciona apenas as colunas necessárias e limita às 12 principais para manter o tamanho ampliado
df_tabela = df_tabela[["País A", "País B", "Menções Juntos"]].head(20)

# Criação do make_subplots
fig = make_subplots(
    rows=2, cols=2,
    row_heights=[0.55, 0.45],     
    column_widths=[0.52, 0.48],   
    specs=[
        [{"type": "geo"}, {"type": "xy"}],                  
        [{"type": "domain"}, {"type": "table"}]             
    ],
    horizontal_spacing=0.05,       
    vertical_spacing=0.1,         
    subplot_titles=(
        "<b>Distribuição Geográfica</b>", 
        f"<b>Relevância por País ({sufixo_label.capitalize()})</b>", 
        "<b>Participação por Bloco Geopolítico</b>", 
        "<b>Países Mencionados Juntos</b>"
    )
)

# Adiciona Traces
fig.add_trace(go.Choropleth(
    locations=df_individual["pais_ingles"], locationmode="country names",
    z=df_individual[metrica_col], colorscale="YlOrRd", showscale=False, showlegend=False,
    hovertemplate=f"<b>%{{location}}</b><br>Menções: %{{z}} {sufixo_label}<extra></extra>"
), row=1, col=1)

fig.add_trace(go.Bar(
    x=df_individual[metrica_col], y=df_individual["pais_pt"], orientation='h',
    text=df_individual[metrica_col].apply(lambda x: f"{x} {sufixo_label}"), textposition='outside', showlegend=False,

    marker=dict(color=df_individual[metrica_col], colorscale="YlOrRd"),
    hovertemplate=f"<b>%{{y}}</b><br>Menções: %{{x}} {sufixo_label}<extra></extra>"
), row=1, col=2)

# Componente 3: Gráfico de Rosca por Bloco
fig.add_trace(go.Pie(
    labels=df_blocos["bloco"], 
    values=df_blocos[metrica_col], 
    hole=0.4, 
    showlegend=True,
    marker=dict(colors=px.colors.sequential.YlOrRd[::-1]),
    hovertemplate=f"<b>%{{label}}</b><br>Menções Total: %{{value}} {sufixo_label}<br>Percentual: %{{percent}}<extra></extra>"
), row=2, col=1)

# Componente 4: Tabela de Dados Estilizada
fig.add_trace(go.Table(
    header=dict(
        # Aplica a tag HTML <b> em cada título do cabeçalho de forma limpa e dinâmica
        values=[f"<b>{col}</b>" for col in df_tabela.columns], 
        fill_color='#9E1B1B',      # Cor vinho/escuro da paleta corporativa
        align='center',
        font=dict(color='white', size=14, family="Arial")
    ),
    cells=dict(
        # Passa as 3 colunas exatas da tabela de coocorrência de países
        values=[df_tabela["País A"], df_tabela["País B"], df_tabela["Menções Juntos"]], 
        fill_color='#f9f9f9', 
        align='center',
        font=dict(color='black', size=13, family="Arial"), 
        height=35                 # Mantém a altura esticada excelente para preencher espaço
    )
), row=2, col=2)

# Configurações Globais do Layout
fig.update_layout(
    dragmode='pan',
    geo1=dict(
        showframe=False, 
        showcoastlines=True, 
        projection_type='equirectangular', 
        landcolor="#f4f4f4", 
        projection_scale=1, 
        center=dict(lat=20, lon=0)
    ),
    margin={"r": 10, "t": 40, "l": 10, "b": 10},
    template="plotly_white",
    height=1100
)

# Ajustes de fontes e eixos cartesianos fixos
fig.update_annotations(font=dict(size=15))
fig.update_xaxes(showgrid=True, gridcolor="#eee", row=1, col=2, fixedrange=True)
fig.update_yaxes(row=1, col=2, fixedrange=True)

# === COMPONENTE DE RENDERIZAÇÃO RESPONSIVA DO STREAMLIT ===
st.plotly_chart(
    fig,
    use_container_width=True,
    config={
        'scrollZoom': True,
        'modeBarButtonsToAdd': ['zoomIn2d', 'zoomOut2d', 'resetGeo'],
        'displayModeBar': True
    }
)
