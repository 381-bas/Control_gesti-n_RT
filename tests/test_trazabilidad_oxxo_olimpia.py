# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from exportar_trazabilidad_oxxo_olimpia import (  # noqa: E402
    choose_peak_period,
    first_appearance,
    route_impact,
)


def test_choose_peak_ignores_initial_historical_stock() -> None:
    periods = pd.DataFrame(
        [
            ("2026-01-S1", 2026011, None),
            ("2026-05-S1", 2026051, "2026-01-S1"),
            ("2026-06-S1", 2026061, "2026-05-S1"),
            ("2026-06-S2", 2026062, "2026-06-S1"),
        ],
        columns=["period_label", "period_order", "previous_period_label"],
    )
    catastro = pd.DataFrame(
        [
            *[(f"old-{i}", "2026-01-S1", 2026011) for i in range(40)],
            *[(f"new-{i}", "2026-06-S1", 2026061) for i in range(14)],
            *[(f"later-{i}", "2026-06-S2", 2026062) for i in range(2)],
        ],
        columns=["local_key", "primera_semana", "primera_semana_orden"],
    )

    result = choose_peak_period(catastro, periods, "2026-05-S1")

    assert result["peak_period"] == "2026-06-S1"
    assert result["previous_period"] == "2026-05-S1"
    assert result["new_locals"] == 14


def test_first_appearance_builds_local_catastro() -> None:
    official = pd.DataFrame(
        [
            {
                "local_key": "OXXO-A",
                "period_label": "2026-06-S1",
                "period_order": 2026061,
                "cadena": "OXXO",
                "cod_kpi_one": "A",
                "cliente": "CASO Y CIA",
                "local": "OXXO A",
                "formato": "OXXO",
                "region": "13 - RM",
                "comuna": "SANTIAGO",
                "direccion": "DIRECCION A",
                "veces_por_semana_contable": 2,
                "ruteros": "RMU01",
                "reponedores": "PERSONA 1",
                "modalidades": "MULTIMARCA",
            },
            {
                "local_key": "OXXO-A",
                "period_label": "2026-06-S2",
                "period_order": 2026062,
                "cadena": "OXXO",
                "cod_kpi_one": "A",
                "cliente": "CASO Y CIA",
                "local": "OXXO A",
                "formato": "OXXO",
                "region": "13 - RM",
                "comuna": "SANTIAGO",
                "direccion": "DIRECCION A",
                "veces_por_semana_contable": 3,
                "ruteros": "RMU02",
                "reponedores": "PERSONA 2",
                "modalidades": "MULTIMARCA",
            },
        ]
    )

    result = first_appearance(official).iloc[0]

    assert result["primera_semana"] == "2026-06-S1"
    assert result["ultima_semana"] == "2026-06-S2"
    assert result["semanas_activas"] == 2
    assert result["frecuencia_inicial"] == 2
    assert result["frecuencia_ultima"] == 3
    assert result["ruteros_iniciales"] == "RMU01"
    assert result["ruteros_ultimos"] == "RMU02"


def test_route_impact_compares_pre_peak_and_latest() -> None:
    history = pd.DataFrame(
        [
            {
                "period_label": "2026-06-S1",
                "period_order": 2026061,
                "modalidad": "MULTIMARCA",
                "rutero": "RMU01",
                "local_key": "OXXO-A",
                "region": "13 - RM",
                "comuna": "SANTIAGO",
                "reponedor": "PERSONA 1",
                "es_alta_local": 1,
            },
            {
                "period_label": "2026-06-S1",
                "period_order": 2026061,
                "modalidad": "MULTIMARCA",
                "rutero": "RMU01",
                "local_key": "OXXO-B",
                "region": "13 - RM",
                "comuna": "SANTIAGO",
                "reponedor": "PERSONA 1",
                "es_alta_local": 1,
            },
        ]
    )
    all_routes = pd.DataFrame(
        [
            ("2026-05-S4", 2026054, "MULTIMARCA", "RMU01", 10, 30, 8, 50, 1, "13 - RM"),
            ("2026-06-S1", 2026061, "MULTIMARCA", "RMU01", 12, 32, 9, 54, 1, "13 - RM"),
            ("2026-06-S3", 2026063, "MULTIMARCA", "RMU01", 12, 33, 9, 56, 1, "13 - RM"),
        ],
        columns=[
            "period_label", "period_order", "modalidad", "rutero",
            "ruta_locales", "ruta_puntos", "ruta_clientes",
            "ruta_carga_asignada", "ruta_personas", "ruta_regiones",
        ],
    )
    case_routes = pd.DataFrame(
        [
            ("2026-06-S1", 2026061, "MULTIMARCA", "RMU01", 2, 2, 4, 1, "13 - RM"),
            ("2026-06-S3", 2026063, "MULTIMARCA", "RMU01", 2, 2, 4, 1, "13 - RM"),
        ],
        columns=[
            "period_label", "period_order", "modalidad", "rutero",
            "caso_locales", "caso_puntos", "caso_carga", "caso_personas",
            "caso_regiones",
        ],
    )
    peak = {
        "peak_period": "2026-06-S1",
        "previous_period": "2026-05-S4",
        "new_locals": 2,
    }

    impact, detail = route_impact(
        history,
        peak,
        "2026-06-S3",
        all_routes,
        case_routes,
    )

    row = impact.iloc[0]
    assert row["nuevos_locales_peak"] == 2
    assert row["delta_ruta_locales_pre_peak"] == 2
    assert row["delta_ruta_puntos_pre_peak"] == 2
    assert row["delta_ruta_carga_asignada_pre_peak"] == 4
    assert len(detail) == 3
