# -*- coding: utf-8 -*-
"""Acceso read-only al modelo de servicios V2."""
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
    connection = sqlite3.connect(
        _readonly_uri(Path(db_path)),
        uri=True,
        timeout=10,
    )
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
        SELECT period_label, period_display, period_order, month_label,
               is_latest_period
        FROM v_rr_periodos
        ORDER BY period_order DESC
        """
    )


def get_snapshot(period: str) -> pd.DataFrame:
    return run_query(
        "SELECT * FROM v_rr_gerencial_v2_actual WHERE period_label = ?",
        (period,),
    )


def get_retail(period: str) -> pd.DataFrame:
    return run_query(
        """
        SELECT ranking_volumen, cadena, volumen_operativo,
               participacion_volumen_pct, locales_activos,
               local_cliente AS puntos_gestion, clientes_activos,
               intensidad_servicio, densidad_cartera, volumen_por_local
        FROM v_rr_cadena_semanal
        WHERE period_label = ?
        ORDER BY ranking_volumen, cadena
        """,
        (period,),
    )


def get_services(period: str) -> pd.DataFrame:
    return run_query(
        """
        SELECT servicio_operativo, carga_servicio,
               carga_modalidades_asignada, participacion_servicio_pct,
               locales_activos, puntos_gestion, clientes_activos,
               personas_activas, codigos_ruta, rutas_multimarca,
               personas_pituto, rutas_breden, personas_propal,
               carga_por_persona, puntos_por_persona
        FROM v_rr_servicio_semanal
        WHERE period_label = ?
        ORDER BY carga_servicio DESC, servicio_operativo
        """,
        (period,),
    )


def get_rt_modalities(period: str) -> pd.DataFrame:
    return run_query(
        """
        WITH base AS (
            SELECT *
            FROM v_rr_modalidad_semanal
            WHERE period_label = ?
              AND modalidad IN ('MULTIMARCA', 'PITUTO')
        )
        SELECT modalidad, carga_asignada,
               ROUND(100.0 * carga_asignada
                 / NULLIF(SUM(carga_asignada) OVER (), 0), 4)
                 AS participacion_dentro_rt_pct,
               personas_activas, rutas_activas, locales_asignados,
               local_cliente_asignados AS puntos_gestion,
               clientes_asignados, carga_por_persona,
               locales_por_persona, carteras_por_persona
        FROM base
        ORDER BY carga_asignada DESC, modalidad
        """,
        (period,),
    )


def get_regions(period: str) -> pd.DataFrame:
    return run_query(
        """
        SELECT ranking_volumen, region, volumen_operativo,
               participacion_volumen_pct, locales_activos,
               puntos_gestion, clientes_activos, frecuencia_media_punto,
               puntos_por_local, clientes_por_local, carga_por_local
        FROM v_rr_region_semanal
        WHERE period_label = ?
        ORDER BY ranking_volumen, region
        """,
        (period,),
    )


def get_rt_region_capacity(period: str) -> pd.DataFrame:
    return run_query(
        """
        SELECT region, carga_retail_trust, participacion_rt_region_pct,
               locales_retail_trust, puntos_retail_trust,
               clientes_retail_trust, carga_multimarca, carga_pituto,
               rutas_multimarca, personas_multimarca, personas_pituto,
               personas_retail_trust, carga_por_ruta_multimarca,
               carga_pituto_por_persona, carga_rt_por_persona,
               puntos_rt_por_persona
        FROM v_rr_region_retail_trust_semanal
        WHERE period_label = ?
        ORDER BY carga_retail_trust DESC, region
        """,
        (period,),
    )


def get_monthly_global() -> pd.DataFrame:
    return run_query(
        "SELECT * FROM v_rr_capacidad_mensual ORDER BY period_year, period_month"
    )


def get_monthly_services() -> pd.DataFrame:
    return run_query(
        """
        SELECT *
        FROM v_rr_servicio_mensual
        ORDER BY period_year, period_month, carga_corte DESC
        """
    )


def get_monthly_rt() -> pd.DataFrame:
    return run_query(
        """
        SELECT *
        FROM v_rr_retail_trust_mensual
        ORDER BY period_year, period_month
        """
    )


def get_clients(period: str) -> pd.DataFrame:
    return run_query(
        """
        SELECT ranking_volumen, cliente, volumen_operativo,
               participacion_volumen_pct, locales_activos, cadenas_activas,
               local_cliente AS puntos_gestion, personas_asignadas,
               rutas_asignadas, intensidad_servicio, volumen_por_local
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
