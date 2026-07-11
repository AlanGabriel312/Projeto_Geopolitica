# -*- coding: utf-8 -*-
"""
Sistema visual compartilhado do GeoPulse (tema claro corporativo).
Importado pelas páginas do app para unificar cabeçalho, cards de KPI, seções e
estilo dos gráficos. Mantém a paleta vinho que o dashboard analítico já usava.
"""
import streamlit as st

# ── Paleta ──────────────────────────────────────────────────────────────────
WINE   = "#9E1B1B"   # cor primária (vinho corporativo)
WINE2  = "#C0392B"
INK    = "#1f2430"   # texto
MUTED  = "#6b7280"   # texto secundário
BG     = "#f4f5f7"   # fundo da página
CARD   = "#ffffff"   # fundo dos cards
BORDER = "#e6e8ec"
BLUE   = "#2E6BE6"
GREEN  = "#1FA971"
AMBER  = "#D98A00"
RED    = "#C0392B"
SLATE  = "#64748b"

PALETA_CAT = [WINE, BLUE, GREEN, AMBER, "#7C5CBF", SLATE]
ESCALA_VINHO = [[0.0, "#f6dedb"], [0.5, "#d17b6f"], [1.0, WINE]]


def injetar_css():
    """CSS global: tipografia, fundo, cards, seções e limpeza do chrome."""
    st.markdown(f"""<style>
    .stApp {{ background:{BG}; }}
    html, body, [class*="css"] {{
        font-family:'Inter','Segoe UI',system-ui,sans-serif; color:{INK};
    }}
    #MainMenu, footer {{ visibility:hidden; }}
    .block-container {{ padding-top:1.4rem; padding-bottom:2rem; max-width:1250px; }}

    /* cabeçalho (hero) */
    .gp-hero {{
        background:linear-gradient(100deg,{WINE},{WINE2}); color:#fff;
        padding:22px 26px; border-radius:16px;
        box-shadow:0 8px 22px rgba(158,27,27,.18);
    }}
    .gp-hero h1 {{ margin:0; font-size:1.5rem; font-weight:750; letter-spacing:.2px; }}
    .gp-hero p  {{ margin:.4rem 0 0; opacity:.93; font-size:.94rem; }}

    /* linha de KPIs */
    .gp-kpis {{ display:flex; gap:14px; flex-wrap:wrap; margin:16px 0 6px; }}
    .gp-kpi {{
        flex:1 1 150px; background:{CARD}; border:1px solid {BORDER};
        border-radius:14px; padding:15px 18px; position:relative; overflow:hidden;
        box-shadow:0 2px 10px rgba(20,30,50,.05);
    }}
    .gp-kpi::before {{
        content:''; position:absolute; left:0; top:0; bottom:0; width:5px;
        background:var(--c,{WINE});
    }}
    .gp-kpi .ic  {{ font-size:1.1rem; }}
    .gp-kpi .val {{ font-size:1.85rem; font-weight:760; line-height:1.1; margin-top:2px; }}
    .gp-kpi .lab {{ font-size:.74rem; color:{MUTED}; text-transform:uppercase;
                    letter-spacing:.5px; margin-top:3px; }}

    /* cabeçalho de seção */
    .gp-sec {{ margin:22px 0 4px; }}
    .gp-sec h3 {{ margin:0; font-size:1.1rem; font-weight:700;
                  border-left:4px solid {WINE}; padding-left:10px; }}
    .gp-sec p  {{ margin:.25rem 0 0 14px; color:{MUTED}; font-size:.85rem; }}

    /* pílula de status */
    .gp-pill {{ display:inline-block; padding:5px 14px; border-radius:999px;
                font-size:.82rem; font-weight:650; }}
    </style>""", unsafe_allow_html=True)


def hero(titulo: str, subtitulo: str, emoji: str = ""):
    pre = f"{emoji}&nbsp; " if emoji else ""
    st.markdown(
        f'<div class="gp-hero"><h1>{pre}{titulo}</h1>'
        f'<p>{subtitulo}</p></div>', unsafe_allow_html=True)


def kpis(items: list):
    """items: lista de dicts {val, lab, cor} (ic opcional)."""
    def _card(i):
        ic = f'<div class="ic">{i["ic"]}</div>' if i.get("ic") else ""
        return (f'<div class="gp-kpi" style="--c:{i.get("cor", WINE)}">{ic}'
                f'<div class="val">{i["val"]}</div>'
                f'<div class="lab">{i["lab"]}</div></div>')
    st.markdown(f'<div class="gp-kpis">{"".join(_card(i) for i in items)}</div>',
                unsafe_allow_html=True)


def secao(titulo: str, descricao: str | None = None):
    d = f"<p>{descricao}</p>" if descricao else ""
    st.markdown(f'<div class="gp-sec"><h3>{titulo}</h3>{d}</div>',
                unsafe_allow_html=True)


def pill(texto: str, cor: str):
    """Pílula colorida (fundo suave, texto na cor)."""
    st.markdown(
        f'<span class="gp-pill" style="background:{cor}1a;color:{cor};">{texto}</span>',
        unsafe_allow_html=True)


def estilo_plotly(fig, altura: int | None = None):
    """Padroniza o visual dos gráficos Plotly com o tema."""
    fig.update_layout(
        template="plotly_white",
        font=dict(family="Inter, Segoe UI, sans-serif", color=INK, size=13),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=34, b=12, l=12, r=12),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
    )
    if altura:
        fig.update_layout(height=altura)
    return fig
