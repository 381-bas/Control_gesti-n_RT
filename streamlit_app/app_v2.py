# -*- coding: utf-8 -*-
"""Página gerencial V2 · servicios operativos y capacidad Retail Trust."""
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
    get_monthly_rt,
    get_monthly_services,
    get_periods,
    get_qa,
    get_regions,
    get_retail,
    get_rt_modalities,
    get_rt_region_capacity,
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
        "La página local requiere el modelo de servicios V2 aplicado.",
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


def kpi_card(
    label: str,
    value: object,
    note: str,
    *,
    decimals: int = 0,
    suffix: str = "",
) -> None:
    rendered = (
        format_integer(value)
        if decimals == 0
        else format_decimal(value, decimals)
    )
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
    services = get_services(latest_period)
    rt_modalities = get_rt_modalities(latest_period)
    regions = get_regions(latest_period)
    rt_regions = get_rt_region_capacity(latest_period)
    monthly_global = get_monthly_global()
    monthly_services = get_monthly_services()
    monthly_rt = get_monthly_rt()
    clients = get_clients(latest_period)
    qa = get_qa(latest_period)
except Exception as exc:  # pragma: no cover
    stop_with_database_error(exc)

if snapshot_df.empty:
    stop_with_database_error(RuntimeError("No existe fotografía gerencial V2."))

snapshot = snapshot_df.iloc[0]
for dataframe in (monthly_global, monthly_services, monthly_rt):
    dataframe["mes"] = dataframe["period_month"].map(MONTH_NAMES)

service_index = services.set_index("servicio_operativo")
rt_service = service_index.loc["RETAIL TRUST"]
breden_service = service_index.loc["BREDEN MASTER"]
propal_service = service_index.loc["PROPAL"]
rt_modality_index = rt_modalities.set_index("modalidad")
multimarca = rt_modality_index.loc["MULTIMARCA"]
pituto = rt_modality_index.loc["PITUTO"]

st.sidebar.markdown("## Control de Gestión RT")
st.sidebar.caption("Modelo de servicios V2 · entorno local")
st.sidebar.markdown(f"**Fotografía actual**  \n{period_display}")
st.sidebar.caption(f"Última carga: {metadata['ultima_carga']}")
st.sidebar.caption(f"Fuente: {db_path.name}")
st.sidebar.divider()
st.sidebar.markdown("**Servicios**")
st.sidebar.caption(
    "Retail Trust agrupa MULTIMARCA y PITUTO. "
    "Breden Master y Propal se analizan como servicios independientes."
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
    f"Situación global actual al corte de {period_display}. "
    "Retail Trust, Breden Master y Propal se muestran como servicios distintos.",
)

section_title(
    "1. Situación operativa actual",
    "El total empresa incluye todos los servicios; la capacidad RT agrupa MULTIMARCA y PITUTO.",
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
    kpi_card("Dotación total", snapshot["personas_activas"], "Personas distintas de todos los servicios")
with cols[5]:
    kpi_card("Dotación Retail Trust", snapshot["personas_retail_trust"], "MULTIMARCA + PITUTO")

st.markdown("<div style='height:.45rem'></div>", unsafe_allow_html=True)
service_cols = st.columns(5)
with service_cols[0]:
    kpi_card("Peso Retail Trust", snapshot["peso_retail_trust_pct"], "Carga contable por servicio", decimals=1, suffix="%")
with service_cols[1]:
    kpi_card("Peso Breden Master", snapshot["peso_breden_master_pct"], "Servicio independiente", decimals=1, suffix="%")
with service_cols[2]:
    kpi_card("Peso Propal", snapshot["peso_propal_pct"], "Servicio independiente", decimals=1, suffix="%")
with service_cols[3]:
    kpi_card("MULTIMARCA dentro de RT", snapshot["peso_multimarca_dentro_rt_pct"], "Carga asignada RT", decimals=1, suffix="%")
with service_cols[4]:
    kpi_card("PITUTO dentro de RT", snapshot["peso_pituto_dentro_rt_pct"], "Carga asignada RT", decimals=1, suffix="%")

section_title(
    "2. Concentración por RETAIL y servicio",
    "RETAIL usa carga oficial. Servicio usa carga contable deduplicada dentro de cada servicio.",
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
    service_chart = services.sort_values("carga_servicio", ascending=True).copy()
    service_chart["etiqueta"] = service_chart.apply(
        lambda row: f"{format_integer(row['carga_servicio'])} | "
        f"{format_percent(row['participacion_servicio_pct'])}",
        axis=1,
    )
    fig = px.bar(
        service_chart,
        x="carga_servicio",
        y="servicio_operativo",
        orientation="h",
        text="etiqueta",
        custom_data=["participacion_servicio_pct", "personas_activas", "locales_activos", "puntos_gestion"],
    )
    fig.update_traces(
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>Carga servicio: %{x:,.0f}"
            "<br>Peso: %{customdata[0]:.1f}%<br>Personas: %{customdata[1]:,.0f}"
            "<br>Locales: %{customdata[2]:,.0f}<br>Puntos: %{customdata[3]:,.0f}<extra></extra>"
        ),
    )
    fig.update_layout(title="Peso contable por servicio", xaxis_title="Carga del servicio", yaxis_title="")
    st.plotly_chart(base_figure(fig, 310), width="stretch")
    service_table = services[[
        "servicio_operativo", "carga_servicio", "participacion_servicio_pct",
        "personas_activas", "locales_activos", "puntos_gestion",
    ]].copy()
    st.dataframe(
        service_table,
        width="stretch",
        hide_index=True,
        column_config={
            "servicio_operativo": "Servicio",
            "carga_servicio": st.column_config.NumberColumn("Carga", format="%,.0f"),
            "participacion_servicio_pct": st.column_config.NumberColumn("Peso", format="%.1f%%"),
            "personas_activas": st.column_config.NumberColumn("Personas", format="%,.0f"),
            "locales_activos": st.column_config.NumberColumn("Locales", format="%,.0f"),
            "puntos_gestion": st.column_config.NumberColumn("Puntos", format="%,.0f"),
        },
    )

section_title(
    "3. Servicio Retail Trust: MULTIMARCA y PITUTO",
    "Ambas modalidades conforman el servicio de reposición de mercaderistas de Retail Trust.",
)
rt_cards = st.columns(4)
with rt_cards[0]:
    kpi_card("Carga Retail Trust", rt_service["carga_servicio"], "Carga deduplicada del servicio")
with rt_cards[1]:
    kpi_card("Personas Retail Trust", rt_service["personas_activas"], "Dotación distinta MM + PITUTO")
with rt_cards[2]:
    kpi_card("Rutas MULTIMARCA", rt_service["rutas_multimarca"], "Estructura permanente")
with rt_cards[3]:
    kpi_card("Personas PITUTO", rt_service["personas_pituto"], "Capacidad flexible")

left, right = st.columns(2)
with left:
    modality_chart = rt_modalities.sort_values("carga_asignada", ascending=True).copy()
    modality_chart["etiqueta"] = modality_chart.apply(
        lambda row: f"{format_integer(row['carga_asignada'])} | "
        f"{format_percent(row['participacion_dentro_rt_pct'])}",
        axis=1,
    )
    fig = px.bar(
        modality_chart,
        x="carga_asignada",
        y="modalidad",
        orientation="h",
        text="etiqueta",
        custom_data=["personas_activas", "locales_asignados", "puntos_gestion", "carga_por_persona"],
    )
    fig.update_traces(
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>Carga asignada: %{x:,.0f}"
            "<br>Personas: %{customdata[0]:,.0f}<br>Locales: %{customdata[1]:,.0f}"
            "<br>Puntos: %{customdata[2]:,.0f}<br>Carga/persona: %{customdata[3]:.1f}<extra></extra>"
        ),
    )
    fig.update_layout(title="Composición de carga dentro de Retail Trust", xaxis_title="Carga asignada", yaxis_title="")
    st.plotly_chart(base_figure(fig, 330), width="stretch")

with right:
    rt_table = rt_modalities[[
        "modalidad", "carga_asignada", "participacion_dentro_rt_pct",
        "personas_activas", "rutas_activas", "locales_asignados",
        "puntos_gestion", "carga_por_persona",
    ]].copy()
    st.dataframe(
        rt_table,
        width="stretch",
        hide_index=True,
        column_config={
            "modalidad": "Modalidad RT",
            "carga_asignada": st.column_config.NumberColumn("Carga", format="%,.0f"),
            "participacion_dentro_rt_pct": st.column_config.NumberColumn("Peso RT", format="%.1f%%"),
            "personas_activas": st.column_config.NumberColumn("Personas", format="%,.0f"),
            "rutas_activas": st.column_config.NumberColumn("Códigos ruta", format="%,.0f"),
            "locales_asignados": st.column_config.NumberColumn("Locales", format="%,.0f"),
            "puntos_gestion": st.column_config.NumberColumn("Puntos", format="%,.0f"),
            "carga_por_persona": st.column_config.NumberColumn("Carga/persona", format="%.1f"),
        },
    )
    st.caption(
        "La carga interna por modalidad es asignada. La carga consolidada de Retail Trust "
        "deduplica LOCAL/CLIENTE compartidos entre MULTIMARCA y PITUTO."
    )

section_title(
    "4. Distribución territorial y capacidad Retail Trust",
    "El peso regional de la izquierda corresponde al total empresa; la capacidad de la derecha solo a Retail Trust.",
)
left, right = st.columns([1.25, 1])
with left:
    top_regions = regions.head(8).copy()
    if len(regions) > 8:
        others = pd.DataFrame({
            "region": ["OTRAS REGIONES"],
            "volumen_operativo": [regions.iloc[8:]["volumen_operativo"].sum()],
            "participacion_volumen_pct": [regions.iloc[8:]["participacion_volumen_pct"].sum()],
            "locales_activos": [regions.iloc[8:]["locales_activos"].sum()],
            "puntos_gestion": [regions.iloc[8:]["puntos_gestion"].sum()],
            "clientes_activos": [regions.iloc[8:]["clientes_activos"].max()],
        })
        top_regions = pd.concat([top_regions, others], ignore_index=True)
    top_regions = top_regions.sort_values("volumen_operativo", ascending=True)
    top_regions["etiqueta"] = top_regions.apply(
        lambda row: f"{format_integer(row['volumen_operativo'])} | "
        f"{format_percent(row['participacion_volumen_pct'])}",
        axis=1,
    )
    fig = px.bar(
        top_regions,
        x="volumen_operativo",
        y="region",
        orientation="h",
        text="etiqueta",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(title="Peso operativo por región", xaxis_title="Carga oficial", yaxis_title="")
    st.plotly_chart(base_figure(fig, 500), width="stretch")

with right:
    capacity_chart = rt_regions.loc[rt_regions["rutas_multimarca"] >= 2].copy()
    if capacity_chart.empty:
        capacity_chart = rt_regions.dropna(subset=["carga_por_ruta_multimarca"]).copy()
    capacity_chart = capacity_chart.sort_values("carga_por_ruta_multimarca", ascending=True)
    fig = px.bar(
        capacity_chart,
        x="carga_por_ruta_multimarca",
        y="region",
        orientation="h",
        text="carga_por_ruta_multimarca",
        custom_data=["rutas_multimarca", "carga_multimarca", "personas_pituto", "puntos_retail_trust"],
    )
    fig.update_traces(
        texttemplate="%{text:.1f}",
        textposition="outside",
        hovertemplate=(
            "<b>%{y}</b><br>Carga por ruta MM: %{x:.1f}"
            "<br>Rutas MM: %{customdata[0]:,.0f}<br>Carga MM: %{customdata[1]:,.0f}"
            "<br>Personas PITUTO: %{customdata[2]:,.0f}<br>Puntos RT: %{customdata[3]:,.0f}<extra></extra>"
        ),
    )
    fig.update_layout(
        title="Carga por ruta MULTIMARCA",
        xaxis_title="Carga asignada por ruta",
        yaxis_title="",
    )
    st.plotly_chart(base_figure(fig, 500), width="stretch")
    st.caption("La visual principal exige al menos dos rutas MULTIMARCA por región para reducir distorsiones por base mínima.")

rt_region_table = rt_regions[[
    "region", "carga_retail_trust", "participacion_rt_region_pct",
    "locales_retail_trust", "puntos_retail_trust", "clientes_retail_trust",
    "rutas_multimarca", "personas_multimarca", "personas_pituto",
    "carga_por_ruta_multimarca", "carga_pituto_por_persona",
    "puntos_rt_por_persona",
]].copy()
st.dataframe(
    rt_region_table,
    width="stretch",
    hide_index=True,
    column_config={
        "region": "Región",
        "carga_retail_trust": st.column_config.NumberColumn("Carga RT", format="%,.0f"),
        "participacion_rt_region_pct": st.column_config.NumberColumn("Peso RT", format="%.1f%%"),
        "locales_retail_trust": st.column_config.NumberColumn("Locales RT", format="%,.0f"),
        "puntos_retail_trust": st.column_config.NumberColumn("Puntos RT", format="%,.0f"),
        "clientes_retail_trust": st.column_config.NumberColumn("Clientes RT", format="%,.0f"),
        "rutas_multimarca": st.column_config.NumberColumn("Rutas MM", format="%,.0f"),
        "personas_multimarca": st.column_config.NumberColumn("Personas MM", format="%,.0f"),
        "personas_pituto": st.column_config.NumberColumn("Personas PITUTO", format="%,.0f"),
        "carga_por_ruta_multimarca": st.column_config.NumberColumn("Carga/ruta MM", format="%.1f"),
        "carga_pituto_por_persona": st.column_config.NumberColumn("Carga PITUTO/persona", format="%.1f"),
        "puntos_rt_por_persona": st.column_config.NumberColumn("Puntos/persona RT", format="%.1f"),
    },
)

section_title(
    "5. Comportamiento mensual",
    "Cada mes usa su último corte disponible; la línea secundaria global muestra el promedio semanal del mes.",
)
left, right = st.columns([1.1, 1])
with left:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly_global["mes"],
        y=monthly_global["volumen_cierre"],
        mode="lines+markers+text",
        text=monthly_global["volumen_cierre"].map(format_integer),
        textposition="top center",
        name="Último corte del mes",
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
        text="carga_corte",
    )
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="top center")
    fig.update_layout(title="Carga contable por servicio", xaxis_title="", yaxis_title="Carga")
    st.plotly_chart(base_figure(fig, 390), width="stretch")

left, right = st.columns(2)
with left:
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=monthly_rt["mes"],
        y=monthly_rt["carga_multimarca_corte"],
        name="MULTIMARCA",
    ))
    fig.add_trace(go.Bar(
        x=monthly_rt["mes"],
        y=monthly_rt["carga_pituto_corte"],
        name="PITUTO",
    ))
    fig.update_layout(title="Retail Trust: carga asignada", barmode="stack", xaxis_title="", yaxis_title="Carga")
    st.plotly_chart(base_figure(fig, 380), width="stretch")

with right:
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly_rt["mes"],
        y=monthly_rt["personas_multimarca_corte"],
        mode="lines+markers+text",
        text=monthly_rt["personas_multimarca_corte"].map(format_integer),
        textposition="top center",
        name="MULTIMARCA",
        line=dict(width=3),
    ))
    fig.add_trace(go.Scatter(
        x=monthly_rt["mes"],
        y=monthly_rt["personas_pituto_corte"],
        mode="lines+markers+text",
        text=monthly_rt["personas_pituto_corte"].map(format_integer),
        textposition="bottom center",
        name="PITUTO",
        line=dict(width=3),
    ))
    fig.update_layout(title="Retail Trust: dotación por modalidad", xaxis_title="", yaxis_title="Personas")
    st.plotly_chart(base_figure(fig, 380), width="stretch")

section_title(
    "6. Lectura operacional basada en datos",
    "Hechos automáticos para revisar capacidad. No se aplican recomendaciones ni umbrales.",
)
first_month = monthly_global.iloc[0]
last_month = monthly_global.iloc[-1]
rt_first = monthly_rt.iloc[0]
rt_last = monthly_rt.iloc[-1]
top_retail = retail.iloc[0]
top_region = regions.iloc[0]

eligible_pressure = rt_regions.loc[rt_regions["rutas_multimarca"] >= 2].dropna(
    subset=["carga_por_ruta_multimarca"]
)
if eligible_pressure.empty:
    eligible_pressure = rt_regions.dropna(subset=["carga_por_ruta_multimarca"])
top_pressure = eligible_pressure.sort_values("carga_por_ruta_multimarca", ascending=False).iloc[0]

load_change = safe_pct_change(last_month["volumen_cierre"], first_month["volumen_cierre"])
local_change = safe_pct_change(last_month["locales_cierre"], first_month["locales_cierre"])
point_change = safe_pct_change(last_month["local_cliente_cierre"], first_month["local_cliente_cierre"])
mm_people_change = int(rt_last["personas_multimarca_corte"] - rt_first["personas_multimarca_corte"])

fact_cols = st.columns(2)
with fact_cols[0]:
    fact_box(
        "Concentración por RETAIL",
        f"{top_retail['cadena']} concentra {format_percent(top_retail['participacion_volumen_pct'])} "
        f"de la carga oficial. Las dos principales cadenas reúnen "
        f"{format_percent(snapshot['concentracion_top2_retail_pct'])}.",
    )
    fact_box(
        "Expansión de la operación",
        f"Entre {MONTH_NAMES[int(first_month['period_month'])]} y "
        f"{MONTH_NAMES[int(last_month['period_month'])]}, los locales cambian "
        f"{format_percent(local_change)}, los puntos {format_percent(point_change)} "
        f"y la carga {format_percent(load_change)}.",
    )
    fact_box(
        "Retail Trust",
        f"El servicio reúne {format_integer(rt_service['personas_activas'])} personas: "
        f"{format_integer(multimarca['personas_activas'])} MULTIMARCA y "
        f"{format_integer(pituto['personas_activas'])} PITUTO. La dotación MULTIMARCA "
        f"cambia en {mm_people_change:+d} persona(s) entre el primer y último corte disponible.",
    )
with fact_cols[1]:
    fact_box(
        "Servicios independientes",
        f"Breden Master opera con {format_integer(breden_service['personas_activas'])} personas "
        f"y {format_integer(breden_service['rutas_breden'])} rutas. Propal opera con "
        f"{format_integer(propal_service['personas_activas'])} personas. Ninguno se incorpora "
        "a la presión de rutas de Retail Trust.",
    )
    fact_box(
        "Concentración regional",
        f"{top_region['region']} representa {format_percent(top_region['participacion_volumen_pct'])} "
        "de la carga total de la empresa.",
    )
    fact_box(
        "Capacidad MULTIMARCA",
        f"Entre las regiones con al menos dos rutas, {top_pressure['region']} presenta la mayor "
        f"carga por ruta MULTIMARCA: {format_decimal(top_pressure['carga_por_ruta_multimarca'], 1)}, "
        f"con {format_integer(top_pressure['rutas_multimarca'])} rutas con presencia.",
    )

section_title("7. Respaldo de detalle")
with st.expander("Detalle por RETAIL"):
    st.dataframe(retail, width="stretch", hide_index=True)
    csv_download(retail, f"retail_{latest_period}.csv")
with st.expander("Detalle por servicio"):
    st.dataframe(services, width="stretch", hide_index=True)
    csv_download(services, f"servicios_{latest_period}.csv")
with st.expander("Detalle Retail Trust por modalidad"):
    st.dataframe(rt_modalities, width="stretch", hide_index=True)
    csv_download(rt_modalities, f"retail_trust_modalidad_{latest_period}.csv")
with st.expander("Detalle Retail Trust por región"):
    st.dataframe(rt_regions, width="stretch", hide_index=True)
    csv_download(rt_regions, f"retail_trust_region_{latest_period}.csv")
with st.expander("Detalle de clientes"):
    st.dataframe(clients, width="stretch", hide_index=True, height=520)
    csv_download(clients, f"clientes_{latest_period}.csv")
with st.expander("Calidad de datos"):
    st.dataframe(qa, width="stretch", hide_index=True)
    csv_download(qa, f"qa_{latest_period}.csv")
