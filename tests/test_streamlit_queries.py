# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STREAMLIT_DIR = ROOT / "streamlit_app"
if str(STREAMLIT_DIR) not in sys.path:
    sys.path.insert(0, str(STREAMLIT_DIR))

from data_access import (  # noqa: E402
    get_metadata,
    get_modalities,
    get_monthly_capacity,
    get_periods,
    get_region_capacity,
    get_regions,
    get_retail,
    get_snapshot,
)

EXPECTED = json.loads(
    (ROOT / "contracts" / "expected_2026_06_S3.json").read_text(
        encoding="utf-8"
    )
)


def test_streamlit_metadata_and_periods() -> None:
    metadata = get_metadata().iloc[0]
    periods = get_periods()

    assert metadata["latest_period_label"] == EXPECTED["periodo_referencia"]
    assert metadata["previous_period_label"] == EXPECTED["periodo_anterior"]
    assert len(periods) == EXPECTED["universo"]["periodos"]


def test_snapshot_gerencial_v1() -> None:
    actual = get_snapshot(EXPECTED["periodo_referencia"]).iloc[0]
    summary = EXPECTED["resumen_global"]
    gerencial = EXPECTED["gerencial_v1"]

    assert actual["volumen_operativo"] == pytest.approx(summary["volumen_operativo"])
    assert actual["locales_activos"] == summary["locales_activos"]
    assert actual["local_cliente"] == summary["local_cliente"]
    assert actual["personas_multimarca"] == EXPECTED["modalidades"]["MULTIMARCA"]["personas_activas"]
    assert actual["personas_pituto"] == EXPECTED["modalidades"]["PITUTO"]["personas_activas"]

    for field, expected_value in gerencial.items():
        assert actual[field] == pytest.approx(expected_value, abs=1e-4)


def test_retail_and_modality_shares() -> None:
    period = EXPECTED["periodo_referencia"]
    retail = get_retail(period)
    modalities = get_modalities(period).set_index("modalidad")

    top = retail.iloc[0]
    assert top["cadena"] == EXPECTED["top_cadena"]["cadena"]
    assert top["volumen_operativo"] == pytest.approx(
        EXPECTED["top_cadena"]["volumen_operativo"]
    )
    assert retail["participacion_volumen_pct"].sum() == pytest.approx(100.0, abs=0.01)
    assert modalities["participacion_carga_pct"].sum() == pytest.approx(100.0, abs=0.01)
    assert modalities.loc["MULTIMARCA", "carga_asignada"] == pytest.approx(6157.0)
    assert modalities.loc["PITUTO", "personas_activas"] == 3


def test_regional_kpi() -> None:
    period = EXPECTED["periodo_referencia"]
    regions = get_regions(period)
    capacity = get_region_capacity(period)

    top = regions.iloc[0]
    for field, expected_value in EXPECTED["top_region"].items():
        if isinstance(expected_value, float):
            assert top[field] == pytest.approx(expected_value, abs=1e-4)
        else:
            assert top[field] == expected_value

    rm = capacity.loc[capacity["region"] == "13 - RM"].iloc[0]
    for field, expected_value in EXPECTED["region_rm"].items():
        assert rm[field] == pytest.approx(expected_value, abs=1e-4)

    pressure = capacity.dropna(subset=["carga_por_ruta_estructural"]).sort_values(
        "carga_por_ruta_estructural", ascending=False
    ).iloc[0]
    assert pressure["region"] == EXPECTED["mayor_carga_por_ruta"]["region"]
    assert pressure["carga_por_ruta_estructural"] == pytest.approx(115.0)


def test_monthly_capacity_closures() -> None:
    monthly = get_monthly_capacity().set_index("month_label")

    for month_label, expected_values in EXPECTED["mensual"].items():
        actual = monthly.loc[month_label]
        for field, expected_value in expected_values.items():
            if isinstance(expected_value, float):
                assert actual[field] == pytest.approx(expected_value, abs=1e-4)
            else:
                assert actual[field] == expected_value


def test_regional_volume_reconciles() -> None:
    period = EXPECTED["periodo_referencia"]
    snapshot = get_snapshot(period).iloc[0]
    regions = get_regions(period)

    assert regions["volumen_operativo"].sum() == pytest.approx(
        snapshot["volumen_operativo"]
    )
    assert regions["participacion_volumen_pct"].sum() == pytest.approx(
        100.0,
        abs=0.01,
    )
