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
    get_monthly_rt,
    get_monthly_services,
    get_periods,
    get_regions,
    get_retail,
    get_rt_modalities,
    get_rt_region_capacity,
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


def test_snapshot_gerencial_v2() -> None:
    period = EXPECTED["periodo_referencia"]
    actual = get_snapshot(period).iloc[0]
    services = get_services(period).set_index("servicio_operativo")
    rt_modalities = get_rt_modalities(period).set_index("modalidad")

    assert actual["volumen_operativo"] == pytest.approx(
        EXPECTED["resumen_global"]["volumen_operativo"]
    )
    assert actual["locales_activos"] == EXPECTED["resumen_global"]["locales_activos"]
    assert actual["local_cliente"] == EXPECTED["resumen_global"]["local_cliente"]

    assert set(services.index) == {"RETAIL TRUST", "BREDEN MASTER", "PROPAL"}
    assert services["participacion_servicio_pct"].sum() == pytest.approx(
        100.0,
        abs=0.01,
    )

    assert actual["personas_retail_trust"] == services.loc[
        "RETAIL TRUST", "personas_activas"
    ]
    assert actual["personas_breden_master"] == services.loc[
        "BREDEN MASTER", "personas_activas"
    ]
    assert actual["personas_propal"] == services.loc["PROPAL", "personas_activas"]

    assert actual["carga_retail_trust"] <= (
        rt_modalities.loc["MULTIMARCA", "carga_asignada"]
        + rt_modalities.loc["PITUTO", "carga_asignada"]
    )
    assert actual["peso_multimarca_dentro_rt_pct"] + actual[
        "peso_pituto_dentro_rt_pct"
    ] == pytest.approx(100.0, abs=0.01)


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


def test_retail_trust_modalities() -> None:
    modalities = get_rt_modalities(EXPECTED["periodo_referencia"]).set_index(
        "modalidad"
    )

    assert set(modalities.index) == {"MULTIMARCA", "PITUTO"}
    assert modalities["participacion_dentro_rt_pct"].sum() == pytest.approx(
        100.0,
        abs=0.01,
    )
    assert modalities.loc["MULTIMARCA", "carga_asignada"] == pytest.approx(
        EXPECTED["modalidades"]["MULTIMARCA"]["carga_asignada"]
    )
    assert modalities.loc["PITUTO", "personas_activas"] == EXPECTED[
        "modalidades"
    ]["PITUTO"]["personas_activas"]


def test_regional_reconciliation() -> None:
    period = EXPECTED["periodo_referencia"]
    snapshot = get_snapshot(period).iloc[0]
    regions = get_regions(period)
    rt_regions = get_rt_region_capacity(period)
    services = get_services(period).set_index("servicio_operativo")

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


def test_monthly_service_model() -> None:
    services = get_monthly_services()
    rt = get_monthly_rt()

    assert services["month_label"].nunique() == 6
    assert rt["month_label"].nunique() == 6
    assert set(services["servicio_operativo"].unique()) == {
        "RETAIL TRUST",
        "BREDEN MASTER",
        "PROPAL",
    }
    monthly_share = services.groupby("month_label")[
        "participacion_corte_pct"
    ].sum()
    assert (monthly_share - 100.0).abs().max() <= 0.01
    assert (
        rt["peso_multimarca_dentro_rt_pct"]
        + rt["peso_pituto_dentro_rt_pct"]
    ).sub(100.0).abs().max() <= 0.01
