# -*- coding: utf-8 -*-
from __future__ import annotations

import ast
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
    get_monthly_pituto,
    get_monthly_rt,
    get_monthly_services,
    get_periods,
    get_pituto_client_region,
    get_pituto_clients,
    get_pituto_regions,
    get_pituto_summary,
    get_regions,
    get_retail,
    get_rt_region_capacity,
    get_rt_summary,
    get_services,
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


def test_snapshot_gerencial_v21() -> None:
    period = EXPECTED["periodo_referencia"]
    actual = get_snapshot(period).iloc[0]
    rt = get_rt_summary(period).iloc[0]
    pituto = get_pituto_summary(period).iloc[0]

    assert actual["volumen_operativo"] == pytest.approx(
        EXPECTED["resumen_global"]["volumen_operativo"]
    )
    assert actual["locales_activos"] == EXPECTED["resumen_global"]["locales_activos"]
    assert actual["local_cliente"] == EXPECTED["resumen_global"]["local_cliente"]

    assert rt["rutas_multimarca"] == EXPECTED["modalidades"]["MULTIMARCA"]["rutas_activas"]
    assert rt["personas_multimarca"] == EXPECTED["modalidades"]["MULTIMARCA"]["personas_activas"]
    assert rt["multimarca_locales"] == EXPECTED["modalidades"]["MULTIMARCA"]["locales_asignados"]
    assert rt["multimarca_gestiones"] == EXPECTED["modalidades"]["MULTIMARCA"]["local_cliente_asignados"]

    assert pituto["pituto_locales"] == EXPECTED["modalidades"]["PITUTO"]["locales_asignados"]
    assert pituto["pituto_gestiones"] == EXPECTED["modalidades"]["PITUTO"]["local_cliente_asignados"]
    assert pituto["pituto_carga"] == pytest.approx(
        EXPECTED["modalidades"]["PITUTO"]["carga_asignada"]
    )

    assert actual["pituto_locales"] == pituto["pituto_locales"]
    assert actual["pituto_gestiones"] == pituto["pituto_gestiones"]
    assert actual["pituto_carga"] == pytest.approx(pituto["pituto_carga"])


def test_retail_and_service_shares() -> None:
    period = EXPECTED["periodo_referencia"]
    retail = get_retail(period)
    services = get_services(period)

    top = retail.iloc[0]
    assert top["cadena"] == EXPECTED["top_cadena"]["cadena"]
    assert top["volumen_operativo"] == pytest.approx(
        EXPECTED["top_cadena"]["volumen_operativo"]
    )
    assert retail["participacion_volumen_pct"].sum() == pytest.approx(
        100.0,
        abs=0.01,
    )
    assert services["participacion_servicio_pct"].sum() == pytest.approx(
        100.0,
        abs=0.01,
    )


def test_pituto_reconciles_by_client_and_region() -> None:
    period = EXPECTED["periodo_referencia"]
    summary = get_pituto_summary(period).iloc[0]
    by_client = get_pituto_clients(period)
    by_region = get_pituto_regions(period)
    client_region = get_pituto_client_region(period)

    assert by_client["pituto_gestiones"].sum() == summary["pituto_gestiones"]
    assert by_client["pituto_carga"].sum() == pytest.approx(summary["pituto_carga"])
    assert by_client["participacion_gestiones_pct"].sum() == pytest.approx(
        100.0,
        abs=0.01,
    )

    assert by_region["pituto_gestiones"].sum() == summary["pituto_gestiones"]
    assert by_region["pituto_carga"].sum() == pytest.approx(summary["pituto_carga"])
    assert by_region["participacion_gestiones_pct"].sum() == pytest.approx(
        100.0,
        abs=0.01,
    )

    assert client_region["pituto_gestiones"].sum() == summary["pituto_gestiones"]
    assert client_region["pituto_carga"].sum() == pytest.approx(summary["pituto_carga"])


def test_regional_reconciliation() -> None:
    period = EXPECTED["periodo_referencia"]
    snapshot = get_snapshot(period).iloc[0]
    regions = get_regions(period)
    rt_regions = get_rt_region_capacity(period)
    services = get_services(period).set_index("servicio_operativo")
    pituto = get_pituto_summary(period).iloc[0]

    assert regions["volumen_operativo"].sum() == pytest.approx(
        snapshot["volumen_operativo"]
    )
    assert regions["participacion_volumen_pct"].sum() == pytest.approx(
        100.0,
        abs=0.01,
    )
    assert rt_regions["carga_retail_trust"].sum() == pytest.approx(
        services.loc["RETAIL TRUST", "carga_servicio"]
    )
    assert rt_regions["participacion_rt_region_pct"].sum() == pytest.approx(
        100.0,
        abs=0.01,
    )
    assert rt_regions["pituto_gestiones"].sum() == pituto["pituto_gestiones"]
    assert rt_regions["pituto_carga"].sum() == pytest.approx(pituto["pituto_carga"])


def test_monthly_service_and_pituto_model() -> None:
    services = get_monthly_services()
    rt = get_monthly_rt()
    pituto = get_monthly_pituto()

    assert services["month_label"].nunique() == 6
    assert rt["month_label"].nunique() == 6
    assert pituto["month_label"].nunique() == 6
    assert set(services["servicio_operativo"].unique()) == {
        "RETAIL TRUST",
        "BREDEN MASTER",
        "PROPAL",
    }

    monthly_share = services.groupby("month_label")[
        "participacion_corte_pct"
    ].sum()
    assert (monthly_share - 100.0).abs().max() <= 0.01

    assert "personas_pituto_corte" not in rt.columns
    assert "pituto_gestiones_corte" in rt.columns
    assert "pituto_locales_corte" in rt.columns
    assert "carga_por_ruta_mm_corte" in rt.columns


def test_app_v21_compiles() -> None:
    source = (STREAMLIT_DIR / "app_v2_1.py").read_text(encoding="utf-8")
    ast.parse(source)
