# -*- coding: utf-8 -*-
"""Acceso read-only al modelo V2.1 con PITUTO medido por gestión."""
from __future__ import annotations

import pandas as pd

from data_access_v2 import *  # noqa: F401,F403
from data_access_v2 import run_query


def get_snapshot(period: str) -> pd.DataFrame:
    return run_query(
        "SELECT * FROM v_rr_gerencial_v2_1_actual WHERE period_label = ?",
        (period,),
    )


def get_rt_summary(period: str) -> pd.DataFrame:
    return run_query(
        """
        SELECT *
        FROM v_rr_retail_trust_operacion_semanal_v2_1
        WHERE period_label = ?
        """,
        (period,),
    )


def get_rt_region_capacity(period: str) -> pd.DataFrame:
    return run_query(
        """
        SELECT
            region,
            carga_retail_trust,
            participacion_rt_region_pct,
            locales_retail_trust,
            puntos_retail_trust,
            clientes_retail_trust,
            carga_multimarca,
            multimarca_locales,
            multimarca_gestiones,
            multimarca_clientes,
            personas_multimarca_con_presencia,
            rutas_multimarca,
            carga_por_ruta_multimarca,
            locales_por_ruta_multimarca,
            gestiones_por_ruta_multimarca,
            pituto_carga,
            pituto_locales,
            pituto_gestiones,
            pituto_clientes,
            peso_pituto_en_gestiones_rt_pct
        FROM v_rr_region_retail_trust_v2_1
        WHERE period_label = ?
        ORDER BY carga_retail_trust DESC, region
        """,
        (period,),
    )


def get_pituto_summary(period: str) -> pd.DataFrame:
    return run_query(
        """
        SELECT *
        FROM v_rr_pituto_resumen_semanal
        WHERE period_label = ?
        """,
        (period,),
    )


def get_pituto_clients(period: str) -> pd.DataFrame:
    return run_query(
        """
        SELECT
            ranking_gestiones,
            cliente,
            pituto_locales,
            pituto_gestiones,
            pituto_cadenas,
            pituto_regiones,
            pituto_carga,
            participacion_gestiones_pct,
            participacion_carga_pct,
            carga_por_gestion
        FROM v_rr_pituto_cliente_semanal
        WHERE period_label = ?
        ORDER BY ranking_gestiones, cliente
        """,
        (period,),
    )


def get_pituto_regions(period: str) -> pd.DataFrame:
    return run_query(
        """
        SELECT
            ranking_gestiones,
            region,
            pituto_locales,
            pituto_gestiones,
            pituto_clientes,
            pituto_cadenas,
            pituto_carga,
            participacion_gestiones_pct,
            participacion_carga_pct,
            gestiones_por_local
        FROM v_rr_pituto_region_semanal
        WHERE period_label = ?
        ORDER BY ranking_gestiones, region
        """,
        (period,),
    )


def get_pituto_client_region(period: str) -> pd.DataFrame:
    return run_query(
        """
        SELECT
            region,
            cliente,
            pituto_locales,
            pituto_gestiones,
            pituto_cadenas,
            pituto_carga,
            cadenas
        FROM v_rr_pituto_cliente_region_semanal
        WHERE period_label = ?
        ORDER BY region, pituto_gestiones DESC, cliente
        """,
        (period,),
    )


def get_monthly_pituto() -> pd.DataFrame:
    return run_query(
        """
        SELECT *
        FROM v_rr_pituto_mensual
        ORDER BY period_year, period_month
        """
    )


def get_monthly_rt() -> pd.DataFrame:
    return run_query(
        """
        SELECT *
        FROM v_rr_retail_trust_operacion_mensual_v2_1
        ORDER BY period_year, period_month
        """
    )
