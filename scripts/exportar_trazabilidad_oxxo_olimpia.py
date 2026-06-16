# -*- coding: utf-8 -*-
"""Exporta un paquete focalizado para analizar CASO Y CIA/OXXO y OLIMPIA/JUMBO RM."""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_VIEWS = {
    "v_rr_periodos",
    "v_rr_local_cliente_semana",
    "v_rr_persona_asignacion_semana",
    "v_rr_base_normalizada",
}


@dataclass(frozen=True)
class CaseSpec:
    code: str
    title: str
    official_sql: str
    assignment_sql: str
    params: tuple[Any, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Genera el paquete de trazabilidad CASO Y CIA/OXXO y OLIMPIA/JUMBO RM."
    )
    parser.add_argument("--db-path", type=Path, default=None)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "exports",
        help="Carpeta raíz de salida.",
    )
    parser.add_argument(
        "--focus-from",
        default="2026-05-S1",
        help="Primer período usado para detectar la ola de altas reciente.",
    )
    parser.add_argument(
        "--expected-oxxo-locals",
        type=int,
        default=14,
        help="Referencia verbal aproximada; solo se usa como contraste.",
    )
    return parser.parse_args()


def resolve_db_path(explicit: Path | None) -> Path:
    if load_dotenv is not None:
        load_dotenv(ROOT / ".env")
    raw = str(explicit) if explicit else os.getenv("RR_DB_PATH", "").strip()
    if not raw:
        raise RuntimeError("Falta RR_DB_PATH o --db-path.")
    path = Path(raw).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"No existe la base: {path}")
    return path


def connect_readonly(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True, timeout=20)
    connection.execute("PRAGMA query_only=ON;")
    connection.execute("PRAGMA busy_timeout=20000;")
    return connection


def validate_views(connection: sqlite3.Connection) -> None:
    names = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type IN ('view','table')"
        ).fetchall()
    }
    missing = sorted(REQUIRED_VIEWS - names)
    if missing:
        raise RuntimeError("Faltan vistas requeridas: " + ", ".join(missing))


def read_df(
    connection: sqlite3.Connection,
    sql: str,
    params: tuple[Any, ...] = (),
) -> pd.DataFrame:
    return pd.read_sql_query(sql, connection, params=params)


def periods_df(connection: sqlite3.Connection) -> pd.DataFrame:
    return read_df(
        connection,
        """
        SELECT period_year, period_month, period_week, period_label,
               period_order, previous_period_label, is_latest_period
        FROM v_rr_periodos
        ORDER BY period_order
        """,
    )


def build_specs() -> tuple[CaseSpec, CaseSpec]:
    oxxo = CaseSpec(
        code="OXXO",
        title="CASO Y CIA / OXXO",
        official_sql="""
            SELECT period_year, period_month, period_week, period_label,
                   period_order, cadena, cod_kpi_one, cliente, local_key,
                   local_cliente_key, local, formato, region, comuna,
                   direccion, veces_por_semana_contable, ruteros,
                   reponedores, modalidades
            FROM v_rr_local_cliente_semana
            WHERE TRIM(UPPER(cliente)) = ?
              AND TRIM(UPPER(cadena)) = ?
            ORDER BY period_order, region, comuna, local
        """,
        assignment_sql="""
            SELECT a.period_year, a.period_month, a.period_week,
                   a.period_label, a.period_order, a.modalidad, a.reponedor,
                   a.rutero, a.cadena, a.cod_kpi_one, a.cliente,
                   a.local_key, a.local_cliente_key, a.local, a.region,
                   a.comuna, a.carga_asignada, lc.formato, lc.direccion
            FROM v_rr_persona_asignacion_semana AS a
            LEFT JOIN v_rr_local_cliente_semana AS lc
              ON lc.period_label = a.period_label
             AND lc.cadena = a.cadena
             AND lc.cod_kpi_one = a.cod_kpi_one
             AND lc.cliente = a.cliente
            WHERE TRIM(UPPER(a.cliente)) = ?
              AND TRIM(UPPER(a.cadena)) = ?
            ORDER BY a.period_order, a.rutero, a.region, a.local
        """,
        params=("CASO Y CIA", "OXXO"),
    )
    olimpia = CaseSpec(
        code="OLIMPIA",
        title="OLIMPIA / JUMBO RM",
        official_sql="""
            SELECT period_year, period_month, period_week, period_label,
                   period_order, cadena, cod_kpi_one, cliente, local_key,
                   local_cliente_key, local, formato, region, comuna,
                   direccion, veces_por_semana_contable, ruteros,
                   reponedores, modalidades
            FROM v_rr_local_cliente_semana
            WHERE TRIM(UPPER(cliente)) = ?
              AND (
                    TRIM(UPPER(cadena)) LIKE '%JUMBO%'
                    OR TRIM(UPPER(formato)) LIKE '%JUMBO%'
                  )
              AND (
                    TRIM(UPPER(region)) LIKE '%RM%'
                    OR TRIM(UPPER(region)) LIKE '%METROPOLIT%'
                  )
            ORDER BY period_order, comuna, local
        """,
        assignment_sql="""
            SELECT a.period_year, a.period_month, a.period_week,
                   a.period_label, a.period_order, a.modalidad, a.reponedor,
                   a.rutero, a.cadena, a.cod_kpi_one, a.cliente,
                   a.local_key, a.local_cliente_key, a.local, a.region,
                   a.comuna, a.carga_asignada, lc.formato, lc.direccion
            FROM v_rr_persona_asignacion_semana AS a
            LEFT JOIN v_rr_local_cliente_semana AS lc
              ON lc.period_label = a.period_label
             AND lc.cadena = a.cadena
             AND lc.cod_kpi_one = a.cod_kpi_one
             AND lc.cliente = a.cliente
            WHERE TRIM(UPPER(a.cliente)) = ?
              AND (
                    TRIM(UPPER(a.cadena)) LIKE '%JUMBO%'
                    OR TRIM(UPPER(lc.formato)) LIKE '%JUMBO%'
                  )
              AND (
                    TRIM(UPPER(a.region)) LIKE '%RM%'
                    OR TRIM(UPPER(a.region)) LIKE '%METROPOLIT%'
                  )
            ORDER BY a.period_order, a.rutero, a.comuna, a.local
        """,
        params=("OLIMPIA",),
    )
    return oxxo, olimpia


def official_for_case(
    connection: sqlite3.Connection,
    spec: CaseSpec,
) -> pd.DataFrame:
    params = spec.params if spec.code == "OLIMPIA" else spec.params
    return read_df(connection, spec.official_sql, params)


def assignments_for_case(
    connection: sqlite3.Connection,
    spec: CaseSpec,
) -> pd.DataFrame:
    return read_df(connection, spec.assignment_sql, spec.params)


def first_appearance(official: pd.DataFrame) -> pd.DataFrame:
    if official.empty:
        return pd.DataFrame()
    ordered = official.sort_values(["local_key", "period_order"]).copy()
    first_rows = ordered.groupby("local_key", as_index=False).first()
    last_rows = ordered.groupby("local_key", as_index=False).last()
    activity = (
        ordered.groupby("local_key", as_index=False)
        .agg(
            semanas_activas=("period_label", "nunique"),
            frecuencia_min=("veces_por_semana_contable", "min"),
            frecuencia_max=("veces_por_semana_contable", "max"),
        )
    )
    first_rows = first_rows.rename(
        columns={
            "period_label": "primera_semana",
            "period_order": "primera_semana_orden",
            "veces_por_semana_contable": "frecuencia_inicial",
            "ruteros": "ruteros_iniciales",
            "reponedores": "reponedores_iniciales",
            "modalidades": "modalidades_iniciales",
        }
    )
    keep_first = [
        "local_key", "cadena", "cod_kpi_one", "cliente", "local", "formato",
        "region", "comuna", "direccion", "primera_semana",
        "primera_semana_orden", "frecuencia_inicial", "ruteros_iniciales",
        "reponedores_iniciales", "modalidades_iniciales",
    ]
    last_rows = last_rows.rename(
        columns={
            "period_label": "ultima_semana",
            "period_order": "ultima_semana_orden",
            "veces_por_semana_contable": "frecuencia_ultima",
            "ruteros": "ruteros_ultimos",
            "reponedores": "reponedores_ultimos",
            "modalidades": "modalidades_ultimas",
        }
    )
    keep_last = [
        "local_key", "ultima_semana", "ultima_semana_orden",
        "frecuencia_ultima", "ruteros_ultimos", "reponedores_ultimos",
        "modalidades_ultimas",
    ]
    return (
        first_rows[keep_first]
        .merge(last_rows[keep_last], on="local_key", how="left")
        .merge(activity, on="local_key", how="left")
    )


def weekly_summary(
    official: pd.DataFrame,
    assignments: pd.DataFrame,
    catastro: pd.DataFrame,
) -> pd.DataFrame:
    if official.empty:
        return pd.DataFrame()
    weekly = (
        official.groupby(
            ["period_year", "period_month", "period_week", "period_label", "period_order"],
            as_index=False,
        )
        .agg(
            locales=("local_key", "nunique"),
            puntos_gestion=("local_cliente_key", "nunique"),
            carga_oficial=("veces_por_semana_contable", "sum"),
            regiones=("region", "nunique"),
            comunas=("comuna", "nunique"),
        )
    )
    if not assignments.empty:
        assign_weekly = (
            assignments.groupby(["period_label", "period_order"], as_index=False)
            .agg(
                rutas_con_presencia=("rutero", "nunique"),
                personas_con_presencia=("reponedor", "nunique"),
                carga_asignada=("carga_asignada", "sum"),
            )
        )
        weekly = weekly.merge(assign_weekly, on=["period_label", "period_order"], how="left")
    if not catastro.empty:
        new_counts = (
            catastro.groupby(
                ["primera_semana", "primera_semana_orden"], as_index=False
            )
            .agg(locales_nuevos=("local_key", "nunique"))
            .rename(
                columns={
                    "primera_semana": "period_label",
                    "primera_semana_orden": "period_order",
                }
            )
        )
        weekly = weekly.merge(new_counts, on=["period_label", "period_order"], how="left")
    for column in ["rutas_con_presencia", "personas_con_presencia", "carga_asignada", "locales_nuevos"]:
        if column not in weekly:
            weekly[column] = 0
        weekly[column] = weekly[column].fillna(0)
    return weekly.sort_values("period_order")


def route_history(
    assignments: pd.DataFrame,
    catastro: pd.DataFrame,
) -> pd.DataFrame:
    if assignments.empty:
        return pd.DataFrame()
    result = assignments.copy()
    first_map = catastro[["local_key", "primera_semana", "primera_semana_orden"]]
    result = result.merge(first_map, on="local_key", how="left")
    result["es_alta_local"] = (
        result["period_order"] == result["primera_semana_orden"]
    ).astype(int)
    result["route_key"] = (
        result["modalidad"].fillna("SIN_MODALIDAD")
        + " | "
        + result["rutero"].fillna("SIN_RUTERO")
    )
    return result.sort_values(["period_order", "route_key", "region", "local"])


def choose_peak_period(
    catastro: pd.DataFrame,
    periods: pd.DataFrame,
    focus_from: str,
) -> dict[str, Any]:
    if catastro.empty:
        return {}
    focus_row = periods.loc[periods["period_label"] == focus_from]
    focus_order = int(focus_row.iloc[0]["period_order"]) if not focus_row.empty else int(periods["period_order"].min())
    cohorts = (
        catastro.loc[catastro["primera_semana_orden"] >= focus_order]
        .groupby(["primera_semana", "primera_semana_orden"], as_index=False)
        .agg(locales_nuevos=("local_key", "nunique"))
        .sort_values(["locales_nuevos", "primera_semana_orden"], ascending=[False, False])
    )
    if cohorts.empty:
        return {}
    peak = cohorts.iloc[0]
    peak_label = str(peak["primera_semana"])
    period_row = periods.loc[periods["period_label"] == peak_label].iloc[0]
    return {
        "peak_period": peak_label,
        "peak_order": int(peak["primera_semana_orden"]),
        "new_locals": int(peak["locales_nuevos"]),
        "previous_period": (
            None
            if pd.isna(period_row["previous_period_label"])
            else str(period_row["previous_period_label"])
        ),
        "cohorts": cohorts,
    }


def all_route_workload(connection: sqlite3.Connection) -> pd.DataFrame:
    return read_df(
        connection,
        """
        SELECT period_label, period_order, modalidad, rutero,
               COUNT(DISTINCT local_key) AS ruta_locales,
               COUNT(DISTINCT local_cliente_key) AS ruta_puntos,
               COUNT(DISTINCT cliente) AS ruta_clientes,
               SUM(carga_asignada) AS ruta_carga_asignada,
               COUNT(DISTINCT reponedor) AS ruta_personas,
               GROUP_CONCAT(DISTINCT region) AS ruta_regiones
        FROM v_rr_persona_asignacion_semana
        WHERE rutero IS NOT NULL
        GROUP BY period_label, period_order, modalidad, rutero
        ORDER BY period_order, modalidad, rutero
        """,
    )


def case_route_workload(assignments: pd.DataFrame) -> pd.DataFrame:
    if assignments.empty:
        return pd.DataFrame()
    return (
        assignments.groupby(
            ["period_label", "period_order", "modalidad", "rutero"],
            as_index=False,
        )
        .agg(
            caso_locales=("local_key", "nunique"),
            caso_puntos=("local_cliente_key", "nunique"),
            caso_carga=("carga_asignada", "sum"),
            caso_personas=("reponedor", "nunique"),
            caso_regiones=("region", lambda series: ", ".join(sorted({str(v) for v in series.dropna()}))),
        )
    )


def route_impact(
    history: pd.DataFrame,
    peak_info: dict[str, Any],
    latest_period: str,
    all_routes: pd.DataFrame,
    case_routes: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if history.empty or not peak_info:
        return pd.DataFrame(), pd.DataFrame()
    peak = peak_info["peak_period"]
    previous = peak_info["previous_period"]
    new_rows = history.loc[
        (history["period_label"] == peak) & (history["es_alta_local"] == 1)
    ].copy()
    impacted = (
        new_rows.groupby(["modalidad", "rutero"], as_index=False)
        .agg(
            nuevos_locales_peak=("local_key", "nunique"),
            nuevas_regiones=("region", lambda s: ", ".join(sorted({str(v) for v in s.dropna()}))),
            nuevas_comunas=("comuna", lambda s: ", ".join(sorted({str(v) for v in s.dropna()}))),
            reponedores_peak=("reponedor", lambda s: ", ".join(sorted({str(v) for v in s.dropna()}))),
        )
    )
    if impacted.empty:
        return pd.DataFrame(), pd.DataFrame()
    periods_keep = [value for value in [previous, peak, latest_period] if value]
    impacted_keys = set(zip(impacted["modalidad"], impacted["rutero"]))
    total_detail = all_routes.loc[
        all_routes["period_label"].isin(periods_keep)
        & all_routes.apply(lambda row: (row["modalidad"], row["rutero"]) in impacted_keys, axis=1)
    ].copy()
    case_detail = case_routes.loc[
        case_routes["period_label"].isin(periods_keep)
        & case_routes.apply(lambda row: (row["modalidad"], row["rutero"]) in impacted_keys, axis=1)
    ].copy()
    detail = total_detail.merge(
        case_detail,
        on=["period_label", "period_order", "modalidad", "rutero"],
        how="left",
    )
    for column in ["caso_locales", "caso_puntos", "caso_carga", "caso_personas"]:
        detail[column] = detail[column].fillna(0)

    metrics = [
        "ruta_locales", "ruta_puntos", "ruta_clientes", "ruta_carga_asignada",
        "caso_locales", "caso_puntos", "caso_carga",
    ]
    wide_parts: list[pd.DataFrame] = []
    labels = {previous: "pre", peak: "peak", latest_period: "latest"}
    for period_label, suffix in labels.items():
        if not period_label:
            continue
        subset = detail.loc[detail["period_label"] == period_label, ["modalidad", "rutero"] + metrics].copy()
        subset = subset.rename(columns={metric: f"{metric}_{suffix}" for metric in metrics})
        wide_parts.append(subset)
    impact = impacted.copy()
    for part in wide_parts:
        impact = impact.merge(part, on=["modalidad", "rutero"], how="left")
    numeric_columns = [column for column in impact.columns if any(column.startswith(prefix) for prefix in metrics)]
    impact[numeric_columns] = impact[numeric_columns].fillna(0)
    for metric in metrics:
        if f"{metric}_peak" in impact and f"{metric}_pre" in impact:
            impact[f"delta_{metric}_pre_peak"] = impact[f"{metric}_peak"] - impact[f"{metric}_pre"]
        if f"{metric}_latest" in impact and f"{metric}_pre" in impact:
            impact[f"delta_{metric}_pre_latest"] = impact[f"{metric}_latest"] - impact[f"{metric}_pre"]
    impact = impact.sort_values(
        ["nuevos_locales_peak", "delta_ruta_carga_asignada_pre_peak"],
        ascending=[False, False],
    )
    return impact, detail.sort_values(["modalidad", "rutero", "period_order"])


def build_case(
    connection: sqlite3.Connection,
    spec: CaseSpec,
    periods: pd.DataFrame,
    focus_from: str,
    latest_period: str,
    all_routes: pd.DataFrame,
) -> dict[str, Any]:
    official = official_for_case(connection, spec)
    assignments = assignments_for_case(connection, spec)
    catastro = first_appearance(official)
    weekly = weekly_summary(official, assignments, catastro)
    history = route_history(assignments, catastro)
    peak = choose_peak_period(catastro, periods, focus_from)
    cohorts = peak.get("cohorts", pd.DataFrame()) if peak else pd.DataFrame()
    case_routes = case_route_workload(assignments)
    impact, route_detail = route_impact(
        history,
        peak,
        latest_period,
        all_routes,
        case_routes,
    )
    if not catastro.empty:
        catastro["activo_ultimo_corte"] = (
            catastro["ultima_semana"] == latest_period
        ).astype(int)
    return {
        "official": official,
        "assignments": assignments,
        "catastro": catastro,
        "weekly": weekly,
        "history": history,
        "peak": peak,
        "cohorts": cohorts,
        "impact": impact,
        "route_detail": route_detail,
    }


def write_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False, sep=";", encoding="utf-8-sig")


def build_dictionary() -> pd.DataFrame:
    rows = [
        ("carga_oficial", "Suma de MAX(VECES POR SEMANA) por LOCAL/CLIENTE."),
        ("carga_asignada", "Carga atribuida a una persona o ruta; puede duplicar una gestión compartida."),
        ("locales_nuevos", "Locales cuya primera aparición histórica ocurre en la semana."),
        ("ruta_locales", "Locales distintos asignados a la ruta considerando todos los clientes."),
        ("ruta_puntos", "LOCAL/CLIENTE distintos asignados a la ruta considerando todos los clientes."),
        ("ruta_carga_asignada", "Suma de carga asignada a la ruta considerando todos los clientes."),
        ("caso_locales", "Locales del cliente/cadena focal presentes en la ruta."),
        ("caso_carga", "Carga asignada del caso focal dentro de la ruta."),
        ("pre", "Semana inmediatamente anterior a la ola principal de altas."),
        ("peak", "Semana con mayor cantidad de altas dentro de la ventana de foco."),
        ("latest", "Último corte disponible en la base."),
        ("personas_con_presencia", "Personas distintas observadas; no se suman entre regiones."),
    ]
    return pd.DataFrame(rows, columns=["campo", "definicion"])


def markdown_summary(
    oxxo: dict[str, Any],
    olimpia: dict[str, Any],
    latest_period: str,
    expected_locals: int,
) -> str:
    o_peak = oxxo.get("peak", {})
    o_impact = oxxo.get("impact", pd.DataFrame())
    o_cat = oxxo.get("catastro", pd.DataFrame())
    o_week = oxxo.get("weekly", pd.DataFrame())
    i_peak = olimpia.get("peak", {})
    i_cat = olimpia.get("catastro", pd.DataFrame())

    actual_new = int(o_peak.get("new_locals", 0))
    routes_affected = int(o_impact[["modalidad", "rutero"]].drop_duplicates().shape[0]) if not o_impact.empty else 0
    ref_status = (
        "CONSISTENTE CON LA REFERENCIA VERBAL"
        if abs(actual_new - expected_locals) <= 1 and 4 <= routes_affected <= 5
        else "REQUIERE REVISIÓN FRENTE A LA REFERENCIA VERBAL"
    )
    latest_oxxo = o_week.loc[o_week["period_label"] == latest_period]
    latest_oxxo_locals = int(latest_oxxo.iloc[0]["locales"]) if not latest_oxxo.empty else 0
    active_oxxo = int(o_cat["activo_ultimo_corte"].sum()) if not o_cat.empty else 0

    top_routes = "Sin rutas afectadas detectadas."
    if not o_impact.empty:
        lines = []
        for _, row in o_impact.head(6).iterrows():
            lines.append(
                f"- {row['modalidad']} / {row['rutero']}: "
                f"{int(row['nuevos_locales_peak'])} locales nuevos; "
                f"Δ locales ruta pre-peak {int(row.get('delta_ruta_locales_pre_peak', 0)):+d}; "
                f"Δ puntos ruta pre-peak {int(row.get('delta_ruta_puntos_pre_peak', 0)):+d}; "
                f"Δ carga ruta pre-peak {float(row.get('delta_ruta_carga_asignada_pre_peak', 0)):+.1f}."
            )
        top_routes = "\n".join(lines)

    olimpia_peak_text = "Sin registros OLIMPIA/JUMBO RM detectados."
    if i_peak:
        olimpia_peak_text = (
            f"Mayor alta reciente: {i_peak['peak_period']} con "
            f"{i_peak['new_locals']} locales nuevos; semana previa: "
            f"{i_peak.get('previous_period') or 'N/A'}. Catastro total: {len(i_cat)} locales."
        )

    return f"""# Resumen ejecutivo de trazabilidad

Generado: {datetime.now().isoformat(timespec='seconds')}
Último corte disponible: {latest_period}

## CASO Y CIA / OXXO

- Semana con mayor alta reciente: **{o_peak.get('peak_period', 'N/A')}**.
- Semana inmediatamente anterior: **{o_peak.get('previous_period', 'N/A')}**.
- Locales nuevos detectados en la ola principal: **{actual_new}**.
- Rutas afectadas por esas altas: **{routes_affected}**.
- Contraste con referencia aproximada de {expected_locals} locales y 4–5 rutas: **{ref_status}**.
- Catastro histórico total: **{len(o_cat)} locales**.
- Locales activos en el último corte: **{active_oxxo}**.
- Locales OXXO visibles en {latest_period}: **{latest_oxxo_locals}**.

### Rutas con mayor impacto

{top_routes}

## OLIMPIA / JUMBO Región Metropolitana

{olimpia_peak_text}

## Reglas de interpretación

- La carga oficial se calcula sin duplicar LOCAL/CLIENTE.
- La carga de ruta es asignada y se usa para medir impacto operacional.
- Una misma persona puede tener presencia en más de una región.
- El paquete no recomienda inversión adicional. Sustenta la redistribución operacional y las dos rutas part-time ya definidas.
"""


def claude_prompt(summary: str) -> str:
    base_path = ROOT / "investigations" / "oxxo_olimpia" / "PROMPT_CLAUDE_BASE.md"
    base = base_path.read_text(encoding="utf-8") if base_path.exists() else "Analiza el paquete adjunto."
    return base + "\n\n---\n\n## Resumen extraído automáticamente\n\n" + summary


def manifest(
    db_path: Path,
    latest_period: str,
    focus_from: str,
    oxxo: dict[str, Any],
    olimpia: dict[str, Any],
) -> dict[str, Any]:
    def case_meta(case: dict[str, Any]) -> dict[str, Any]:
        peak = case.get("peak", {})
        impact = case.get("impact", pd.DataFrame())
        return {
            "rows_official": int(len(case.get("official", []))),
            "rows_assignments": int(len(case.get("assignments", []))),
            "locales_catastro": int(len(case.get("catastro", []))),
            "peak_period": peak.get("peak_period"),
            "previous_period": peak.get("previous_period"),
            "new_locals_peak": int(peak.get("new_locals", 0)),
            "impacted_routes": int(impact[["modalidad", "rutero"]].drop_duplicates().shape[0]) if not impact.empty else 0,
        }

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "database": str(db_path),
        "latest_period": latest_period,
        "focus_from": focus_from,
        "filters": {
            "oxxo": {"cliente": "CASO Y CIA", "cadena": "OXXO"},
            "olimpia": {
                "cliente": "OLIMPIA",
                "retail": "JUMBO por CADENA o FORMATO",
                "region": "RM o METROPOLITANA",
            },
        },
        "oxxo": case_meta(oxxo),
        "olimpia": case_meta(olimpia),
    }


def export_package(
    output_root: Path,
    db_path: Path,
    focus_from: str,
    expected_locals: int,
    periods: pd.DataFrame,
    oxxo: dict[str, Any],
    olimpia: dict[str, Any],
) -> tuple[Path, Path]:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    package_dir = output_root.expanduser().resolve() / f"trazabilidad_oxxo_olimpia_{stamp}"
    package_dir.mkdir(parents=True, exist_ok=False)
    latest_period = str(periods.loc[periods["is_latest_period"] == 1, "period_label"].iloc[0])

    summary = markdown_summary(oxxo, olimpia, latest_period, expected_locals)
    (package_dir / "00_RESUMEN_EJECUTIVO.md").write_text(summary, encoding="utf-8")
    (package_dir / "PROMPT_CLAUDE_LISTO.md").write_text(
        claude_prompt(summary),
        encoding="utf-8",
    )
    manifest_data = manifest(db_path, latest_period, focus_from, oxxo, olimpia)
    (package_dir / "00_MANIFEST.json").write_text(
        json.dumps(manifest_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    exports = {
        "01_OXXO_RESUMEN_SEMANAL.csv": oxxo["weekly"],
        "02_OXXO_ALTAS_POR_SEMANA.csv": oxxo["cohorts"],
        "03_OXXO_CATASTRO_LOCAL.csv": oxxo["catastro"],
        "04_OXXO_HISTORIAL_RUTA.csv": oxxo["history"],
        "05_OXXO_IMPACTO_RUTAS.csv": oxxo["impact"],
        "06_OXXO_CARGA_RUTA_PERIODO.csv": oxxo["route_detail"],
        "07_OLIMPIA_RESUMEN_SEMANAL.csv": olimpia["weekly"],
        "08_OLIMPIA_CATASTRO_LOCAL.csv": olimpia["catastro"],
        "09_OLIMPIA_HISTORIAL_RUTA.csv": olimpia["history"],
        "10_OLIMPIA_IMPACTO_RUTAS.csv": olimpia["impact"],
        "11_DICCIONARIO_DATOS.csv": build_dictionary(),
    }
    for filename, dataframe in exports.items():
        write_csv(dataframe, package_dir / filename)

    zip_path = package_dir.with_suffix(".zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(package_dir.iterdir()):
            archive.write(path, arcname=path.name)
    return package_dir, zip_path


def main() -> int:
    args = parse_args()
    try:
        db_path = resolve_db_path(args.db_path)
        connection = connect_readonly(db_path)
        try:
            validate_views(connection)
            periods = periods_df(connection)
            latest_period = str(
                periods.loc[periods["is_latest_period"] == 1, "period_label"].iloc[0]
            )
            all_routes = all_route_workload(connection)
            oxxo_spec, olimpia_spec = build_specs()
            oxxo = build_case(
                connection,
                oxxo_spec,
                periods,
                args.focus_from,
                latest_period,
                all_routes,
            )
            olimpia = build_case(
                connection,
                olimpia_spec,
                periods,
                args.focus_from,
                latest_period,
                all_routes,
            )
        finally:
            connection.close()

        package_dir, zip_path = export_package(
            args.output_dir,
            db_path,
            args.focus_from,
            args.expected_oxxo_locals,
            periods,
            oxxo,
            olimpia,
        )
        print("TRAZABILIDAD GENERADA")
        print(f"- carpeta: {package_dir}")
        print(f"- zip: {zip_path}")
        print(f"- OXXO locales catastro: {len(oxxo['catastro'])}")
        print(f"- OXXO semana de mayor alta: {oxxo.get('peak', {}).get('peak_period')}")
        print(f"- OXXO locales nuevos: {oxxo.get('peak', {}).get('new_locals', 0)}")
        print(f"- OXXO rutas afectadas: {len(oxxo['impact'])}")
        print(f"- OLIMPIA locales catastro: {len(olimpia['catastro'])}")
        return 0
    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
