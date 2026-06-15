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
    get_chain_ranking,
    get_client_ranking,
    get_growth_components,
    get_metadata,
    get_modality_summary,
    get_periods,
    get_summary,
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


def test_streamlit_summary_query() -> None:
    actual = get_summary(
        EXPECTED["periodo_referencia"],
        EXPECTED["periodo_anterior"],
    ).iloc[0]

    expected = EXPECTED["resumen_global"]
    assert actual["volumen_operativo"] == pytest.approx(expected["volumen_operativo"])
    assert actual["locales_activos"] == expected["locales_activos"]
    assert actual["local_cliente"] == expected["local_cliente"]
    assert actual["personas_activas"] == expected["personas_activas"]
    assert actual["delta_volumen_operativo"] == pytest.approx(
        expected["delta_volumen_operativo"]
    )


def test_streamlit_rankings() -> None:
    current = EXPECTED["periodo_referencia"]
    previous = EXPECTED["periodo_anterior"]

    chain = get_chain_ranking(current, previous).iloc[0]
    client = get_client_ranking(current, previous).iloc[0]

    assert chain["cadena"] == EXPECTED["top_cadena"]["cadena"]
    assert chain["volumen_operativo"] == pytest.approx(
        EXPECTED["top_cadena"]["volumen_operativo"]
    )
    assert client["cliente"] == EXPECTED["top_cliente"]["cliente"]
    assert client["volumen_operativo"] == pytest.approx(
        EXPECTED["top_cliente"]["volumen_operativo"]
    )


def test_streamlit_modalities_and_growth() -> None:
    current = EXPECTED["periodo_referencia"]
    previous = EXPECTED["periodo_anterior"]

    modalities = get_modality_summary(current, previous).set_index("modalidad")
    growth = get_growth_components(current, previous).set_index("tipo_movimiento")

    assert modalities.loc["MULTIMARCA", "personas_activas"] == 63
    assert modalities.loc["PITUTO", "carga_asignada"] == pytest.approx(1365.0)
    assert growth.loc["NUEVO", "casos"] == 64
    assert growth.loc["NUEVO", "efecto_volumen"] == pytest.approx(64.0)
