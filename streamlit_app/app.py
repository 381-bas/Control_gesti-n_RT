# -*- coding: utf-8 -*-
"""Dashboard gerencial local · Control de Gestión RT."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data_access import (
    get_catastro,
    get_catastro_options,
    get_chain_ranking,
    get_client_ranking,
    get_database_path,
    get_growth_components,
    get_growth_detail,
    get_metadata,
    get_modality_summary,
    get_modality_trend,
    get_periods,
    get_qa,
    get_state_summary,
    get_summary,
    get_summary_trend,
)
from ui import (
    base_figure,
    csv_download,
    inject_css,
    metric,
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


@st.cache_data(show_spinner=False)
def _period_maps(periods: pd.DataFrame) -> tuple[dict[str, str], dict[str, str]]:
    label_to_display = dict(zip(periods["period_label"], periods["period_display"]))
    display_to_label = {display: label for label, display in label_to_display.items()}
    return label_to_display, display_to_label


def stop_with_database_error(exc: Exception) -> None:
    page_header(
        "Base no disponible",
        "El dashboard local requiere la base SQLite con las vistas de la Ruta 2.",
    )
    st.error(str(exc))
    st.code(
        "Copy-Item .env.example .env\n"
        "python scripts\\aplicar_vistas.py\n"
        "python -m streamlit run streamlit_app\\app.py",
        language="powershell",
    )
    st.stop()


try:
    db_path = get_database_path()
    metadata_df = get_metadata()
    periods = get_periods()
except Exception as exc:  # pragma: no cover
    stop_with_database_error(exc)

if metadata_df.empty or periods.empty:
    stop_with_database_error(RuntimeError("Las vistas gerenciales no contienen datos."))

metadata = metadata_df.iloc[0]
label_to_display, display_to_label = _period_maps(periods)
period_labels_desc = periods["period_label"].tolist()
latest_period = str(metadata["latest_period_label"])

st.sidebar.markdown("## Control de Gestión RT")
st.sidebar.caption("Dashboard gerencial · entorno local")

page = st.sidebar.radio(
    "Vista",
    [
        "Resumen gerencial",
        "Cadenas y clientes",
        "Modalidades y dotación",
        "Crecimiento y movimientos",
        "Catastro y calidad",
    ],
)

current_index = period_labels_desc.index(latest_period) if latest_period in period_labels_desc else 0
current_display = st.sidebar.selectbox(
    "Período actual",
    [label_to_display[label] for label in period_labels_desc],
    index=current_index,
)
current_period = display_to_label[current_display]
current_order = int(periods.loc[periods["period_label"] == current_period, "period_order"].iloc[0])

comparison_candidates = periods.loc[
    periods["period_order"] < current_order,
    "period_label",
].tolist()
if not comparison_candidates:
    comparison_candidates = [current_period]

previous_period = periods.loc[
    periods["period_label"] == current_period,
    "previous_period_label",
].iloc[0]
default_comparison = (
    str(previous_period)
    if pd.notna(previous_period) and str(previous_period) in comparison_candidates
    else comparison_candidates[0]
)
comparison_display = st.sidebar.selectbox(
    "Comparar contra",
    [label_to_display[label] for label in comparison_candidates],
    index=comparison_candidates.index(default_comparison),
)
comparison_period = display_to_label[comparison_display]

st.sidebar.divider()
st.sidebar.caption(f"Base: {db_path.name}")
st.sidebar.caption(f"Última carga: {metadata['ultima_carga']}")
if int(metadata["controles_error"]) == 0:
    st.sidebar.markdown('<span class="rt-status-ok">QA sin errores críticos</span>', unsafe_allow_html=True)
else:
    st.sidebar.markdown('<span class="rt-status-warn">QA requiere revisión</span>', unsafe_allow_html=True)

summary_df = get_summary(current_period, comparison_period)
if summary_df.empty:
    st.error("No existe resumen para la selección actual.")
    st.stop()
summary = summary_df.iloc[0]

if page == "Resumen gerencial":
    page_header(
        "Resumen gerencial",
        f"Fotografía {current_display} comparada con {comparison_display}.",
    )

    cols = st.columns(6)
    with cols[0]:
        metric("Volumen operativo", summary["volumen_operativo"], summary["delta_volumen_operativo"],
               help_text="Suma del máximo de frecuencia por LOCAL/CLIENTE.")
    with cols[1]:
        metric("Locales activos", summary["locales_activos"], summary["delta_locales_activos"])
    with cols[2]:
        metric("LOCAL/CLIENTE", summary["local_cliente"], summary["delta_local_cliente"])
    with cols[3]:
        metric("Clientes activos", summary["clientes_activos"], summary["delta_clientes_activos"])
    with cols[4]:
        metric("Personas activas", summary["personas_activas"], summary["delta_personas_activas"])
    with cols[5]:
        metric("Rutas activas", summary["rutas_activas"], summary["delta_rutas_activas"])

    cols = st.columns(5)
    with cols[0]:
        metric("Intensidad de servicio", summary["intensidad_servicio"], value_kind="decimal")
    with cols[1]:
        metric("Densidad de cartera", summary["densidad_cartera"], value_kind="decimal")
    with cols[2]:
        metric("Volumen por local", summary["volumen_por_local"], value_kind="decimal")
    with cols[3]:
        metric("Volumen por persona", summary["volumen_por_persona"], value_kind="decimal")
    with cols[4]:
        metric("Carteras por persona", summary["carteras_por_persona"], value_kind="decimal")

    trend = get_summary_trend()
    left, right = st.columns([1.35, 1])
    with left:
        section_title("Evolución semanal", "Selector de métrica y referencia móvil de cuatro semanas.")
        metric_options = {
            "Volumen operativo": "volumen_operativo",
            "Locales activos": "locales_activos",
            "LOCAL/CLIENTE": "local_cliente",
            "Personas activas": "personas_activas",
            "Volumen por persona": "volumen_por_persona",
        }
        selected_metric_label = st.selectbox(
            "Métrica de evolución",
            list(metric_options.keys()),
            label_visibility="collapsed",
        )
        selected_metric = metric_options[selected_metric_label]
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=trend["period_label"],
            y=trend[selected_metric],
            mode="lines+markers",
            name=selected_metric_label,
            line=dict(width=3, color="#2563eb"),
            marker=dict(size=7),
            hovertemplate="%{x}<br>%{y:,.2f}<extra></extra>",
        ))
        if selected_metric == "volumen_operativo":
            fig.add_trace(go.Scatter(
                x=trend["period_label"],
                y=trend["volumen_promedio_movil_4s"],
                mode="lines",
                name="Promedio móvil 4 semanas",
                line=dict(width=2, dash="dash", color="#94a3b8"),
                hovertemplate="%{x}<br>%{y:,.2f}<extra></extra>",
            ))
        fig.update_layout(title=selected_metric_label)
        st.plotly_chart(base_figure(fig, 420), use_container_width=True)

    with right:
        section_title("Ranking de cadenas", "Volumen oficial, ordenado de mayor a menor.")
        chains = get_chain_ranking(current_period, comparison_period)
        top_chains = chains.head(10).sort_values("volumen_operativo", ascending=True)
        fig = px.bar(
            top_chains,
            x="volumen_operativo",
            y="cadena",
            orientation="h",
            text="volumen_operativo",
            color="participacion_volumen_pct",
            color_continuous_scale="Blues",
        )
        fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        fig.update_layout(title="Top 10 cadenas", coloraxis_showscale=False)
        st.plotly_chart(base_figure(fig, 420), use_container_width=True)

    left, right = st.columns([1, 1])
    with left:
        section_title("Clientes de mayor volumen")
        clients = get_client_ranking(current_period, comparison_period)
        top_clients = clients.head(10).sort_values("volumen_operativo", ascending=True)
        fig = px.bar(
            top_clients,
            x="volumen_operativo",
            y="cliente",
            orientation="h",
            text="volumen_operativo",
            color="delta_volumen_operativo",
            color_continuous_scale="RdBu",
            color_continuous_midpoint=0,
        )
        fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
        fig.update_layout(title="Top 10 clientes", coloraxis_showscale=False)
        st.plotly_chart(base_figure(fig, 410), use_container_width=True)

    with right:
        section_title("Estructura por modalidad", "Carga asignada y personas activas no equivalen al volumen oficial.")
        modalities = get_modality_summary(current_period, comparison_period)
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=modalities["modalidad"],
            y=modalities["carga_asignada"],
            name="Carga asignada",
            marker_color="#2563eb",
            yaxis="y",
            hovertemplate="%{x}<br>Carga: %{y:,.0f}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=modalities["modalidad"],
            y=modalities["personas_activas"],
            name="Personas activas",
            mode="lines+markers",
            marker=dict(size=9, color="#f59e0b"),
            line=dict(width=3, color="#f59e0b"),
            yaxis="y2",
            hovertemplate="%{x}<br>Personas: %{y:,.0f}<extra></extra>",
        ))
        fig.update_layout(
            title="Carga asignada y personas",
            yaxis=dict(title="Carga asignada"),
            yaxis2=dict(title="Personas", overlaying="y", side="right", showgrid=False),
        )
        st.plotly_chart(base_figure(fig, 410), use_container_width=True)

    section_title("Tabla ejecutiva de cadenas")
    display_chains = chains[[
        "ranking_volumen", "cadena", "volumen_operativo", "participacion_volumen_pct",
        "delta_volumen_operativo", "delta_volumen_operativo_pct", "locales_activos",
        "local_cliente", "clientes_activos", "personas_activas", "volumen_por_persona"
    ]].copy()
    st.dataframe(
        display_chains,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ranking_volumen": st.column_config.NumberColumn("Rank", format="%d"),
            "cadena": "Cadena",
            "volumen_operativo": st.column_config.NumberColumn("Volumen", format="%,.0f"),
            "participacion_volumen_pct": st.column_config.NumberColumn("Share", format="%.1f%%"),
            "delta_volumen_operativo": st.column_config.NumberColumn("Δ volumen", format="%+.0f"),
            "delta_volumen_operativo_pct": st.column_config.NumberColumn("Δ %", format="%+.1f%%"),
            "locales_activos": st.column_config.NumberColumn("Locales", format="%,.0f"),
            "local_cliente": st.column_config.NumberColumn("LOCAL/CLIENTE", format="%,.0f"),
            "clientes_activos": st.column_config.NumberColumn("Clientes", format="%,.0f"),
            "personas_activas": st.column_config.NumberColumn("Personas", format="%,.0f"),
            "volumen_por_persona": st.column_config.NumberColumn("Vol./persona", format="%.1f"),
        },
    )
    csv_download(display_chains, f"cadenas_{current_period}.csv")

elif page == "Cadenas y clientes":
    page_header(
        "Cadenas y clientes",
        "Concentración, ranking, evolución comparativa y drilldown comercial.",
    )
    chains = get_chain_ranking(current_period, comparison_period)
    chain_options = ["Todas"] + chains["cadena"].tolist()
    selected_chain = st.selectbox("Cadena para profundizar", chain_options)
    chain_filter = None if selected_chain == "Todas" else selected_chain
    clients = get_client_ranking(current_period, comparison_period, chain_filter)

    top1_share = float(chains.iloc[0]["participacion_volumen_pct"]) if not chains.empty else 0
    top2_share = float(chains.head(2)["participacion_volumen_pct"].sum()) if not chains.empty else 0
    top5_clients_share = float(clients.head(5)["participacion_volumen_pct"].sum()) if not clients.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    with c1: metric("Top 1 cadena", top1_share, value_kind="decimal")
    with c2: metric("Concentración Top 2", top2_share, value_kind="decimal")
    with c3: metric("Clientes visibles", len(clients))
    with c4: metric("Concentración Top 5 clientes", top5_clients_share, value_kind="decimal")

    left, right = st.columns([1, 1])
    with left:
        section_title("Pareto de cadenas")
        pareto = chains.sort_values("ranking_volumen")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=pareto["cadena"], y=pareto["volumen_operativo"],
            name="Volumen", marker_color="#2563eb"
        ))
        fig.add_trace(go.Scatter(
            x=pareto["cadena"], y=pareto["participacion_acumulada_pct"],
            name="Participación acumulada", mode="lines+markers", yaxis="y2",
            line=dict(color="#f59e0b", width=3),
        ))
        fig.update_layout(
            title="Volumen y concentración acumulada",
            yaxis=dict(title="Volumen"),
            yaxis2=dict(title="Acumulado %", overlaying="y", side="right", range=[0, 105], showgrid=False),
        )
        st.plotly_chart(base_figure(fig, 430), use_container_width=True)

    with right:
        section_title("Variación de cadenas")
        variation = chains.sort_values("delta_volumen_operativo", ascending=True)
        fig = px.bar(
            variation,
            x="delta_volumen_operativo",
            y="cadena",
            orientation="h",
            color="delta_volumen_operativo",
            color_continuous_scale="RdBu",
            color_continuous_midpoint=0,
            text="delta_volumen_operativo",
        )
        fig.update_traces(texttemplate="%{text:+,.0f}", textposition="outside")
        fig.update_layout(title=f"Cambio vs. {comparison_display}", coloraxis_showscale=False)
        st.plotly_chart(base_figure(fig, 430), use_container_width=True)

    section_title(
        "Ranking de clientes" if not chain_filter else f"Clientes dentro de {chain_filter}",
        "Orden descendente por volumen operativo.",
    )
    slider_max = min(50, max(10, len(clients)))
    top_n = st.slider("Cantidad de clientes", min_value=10, max_value=slider_max, value=min(20, slider_max))
    chart_clients = clients.head(top_n).sort_values("volumen_operativo", ascending=True)
    fig = px.bar(
        chart_clients,
        x="volumen_operativo",
        y="cliente",
        orientation="h",
        color="delta_volumen_operativo",
        color_continuous_scale="RdBu",
        color_continuous_midpoint=0,
        text="volumen_operativo",
    )
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig.update_layout(title=f"Top {top_n} clientes", coloraxis_showscale=False)
    st.plotly_chart(base_figure(fig, max(430, top_n * 24)), use_container_width=True)

    st.dataframe(clients, use_container_width=True, hide_index=True)
    csv_download(clients, f"clientes_{current_period}_{chain_filter or 'todas'}.csv")

elif page == "Modalidades y dotación":
    page_header(
        "Modalidades y dotación",
        "Personas, rutas y carga estructural por modalidad.",
    )
    modalities = get_modality_summary(current_period, comparison_period)
    trend = get_modality_trend()

    total_people_modality = modalities["personas_activas"].sum()
    total_routes_modality = modalities["rutas_activas"].sum()
    total_load = modalities["carga_asignada"].sum()
    official_volume = float(summary["volumen_operativo"])

    c1, c2, c3, c4 = st.columns(4)
    with c1: metric("Personas-modalidad", total_people_modality)
    with c2: metric("Rutas por modalidad", total_routes_modality)
    with c3: metric("Carga asignada", total_load)
    with c4: metric("Diferencia vs volumen oficial", total_load - official_volume)

    st.caption("Personas-modalidad es la suma de dotación distinta dentro de cada modalidad; no reemplaza el total oficial de personas únicas.")

    selected_measure = st.selectbox(
        "Métrica para comparar modalidades",
        ["carga_asignada", "personas_activas", "locales_asignados", "local_cliente_asignados", "carga_por_persona"],
        format_func=lambda x: {
            "carga_asignada": "Carga asignada",
            "personas_activas": "Personas activas",
            "locales_asignados": "Locales asignados",
            "local_cliente_asignados": "Carteras asignadas",
            "carga_por_persona": "Carga por persona",
        }[x],
    )
    left, right = st.columns([1, 1])
    with left:
        section_title("Comparación actual")
        chart = modalities.sort_values(selected_measure, ascending=True)
        fig = px.bar(
            chart,
            x=selected_measure,
            y="modalidad",
            orientation="h",
            text=selected_measure,
            color=selected_measure,
            color_continuous_scale="Blues",
        )
        fig.update_traces(texttemplate="%{text:,.1f}", textposition="outside")
        fig.update_layout(title=selected_measure.replace("_", " ").title(), coloraxis_showscale=False)
        st.plotly_chart(base_figure(fig, 420), use_container_width=True)

    with right:
        section_title("Evolución semanal")
        trend_measure = st.selectbox(
            "Métrica temporal",
            ["personas_activas", "carga_asignada", "carga_por_persona"],
            format_func=lambda x: x.replace("_", " ").title(),
        )
        fig = px.line(
            trend,
            x="period_label",
            y=trend_measure,
            color="modalidad",
            markers=True,
        )
        fig.update_layout(title=trend_measure.replace("_", " ").title())
        st.plotly_chart(base_figure(fig, 420), use_container_width=True)

    section_title("Ratios por modalidad")
    table = modalities[[
        "modalidad", "personas_activas", "rutas_activas", "locales_asignados",
        "local_cliente_asignados", "clientes_asignados", "carga_asignada",
        "carga_por_persona", "locales_por_persona", "carteras_por_persona",
        "delta_personas_activas", "delta_carga_asignada", "delta_carga_asignada_pct"
    ]]
    st.dataframe(table, use_container_width=True, hide_index=True)
    csv_download(table, f"modalidades_{current_period}.csv")

elif page == "Crecimiento y movimientos":
    page_header(
        "Crecimiento y movimientos",
        f"Explicación de la variación entre {comparison_display} y {current_display}.",
    )
    components = get_growth_components(current_period, comparison_period)
    component_map = {
        row["tipo_movimiento"]: row for _, row in components.iterrows()
    }

    c1, c2, c3, c4, c5 = st.columns(5)
    for col, movement, label in zip(
        [c1, c2, c3, c4, c5],
        ["NUEVO", "RETIRADO", "AUMENTA_FRECUENCIA", "DISMINUYE_FRECUENCIA", "SIN_CAMBIO"],
        ["Nuevos", "Retirados", "Aumentos de frecuencia", "Disminuciones", "Sin cambio"],
    ):
        with col:
            row = component_map.get(movement)
            metric(label, 0 if row is None else row["casos"],
                   0 if row is None else row["efecto_volumen"])

    ordered = ["NUEVO", "AUMENTA_FRECUENCIA", "DISMINUYE_FRECUENCIA", "RETIRADO"]
    values = []
    labels = []
    for movement in ordered:
        row = component_map.get(movement)
        labels.append(movement.replace("_", " ").title())
        values.append(0 if row is None else float(row["efecto_volumen"]))
    labels.append("Variación neta")
    values.append(sum(values))

    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["relative"] * 4 + ["total"],
        x=labels,
        y=values,
        text=[f"{v:+,.0f}" for v in values],
        textposition="outside",
        connector={"line": {"color": "#94a3b8"}},
        increasing={"marker": {"color": "#16a34a"}},
        decreasing={"marker": {"color": "#dc2626"}},
        totals={"marker": {"color": "#2563eb"}},
    ))
    fig.update_layout(title="Puente de variación del volumen operativo")
    st.plotly_chart(base_figure(fig, 440), use_container_width=True)

    section_title("Detalle de movimientos")
    movement_filter = st.selectbox(
        "Tipo de movimiento",
        ["TODOS", "NUEVO", "RETIRADO", "AUMENTA_FRECUENCIA", "DISMINUYE_FRECUENCIA", "SIN_CAMBIO"],
    )
    detail = get_growth_detail(current_period, comparison_period, movement_filter)
    st.dataframe(detail, use_container_width=True, hide_index=True, height=500)
    csv_download(detail, f"movimientos_{current_period}_vs_{comparison_period}.csv")

else:
    page_header(
        "Catastro y calidad",
        "Estados operativos, cobertura territorial y trazabilidad de la carga.",
    )
    options = get_catastro_options(current_period)
    f1, f2, f3 = st.columns(3)
    with f1:
        chain = st.selectbox("Cadena", ["Todas"] + options["cadenas"])
    with f2:
        region = st.selectbox("Región", ["Todas"] + options["regiones"])
    with f3:
        situation = st.selectbox("Situación", ["Todas"] + options["situaciones"])

    catastro = get_catastro(
        current_period,
        None if chain == "Todas" else chain,
        None if region == "Todas" else region,
        None if situation == "Todas" else situation,
    )
    states = get_state_summary(current_period)
    qa = get_qa(current_period)

    c1, c2, c3, c4 = st.columns(4)
    with c1: metric("Locales en catastro", len(catastro))
    with c2: metric("Volumen visible", catastro["volumen_operativo"].sum())
    with c3: metric("Personas asignadas", catastro["personas_asignadas"].sum())
    with c4: metric("Estados registrados", states["locales"].sum() if not states.empty else 0)

    left, right = st.columns([1, 1])
    with left:
        section_title("Estados operativos")
        if states["locales"].sum() > 0:
            fig = px.bar(
                states.sort_values("locales"),
                x="locales", y="estado_catastro", orientation="h",
                text="locales", color="locales", color_continuous_scale="Oranges",
            )
            fig.update_layout(title="Locales por estado", coloraxis_showscale=False)
            st.plotly_chart(base_figure(fig, 350), use_container_width=True)
        else:
            st.info("No existen estados registrados para este período.")

    with right:
        section_title("Salud de los datos")
        qa_summary = qa.groupby("severity", as_index=False)["affected_count"].sum()
        fig = px.bar(
            qa_summary,
            x="severity", y="affected_count",
            text="affected_count", color="severity",
            color_discrete_map={"ERROR": "#dc2626", "WARN": "#f59e0b", "INFO": "#2563eb"},
        )
        fig.update_layout(title="Observaciones por severidad", showlegend=False)
        st.plotly_chart(base_figure(fig, 350), use_container_width=True)

    section_title("Catastro de locales")
    st.dataframe(catastro, use_container_width=True, hide_index=True, height=480)
    csv_download(catastro, f"catastro_{current_period}.csv")

    section_title("Detalle QA")
    st.dataframe(qa, use_container_width=True, hide_index=True)
    csv_download(qa, f"qa_{current_period}.csv")
