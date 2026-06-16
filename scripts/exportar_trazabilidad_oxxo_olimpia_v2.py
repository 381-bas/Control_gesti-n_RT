# -*- coding: utf-8 -*-
"""Launcher corregido para la trazabilidad OXXO/OLIMPIA.

Corrige el caso en que la semana de mayor alta coincide con el último corte.
En la versión inicial, un diccionario de períodos sobrescribía la etiqueta
`peak` con `latest`, por lo que no se generaban las columnas *_peak.
"""
from __future__ import annotations

from typing import Any

import pandas as pd

import exportar_trazabilidad_oxxo_olimpia as core


def route_impact_fixed(
    history: pd.DataFrame,
    peak_info: dict[str, Any],
    latest_period: str,
    all_routes: pd.DataFrame,
    case_routes: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compara pre, peak y latest aunque dos etiquetas apunten al mismo período."""
    if history.empty or not peak_info:
        return pd.DataFrame(), pd.DataFrame()

    peak = peak_info["peak_period"]
    previous = peak_info.get("previous_period")

    new_rows = history.loc[
        (history["period_label"] == peak)
        & (history["es_alta_local"] == 1)
    ].copy()

    impacted = (
        new_rows.groupby(["modalidad", "rutero"], as_index=False)
        .agg(
            nuevos_locales_peak=("local_key", "nunique"),
            nuevas_regiones=(
                "region",
                lambda values: ", ".join(
                    sorted({str(value) for value in values.dropna()})
                ),
            ),
            nuevas_comunas=(
                "comuna",
                lambda values: ", ".join(
                    sorted({str(value) for value in values.dropna()})
                ),
            ),
            reponedores_peak=(
                "reponedor",
                lambda values: ", ".join(
                    sorted({str(value) for value in values.dropna()})
                ),
            ),
        )
    )
    if impacted.empty:
        return pd.DataFrame(), pd.DataFrame()

    impacted_keys = set(zip(impacted["modalidad"], impacted["rutero"]))
    periods_keep = {
        period
        for period in (previous, peak, latest_period)
        if period is not None
    }

    total_detail = all_routes.loc[
        all_routes["period_label"].isin(periods_keep)
        & pd.Series(
            list(zip(all_routes["modalidad"], all_routes["rutero"])),
            index=all_routes.index,
        ).isin(impacted_keys)
    ].copy()

    case_detail = case_routes.loc[
        case_routes["period_label"].isin(periods_keep)
        & pd.Series(
            list(zip(case_routes["modalidad"], case_routes["rutero"])),
            index=case_routes.index,
        ).isin(impacted_keys)
    ].copy()

    detail = total_detail.merge(
        case_detail,
        on=["period_label", "period_order", "modalidad", "rutero"],
        how="left",
    )

    case_numeric = [
        "caso_locales",
        "caso_puntos",
        "caso_carga",
        "caso_personas",
    ]
    for column in case_numeric:
        if column not in detail.columns:
            detail[column] = 0
        detail[column] = detail[column].fillna(0)

    metrics = [
        "ruta_locales",
        "ruta_puntos",
        "ruta_clientes",
        "ruta_carga_asignada",
        "caso_locales",
        "caso_puntos",
        "caso_carga",
    ]

    impact = impacted.copy()
    snapshots = [
        (previous, "pre"),
        (peak, "peak"),
        (latest_period, "latest"),
    ]

    # Se itera una lista, no un diccionario. Así peak y latest pueden referirse
    # a la misma semana sin que una etiqueta sobrescriba a la otra.
    for period_label, suffix in snapshots:
        snapshot = impact[["modalidad", "rutero"]].copy()
        if period_label is not None:
            period_values = detail.loc[
                detail["period_label"] == period_label,
                ["modalidad", "rutero"] + metrics,
            ].copy()
            period_values = period_values.rename(
                columns={metric: f"{metric}_{suffix}" for metric in metrics}
            )
            snapshot = snapshot.merge(
                period_values,
                on=["modalidad", "rutero"],
                how="left",
            )
        for metric in metrics:
            column = f"{metric}_{suffix}"
            if column not in snapshot.columns:
                snapshot[column] = 0
        snapshot_columns = [
            "modalidad",
            "rutero",
            *[f"{metric}_{suffix}" for metric in metrics],
        ]
        impact = impact.merge(
            snapshot[snapshot_columns],
            on=["modalidad", "rutero"],
            how="left",
        )

    numeric_columns = [
        f"{metric}_{suffix}"
        for suffix in ("pre", "peak", "latest")
        for metric in metrics
    ]
    impact[numeric_columns] = impact[numeric_columns].fillna(0)

    for metric in metrics:
        impact[f"delta_{metric}_pre_peak"] = (
            impact[f"{metric}_peak"] - impact[f"{metric}_pre"]
        )
        impact[f"delta_{metric}_pre_latest"] = (
            impact[f"{metric}_latest"] - impact[f"{metric}_pre"]
        )

    impact = impact.sort_values(
        ["nuevos_locales_peak", "delta_ruta_carga_asignada_pre_peak"],
        ascending=[False, False],
    )

    return impact, detail.sort_values(
        ["modalidad", "rutero", "period_order"]
    )


def main() -> int:
    core.route_impact = route_impact_fixed
    return core.main()


if __name__ == "__main__":
    raise SystemExit(main())
