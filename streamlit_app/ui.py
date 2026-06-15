# -*- coding: utf-8 -*-
"""Componentes visuales compartidos del dashboard gerencial."""
from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


APP_CSS = """
<style>
    .stApp { background: #f4f6f8; }
    [data-testid="stSidebar"] { background: #111827; }
    [data-testid="stSidebar"] * { color: #f9fafb; }
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stRadio label { color: #d1d5db !important; }
    .block-container { max-width: 1500px; padding-top: 1.3rem; padding-bottom: 3rem; }
    .rt-eyebrow { color: #64748b; font-size: .78rem; letter-spacing: .08em;
        text-transform: uppercase; font-weight: 700; margin-bottom: .15rem; }
    .rt-title { color: #0f172a; font-size: 2rem; line-height: 1.15;
        font-weight: 760; margin: 0 0 .25rem 0; }
    .rt-subtitle { color: #64748b; font-size: .95rem; margin-bottom: 1.1rem; }
    .rt-section { color: #0f172a; font-size: 1.15rem; font-weight: 720;
        margin-top: .35rem; margin-bottom: .25rem; }
    .rt-note { color: #64748b; font-size: .82rem; }
    [data-testid="stMetric"] { background: white; border: 1px solid #e2e8f0;
        padding: .85rem 1rem; border-radius: 12px; box-shadow: 0 1px 2px rgba(15,23,42,.04); }
    [data-testid="stMetricLabel"] { color: #64748b; font-weight: 650; }
    [data-testid="stMetricValue"] { color: #0f172a; }
    div[data-testid="stDataFrame"] { background: white; border-radius: 12px;
        border: 1px solid #e2e8f0; overflow: hidden; }
    .rt-status-ok { display:inline-block; padding:.25rem .55rem; border-radius:999px;
        background:#dcfce7; color:#166534; font-size:.78rem; font-weight:700; }
    .rt-status-warn { display:inline-block; padding:.25rem .55rem; border-radius:999px;
        background:#fef3c7; color:#92400e; font-size:.78rem; font-weight:700; }
</style>
"""


def inject_css() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str, eyebrow: str = "Control de Gestión RT") -> None:
    st.markdown(
        f"""
        <div class="rt-eyebrow">{eyebrow}</div>
        <div class="rt-title">{title}</div>
        <div class="rt-subtitle">{subtitle}</div>
        """,
        unsafe_allow_html=True,
    )


def section_title(title: str, note: str | None = None) -> None:
    st.markdown(f'<div class="rt-section">{title}</div>', unsafe_allow_html=True)
    if note:
        st.markdown(f'<div class="rt-note">{note}</div>', unsafe_allow_html=True)


def format_integer(value: Any) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{float(value):,.0f}".replace(",", ".")


def format_decimal(value: Any, decimals: int = 2) -> str:
    if value is None or pd.isna(value):
        return "—"
    text = f"{float(value):,.{decimals}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def format_percent(value: Any, decimals: int = 1) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{format_decimal(value, decimals)}%"


def metric(
    label: str,
    value: Any,
    delta: Any | None = None,
    *,
    value_kind: str = "integer",
    delta_kind: str = "integer",
    help_text: str | None = None,
) -> None:
    value_text = (
        format_integer(value)
        if value_kind == "integer"
        else format_decimal(value)
    )
    delta_text: str | None = None
    if delta is not None and not pd.isna(delta):
        delta_text = (
            format_percent(delta)
            if delta_kind == "percent"
            else format_integer(delta)
        )
    st.metric(label, value_text, delta=delta_text, help=help_text)


def base_figure(fig: go.Figure, height: int = 380) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=10, r=15, t=45, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="white",
        font=dict(family="Arial, sans-serif", color="#334155", size=12),
        title_font=dict(size=16, color="#0f172a"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hoverlabel=dict(bgcolor="white", font_size=12),
    )
    fig.update_xaxes(showgrid=False, linecolor="#e2e8f0")
    fig.update_yaxes(gridcolor="#eef2f7", zerolinecolor="#cbd5e1")
    return fig


def csv_download(df: pd.DataFrame, file_name: str, label: str = "Descargar CSV") -> None:
    data = df.to_csv(index=False, sep=";", encoding="utf-8-sig")
    st.download_button(
        label=label,
        data=data,
        file_name=file_name,
        mime="text/csv",
        use_container_width=False,
    )
