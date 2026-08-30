# -*- coding: utf-8 -*-
# app/streamlit_app.py — Dashboard ANALÍTICO (página principal do GeoPulse).
# Lógica de dados preservada; apresentação unificada pelo tema em app/_ui.py.
import os
import sys
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))   # p/ importar _ui
import _ui  # noqa: E402

st.set_page_config(page_title="GeoPulse · Analítico", layout="wide")
_ui.injetar_css()

# ==============================================================================
# LEITURA DA CAMADA GOLD
# ==============================================================================
PATH_GOLD_INDIVIDUAL = "./datalake/gold/clipping_geopolitica.parquet"
PATH_GOLD_CONEXOES = "./datalake/gold/coocorrencia_paises.parquet"


def carregar_dados_gold():
    """Lê os parquets analíticos da Gold; cai em dados de exemplo se não existirem."""
    if not os.path.exists(PATH_GOLD_INDIVIDUAL) or not os.path.exists(PATH_GOLD_CONEXOES):
        gold_mock = pd.DataFrame({
            "pais": ["ira", "israel", "brasil", "ucrania", "russia", "estados unidos",
                     "libano", "franca", "china", "palestina", "reino unido", "india"],
            "mencoes": [15, 13, 23, 29, 26, 17, 8, 5, 4, 2, 2, 2],
        })
        gold_conexoes_mock = pd.DataFrame({
            "pais_a": ["estados unidos", "brasil", "ira", "franca", "brasil",
                       "russia", "china", "ira", "franca", "reino unido",
                       "ira", "israel", "china"],
            "pais_b": ["ira", "russia", "ucrania", "russia", "ira",
                       "ucrania", "franca", "russia", "reino unido", "russia",
                       "israel", "libano", "russia"],
            "mencoes_juntos": [4, 3, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1],
        })
        return gold_mock, gold_conexoes_mock, True

    gold = pd.read_parquet(PATH_GOLD_INDIVIDUAL)
    gold_conexoes = pd.read_parquet(PATH_GOLD_CONEXOES)
    return gold, gold_conexoes, False


gold_data, gold_conexoes_data, modo_demo = carregar_dados_gold()

if not modo_demo:
    data_atualizacao = datetime.fromtimestamp(
        os.path.getmtime(PATH_GOLD_INDIVIDUAL)).strftime("%d/%m/%Y %H:%M")
else:
    data_atualizacao = datetime.now().strftime("%d/%m/%Y %H:%M")

# ==============================================================================
# CABEÇALHO + KPIs
# ==============================================================================
_ui.hero("Análise de Conflitos Geopolíticos",
         "O que a cobertura de notícias está dizendo: quais países dominam a pauta "
         "e quais aparecem associados entre si.")

status_txt = "Operacional" if not modo_demo else "Ambiente demo"
_ui.kpis([
    {"val": data_atualizacao,      "lab": "Última ingestão",     "cor": _ui.SLATE},
    {"val": status_txt,            "lab": "Status do pipeline",  "cor": _ui.GREEN if not modo_demo else _ui.AMBER},
    {"val": "Oriente Médio",       "lab": "Foco narrativo",      "cor": _ui.WINE},
    {"val": "Bronze→Silver→Gold",  "lab": "Camadas ativas",      "cor": _ui.BLUE},
])

# ── Sidebar (ficha técnica) ─────────────────────────────────────────────────
with st.sidebar:
    st.header("Ficha Técnica")
    if st.button("Atualizar dados", use_container_width=True):
        st.rerun()
    st.markdown("---")
    st.markdown("**Domínio:** Geopolítica & Notícias")
    st.markdown("**Público-alvo:** Diretores e Analistas de Risco Corporativo")
    st.markdown(
        "**Problema:** o monitoramento manual de canais jornalísticos consome "
        "tempo de equipes estratégicas.\n\n"
        "**Propósito:** automatizar a captura de pautas globais pela mineração "
        "de transcrições de mídia.")
    st.markdown("---")
    st.success("**KPI principal:** volume de citações por país.")

# ==============================================================================
# DICIONÁRIOS DE MAPEAMENTO (preservados)
# ==============================================================================
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

# ==============================================================================
# PREPARO DOS DADOS (preservado)
# ==============================================================================
df_individual = gold_data.copy()
metrica_col = "mencoes"
sufixo_label = "vezes"

df_individual["pais_ingles"] = df_individual["pais"].map(mapa_nomes)
df_individual["pais_pt"] = df_individual["pais"].map(nomes_exibicao)
df_individual["pais_pt"] = df_individual["pais_pt"].fillna(df_individual["pais"].str.capitalize())
df_individual["bloco"] = df_individual["pais"].map(blocos_geopoliticos).fillna("Outros / Global")

df_blocos = df_individual.groupby("bloco", as_index=False)[metrica_col].sum()

df_individual = df_individual.dropna(subset=["pais_ingles"])
df_individual = df_individual.groupby(["pais_ingles", "pais_pt"], as_index=False)[metrica_col].sum()
df_individual = df_individual.sort_values(by=metrica_col, ascending=True)

df_tabela = gold_conexoes_data.copy()
df_tabela["País A"] = df_tabela["pais_a"].map(nomes_exibicao).fillna(df_tabela["pais_a"].str.capitalize())
df_tabela["País B"] = df_tabela["pais_b"].map(nomes_exibicao).fillna(df_tabela["pais_b"].str.capitalize())
if "mencoes_juntos" in df_tabela.columns:
    df_tabela = df_tabela.rename(columns={"mencoes_juntos": "Menções Juntos"})
elif "Ocorrências" in df_tabela.columns:
    df_tabela = df_tabela.rename(columns={"Ocorrências": "Menções Juntos"})
df_tabela = df_tabela[["País A", "País B", "Menções Juntos"]].head(20)

# ==============================================================================
# GRADE DE GRÁFICOS (paleta vinho unificada)
# ==============================================================================
_ui.secao("Panorama geopolítico",
          "Mapa, ranking, blocos e co-ocorrências — o retrato de quem domina a "
          "narrativa no período.")

fig = make_subplots(
    rows=2, cols=2,
    row_heights=[0.55, 0.45], column_widths=[0.52, 0.48],
    specs=[[{"type": "geo"}, {"type": "xy"}],
           [{"type": "domain"}, {"type": "table"}]],
    horizontal_spacing=0.05, vertical_spacing=0.12,
    subplot_titles=("<b>Distribuição Geográfica</b>",
                    f"<b>Relevância por País ({sufixo_label.capitalize()})</b>",
                    "<b>Participação por Bloco Geopolítico</b>",
                    "<b>Países Mencionados Juntos</b>"))

fig.add_trace(go.Choropleth(
    locations=df_individual["pais_ingles"], locationmode="country names",
    z=df_individual[metrica_col], colorscale=_ui.ESCALA_VINHO, showscale=False, showlegend=False,
    hovertemplate=f"<b>%{{location}}</b><br>Menções: %{{z}} {sufixo_label}<extra></extra>"
), row=1, col=1)

fig.add_trace(go.Bar(
    x=df_individual[metrica_col], y=df_individual["pais_pt"], orientation='h',
    text=df_individual[metrica_col].apply(lambda x: f"{x}"), textposition='outside',
    showlegend=False, cliponaxis=False,
    marker=dict(color=df_individual[metrica_col], colorscale=_ui.ESCALA_VINHO),
    hovertemplate=f"<b>%{{y}}</b><br>Menções: %{{x}} {sufixo_label}<extra></extra>"
), row=1, col=2)

fig.add_trace(go.Pie(
    labels=df_blocos["bloco"], values=df_blocos[metrica_col], hole=0.45, showlegend=True,
    marker=dict(colors=_ui.PALETA_CAT, line=dict(color="#ffffff", width=1.5)),
    hovertemplate=f"<b>%{{label}}</b><br>Total: %{{value}} {sufixo_label}<br>%{{percent}}<extra></extra>"
), row=2, col=1)

fig.add_trace(go.Table(
    header=dict(values=[f"<b>{c}</b>" for c in df_tabela.columns],
                fill_color=_ui.WINE, align='center',
                font=dict(color='white', size=14, family="Inter, Arial")),
    cells=dict(values=[df_tabela["País A"], df_tabela["País B"], df_tabela["Menções Juntos"]],
               fill_color='#faf7f7', align='center',
               font=dict(color=_ui.INK, size=13, family="Inter, Arial"), height=34)
), row=2, col=2)

fig.update_layout(
    dragmode='pan',
    geo1=dict(showframe=False, showcoastlines=True, projection_type='equirectangular',
              landcolor="#eef0f3", bgcolor="rgba(0,0,0,0)",
              projection_scale=1, center=dict(lat=20, lon=0)),
    height=1080,
)
_ui.estilo_plotly(fig)
fig.update_annotations(font=dict(size=15, color=_ui.INK))
fig.update_xaxes(showgrid=True, gridcolor="#eef0f3", row=1, col=2, fixedrange=True)
fig.update_yaxes(row=1, col=2, fixedrange=True)

st.plotly_chart(fig, use_container_width=True,
                config={'scrollZoom': True,
                        'modeBarButtonsToAdd': ['zoomIn2d', 'zoomOut2d', 'resetGeo'],
                        'displayModeBar': True})

with st.expander("Como interpretar este painel"):
    st.markdown(
        "- **Mapa e ranking** mostram os países mais citados nas transcrições do período.\n"
        "- **Blocos geopolíticos** agregam os países (BRICS+, OTAN/Ocidente, Oriente "
        "Médio…) para ler o foco da cobertura de forma macro.\n"
        "- **Países mencionados juntos** revela associações — quem aparece no mesmo "
        "trecho que quem (sinal de tensão, aliança ou negociação).")
