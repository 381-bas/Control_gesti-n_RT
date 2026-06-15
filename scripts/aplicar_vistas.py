# -*- coding: utf-8 -*-
"""
Aplica la capa SQL gerencial de Control de Gestión RT.

El proceso:
1. Abre la base SQLite indicada por RR_DB_PATH o --db-path.
2. Genera un backup consistente con la API de backup de SQLite.
3. Aplica los archivos SQL 01..07 en orden.
4. Reconstruye las tablas materializadas y vistas gerenciales.
5. Ejecuta controles mínimos y reporta tiempos.

No modifica los Excel de origen ni elimina tablas raw.
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None


REQUIRED_VIEWS = {
    "v_rr_periodos",
    "v_rr_resumen_global",
    "v_rr_resumen_global_compare",
    "v_rr_resumen_mensual",
    "v_rr_cadena_semanal",
    "v_rr_cliente_semanal",
    "v_rr_modalidad_semanal",
    "v_rr_crecimiento_semanal",
    "v_rr_movimientos_local_cliente",
    "v_rr_catastro_local_semana",
    "v_rr_dashboard_qa",
    "v_rr_dashboard_metadata",
}

REQUIRED_FACTS = {
    "fact_rr_local_cliente_semana",
    "fact_rr_resumen_global",
    "fact_rr_cadena_semanal",
    "fact_rr_cliente_semanal",
    "fact_rr_cadena_cliente_semanal",
    "fact_rr_local_cliente_modalidad_semana",
    "fact_rr_persona_asignacion_semana",
    "fact_rr_modalidad_semanal",
    "fact_rr_movimientos_local_cliente",
    "fact_rr_movimientos_personal",
    "fact_rr_movimientos_asignacion",
    "fact_rr_catastro_local_semana",
    "fact_rr_dashboard_qa",
}


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description="Aplica las vistas y materializaciones gerenciales RR."
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help="Ruta explícita a rr_historico.sqlite.",
    )
    parser.add_argument(
        "--sql-dir",
        type=Path,
        default=root / "sql",
        help="Carpeta que contiene 01_periodos.sql ... 07_dashboard_qa.sql.",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Omite el backup previo. No recomendado.",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=None,
        help="Carpeta de backups. Default: <carpeta_db>/backup.",
    )
    return parser.parse_args()


def resolve_db_path(explicit: Path | None) -> Path:
    if load_dotenv is not None:
        root = Path(__file__).resolve().parents[1]
        load_dotenv(root / ".env")

    raw = str(explicit) if explicit else os.getenv("RR_DB_PATH")
    if not raw:
        raise RuntimeError(
            "Falta RR_DB_PATH. Crea .env desde .env.example "
            "o utiliza --db-path."
        )

    db_path = Path(raw).expanduser().resolve()
    if not db_path.exists():
        raise FileNotFoundError(f"No existe la base SQLite: {db_path}")
    return db_path


def discover_sql_files(sql_dir: Path) -> list[Path]:
    files = sorted(sql_dir.glob("[0-9][0-9]_*.sql"))
    expected = [f"{number:02d}_" for number in range(1, 8)]

    found_prefixes = {path.name[:3] for path in files}
    missing = [prefix for prefix in expected if prefix not in found_prefixes]
    if missing:
        raise RuntimeError(
            "Faltan archivos SQL para los prefijos: " + ", ".join(missing)
        )
    return files


def configure_connection(connection: sqlite3.Connection) -> None:
    connection.execute("PRAGMA journal_mode=WAL;")
    connection.execute("PRAGMA synchronous=NORMAL;")
    connection.execute("PRAGMA temp_store=MEMORY;")
    connection.execute("PRAGMA busy_timeout=10000;")
    connection.execute("PRAGMA cache_size=-200000;")


def create_backup(db_path: Path, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"rr_historico_before_route2_{stamp}.sqlite"

    source = sqlite3.connect(db_path)
    destination = sqlite3.connect(backup_path)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()

    return backup_path


def apply_sql_files(
    connection: sqlite3.Connection,
    files: Iterable[Path],
) -> list[tuple[str, float]]:
    timings: list[tuple[str, float]] = []

    for path in files:
        started = time.perf_counter()
        sql = path.read_text(encoding="utf-8")
        connection.executescript(sql)
        elapsed = time.perf_counter() - started
        timings.append((path.name, elapsed))
        print(f"[OK] {path.name}: {elapsed:.2f} s")

    connection.execute("ANALYZE;")
    connection.commit()
    return timings


def get_object_names(
    connection: sqlite3.Connection,
    object_type: str,
) -> set[str]:
    rows = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = ?
        """,
        (object_type,),
    ).fetchall()
    return {row[0] for row in rows}


def validate_model(connection: sqlite3.Connection) -> dict[str, object]:
    views = get_object_names(connection, "view")
    tables = get_object_names(connection, "table")

    missing_views = sorted(REQUIRED_VIEWS - views)
    missing_facts = sorted(REQUIRED_FACTS - tables)
    if missing_views or missing_facts:
        raise RuntimeError(
            f"Objetos faltantes. Vistas={missing_views}; facts={missing_facts}"
        )

    metadata = connection.execute(
        "SELECT * FROM v_rr_dashboard_metadata"
    ).fetchone()
    metadata_columns = [
        description[0]
        for description in connection.execute(
            "SELECT * FROM v_rr_dashboard_metadata"
        ).description
    ]
    metadata_dict = dict(zip(metadata_columns, metadata, strict=True))

    positive_errors = connection.execute(
        """
        SELECT COUNT(*)
        FROM v_rr_dashboard_qa
        WHERE severity = 'ERROR'
          AND affected_count > 0
        """
    ).fetchone()[0]

    delta_mismatches = connection.execute(
        """
        SELECT COUNT(*)
        FROM v_rr_crecimiento_semanal
        WHERE previous_period_label IS NOT NULL
          AND qa_delta_movimientos_cuadra <> 1
        """
    ).fetchone()[0]

    duplicate_keys = connection.execute(
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

    if positive_errors:
        raise RuntimeError(
            f"QA contiene {positive_errors} controles ERROR con afectados."
        )
    if delta_mismatches:
        raise RuntimeError(
            f"Existen {delta_mismatches} períodos cuyo delta no cuadra."
        )
    if duplicate_keys:
        raise RuntimeError(
            f"Existen {duplicate_keys} duplicados en la clave LOCAL/CLIENTE."
        )

    return {
        **metadata_dict,
        "positive_error_checks": positive_errors,
        "delta_mismatches": delta_mismatches,
        "duplicate_local_client_keys": duplicate_keys,
    }


def main() -> int:
    args = parse_args()

    try:
        db_path = resolve_db_path(args.db_path)
        sql_dir = args.sql_dir.expanduser().resolve()
        sql_files = discover_sql_files(sql_dir)

        print(f"DB: {db_path}")
        print(f"SQL: {sql_dir}")

        if not args.no_backup:
            backup_dir = (
                args.backup_dir.expanduser().resolve()
                if args.backup_dir
                else db_path.parent / "backup"
            )
            backup_path = create_backup(db_path, backup_dir)
            print(f"Backup: {backup_path}")

        connection = sqlite3.connect(db_path)
        try:
            configure_connection(connection)
            started = time.perf_counter()
            timings = apply_sql_files(connection, sql_files)
            validation = validate_model(connection)
            elapsed = time.perf_counter() - started
        finally:
            connection.close()

        print("\nVALIDACIÓN")
        for key, value in validation.items():
            print(f"- {key}: {value}")

        print("\nTIEMPOS")
        for name, seconds in timings:
            print(f"- {name}: {seconds:.2f} s")
        print(f"- total: {elapsed:.2f} s")

        return 0

    except Exception as exc:
        print(f"[ERROR] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
