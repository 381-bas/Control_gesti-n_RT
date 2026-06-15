# -*- coding: utf-8 -*-
"""Acceso read-only a la capa SQL gerencial de Control de Gestión RT."""
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
    """Obtiene y valida la base SQLite configurada en RR_DB_PATH."""
    raw = os.getenv("RR_DB_PATH", "").strip()
    if not raw:
        raise RuntimeError(
            "Falta RR_DB_PATH. Copia .env.example a .env y configura la ruta local."
        )
    path = Path(raw).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"No existe la base SQLite configurada: {path}")
    return path


def database_version(path: Path) -> int:
    """Firma simple para invalidar caché cuando la base se actualiza."""
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
    """Ejecuta una consulta de lectura y devuelve un DataFrame cacheado."""
    del db_version
    path = Path(db_path)
    connection = sqlite3.connect(
        _readonly_uri(path),
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
        SELECT
            period_label,
            period_display,
            period_order,
            previous_period_label,
            is_latest_period,
            month_label
        FROM v_rr_periodos
        ORDER BY period_order DESC
        """
    )


def get_summary(current_period: str, comparison_period: str) -> pd.DataFrame:
    return run_query(
        """
        WITH current AS (
            SELECT *
            FROM v_rr_resumen_global
            WHERE period_label = ?
        ),
        comparison AS (
            SELECT *
            FROM v_rr_resumen_global
            WHERE period_label = ?
        )
        SELECT
            c.*,
            p.period_label AS comparison_period_label,
            p.volumen_operativo AS volumen_operativo_comparacion,
            p.locales_activos AS locales_activos_comparacion,
            p.local_cliente AS local_cliente_comparacion,
            p.clientes_activos AS clientes_activos_comparacion,
            p.personas_activas AS personas_activas_comparacion,
            p.rutas_activas AS rutas_activas_comparacion,

            c.volumen_operativo - p.volumen_operativo AS delta_volumen_operativo,
            ROUND(100.0 * (c.volumen_operativo - p.volumen_operativo)
                  / NULLIF(p.volumen_operativo, 0), 4)
                AS delta_volumen_operativo_pct,

            c.locales_activos - p.locales_activos AS delta_locales_activos,
            ROUND(100.0 * (c.locales_activos - p.locales_activos)
                  / NULLIF(p.locales_activos, 0), 4)
                AS delta_locales_activos_pct,

            c.local_cliente - p.local_cliente AS delta_local_cliente,
            ROUND(100.0 * (c.local_cliente - p.local_cliente)
                  / NULLIF(p.local_cliente, 0), 4)
                AS delta_local_cliente_pct,

            c.clientes_activos - p.clientes_activos AS delta_clientes_activos,
            c.personas_activas - p.personas_activas AS delta_personas_activas,
            ROUND(100.0 * (c.personas_activas - p.personas_activas)
                  / NULLIF(p.personas_activas, 0), 4)
                AS delta_personas_activas_pct,
            c.rutas_activas - p.rutas_activas AS delta_rutas_activas
        FROM current AS c
        CROSS JOIN comparison AS p
        """,
        (current_period, comparison_period),
    )


def get_summary_trend() -> pd.DataFrame:
    return run_query(
        """
        SELECT
            period_label,
            period_order,
            volumen_operativo,
            locales_activos,
            local_cliente,
            clientes_activos,
            personas_activas,
            rutas_activas,
            intensidad_servicio,
            densidad_cartera,
            volumen_por_persona,
            AVG(volumen_operativo) OVER (
                ORDER BY period_order
                ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
            ) AS volumen_promedio_movil_4s
        FROM v_rr_resumen_global
        ORDER BY period_order
        """
    )


def get_chain_ranking(
    current_period: str,
    comparison_period: str,
) -> pd.DataFrame:
    return run_query(
        """
        WITH current AS (
            SELECT * FROM v_rr_cadena_semanal WHERE period_label = ?
        ),
        comparison AS (
            SELECT * FROM v_rr_cadena_semanal WHERE period_label = ?
        )
        SELECT
            c.cadena,
            c.ranking_volumen,
            c.volumen_operativo,
            c.participacion_volumen_pct,
            c.participacion_acumulada_pct,
            c.locales_activos,
            c.local_cliente,
            c.clientes_activos,
            c.personas_activas,
            c.rutas_activas,
            c.intensidad_servicio,
            c.densidad_cartera,
            c.volumen_por_local,
            c.volumen_por_persona,
            c.locales_por_persona,
            p.volumen_operativo AS volumen_comparacion,
            COALESCE(c.volumen_operativo, 0) - COALESCE(p.volumen_operativo, 0)
                AS delta_volumen_operativo,
            ROUND(100.0 * (COALESCE(c.volumen_operativo, 0)
                  - COALESCE(p.volumen_operativo, 0))
                  / NULLIF(p.volumen_operativo, 0), 4)
                AS delta_volumen_operativo_pct,
            c.locales_activos - COALESCE(p.locales_activos, 0)
                AS delta_locales_activos,
            c.local_cliente - COALESCE(p.local_cliente, 0)
                AS delta_local_cliente,
            c.personas_activas - COALESCE(p.personas_activas, 0)
                AS delta_personas_activas
        FROM current AS c
        LEFT JOIN comparison AS p ON p.cadena = c.cadena
        ORDER BY c.volumen_operativo DESC, c.cadena
        """,
        (current_period, comparison_period),
    )


def get_client_ranking(
    current_period: str,
    comparison_period: str,
    chain: str | None = None,
) -> pd.DataFrame:
    if chain:
        return run_query(
            """
            WITH current AS (
                SELECT *
                FROM v_rr_cadena_cliente_semanal
                WHERE period_label = ? AND cadena = ?
            ),
            comparison AS (
                SELECT *
                FROM v_rr_cadena_cliente_semanal
                WHERE period_label = ? AND cadena = ?
            )
            SELECT
                c.cliente,
                c.ranking_cliente_en_cadena AS ranking_volumen,
                c.volumen_operativo,
                c.participacion_en_cadena_pct AS participacion_volumen_pct,
                c.locales_activos,
                c.local_cliente,
                c.intensidad_servicio,
                p.volumen_operativo AS volumen_comparacion,
                c.volumen_operativo - COALESCE(p.volumen_operativo, 0)
                    AS delta_volumen_operativo,
                ROUND(100.0 * (c.volumen_operativo
                      - COALESCE(p.volumen_operativo, 0))
                      / NULLIF(p.volumen_operativo, 0), 4)
                    AS delta_volumen_operativo_pct
            FROM current AS c
            LEFT JOIN comparison AS p ON p.cliente = c.cliente
            ORDER BY c.volumen_operativo DESC, c.cliente
            """,
            (current_period, chain, comparison_period, chain),
        )

    return run_query(
        """
        WITH current AS (
            SELECT * FROM v_rr_cliente_semanal WHERE period_label = ?
        ),
        comparison AS (
            SELECT * FROM v_rr_cliente_semanal WHERE period_label = ?
        )
        SELECT
            c.cliente,
            c.ranking_volumen,
            c.volumen_operativo,
            c.participacion_volumen_pct,
            c.participacion_acumulada_pct,
            c.locales_activos,
            c.cadenas_activas,
            c.local_cliente,
            c.personas_asignadas,
            c.rutas_asignadas,
            c.intensidad_servicio,
            c.volumen_por_local,
            p.volumen_operativo AS volumen_comparacion,
            c.volumen_operativo - COALESCE(p.volumen_operativo, 0)
                AS delta_volumen_operativo,
            ROUND(100.0 * (c.volumen_operativo
                  - COALESCE(p.volumen_operativo, 0))
                  / NULLIF(p.volumen_operativo, 0), 4)
                AS delta_volumen_operativo_pct,
            c.locales_activos - COALESCE(p.locales_activos, 0)
                AS delta_locales_activos
        FROM current AS c
        LEFT JOIN comparison AS p ON p.cliente = c.cliente
        ORDER BY c.volumen_operativo DESC, c.cliente
        """,
        (current_period, comparison_period),
    )


def get_modality_summary(
    current_period: str,
    comparison_period: str,
) -> pd.DataFrame:
    return run_query(
        """
        WITH current AS (
            SELECT * FROM v_rr_modalidad_semanal WHERE period_label = ?
        ),
        comparison AS (
            SELECT * FROM v_rr_modalidad_semanal WHERE period_label = ?
        )
        SELECT
            c.*,
            p.personas_activas AS personas_comparacion,
            p.rutas_activas AS rutas_comparacion,
            p.locales_asignados AS locales_comparacion,
            p.local_cliente_asignados AS carteras_comparacion,
            p.carga_asignada AS carga_comparacion,
            c.personas_activas - COALESCE(p.personas_activas, 0)
                AS delta_personas_activas,
            c.rutas_activas - COALESCE(p.rutas_activas, 0)
                AS delta_rutas_activas,
            c.locales_asignados - COALESCE(p.locales_asignados, 0)
                AS delta_locales_asignados,
            c.local_cliente_asignados - COALESCE(p.local_cliente_asignados, 0)
                AS delta_local_cliente_asignados,
            c.carga_asignada - COALESCE(p.carga_asignada, 0)
                AS delta_carga_asignada,
            ROUND(100.0 * (c.carga_asignada - COALESCE(p.carga_asignada, 0))
                  / NULLIF(p.carga_asignada, 0), 4)
                AS delta_carga_asignada_pct
        FROM current AS c
        LEFT JOIN comparison AS p ON p.modalidad = c.modalidad
        ORDER BY c.carga_asignada DESC, c.modalidad
        """,
        (current_period, comparison_period),
    )


def get_modality_trend() -> pd.DataFrame:
    return run_query(
        """
        SELECT
            period_label,
            period_order,
            modalidad,
            personas_activas,
            rutas_activas,
            locales_asignados,
            local_cliente_asignados,
            carga_asignada,
            carga_por_persona
        FROM v_rr_modalidad_semanal
        ORDER BY period_order, modalidad
        """
    )


def get_growth_components(
    current_period: str,
    comparison_period: str,
) -> pd.DataFrame:
    return run_query(
        """
        WITH current AS (
            SELECT *
            FROM fact_rr_local_cliente_semana
            WHERE period_label = ?
        ),
        comparison AS (
            SELECT *
            FROM fact_rr_local_cliente_semana
            WHERE period_label = ?
        ),
        actual AS (
            SELECT
                c.cadena,
                c.cod_kpi_one,
                c.cliente,
                c.local_key,
                c.local_cliente_key,
                c.local,
                c.veces_por_semana_contable AS frecuencia_actual,
                p.veces_por_semana_contable AS frecuencia_comparacion
            FROM current AS c
            LEFT JOIN comparison AS p
              ON p.cadena = c.cadena
             AND p.cod_kpi_one = c.cod_kpi_one
             AND p.cliente = c.cliente
        ),
        retirados AS (
            SELECT
                p.cadena,
                p.cod_kpi_one,
                p.cliente,
                p.local_key,
                p.local_cliente_key,
                p.local,
                NULL AS frecuencia_actual,
                p.veces_por_semana_contable AS frecuencia_comparacion
            FROM comparison AS p
            LEFT JOIN current AS c
              ON c.cadena = p.cadena
             AND c.cod_kpi_one = p.cod_kpi_one
             AND c.cliente = p.cliente
            WHERE c.local_cliente_key IS NULL
        ),
        universo AS (
            SELECT * FROM actual
            UNION ALL
            SELECT * FROM retirados
        ),
        clasificado AS (
            SELECT
                *,
                COALESCE(frecuencia_actual, 0)
                    - COALESCE(frecuencia_comparacion, 0) AS delta_volumen,
                CASE
                    WHEN frecuencia_comparacion IS NULL
                     AND frecuencia_actual IS NOT NULL THEN 'NUEVO'
                    WHEN frecuencia_actual IS NULL
                     AND frecuencia_comparacion IS NOT NULL THEN 'RETIRADO'
                    WHEN frecuencia_actual > frecuencia_comparacion
                        THEN 'AUMENTA_FRECUENCIA'
                    WHEN frecuencia_actual < frecuencia_comparacion
                        THEN 'DISMINUYE_FRECUENCIA'
                    ELSE 'SIN_CAMBIO'
                END AS tipo_movimiento
            FROM universo
        )
        SELECT
            tipo_movimiento,
            COUNT(*) AS casos,
            SUM(delta_volumen) AS efecto_volumen,
            COUNT(DISTINCT local_key) AS locales_involucrados,
            COUNT(DISTINCT cliente) AS clientes_involucrados
        FROM clasificado
        GROUP BY tipo_movimiento
        ORDER BY CASE tipo_movimiento
            WHEN 'NUEVO' THEN 1
            WHEN 'AUMENTA_FRECUENCIA' THEN 2
            WHEN 'DISMINUYE_FRECUENCIA' THEN 3
            WHEN 'RETIRADO' THEN 4
            ELSE 5
        END
        """,
        (current_period, comparison_period),
    )


def get_growth_detail(
    current_period: str,
    comparison_period: str,
    movement: str | None = None,
) -> pd.DataFrame:
    movement_filter = "" if movement in (None, "TODOS") else "WHERE tipo_movimiento = ?"
    params: tuple[Any, ...] = (
        current_period,
        comparison_period,
    ) + (() if not movement_filter else (movement,))

    return run_query(
        f"""
        WITH current AS (
            SELECT * FROM fact_rr_local_cliente_semana WHERE period_label = ?
        ),
        comparison AS (
            SELECT * FROM fact_rr_local_cliente_semana WHERE period_label = ?
        ),
        actual AS (
            SELECT
                c.cadena,
                c.cod_kpi_one,
                c.local,
                c.cliente,
                c.veces_por_semana_contable AS frecuencia_actual,
                p.veces_por_semana_contable AS frecuencia_comparacion,
                c.ruteros AS ruteros_actual,
                p.ruteros AS ruteros_comparacion,
                c.reponedores AS reponedores_actual,
                p.reponedores AS reponedores_comparacion,
                c.modalidades AS modalidades_actual,
                p.modalidades AS modalidades_comparacion
            FROM current AS c
            LEFT JOIN comparison AS p
              ON p.cadena = c.cadena
             AND p.cod_kpi_one = c.cod_kpi_one
             AND p.cliente = c.cliente
        ),
        retirados AS (
            SELECT
                p.cadena,
                p.cod_kpi_one,
                p.local,
                p.cliente,
                NULL AS frecuencia_actual,
                p.veces_por_semana_contable AS frecuencia_comparacion,
                NULL AS ruteros_actual,
                p.ruteros AS ruteros_comparacion,
                NULL AS reponedores_actual,
                p.reponedores AS reponedores_comparacion,
                NULL AS modalidades_actual,
                p.modalidades AS modalidades_comparacion
            FROM comparison AS p
            LEFT JOIN current AS c
              ON c.cadena = p.cadena
             AND c.cod_kpi_one = p.cod_kpi_one
             AND c.cliente = p.cliente
            WHERE c.local_cliente_key IS NULL
        ),
        universo AS (
            SELECT * FROM actual
            UNION ALL
            SELECT * FROM retirados
        ),
        clasificado AS (
            SELECT
                *,
                COALESCE(frecuencia_actual, 0)
                    - COALESCE(frecuencia_comparacion, 0) AS delta_volumen,
                CASE
                    WHEN frecuencia_comparacion IS NULL
                     AND frecuencia_actual IS NOT NULL THEN 'NUEVO'
                    WHEN frecuencia_actual IS NULL
                     AND frecuencia_comparacion IS NOT NULL THEN 'RETIRADO'
                    WHEN frecuencia_actual > frecuencia_comparacion
                        THEN 'AUMENTA_FRECUENCIA'
                    WHEN frecuencia_actual < frecuencia_comparacion
                        THEN 'DISMINUYE_FRECUENCIA'
                    ELSE 'SIN_CAMBIO'
                END AS tipo_movimiento
            FROM universo
        )
        SELECT *
        FROM clasificado
        {movement_filter}
        ORDER BY ABS(delta_volumen) DESC, cadena, cliente, cod_kpi_one
        """,
        params,
    )


def get_catastro(
    period: str,
    chain: str | None = None,
    region: str | None = None,
    situation: str | None = None,
) -> pd.DataFrame:
    filters = ["period_label = ?"]
    params: list[Any] = [period]
    if chain:
        filters.append("cadena = ?")
        params.append(chain)
    if region:
        filters.append("region = ?")
        params.append(region)
    if situation:
        filters.append("situacion_catastro = ?")
        params.append(situation)

    return run_query(
        f"""
        SELECT *
        FROM v_rr_catastro_local_semana
        WHERE {' AND '.join(filters)}
        ORDER BY volumen_operativo DESC, cadena, local
        """,
        params,
    )


def get_catastro_options(period: str) -> dict[str, list[str]]:
    df = run_query(
        """
        SELECT cadena, region, situacion_catastro
        FROM v_rr_catastro_local_semana
        WHERE period_label = ?
        """,
        (period,),
    )
    return {
        "cadenas": sorted(df["cadena"].dropna().unique().tolist()),
        "regiones": sorted(df["region"].dropna().unique().tolist()),
        "situaciones": sorted(df["situacion_catastro"].dropna().unique().tolist()),
    }


def get_state_summary(period: str) -> pd.DataFrame:
    return run_query(
        """
        SELECT estado_catastro, locales
        FROM v_rr_catastro_estado_resumen
        WHERE period_label = ?
        ORDER BY locales DESC, estado_catastro
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
