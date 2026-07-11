# -*- coding: utf-8 -*-
"""
Página de OBSERVAÇÃO (observabilidade da ingestão) — GeoPulse.

Responde: "o robô está saudável?". Lê o estado SQLite
(datalake/control/ingestion.db) via ingestor.state.StateStore.
Cobre as métricas do contrato (Seção 6.3): ciclos, descobertos/ingeridos/
pulados/falhas, erros e evolução ao longo do período.
"""
import sys
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]        # youtube_ingestor/
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "app"))             # p/ importar _ui
from ingestor.state import StateStore             # noqa: E402
import _ui                                        # noqa: E402

st.set_page_config(page_title="GeoPulse · Observação", layout="wide")
_ui.injetar_css()

DB = ROOT / "datalake" / "control" / "ingestion.db"

_ui.hero("Observação da Ingestão",
         "Saúde do pipeline perene · a resposta de engenharia: o robô está rodando, "
         "descobrindo e processando vídeos sem intervenção?")

# ── Guarda: sem banco ainda ────────────────────────────────────────────────
if not DB.exists():
    st.warning(
        "Nenhum estado de ingestão encontrado.\n\n"
        "Rode um ciclo primeiro, na pasta do projeto:\n\n"
        "```\npython scheduler.py --once\n```")
    st.stop()

store = StateStore(str(DB))
resumo = store.resumo()
runs = store.runs()
wms = store.watermarks()
por_dia = store.ingestoes_por_dia()
falhas = store.falhas()
ult = store.ultima_execucao()


def _tot(chave):
    return sum(r.get(chave, 0) for r in runs)


def _idade_min(iso):
    return int((datetime.now(timezone.utc) - datetime.fromisoformat(iso)).total_seconds() // 60)


# ── Saúde (idade do último ciclo) ──────────────────────────────────────────
st.write("")
if ult:
    mins = _idade_min(ult)
    rot = f"{mins} min" if mins < 60 else (f"{mins//60} h" if mins < 1440 else f"{mins//1440} dia(s)")
    if mins <= 60:
        _ui.pill(f"Pipeline ativo — último ciclo há {rot}", _ui.GREEN)
    elif mins <= 24 * 60:
        _ui.pill(f"Último ciclo há {rot} — verifique o agendamento", _ui.AMBER)
    else:
        _ui.pill(f"Sem ciclos há {rot} — pipeline pode estar parado", _ui.RED)

# ── KPIs (somados sobre a história de ciclos = atividade acumulada) ─────────
_ui.kpis([
    {"val": len(runs),           "lab": "Ciclos executados",       "cor": _ui.SLATE},
    {"val": _tot("descobertos"), "lab": "Vídeos descobertos",      "cor": _ui.BLUE},
    {"val": _tot("ingeridos"),   "lab": "Ingeridos",               "cor": _ui.GREEN},
    {"val": _tot("pulados"),     "lab": "Pulados (idempotência)",  "cor": _ui.WINE},
    {"val": _tot("falhas"),      "lab": "Falhas",                  "cor": _ui.RED},
])
st.caption(f"Status atual dos vídeos únicos no lakehouse: **{resumo}**")

# ── Evolução + watermark ────────────────────────────────────────────────────
colA, colB = st.columns([3, 2], gap="large")
with colA:
    _ui.secao("Ingestões por dia",
              "Quantos vídeos entraram no lakehouse a cada dia — a evolução do "
              "pipeline ao longo do período de observação.")
    if por_dia:
        dfd = pd.DataFrame(por_dia)
        fig = px.bar(dfd, x="dia", y="ingeridos", text="ingeridos",
                     color_discrete_sequence=[_ui.WINE])
        fig.update_traces(textposition="outside", cliponaxis=False,
                          marker_line_width=0)
        fig.update_layout(xaxis_title=None, yaxis_title="vídeos")
        st.plotly_chart(_ui.estilo_plotly(fig, altura=300), use_container_width=True)
    else:
        st.info("Ainda sem vídeos ingeridos.")

with colB:
    _ui.secao("Watermark por canal",
              "Até onde cada canal já foi processado — a base da "
              "incrementalidade (só entra vídeo novo).")
    if wms:
        dfw = pd.DataFrame(wms)[["channel_id", "last_published_at",
                                 "last_run_at", "videos_total"]]
        dfw.columns = ["Canal (ID)", "Último publishedAt", "Último ciclo", "Vídeos"]
        st.dataframe(dfw, use_container_width=True, hide_index=True)
    else:
        st.info("Sem watermark registrado.")

# ── Histórico de ciclos ──────────────────────────────────────────────────────
_ui.secao("Histórico de ciclos",
          "Cada linha é uma execução do agendador — a prova de que roda sozinho.")
if runs:
    dfr = pd.DataFrame(runs)[["run_at", "canal", "descobertos", "ingeridos",
                              "pulados", "falhas"]]
    dfr.columns = ["Quando (UTC)", "Canal", "Descobertos", "Ingeridos",
                   "Pulados", "Falhas"]
    st.dataframe(dfr, use_container_width=True, hide_index=True, height=240)
else:
    st.info("Nenhum ciclo registrado ainda.")

# ── Falhas ───────────────────────────────────────────────────────────────────
_ui.secao("Falhas de ingestão",
          "Vídeos que não puderam ser processados (ex: legenda desativada) — "
          "registrados, não escondidos.")
if falhas:
    dff = pd.DataFrame(falhas)[["video_id", "channel_id", "dominio",
                                "error", "attempts"]]
    dff.columns = ["Vídeo", "Canal", "Domínio", "Erro", "Tentativas"]
    st.dataframe(dff, use_container_width=True, hide_index=True)
else:
    st.success("Nenhuma falha registrada.")

# ── Como interpretar (storytelling p/ o público de negócio) ─────────────────
with st.expander("Como interpretar este painel"):
    st.markdown(
        "- **Ciclos executados** provam que o agendador dispara sozinho, no "
        "intervalo configurado.\n"
        "- **Descobertos vs. Ingeridos** mostra quanto do que apareceu virou dado "
        "útil; a diferença são falhas ou pulados.\n"
        "- **Pulados (idempotência)** é saudável: significa que o robô reconheceu "
        "vídeos já processados e **não duplicou** trabalho.\n"
        "- **Falhas** não precisam ser zero — precisam ser **explicadas** (a maioria "
        "é legenda desativada no vídeo).")
