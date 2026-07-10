# -*- coding: utf-8 -*-
"""
Página de OBSERVAÇÃO (observabilidade da ingestão) — GeoPulse.

Responde "o robô está saudável?". Lê exclusivamente o estado SQLite
(datalake/control/ingestion.db) — a fonte da verdade do pipeline — via os
helpers de ingestor.state.StateStore.

Cobre as métricas do contrato (Seção 6.3): ciclos executados, vídeos
descobertos/ingeridos/pulados/falha, erros e evolução ao longo do período.
"""
import sys
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import plotly.express as px
import streamlit as st

# Raiz do projeto = youtube_ingestor/ (este arquivo está em app/pages/)
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from ingestor.state import StateStore   # noqa: E402

st.set_page_config(page_title="GeoPulse · Observação", page_icon="🛠️", layout="wide")

DB = ROOT / "datalake" / "control" / "ingestion.db"

st.title("🛠️ Observação da Ingestão")
st.caption("Saúde do pipeline perene · fonte: datalake/control/ingestion.db (SQLite)")

# ── Guarda: sem banco ainda ────────────────────────────────────────────────
if not DB.exists():
    st.warning(
        "🟡 Nenhum estado de ingestão encontrado.\n\n"
        "Rode um ciclo primeiro, na pasta do projeto:\n\n"
        "```\npython scheduler.py --once\n```"
    )
    st.stop()

store = StateStore(str(DB))
resumo = store.resumo()                 # {status: n}
runs = store.runs()                     # list[dict] ciclos
wms = store.watermarks()                # list[dict] por canal
por_dia = store.ingestoes_por_dia()     # [{dia, ingeridos}]
falhas = store.falhas()                 # list[dict]
ult = store.ultima_execucao()           # ISO ou None

# ── Indicador de saúde (idade do último ciclo) ─────────────────────────────
def _idade_min(iso: str) -> int:
    return int((datetime.now(timezone.utc) - datetime.fromisoformat(iso)).total_seconds() // 60)

if ult:
    mins = _idade_min(ult)
    rotulo = f"{mins} min" if mins < 60 else (f"{mins//60} h" if mins < 1440 else f"{mins//1440} dia(s)")
    if mins <= 60:
        st.success(f"🟢 Pipeline ativo — último ciclo há {rotulo}.")
    elif mins <= 24 * 60:
        st.warning(f"🟡 Último ciclo há {rotulo} — verifique o agendamento.")
    else:
        st.error(f"🔴 Sem ciclos há {rotulo} — pipeline pode estar parado.")

# ── KPIs (somados sobre a história de ciclos = atividade acumulada) ─────────
def _tot(chave: str) -> int:
    return sum(r.get(chave, 0) for r in runs)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("🔄 Ciclos executados", len(runs))
c2.metric("🔎 Descobertos", _tot("descobertos"))
c3.metric("✅ Ingeridos", _tot("ingeridos"))
c4.metric("↩️ Pulados (idempotência)", _tot("pulados"))
c5.metric("⚠️ Falhas", _tot("falhas"))
st.caption(f"Vídeos únicos atualmente no lakehouse (por status): {resumo}")

st.markdown("---")

# ── Evolução: vídeos ingeridos por dia ──────────────────────────────────────
colA, colB = st.columns([3, 2])
with colA:
    st.subheader("📈 Ingestões por dia")
    if por_dia:
        dfd = pd.DataFrame(por_dia)
        fig = px.bar(dfd, x="dia", y="ingeridos", text="ingeridos",
                     color_discrete_sequence=["#2E86DE"])
        fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), height=300,
                          xaxis_title=None, yaxis_title="vídeos")
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Ainda sem vídeos ingeridos.")

with colB:
    st.subheader("🛰️ Watermark por canal")
    if wms:
        dfw = pd.DataFrame(wms)[["channel_id", "last_published_at",
                                 "last_run_at", "videos_total"]]
        dfw.columns = ["Canal (ID)", "Último publishedAt", "Último ciclo", "Vídeos"]
        st.dataframe(dfw, use_container_width=True, hide_index=True)
    else:
        st.info("Sem watermark registrado.")

st.markdown("---")

# ── Histórico de ciclos ──────────────────────────────────────────────────────
st.subheader("🗂️ Histórico de ciclos de ingestão")
if runs:
    dfr = pd.DataFrame(runs)[["run_at", "canal", "descobertos", "ingeridos",
                              "pulados", "falhas"]]
    dfr.columns = ["Quando (UTC)", "Canal", "Descobertos", "Ingeridos",
                   "Pulados", "Falhas"]
    st.dataframe(dfr, use_container_width=True, hide_index=True)
else:
    st.info("Nenhum ciclo registrado ainda.")

# ── Falhas (diagnóstico) ─────────────────────────────────────────────────────
st.subheader("⚠️ Falhas de ingestão")
if falhas:
    dff = pd.DataFrame(falhas)[["video_id", "channel_id", "dominio",
                                "error", "attempts"]]
    dff.columns = ["Vídeo", "Canal", "Domínio", "Erro", "Tentativas"]
    st.dataframe(dff, use_container_width=True, hide_index=True)
else:
    st.success("Nenhuma falha registrada. 🎉")
