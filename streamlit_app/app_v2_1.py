# -*- coding: utf-8 -*-
"""Página gerencial V2.1 · capacidad MULTIMARCA y gestión PITUTO."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_access import (
    get_clients,
    get_database_path,
    get_metadata,
    get_monthly_global,
    get_monthly_pituto,
    get_monthly_rt,
    get_monthly_services,
    get_periods,
    get_pituto_client_region,
    get_pituto_clients,
    get_pituto_regions,
    get_pituto_summary,
    get_qa,
    get_regions,
    get_retail,
    get_rt_region_capacity,
    get_rt_summary,
    get_services,
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
    initial_sidebar_state="collapsed",
)
inject_css()

MONTH_NAMES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}


def stop_with_database_error(exc: Exception) -> None:
    page_header(
        "Base no disponible",
        "La página requiere el PATCH 12 de gestión PITUTO aplicado.",
    )
    st.error(str(exc))
    st.code(
        "git pull origin feature/dashboard-control-gestion-v2-1\n"
        "python scripts\\aplicar_vistas.py\n"
        "python -m streamlit run streamlit_app\\app.py",
        language="powershell",
    )
    st.stop()


def kpi_card(
    label: str,
    value: object,
    note: str,
    *,
    decimals: int = 0,
    suffix: str = "",
) -> None:
    rendered = format_integer(value) if decimals == 0 else format_decimal(value, decimals)
    st.markdown(
        f"""
        <div class="rt-kpi-card">
            <div class="rt-kpi-label">{label}</div>
            <div class="rt-kpi-value">{rendered}{suffix}</div>
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


def safe_pct_change(current: float, previous: float) -> float | None:
    if previous is None or pd.isna(previous) or float(previous) == 0:
        return None
    return 100.0 * (float(current) - float(previous)) / float(previous)


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
    snapshot = get_snapshot(latest_period).iloc[0]
    rt_summary = get_rt_summary(latest_period).iloc[0]
    pituto_summary = get_pituto_summary(latest_period).iloc[0]
    retail = get_retail(latest_period)
    services = get_services(latest_period)
    regions = get_regions(latest_period)
    rt_regions = get_rt_region_capacity(latest_period)
    pituto_clients = get_pituto_clients(latest_period)
    pituto_regions = get_pituto_regions(latest_period)
    pituto_client_region = get_pituto_client_region(latest_period)
    monthly_global = get_monthly_global()
    monthly_services = get_monthly_services()
    monthly_rt = get_monthly_rt()
    monthly_pituto = get_monthly_pituto()
    clients = get_clients(latest_period)
    qa = get_qa(latest_period)
except Exception as exc:  # pragma: no cover
    stop_with_database_error(exc)

for dataframe in (monthly_global, monthly_services, monthly_rt, monthly_pituto):
    dataframe["mes"] = dataframe["period_month"].map(MONTH_NAMES)

st.sidebar.markdown("## Control de Gestión RT")
st.sidebar.caption("V2.1 · gestión PITUTO corregida")
st.sidebar.markdown(f"**Último corte disponible**  \n{period_display}")
st.sidebar.caption(f"Última carga: {metadata['ultima_carga']}")
st.sidebar.caption(f"Fuente: {db_path.name}")
st.sidebar.divider()
st.sidebar.markdown("**Regla PITUTO**")
st.sidebar.caption(
    "PITUTO se mide por locales y combinaciones LOCAL/CLIENTE. "
    "No se interpreta como ruta ni como dotación desde esta base."
)

page_header(
    "Capacidad y carga operativa",
    f"Situación al corte de {period_display}. MULTIMARCA representa la estructura de rutas; "
    "PITUTO representa gestiones puntuales por LOCAL/CLIENTE.",
)

# ------------------------------------------------------------------
# 1. Situación actual
# ------------------------------------------------------------------
section_title(
    "1. Situación operativa actual",
    "El total empresa se mantiene separado de la capacidad MULTIMARCA y la gestión PITUTO.",
)
cols = st.columns(6)
with cols[0]:
    kpi_card("Carga operativa oficial", snapshot["volumen_operativo"], "LOCAL/CLIENTE sin duplicación")
with cols[1]:
    kpi_card("Locales cubiertos", snapshot["locales_activos"], "Total empresa")
with cols[2]:
    kpi_card("Puntos de gestión", snapshot["local_cliente"], "Combinaciones LOCAL/CLIENTE")
with cols[3]:
    kpi_card("Clientes activos", snapshot["clientes_activos"], "Cartera total")
with cols[4]:
    kpi_card("Rutas MULTIMARCA", rt_summary["rutas_multimarca"], "Estructura de rutas RT")
with cols[5]:
    kpi_card("Gestiones PITUTO", pituto_summary["pituto_gestiones"], "Combinaciones LOCAL/CLIENTE")

st.markdown("<div style='height:.45rem'></div>", unsafe_allow_html=True)
cols = st.columns(6)
with cols[0]:
    kpi_card("Personas MULTIMARCA", rt_summary["personas_multimarca"], "Personas con asignación MM")
with cols[1]:
    kpi_card("Locales MULTIMARCA", rt_summary["multimarca_locales"], "Cobertura estructural")
with cols[2]:
    kpi_card("Puntos MULTIMARCA", rt_summary["multimarca_gestiones"], "LOCAL/CLIENTE asignados")
with cols[3]:
    kpi_card("Locales PITUTO", pituto_summary["pituto_locales"], "Locales con gestión puntual")
with cols[4]:
    kpi_card("Clientes PITUTO", pituto_summary["pituto_clientes"], "Clientes con PITUTO")
with cols[5]:
    kpi_card(
        "Peso PITUTO en RT",
        rt_summary["peso_pituto_en_gestiones_rt_pct"],
        "Sobre gestiones consolidadas RT",
        decimals=1,
        suffix="%",
    )

# ------------------------------------------------------------------
# 2. Concentración empresa y servicios
# ------------------------------------------------------------------
section_title(
    "2. Concentración por RETAIL y servicio",
    "RETAIL usa carga oficial. Los servicios se mantienen separados por su carga contable.",
)
left, right = st.columns([1.45, 1])
with left:
    chart = retail.sort_values("volumen_operativo", ascending=True).copy()
    chart["etiqueta"] = chart.apply(
        lambda row: f"{format_integer(row['volumen_operativo'])} | "
        f"{format_percent(row['participacion_volumen_pct'])}",
        axis=1,
    )
    fig = px.bar(
        chart,
        x="volumen_operativo",
        y="cadena",
        orientation="h",
        text="etiqueta",
        custom_data=["locales_activos", "puntos_gestion", "clientes_activos"],
    )
    fig.update_traces(
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>Carga: %{x:,.0f}"
            "<br>Locales: %{customdata[0]:,.0f}"
            "<br>Puntos: %{customdata[1]:,.0f}"
            "<br>Clientes: %{customdata[2]:,.0f}<extra></extra>"
        ),
    )
    fig.update_layout(title="Peso operativo por RETAIL", xaxis_title="Carga oficial", yaxis_title="")
    st.plotly_chart(base_figure(fig, 430), width="stretch")

with right:
    chart = services.sort_values("carga_servicio", ascending=True).copy()
    chart["etiqueta"] = chart.apply(
        lambda row: f"{format_integer(row['carga_servicio'])} | "
        f"{format_percent(row['participacion_servicio_pct'])}",
        axis=1,
    )
    fig = px.bar(
        chart,
        x="carga_servicio",
        y="servicio_operativo",
        orientation="h",
        text="etiqueta",
        custom_data=["locales_activos", "puntos_gestion", "clientes_activos"],
    )
    fig.update_traces(
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>Carga: %{x:,.0f}"
            "<br>Locales: %{customdata[0]:,.0f}"
            "<br>Puntos: %{customdata[1]:,.0f}"
            "<br>Clientes: %{customdata[2]:,.0f}<extra></extra>"
        ),
    )
    fig.update_layout(title="Peso contable por servicio", xaxis_title="Carga", yaxis_title="")
    st.plotly_chart(base_figure(fig, 360), width="stretch")

# ------------------------------------------------------------------
# 3. Retail Trust: MM y PITUTO separados por unidad válida
# ------------------------------------------------------------------
section_title(
    "3. Retail Trust: estructura MULTIMARCA y gestión PITUTO",
    "MULTIMARCA se analiza por rutas. PITUTO se analiza por locales y combinaciones LOCAL/CLIENTE.",
)
left, right = st.columns(2)
with left:
    mm_metrics = pd.DataFrame(
        {
            "Indicador": ["Carga", "Locales", "Puntos", "Rutas"],
            "Valor": [
                rt_summary["carga_multimarca"],
                rt_summary["multimarca_locales"],
                rt_summary["multimarca_gestiones"],
                rt_summary["rutas_multimarca"],
            ],
        }
    )
    fig = px.bar(mm_metrics, x="Indicador", y="Valor", text="Valor")
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig.update_layout(title="MULTIMARCA: estructura vigente", xaxis_title="", yaxis_title="Cantidad")
    st.plotly_chart(base_figure(fig, 330), width="stretch")
    st.caption(
        f"Carga/ruta: {format_decimal(rt_summary['carga_por_ruta_multimarca'], 1)} · "
        f"Locales/ruta: {format_decimal(rt_summary['locales_por_ruta_multimarca'], 1)} · "
        f"Puntos/ruta: {format_decimal(rt_summary['gestiones_por_ruta_multimarca'], 1)}"
    )

with right:
    pituto_metrics = pd.DataFrame(
        {
            "Indicador": ["Carga", "Locales", "Gestiones", "Clientes"],
            "Valor": [
                pituto_summary["pituto_carga"],
                pituto_summary["pituto_locales"],
                pituto_summary["pituto_gestiones"],
                pituto_summary["pituto_clientes"],
            ],
        }
    )
    fig = px.bar(pituto_metrics, x="Indicador", y="Valor", text="Valor")
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig.update_layout(title="PITUTO: gestiones vigentes", xaxis_title="", yaxis_title="Cantidad")
    st.plotly_chart(base_figure(fig, 330), width="stretch")
    st.caption(
        f"Gestiones/local: {format_decimal(pituto_summary['gestiones_por_local'], 2)} · "
        f"Carga/gestión: {format_decimal(pituto_summary['carga_por_gestion'], 2)} · "
        "La dotación real se administra en otra base."
    )

pit_left, pit_right = st.columns(2)
with pit_left:
    chart = pituto_clients.head(12).sort_values("pituto_gestiones", ascending=True).copy()
    chart["etiqueta"] = chart.apply(
        lambda row: f"{format_integer(row['pituto_gestiones'])} | "
        f"{format_percent(row['participacion_gestiones_pct'])}",
        axis=1,
    )
    fig = px.bar(
        chart,
        x="pituto_gestiones",
        y="cliente",
        orientation="h",
        text="etiqueta",
        custom_data=["pituto_locales", "pituto_carga", "pituto_regiones"],
    )
    fig.update_traces(
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>Gestiones: %{x:,.0f}"
            "<br>Locales: %{customdata[0]:,.0f}"
            "<br>Carga: %{customdata[1]:,.0f}"
            "<br>Regiones: %{customdata[2]:,.0f}<extra></extra>"
        ),
    )
    fig.update_layout(title="PITUTO por cliente", xaxis_title="Gestiones LOCAL/CLIENTE", yaxis_title="")
    st.plotly_chart(base_figure(fig, 470), width="stretch")

with pit_right:
    chart = pituto_regions.sort_values("pituto_gestiones", ascending=True).copy()
    chart["etiqueta"] = chart.apply(
        lambda row: f"{format_integer(row['pituto_gestiones'])} | "
        f"{format_percent(row['participacion_gestiones_pct'])}",
        axis=1,
    )
    fig = px.bar(
        chart,
        x="pituto_gestiones",
        y="region",
        orientation="h",
        text="etiqueta",
        custom_data=["pituto_locales", "pituto_clientes", "pituto_carga"],
    )
    fig.update_traces(
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>Gestiones: %{x:,.0f}"
            "<br>Locales: %{customdata[0]:,.0f}"
            "<br>Clientes: %{customdata[1]:,.0f}"
            "<br>Carga: %{customdata[2]:,.0f}<extra></extra>"
        ),
    )
    fig.update_layout(title="PITUTO por región", xaxis_title="Gestiones LOCAL/CLIENTE", yaxis_title="")
    st.plotly_chart(base_figure(fig, 470), width="stretch")

# ------------------------------------------------------------------
# 4. Región y presión MM
# ------------------------------------------------------------------
section_title(
    "4. Distribución territorial y capacidad MULTIMARCA",
    "La presión de rutas utiliza exclusivamente MULTIMARCA. PITUTO aparece como volumen de gestiones por región.",
)
left, right = st.columns([1.25, 1])
with left:
    top_regions = regions.head(8).copy()
    if len(regions) > 8:
        others = pd.DataFrame(
            {
                "region": ["OTRAS REGIONES"],
                "volumen_operativo": [regions.iloc[8:]["volumen_operativo"].sum()],
                "participacion_volumen_pct": [regions.iloc[8:]["participacion_volumen_pct"].sum()],
            }
        )
        top_regions = pd.concat([top_regions, others], ignore_index=True)
    top_regions = top_regions.sort_values("volumen_operativo", ascending=True)
    top_regions["etiqueta"] = top_regions.apply(
        lambda row: f"{format_integer(row['volumen_operativo'])} | "
        f"{format_percent(row['participacion_volumen_pct'])}",
        axis=1,
    )
    fig = px.bar(top_regions, x="volumen_operativo", y="region", orientation="h", text="etiqueta")
    fig.update_traces(textposition="outside")
    fig.update_layout(title="Peso operativo por región", xaxis_title="Carga oficial", yaxis_title="")
    st.plotly_chart(base_figure(fig, 500), width="stretch")

with right:
    capacity = rt_regions.loc[rt_regions["rutas_multimarca"] >= 2].copy()
    if capacity.empty:
        capacity = rt_regions.dropna(subset=["carga_por_ruta_multimarca"]).copy()
    capacity = capacity.sort_values("carga_por_ruta_multimarca", ascending=True)
    fig = px.bar(
        capacity,
        x="carga_por_ruta_multimarca",
        y="region",
        orientation="h",
        text="carga_por_ruta_multimarca",
        custom_data=[
            "rutas_multimarca",
            "multimarca_locales",
            "multimarca_gestiones",
            "pituto_gestiones",
        ],
    )
    fig.update_traces(
        texttemplate="%{text:.1f}",
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>Carga/ruta MM: %{x:.1f}"
            "<br>Rutas MM: %{customdata[0]:,.0f}"
            "<br>Locales MM: %{customdata[1]:,.0f}"
            "<br>Puntos MM: %{customdata[2]:,.0f}"
            "<br>Gestiones PITUTO: %{customdata[3]:,.0f}<extra></extra>"
        ),
    )
    fig.update_layout(title="Carga por ruta MULTIMARCA", xaxis_title="Carga por ruta", yaxis_title="")
    st.plotly_chart(base_figure(fig, 500), width="stretch")
    st.caption("El ranking principal exige al menos dos rutas MULTIMARCA por región.")

region_table = rt_regions[[
    "region",
    "carga_retail_trust",
    "participacion_rt_region_pct",
    "rutas_multimarca",
    "personas_multimarca_con_presencia",
    "multimarca_locales",
    "multimarca_gestiones",
    "carga_por_ruta_multimarca",
    "locales_por_ruta_multimarca",
    "gestiones_por_ruta_multimarca",
    "pituto_locales",
    "pituto_gestiones",
    "pituto_clientes",
    "pituto_carga",
]].copy()
st.dataframe(
    region_table,
    width="stretch",
    hide_index=True,
    column_config={
        "region": "Región",
        "carga_retail_trust": st.column_config.NumberColumn("Carga RT", format="%,.0f"),
        "participacion_rt_region_pct": st.column_config.NumberColumn("Peso RT", format="%.1f%%"),
        "rutas_multimarca": st.column_config.NumberColumn("Rutas MM", format="%,.0f"),
        "personas_multimarca_con_presencia": st.column_config.NumberColumn("Personas MM con presencia", format="%,.0f"),
        "multimarca_locales": st.column_config.NumberColumn("Locales MM", format="%,.0f"),
        "multimarca_gestiones": st.column_config.NumberColumn("Puntos MM", format="%,.0f"),
        "carga_por_ruta_multimarca": st.column_config.NumberColumn("Carga/ruta MM", format="%.1f"),
        "locales_por_ruta_multimarca": st.column_config.NumberColumn("Locales/ruta MM", format="%.1f"),
        "gestiones_por_ruta_multimarca": st.column_config.NumberColumn("Puntos/ruta MM", format="%.1f"),
        "pituto_locales": st.column_config.NumberColumn("Locales PITUTO", format="%,.0f"),
        "pituto_gestiones": st.column_config.NumberColumn("Gestiones PITUTO", format="%,.0f"),
        "pituto_clientes": st.column_config.NumberColumn("Clientes PITUTO", format="%,.0f"),
        "pituto_carga": st.column_config.NumberColumn("Carga PITUTO", format="%,.0f"),
    },
)

# ------------------------------------------------------------------
# 5. Tendencias mensuales
# ------------------------------------------------------------------
section_title(
    "5. Comportamiento mensual",
    "Cada mes usa el último corte disponible. PITUTO se visualiza por gestiones y locales, no por personas.",
)
left, right = st.columns(2)
with left:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly_global["mes"],
        y=monthly_global["volumen_cierre"],
        mode="lines+markers+text",
        text=monthly_global["volumen_cierre"].map(format_integer),
        textposition="top center",
        name="Último corte",
        line=dict(width=3),
    ))
    fig.add_trace(go.Scatter(
        x=monthly_global["mes"],
        y=monthly_global["volumen_promedio_semanal"],
        mode="lines+markers",
        name="Promedio semanal",
        line=dict(width=2, dash="dash"),
    ))
    fig.update_layout(title="Carga operativa total", xaxis_title="", yaxis_title="Carga")
    st.plotly_chart(base_figure(fig, 390), width="stretch")

with right:
    fig = px.line(
        monthly_services,
        x="mes",
        y="carga_corte",
        color="servicio_operativo",
        markers=True,
    )
    fig.update_layout(title="Carga por servicio", xaxis_title="", yaxis_title="Carga")
    st.plotly_chart(base_figure(fig, 390), width="stretch")

pressure_tabs = st.tabs([
    "Carga por ruta MM",
    "Locales por ruta MM",
    "Puntos por ruta MM",
    "Gestiones PITUTO",
])
pressure_fields = [
    ("carga_por_ruta_mm_corte", "Carga por ruta MULTIMARCA"),
    ("locales_por_ruta_mm_corte", "Locales por ruta MULTIMARCA"),
    ("gestiones_por_ruta_mm_corte", "Puntos por ruta MULTIMARCA"),
]
for tab, (field, title) in zip(pressure_tabs[:3], pressure_fields):
    with tab:
        fig = px.line(monthly_rt, x="mes", y=field, markers=True, text=field)
        fig.update_traces(texttemplate="%{text:.1f}", textposition="top center")
        fig.update_layout(title=title, xaxis_title="", yaxis_title=title)
        st.plotly_chart(base_figure(fig, 380), width="stretch")

with pressure_tabs[3]:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=monthly_pituto["mes"],
        y=monthly_pituto["pituto_gestiones_corte"],
        name="Gestiones",
        text=monthly_pituto["pituto_gestiones_corte"].map(format_integer),
        textposition="outside",
    ))
    fig.add_trace(go.Scatter(
        x=monthly_pituto["mes"],
        y=monthly_pituto["pituto_locales_corte"],
        mode="lines+markers+text",
        text=monthly_pituto["pituto_locales_corte"].map(format_integer),
        textposition="top center",
        name="Locales",
        line=dict(width=3),
    ))
    fig.update_layout(title="PITUTO: locales y gestiones", xaxis_title="", yaxis_title="Cantidad")
    st.plotly_chart(base_figure(fig, 380), width="stretch")

# ------------------------------------------------------------------
# 6. Lectura automática
# ------------------------------------------------------------------
section_title(
    "6. Lectura operacional basada en datos",
    "Hechos verificables; no se aplican recomendaciones ni umbrales automáticos.",
)
first_rt = monthly_rt.iloc[0]
last_rt = monthly_rt.iloc[-1]
first_pituto = monthly_pituto.iloc[0]
last_pituto = monthly_pituto.iloc[-1]
top_retail = retail.iloc[0]
top_pituto_client = pituto_clients.iloc[0]
top_pituto_region = pituto_regions.iloc[0]

fact_cols = st.columns(2)
with fact_cols[0]:
    fact_box(
        "Concentración por RETAIL",
        f"{top_retail['cadena']} concentra {format_percent(top_retail['participacion_volumen_pct'])} "
        "de la carga oficial.",
    )
    fact_box(
        "Presión MULTIMARCA",
        f"Las rutas cambian de {format_integer(first_rt['rutas_mm_corte'])} a "
        f"{format_integer(last_rt['rutas_mm_corte'])}; la carga por ruta cambia "
        f"{format_percent(safe_pct_change(last_rt['carga_por_ruta_mm_corte'], first_rt['carga_por_ruta_mm_corte']))}.",
    )
    fact_box(
        "Cobertura MULTIMARCA",
        f"Los locales por ruta cambian {format_percent(safe_pct_change(last_rt['locales_por_ruta_mm_corte'], first_rt['locales_por_ruta_mm_corte']))} "
        f"y los puntos por ruta {format_percent(safe_pct_change(last_rt['gestiones_por_ruta_mm_corte'], first_rt['gestiones_por_ruta_mm_corte']))}.",
    )
with fact_cols[1]:
    fact_box(
        "Gestión PITUTO",
        f"PITUTO registra {format_integer(pituto_summary['pituto_gestiones'])} gestiones en "
        f"{format_integer(pituto_summary['pituto_locales'])} locales. "
        "La cantidad real de personas se controla en otra base.",
    )
    fact_box(
        "Principal cliente PITUTO",
        f"{top_pituto_client['cliente']} concentra "
        f"{format_percent(top_pituto_client['participacion_gestiones_pct'])} de las gestiones PITUTO.",
    )
    fact_box(
        "Principal región PITUTO",
        f"{top_pituto_region['region']} concentra "
        f"{format_percent(top_pituto_region['participacion_gestiones_pct'])}; "
        f"las gestiones PITUTO cambian {format_percent(safe_pct_change(last_pituto['pituto_gestiones_corte'], first_pituto['pituto_gestiones_corte']))} "
        "entre el primer y último corte disponible.",
    )

# ------------------------------------------------------------------
# 7. Detalle
# ------------------------------------------------------------------
section_title("7. Respaldo de detalle")
with st.expander("PITUTO por cliente"):
    st.dataframe(pituto_clients, width="stretch", hide_index=True)
    csv_download(pituto_clients, f"pituto_cliente_{latest_period}.csv")
with st.expander("PITUTO por región"):
    st.dataframe(pituto_regions, width="stretch", hide_index=True)
    csv_download(pituto_regions, f"pituto_region_{latest_period}.csv")
with st.expander("PITUTO cliente × región"):
    st.dataframe(pituto_client_region, width="stretch", hide_index=True)
    csv_download(pituto_client_region, f"pituto_cliente_region_{latest_period}.csv")
with st.expander("Retail Trust por región"):
    st.dataframe(rt_regions, width="stretch", hide_index=True)
    csv_download(rt_regions, f"retail_trust_region_{latest_period}.csv")
with st.expander("Detalle por RETAIL"):
    st.dataframe(retail, width="stretch", hide_index=True)
    csv_download(retail, f"retail_{latest_period}.csv")
with st.expander("Detalle por servicio"):
    st.dataframe(services, width="stretch", hide_index=True)
    csv_download(services, f"servicios_{latest_period}.csv")
with st.expander("Detalle de clientes"):
    st.dataframe(clients, width="stretch", hide_index=True, height=520)
    csv_download(clients, f"clientes_{latest_period}.csv")
with st.expander("Calidad de datos"):
    st.dataframe(qa, width="stretch", hide_index=True)
    csv_download(qa, f"qa_{latest_period}.csv")
