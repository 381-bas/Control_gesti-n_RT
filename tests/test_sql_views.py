# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_PATH = ROOT / "contracts" / "expected_2026_06_S3.json"


def _db_path() -> Path:
    if load_dotenv is not None:
        load_dotenv(ROOT / ".env")

    raw = os.getenv("TEST_RR_DB_PATH") or os.getenv("RR_DB_PATH")
    if not raw:
        pytest.fail(
            "Falta TEST_RR_DB_PATH o RR_DB_PATH para ejecutar los tests."
        )

    path = Path(raw).expanduser().resolve()
    if not path.exists():
        pytest.fail(f"No existe la base de prueba: {path}")
    return path


@pytest.fixture(scope="session")
def expected() -> dict:
    return json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def connection() -> sqlite3.Connection:
    connection = sqlite3.connect(_db_path())
    connection.row_factory = sqlite3.Row
    yield connection
    connection.close()


def _one(connection: sqlite3.Connection, sql: str, params: tuple = ()) -> dict:
    row = connection.execute(sql, params).fetchone()
    assert row is not None
    return dict(row)


def assert_close(actual: float, expected: float, tolerance: float = 1e-4) -> None:
    assert actual == pytest.approx(expected, abs=tolerance)


def test_universo(connection: sqlite3.Connection, expected: dict) -> None:
    universe = expected["universo"]

    metadata = _one(connection, "SELECT * FROM v_rr_dashboard_metadata")
    assert metadata["archivos_validos"] == universe["archivos_validos"]
    assert metadata["primer_periodo"] == universe["primer_periodo"]
    assert metadata["ultimo_periodo"] == universe["ultimo_periodo"]

    raw_rows = connection.execute(
        "SELECT COUNT(*) FROM v_rr_base_normalizada"
    ).fetchone()[0]
    periods = connection.execute(
        "SELECT COUNT(*) FROM v_rr_periodos"
    ).fetchone()[0]
    local_client = connection.execute(
        "SELECT COUNT(*) FROM fact_rr_local_cliente_semana"
    ).fetchone()[0]

    assert raw_rows == universe["filas_raw"]
    assert periods == universe["periodos"]
    assert local_client == universe["local_cliente_historico"]


def test_resumen_global(connection: sqlite3.Connection, expected: dict) -> None:
    period = expected["periodo_referencia"]
    actual = _one(
        connection,
        """
        SELECT *
        FROM v_rr_resumen_global_compare
        WHERE period_label = ?
        """,
        (period,),
    )

    for field, expected_value in expected["resumen_global"].items():
        if isinstance(expected_value, float):
            assert_close(actual[field], expected_value)
        else:
            assert actual[field] == expected_value

    assert actual["previous_period_label"] == expected["periodo_anterior"]


def test_top_cadena(connection: sqlite3.Connection, expected: dict) -> None:
    actual = _one(
        connection,
        """
        SELECT
            cadena,
            volumen_operativo,
            locales_activos,
            local_cliente,
            participacion_volumen_pct
        FROM v_rr_cadena_semanal
        WHERE period_label = ?
        ORDER BY ranking_volumen
        LIMIT 1
        """,
        (expected["periodo_referencia"],),
    )

    for field, expected_value in expected["top_cadena"].items():
        if isinstance(expected_value, float):
            assert_close(actual[field], expected_value)
        else:
            assert actual[field] == expected_value


def test_top_cliente(connection: sqlite3.Connection, expected: dict) -> None:
    actual = _one(
        connection,
        """
        SELECT
            cliente,
            volumen_operativo,
            locales_activos,
            cadenas_activas,
            participacion_volumen_pct
        FROM v_rr_cliente_semanal
        WHERE period_label = ?
        ORDER BY ranking_volumen
        LIMIT 1
        """,
        (expected["periodo_referencia"],),
    )

    for field, expected_value in expected["top_cliente"].items():
        if isinstance(expected_value, float):
            assert_close(actual[field], expected_value)
        else:
            assert actual[field] == expected_value


@pytest.mark.parametrize(
    "modalidad",
    ["MULTIMARCA", "PITUTO", "BREDEN", "PROPAL"],
)
def test_modalidad(
    connection: sqlite3.Connection,
    expected: dict,
    modalidad: str,
) -> None:
    actual = _one(
        connection,
        """
        SELECT
            personas_activas,
            rutas_activas,
            locales_asignados,
            local_cliente_asignados,
            carga_asignada
        FROM v_rr_modalidad_semanal
        WHERE period_label = ?
          AND modalidad = ?
        """,
        (expected["periodo_referencia"], modalidad),
    )

    for field, expected_value in expected["modalidades"][modalidad].items():
        if isinstance(expected_value, float):
            assert_close(actual[field], expected_value)
        else:
            assert actual[field] == expected_value


def test_crecimiento_cuadra(
    connection: sqlite3.Connection,
    expected: dict,
) -> None:
    actual = _one(
        connection,
        """
        SELECT
            nuevos_local_cliente,
            retirados_local_cliente,
            aumentos_frecuencia,
            disminuciones_frecuencia,
            efecto_neto_movimientos,
            qa_delta_movimientos_cuadra
        FROM v_rr_crecimiento_semanal
        WHERE period_label = ?
        """,
        (expected["periodo_referencia"],),
    )

    for field, expected_value in expected["crecimiento"].items():
        if isinstance(expected_value, float):
            assert_close(actual[field], expected_value)
        else:
            assert actual[field] == expected_value


def test_cierre_mensual(connection: sqlite3.Connection, expected: dict) -> None:
    month = expected["cierre_mensual"]["month_label"]
    actual = _one(
        connection,
        """
        SELECT
            month_label,
            cierre_period_label,
            volumen_cierre,
            locales_cierre,
            local_cliente_cierre,
            personas_cierre
        FROM v_rr_resumen_mensual
        WHERE month_label = ?
        """,
        (month,),
    )

    for field, expected_value in expected["cierre_mensual"].items():
        if isinstance(expected_value, float):
            assert_close(actual[field], expected_value)
        else:
            assert actual[field] == expected_value


def test_unicidad_local_cliente(connection: sqlite3.Connection) -> None:
    duplicates = connection.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT
                period_label,
                cadena,
                cod_kpi_one,
                cliente,
                COUNT(*) AS n
            FROM fact_rr_local_cliente_semana
            GROUP BY 1, 2, 3, 4
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]
    assert duplicates == 0


def test_qa_sin_errores_positivos(connection: sqlite3.Connection) -> None:
    errors = connection.execute(
        """
        SELECT COUNT(*)
        FROM v_rr_dashboard_qa
        WHERE severity = 'ERROR'
          AND affected_count > 0
        """
    ).fetchone()[0]
    assert errors == 0


def test_todos_los_deltas_cuadran(connection: sqlite3.Connection) -> None:
    mismatches = connection.execute(
        """
        SELECT COUNT(*)
        FROM v_rr_crecimiento_semanal
        WHERE previous_period_label IS NOT NULL
          AND qa_delta_movimientos_cuadra <> 1
        """
    ).fetchone()[0]
    assert mismatches == 0
