# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from exportar_trazabilidad_oxxo_olimpia_v2 import route_impact_fixed  # noqa: E402


def test_peak_can_equal_latest_period() -> None:
    history = pd.DataFrame(
        [
            {
                "period_label": "2026-06-S3",
                "period_order": 2026063,
                "modalidad": "MULTIMARCA",
                "rutero": "RMU01",
                "local_key": "OXXO-A",
                "region": "13 - RM",
                "comuna": "SANTIAGO",
                "reponedor": "PERSONA 1",
                "es_alta_local": 1,
            }
        ]
    )
    all_routes = pd.DataFrame(
        [
            ("2026-06-S2", 2026062, "MULTIMARCA", "RMU01", 10, 30, 8, 50, 1, "13 - RM"),
            ("2026-06-S3", 2026063, "MULTIMARCA", "RMU01", 11, 31, 9, 52, 1, "13 - RM"),
        ],
        columns=[
            "period_label", "period_order", "modalidad", "rutero",
            "ruta_locales", "ruta_puntos", "ruta_clientes",
            "ruta_carga_asignada", "ruta_personas", "ruta_regiones",
        ],
    )
    case_routes = pd.DataFrame(
        [
            ("2026-06-S3", 2026063, "MULTIMARCA", "RMU01", 1, 1, 2, 1, "13 - RM"),
        ],
        columns=[
            "period_label", "period_order", "modalidad", "rutero",
            "caso_locales", "caso_puntos", "caso_carga", "caso_personas",
            "caso_regiones",
        ],
    )
    peak = {
        "peak_period": "2026-06-S3",
        "previous_period": "2026-06-S2",
        "new_locals": 1,
    }

    impact, detail = route_impact_fixed(
        history,
        peak,
        "2026-06-S3",
        all_routes,
        case_routes,
    )

    row = impact.iloc[0]
    assert row["ruta_locales_peak"] == 11
    assert row["ruta_locales_latest"] == 11
    assert row["delta_ruta_locales_pre_peak"] == 1
    assert row["delta_ruta_locales_pre_latest"] == 1
    assert row["delta_ruta_carga_asignada_pre_peak"] == 2
    assert len(detail) == 2
