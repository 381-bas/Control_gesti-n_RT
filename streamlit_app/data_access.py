# -*- coding: utf-8 -*-
"""Acceso read-only a la capa SQL gerencial V1 de Control de Gestión RT."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")


def get_database_path() -> Path:
    raw = os.getenv("RR_DB_PATH", "").strip()
    if not raw:
        raise RuntimeError(
            "Falta RR_DB_PATH. Copia .env.example a .env y configura la base local."
        )
    path = Path(raw).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"No existe la base SQLite configurada: {path}")
    return path


def database_version(path: Path) -> int:
    return path.stat().st_mtime_ns


def _readonly_uri(path: Path) -> str:
    return f"{path.as_uri()}?mode=ro"


@st.cache_data(ttl=300, show_spinner=False)
def query_df(
    db_path: str,
    db_version: int,
    sql: str,
    params: tuple[Any, ...] = (),
) -> pd.DataFrame:
    del db_version
    path = Path(db_path)
    connection = sqlite3.connect(_readonly_uri(path), uri=True, timeout=10)
    try:
        connection.execute("PRAGMA query_only=ON;")
        connection.execute("PRAGMA busy_timeout=10000;")
        return pd.read_sql_query(sql, connection, params=params)
    finally:
        connection.close()


def run_query(sql: str, params: Iterable[Any] = ()) -> pd.DataFrame:
    path = get_database_path()
    return query_df(
        str(path),
        database_version(path),
        sql,
        tuple(params),
    )


def get_metadata() -> pd.DataFrame:
    return run_query("SELECT * FROM v_rr_dashboard_metadata")


def get_periods() -> pd.DataFrame:
    return run_query(
        """
        SELECT
            period_label,
            period_display,
            period_order,
            month_label,
            is_latest_period
        FROM v_rr_periodos
        ORDER BY period_order DESC
        """
    )


def get_snapshot(period: str) -> pd.DataFrame:
    return run_query(
        """
        WITH retail AS (
            SELECT
                SUM(CASE WHEN ranking_volumen = 1
                    THEN participacion_volumen_pct ELSE 0 END)
                    AS concentracion_top1_retail_pct,
                SUM(CASE WHEN ranking_volumen <= 2
                    THEN participacion_volumen_pct ELSE 0 END)
                    AS concentracion_top2_retail_pct
            FROM v_rr_cadena_semanal
            WHERE period_label = ?
        ),
        region AS (
            SELECT
                SUM(CASE WHEN ranking_volumen = 1
                    THEN participacion_volumen_pct ELSE 0 END)
                    AS concentracion_top1_region_pct,
                SUM(CASE WHEN ranking_volumen <= 2
                    THEN participacion_volumen_pct ELSE 0 END)
                    AS concentracion_top2_region_pct
            FROM v_rr_region_semanal
            WHERE period_label = ?
        ),
        modalidad AS (
            SELECT
                MAX(CASE WHEN modalidad = 'MULTIMARCA'
                    THEN carga_asignada END) AS carga_multimarca,
                MAX(CASE WHEN modalidad = 'MULTIMARCA'
                    THEN personas_activas END) AS personas_multimarca,
                MAX(CASE WHEN modalidad = 'PITUTO'
                    THEN carga_asignada END) AS carga_pituto,
                MAX(CASE WHEN modalidad = 'PITUTO'
                    THEN personas_activas END) AS personas_pituto,
                SUM(carga_asignada) AS carga_asignada_total
            FROM v_rr_modalidad_semanal
            WHERE period_label = ?
        )
        SELECT
            r.*,
            retail.concentracion_top1_retail_pct,
            retail.concentracion_top2_retail_pct,
            region.concentracion_top1_region_pct,
            region.concentracion_top2_region_pct,
            modalidad.carga_multimarca,
            modalidad.personas_multimarca,
            modalidad.carga_pituto,
            modalidad.personas_pituto,
            modalidad.carga_asignada_total,
            ROUND(100.0 * modalidad.carga_multimarca
                  / NULLIF(modalidad.carga_asignada_total, 0), 4)
                AS peso_multimarca_pct,
            ROUND(100.0 * modalidad.carga_pituto
                  / NULLIF(modalidad.carga_asignada_total, 0), 4)
                AS peso_pituto_pct
        FROM v_rr_resumen_global AS r
        CROSS JOIN retail
        CROSS JOIN region
        CROSS JOIN modalidad
        WHERE r.period_label = ?
        """,
        (period, period, period, period),
    )


def get_retail(period: str) -> pd.DataFrame:
    return run_query(
        """
        SELECT
            ranking_volumen,
            cadena,
            volumen_operativo,
            participacion_volumen_pct,
            locales_activos,
            local_cliente AS puntos_gestion,
            clientes_activos,
            intensidad_servicio,
            densidad_cartera,
            volumen_por_local
        FROM v_rr_cadena_semanal
        WHERE period_label = ?
        ORDER BY ranking_volumen, cadena
        """,
        (period,),
    )


def get_modalities(period: str) -> pd.DataFrame:
    return run_query(
        """
        WITH base AS (
            SELECT *
            FROM v_rr_modalidad_semanal
            WHERE period_label = ?
              AND modalidad IN ('MULTIMARCA', 'PITUTO', 'BREDEN', 'PROPAL')
        )
        SELECT
            modalidad,
            carga_asignada,
            ROUND(100.0 * carga_asignada
                  / NULLIF(SUM(carga_asignada) OVER (), 0), 4)
                AS participacion_carga_pct,
            personas_activas,
            rutas_activas,
            locales_asignados,
            local_cliente_asignados AS puntos_gestion,
            clientes_asignados,
            carga_por_persona,
            locales_por_persona,
            carteras_por_persona
        FROM base
        ORDER BY carga_asignada DESC, modalidad
        """,
        (period,),
    )


def get_regions(period: str) -> pd.DataFrame:
    return run_query(
        """
        SELECT
            ranking_volumen,
            region,
            volumen_operativo,
            participacion_volumen_pct,
            locales_activos,
            puntos_gestion,
            clientes_activos,
            frecuencia_media_punto,
            puntos_por_local,
            clientes_por_local,
            carga_por_local
        FROM v_rr_region_semanal
        WHERE period_label = ?
        ORDER BY ranking_volumen, region
        """,
        (period,),
    )


def get_region_capacity(period: str) -> pd.DataFrame:
    return run_query(
        """
        SELECT
            ranking_volumen,
            region,
            volumen_operativo,
            participacion_volumen_pct,
            locales_activos,
            puntos_gestion,
            clientes_activos,
            rutas_estructurales,
            distribucion_presencia_rutas_pct,
            personas_estructurales,
            personas_flexibles,
            personas_con_presencia,
            carga_estructural,
            carga_flexible,
            carga_por_ruta_estructural,
            carga_flexible_por_persona,
            volumen_oficial_por_persona,
            puntos_por_persona
        FROM v_rr_region_capacidad_semanal
        WHERE period_label = ?
        ORDER BY ranking_volumen, region
        """,
        (period,),
    )


def get_monthly_capacity() -> pd.DataFrame:
    return run_query(
        """
        SELECT *
        FROM v_rr_capacidad_mensual
        ORDER BY period_year, period_month
        """
    )


def get_monthly_modalities() -> pd.DataFrame:
    return run_query(
        """
        SELECT *
        FROM v_rr_modalidad_mensual
        ORDER BY period_year, period_month, modalidad
        """
    )


def get_monthly_retail() -> pd.DataFrame:
    return run_query(
        """
        SELECT *
        FROM v_rr_retail_mensual
        ORDER BY period_year, period_month, ranking_cierre, cadena
        """
    )


def get_monthly_regions() -> pd.DataFrame:
    return run_query(
        """
        SELECT *
        FROM v_rr_region_mensual
        ORDER BY period_year, period_month, ranking_cierre, region
        """
    )


def get_clients(period: str) -> pd.DataFrame:
    return run_query(
        """
        SELECT
            ranking_volumen,
            cliente,
            volumen_operativo,
            participacion_volumen_pct,
            locales_activos,
            cadenas_activas,
            local_cliente AS puntos_gestion,
            personas_asignadas,
            rutas_asignadas,
            intensidad_servicio,
            volumen_por_local
        FROM v_rr_cliente_semanal
        WHERE period_label = ?
        ORDER BY ranking_volumen, cliente
        """,
        (period,),
    )


def get_qa(period: str) -> pd.DataFrame:
    return run_query(
        """
        SELECT severity, check_name, affected_count, detail
        FROM v_rr_dashboard_qa
        WHERE period_label = ?
        ORDER BY CASE severity
            WHEN 'ERROR' THEN 1
            WHEN 'WARN' THEN 2
            ELSE 3
        END, affected_count DESC, check_name
        """,
        (period,),
    )
