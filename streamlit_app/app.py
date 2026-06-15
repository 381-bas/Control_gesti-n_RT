# -*- coding: utf-8 -*-
"""Página gerencial V1 · Control de Gestión RT."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_access import (
    get_clients,
    get_database_path,
    get_metadata,
    get_modalities,
    get_monthly_capacity,
    get_monthly_modalities,
    get_periods,
    get_qa,
    get_region_capacity,
    get_regions,
    get_retail,
    get_snapshot,
)
from ui import (
    base_figure,
    csv_download,
    format_decimal,
    format_integer,
    format_percent,
    inject_css,
    page_header,
    section_title,
)

st.set_page_config(
    page_title="Control de Gestión RT",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()

MONTH_NAMES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


def stop_with_database_error(exc: Exception) -> None:
    page_header(
        "Base no disponible",
        "La página local requiere la capa SQL gerencial V1 aplicada.",
    )
    st.error(str(exc))
    st.code(
        "git pull origin main\n"
        "python scripts\\aplicar_vistas.py\n"
        "python -m streamlit run streamlit_app\\app.py",
        language="powershell",
    )
    st.stop()


def safe_pct_change(current: float, previous: float) -> float | None:
    if previous is None or pd.isna(previous) or float(previous) == 0:
        return None
    return 100.0 * (float(current) - float(previous)) / float(previous)


def kpi_card(label: str, value: object, note: str, *, decimal: bool = False) -> None:
    rendered = format_decimal(value) if decimal else format_integer(value)
    st.markdown(
        f"""
        <div class="rt-kpi-card">
            <div class="rt-kpi-label">{label}</div>
            <div class="rt-kpi-value">{rendered}</div>
            <div class="rt-kpi-note">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def fact_box(title: str, text: str) -> None:
    st.markdown(
        f"""
        <div class="rt-fact-box">
            <div class="rt-fact-title">{title}</div>
            <div class="rt-fact-text">{text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


try:
    db_path = get_database_path()
    metadata_df = get_metadata()
    periods = get_periods()
except Exception as exc:  # pragma: no cover
    stop_with_database_error(exc)

if metadata_df.empty or periods.empty:
    stop_with_database_error(RuntimeError("Las vistas gerenciales no contienen datos."))

metadata = metadata_df.iloc[0]
latest_period = str(metadata["latest_period_label"])
period_row = periods.loc[periods["period_label"] == latest_period].iloc[0]
period_display = str(period_row["period_display"])

try:
    snapshot_df = get_snapshot(latest_period)
    retail = get_retail(latest_period)
    modalities = get_modalities(latest_period)
    regions = get_regions(latest_period)
    region_capacity = get_region_capacity(latest_period)
    monthly = get_monthly_capacity()
    monthly_modalities = get_monthly_modalities()
    clients = get_clients(latest_period)
    qa = get_qa(latest_period)
except Exception as exc:  # pragma: no cover
    stop_with_database_error(exc)

if snapshot_df.empty:
    stop_with_database_error(RuntimeError("No existe fotografía gerencial actual."))

snapshot = snapshot_df.iloc[0]
monthly = monthly.copy()
monthly["mes"] = monthly["period_month"].map(MONTH_NAMES)
monthly_modalities = monthly_modalities.copy()
monthly_modalities["mes"] = monthly_modalities["period_month"].map(MONTH_NAMES)

st.sidebar.markdown("## Control de Gestión RT")
st.sidebar.caption("Página gerencial V1 · entorno local")
st.sidebar.markdown(f"**Fotografía actual**  \n{period_display}")
st.sidebar.caption(f"Última carga: {metadata['ultima_carga']}")
st.sidebar.caption(f"Fuente: {db_path.name}")
st.sidebar.divider()
st.sidebar.markdown("**Lectura de la página**")
st.sidebar.caption(
    "Situación actual, concentración por RETAIL, modalidad y región, "
    "capacidad regional y comportamiento mensual."
)
if int(metadata["controles_error"]) == 0:
    st.sidebar.markdown(
        '<span class="rt-status-ok">QA sin errores críticos</span>',
        unsafe_allow_html=True,
    )
else:
    st.sidebar.markdown(
        '<span class="rt-status-warn">QA requiere revisión</span>',
        unsafe_allow_html=True,
    )

page_header(
    "Capacidad y carga operativa",
    f"Situación global actual al cierre de {period_display}. "
    "Las tendencias se presentan por cierre mensual.",
)

section_title(
    "1. Situación operativa actual",
    "Tamaño vigente de la operación. Las tarjetas no comparan contra la semana anterior.",
)
cols = st.columns(6)
with cols[0]:
    kpi_card(
        "Carga operativa semanal",
        snapshot["volumen_operativo"],
        "Frecuencia oficial consolidada",
    )
with cols[1]:
    kpi_card("Locales cubiertos", snapshot["locales_activos"], "Salas con presencia")
with cols[2]:
    kpi_card("Puntos de gestión", snapshot["local_cliente"], "Combinaciones LOCAL/CLIENTE")
with cols[3]:
    kpi_card("Clientes activos", snapshot["clientes_activos"], "Cartera con presencia")
with cols[4]:
    kpi_card("Personas MULTIMARCA", snapshot["personas_multimarca"], "Dotación estructural principal")
with cols[5]:
    kpi_card("Personas PITUTO", snapshot["personas_pituto"], "Capacidad flexible vigente")

st.markdown("<div style='height:.45rem'></div>", unsafe_allow_html=True)
context_cols = st.columns(4)
with context_cols[0]:
    kpi_card(
        "Top 2 RETAIL",
        snapshot["concentracion_top2_retail_pct"],
        "Concentración del volumen (%)",
        decimal=True,
    )
with context_cols[1]:
    kpi_card(
        "Top 2 regiones",
        snapshot["concentracion_top2_region_pct"],
        "Concentración territorial (%)",
        decimal=True,
    )
with context_cols[2]:
    kpi_card(
        "Peso MULTIMARCA",
        snapshot["peso_multimarca_pct"],
        "Sobre carga asignada (%)",
        decimal=True,
    )
with context_cols[3]:
    kpi_card(
        "Peso PITUTO",
        snapshot["peso_pituto_pct"],
        "Sobre carga asignada (%)",
        decimal=True,
    )

section_title(
    "2. Concentración actual por RETAIL y modalidad",
    "Cantidad y porcentaje de peso dentro de cada universo.",
)
left, right = st.columns([1.45, 1])
with left:
    retail_chart = retail.sort_values("volumen_operativo", ascending=True).copy()
    retail_chart["etiqueta"] = retail_chart.apply(
        lambda row: f"{format_integer(row['volumen_operativo'])} | "
        f"{format_percent(row['participacion_volumen_pct'])}",
        axis=1,
    )
    fig = px.bar(
        retail_chart,
        x="volumen_operativo",
        y="cadena",
        orientation="h",
        text="etiqueta",
        custom_data=["participacion_volumen_pct", "locales_activos", "puntos_gestion", "clientes_activos"],
    )
    fig.update_traces(
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>Carga: %{x:,.0f}<br>Peso: %{customdata[0]:.1f}%"
            "<br>Locales: %{customdata[1]:,.0f}<br>Puntos: %{customdata[2]:,.0f}"
            "<br>Clientes: %{customdata[3]:,.0f}<extra></extra>"
        ),
    )
    fig.update_layout(title="Peso operativo por RETAIL", xaxis_title="Carga operativa", yaxis_title="")
    st.plotly_chart(base_figure(fig, 430), width="stretch")

with right:
    fig = go.Figure(
        go.Pie(
            labels=modalities["modalidad"],
            values=modalities["carga_asignada"],
            hole=0.58,
            textinfo="label+percent",
            hovertemplate=(
                "<b>%{label}</b><br>Carga asignada: %{value:,.0f}"
                "<br>Peso: %{percent}<extra></extra>"
            ),
        )
    )
    fig.update_layout(
        title="Peso de carga por modalidad",
        annotations=[
            dict(
                text=f"{format_integer(modalities['carga_asignada'].sum())}<br><span style='font-size:11px'>asignada</span>",
                x=0.5,
                y=0.5,
                showarrow=False,
                font=dict(size=19),
            )
        ],
    )
    st.plotly_chart(base_figure(fig, 350), width="stretch")
    modality_compact = modalities[[
        "modalidad",
        "carga_asignada",
        "participacion_carga_pct",
        "personas_activas",
        "carga_por_persona",
    ]].copy()
    st.dataframe(
        modality_compact,
        width="stretch",
        hide_index=True,
        column_config={
            "modalidad": "Modalidad",
            "carga_asignada": st.column_config.NumberColumn("Carga", format="%,.0f"),
            "participacion_carga_pct": st.column_config.NumberColumn("Peso", format="%.1f%%"),
            "personas_activas": st.column_config.NumberColumn("Personas", format="%,.0f"),
            "carga_por_persona": st.column_config.NumberColumn("Carga/persona", format="%.1f"),
        },
    )
    difference = float(snapshot["carga_asignada_total"] - snapshot["volumen_operativo"])
    st.caption(
        f"La carga asignada supera al volumen oficial en {format_integer(difference)} "
        "por gestiones compartidas entre modalidades."
    )

section_title(
    "3. Distribución territorial y capacidad regional",
    "El volumen regional usa la métrica oficial. Las rutas estructurales corresponden a MULTIMARCA y BREDEN.",
)
left, right = st.columns([1.35, 1])
with left:
    region_chart = regions.sort_values("volumen_operativo", ascending=True).copy()
    region_chart["etiqueta"] = region_chart.apply(
        lambda row: f"{format_integer(row['volumen_operativo'])} | "
        f"{format_percent(row['participacion_volumen_pct'])}",
        axis=1,
    )
    fig = px.bar(
        region_chart,
        x="volumen_operativo",
        y="region",
        orientation="h",
        text="etiqueta",
        custom_data=["participacion_volumen_pct", "locales_activos", "puntos_gestion", "clientes_activos"],
    )
    fig.update_traces(
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>Carga: %{x:,.0f}<br>Peso: %{customdata[0]:.1f}%"
            "<br>Locales: %{customdata[1]:,.0f}<br>Puntos: %{customdata[2]:,.0f}"
            "<br>Clientes: %{customdata[3]:,.0f}<extra></extra>"
        ),
    )
    fig.update_layout(title="Peso operativo por región", xaxis_title="Carga operativa", yaxis_title="")
    st.plotly_chart(base_figure(fig, 560), width="stretch")

with right:
    capacity_chart = region_capacity.dropna(subset=["carga_por_ruta_estructural"]).copy()
    capacity_chart = capacity_chart.sort_values("carga_por_ruta_estructural", ascending=True)
    fig = px.bar(
        capacity_chart,
        x="carga_por_ruta_estructural",
        y="region",
        orientation="h",
        text="carga_por_ruta_estructural",
        custom_data=["rutas_estructurales", "carga_estructural", "puntos_gestion"],
    )
    fig.update_traces(
        texttemplate="%{text:.1f}",
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>Carga por ruta: %{x:.1f}"
            "<br>Rutas estructurales: %{customdata[0]:,.0f}"
            "<br>Carga estructural: %{customdata[1]:,.0f}"
            "<br>Puntos de gestión: %{customdata[2]:,.0f}<extra></extra>"
        ),
    )
    fig.update_layout(
        title="Carga por ruta estructural",
        xaxis_title="Carga asignada por ruta",
        yaxis_title="",
    )
    st.plotly_chart(base_figure(fig, 560), width="stretch")

capacity_table = region_capacity[[
    "region",
    "volumen_operativo",
    "participacion_volumen_pct",
    "rutas_estructurales",
    "distribucion_presencia_rutas_pct",
    "personas_flexibles",
    "clientes_activos",
    "puntos_gestion",
    "carga_por_ruta_estructural",
    "carga_flexible_por_persona",
    "puntos_por_persona",
]].copy()
st.dataframe(
    capacity_table,
    width="stretch",
    hide_index=True,
    column_config={
        "region": "Región",
        "volumen_operativo": st.column_config.NumberColumn("Carga oficial", format="%,.0f"),
        "participacion_volumen_pct": st.column_config.NumberColumn("Peso", format="%.1f%%"),
        "rutas_estructurales": st.column_config.NumberColumn("Rutas estructurales", format="%,.0f"),
        "distribucion_presencia_rutas_pct": st.column_config.NumberColumn("Distribución rutas", format="%.1f%%"),
        "personas_flexibles": st.column_config.NumberColumn("Personas flexibles", format="%,.0f"),
        "clientes_activos": st.column_config.NumberColumn("Clientes", format="%,.0f"),
        "puntos_gestion": st.column_config.NumberColumn("Puntos", format="%,.0f"),
        "carga_por_ruta_estructural": st.column_config.NumberColumn("Carga/ruta", format="%.1f"),
        "carga_flexible_por_persona": st.column_config.NumberColumn("Carga flexible/persona", format="%.1f"),
        "puntos_por_persona": st.column_config.NumberColumn("Puntos/persona", format="%.1f"),
    },
)
st.caption(
    "Distribución rutas = presencias REGIÓN + RUTERO para MULTIMARCA/BREDEN. "
    "Una ruta presente en más de una región participa en cada región."
)

section_title(
    "4. Comportamiento mensual",
    "La línea principal utiliza la última semana disponible de cada mes; la secundaria muestra el promedio semanal.",
)
metric_tabs = st.tabs(["Carga operativa", "Puntos de gestión", "Locales", "Clientes"])
monthly_fields = [
    ("volumen_cierre", "volumen_promedio_semanal", "Carga operativa"),
    ("local_cliente_cierre", "local_cliente_promedio_semanal", "Puntos de gestión"),
    ("locales_cierre", "locales_promedio_semanal", "Locales"),
    ("clientes_cierre", "clientes_promedio_semanal", "Clientes"),
]
for tab, (close_field, average_field, title) in zip(metric_tabs, monthly_fields):
    with tab:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=monthly["mes"],
                y=monthly[close_field],
                mode="lines+markers+text",
                text=monthly[close_field].map(lambda value: format_integer(value)),
                textposition="top center",
                name="Cierre mensual",
                line=dict(width=3),
                marker=dict(size=9),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=monthly["mes"],
                y=monthly[average_field],
                mode="lines+markers",
                name="Promedio semanal",
                line=dict(width=2, dash="dash"),
                marker=dict(size=7),
            )
        )
        fig.update_layout(title=title, xaxis_title="", yaxis_title=title)
        st.plotly_chart(base_figure(fig, 390), width="stretch")

left, right = st.columns(2)
for container, modality in [(left, "MULTIMARCA"), (right, "PITUTO")]:
    with container:
        subset = monthly_modalities.loc[
            monthly_modalities["modalidad"] == modality
        ].copy()
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=subset["mes"],
                y=subset["carga_cierre"],
                name="Carga asignada",
                text=subset["carga_cierre"].map(lambda value: format_integer(value)),
                textposition="outside",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=subset["mes"],
                y=subset["personas_cierre"],
                name="Personas",
                mode="lines+markers+text",
                text=subset["personas_cierre"].map(lambda value: format_integer(value)),
                textposition="top center",
                yaxis="y2",
                line=dict(width=3),
                marker=dict(size=9),
            )
        )
        fig.update_layout(
            title=f"{modality}: carga y personas",
            yaxis=dict(title="Carga asignada"),
            yaxis2=dict(title="Personas", overlaying="y", side="right", showgrid=False),
        )
        st.plotly_chart(base_figure(fig, 400), width="stretch")

section_title(
    "5. Lectura operacional basada en datos",
    "Hechos automáticos para respaldar la revisión de capacidad; no aplican umbrales ni recomendaciones.",
)
first_month = monthly.iloc[0]
last_month = monthly.iloc[-1]
mm_monthly = monthly_modalities.loc[monthly_modalities["modalidad"] == "MULTIMARCA"].sort_values("period_month")
pit_monthly = monthly_modalities.loc[monthly_modalities["modalidad"] == "PITUTO"].sort_values("period_month")
mm_last = mm_monthly.iloc[-1]
pit_last = pit_monthly.iloc[-1]

top_retail = retail.iloc[0]
top_region = regions.iloc[0]
top_pressure = region_capacity.dropna(subset=["carga_por_ruta_estructural"]).sort_values(
    "carga_por_ruta_estructural", ascending=False
).iloc[0]

load_change = safe_pct_change(last_month["volumen_cierre"], first_month["volumen_cierre"])
local_change = safe_pct_change(last_month["locales_cierre"], first_month["locales_cierre"])
point_change = safe_pct_change(last_month["local_cliente_cierre"], first_month["local_cliente_cierre"])

fact_cols = st.columns(2)
with fact_cols[0]:
    fact_box(
        "Concentración operativa",
        f"{top_retail['cadena']} concentra {format_percent(top_retail['participacion_volumen_pct'])} "
        f"de la carga. Las dos principales cadenas reúnen "
        f"{format_percent(snapshot['concentracion_top2_retail_pct'])}.",
    )
    fact_box(
        "Expansión territorial",
        f"Entre {MONTH_NAMES[int(first_month['period_month'])]} y "
        f"{MONTH_NAMES[int(last_month['period_month'])]}, los locales cambian "
        f"{format_percent(local_change)} y los puntos de gestión {format_percent(point_change)}, "
        f"mientras la carga cambia {format_percent(load_change)}.",
    )
    fact_box(
        "MULTIMARCA",
        f"La dotación de cierre se mueve entre {format_integer(mm_monthly['personas_cierre'].min())} "
        f"y {format_integer(mm_monthly['personas_cierre'].max())} personas. Actualmente son "
        f"{format_integer(mm_last['personas_cierre'])}, con {format_integer(mm_last['locales_cierre'])} "
        f"locales y {format_integer(mm_last['puntos_cierre'])} puntos asignados.",
    )
with fact_cols[1]:
    fact_box(
        "Concentración regional",
        f"{top_region['region']} representa {format_percent(top_region['participacion_volumen_pct'])} "
        f"de la carga; las dos principales regiones concentran "
        f"{format_percent(snapshot['concentracion_top2_region_pct'])}.",
    )
    fact_box(
        "Capacidad estructural regional",
        f"{top_pressure['region']} registra la mayor carga por ruta estructural: "
        f"{format_decimal(top_pressure['carga_por_ruta_estructural'], 1)}, con "
        f"{format_integer(top_pressure['rutas_estructurales'])} rutas con presencia.",
    )
    fact_box(
        "PITUTO",
        f"Actualmente opera con {format_integer(pit_last['personas_cierre'])} personas, "
        f"{format_integer(pit_last['locales_cierre'])} locales y "
        f"{format_integer(pit_last['puntos_cierre'])} puntos. Durante los cierres mensuales, "
        f"la carga se ha movido entre {format_integer(pit_monthly['carga_cierre'].min())} y "
        f"{format_integer(pit_monthly['carga_cierre'].max())}.",
    )

section_title("6. Respaldo de detalle")
with st.expander("Detalle por RETAIL"):
    st.dataframe(retail, width="stretch", hide_index=True)
    csv_download(retail, f"retail_{latest_period}.csv")
with st.expander("Detalle por modalidad"):
    st.dataframe(modalities, width="stretch", hide_index=True)
    csv_download(modalities, f"modalidades_{latest_period}.csv")
with st.expander("Detalle por región"):
    st.dataframe(region_capacity, width="stretch", hide_index=True)
    csv_download(region_capacity, f"capacidad_region_{latest_period}.csv")
with st.expander("Detalle de clientes"):
    st.dataframe(clients, width="stretch", hide_index=True, height=520)
    csv_download(clients, f"clientes_{latest_period}.csv")
with st.expander("Calidad de datos"):
    st.dataframe(qa, width="stretch", hide_index=True)
    csv_download(qa, f"qa_{latest_period}.csv")
