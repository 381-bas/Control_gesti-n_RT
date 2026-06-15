-- 01_periodos.sql
-- Propósito:
--   Definir el universo válido, normalizar la base histórica y construir
--   el calendario semanal canónico del dashboard.
--
-- Granos:
--   v_rr_fuentes_validas   : 1 fila por archivo semanal válido.
--   v_rr_base_normalizada  : 1 fila por registro fuente.
--   v_rr_periodos          : 1 fila por período semanal.

DROP VIEW IF EXISTS v_rr_periodos;
DROP VIEW IF EXISTS v_rr_base_normalizada;
DROP VIEW IF EXISTS v_rr_fuentes_validas;

CREATE VIEW v_rr_fuentes_validas AS
WITH src AS (
    SELECT
        m.*,
        replace(m.relative_path, '/', '\') AS relative_path_norm,
        CASE
            WHEN instr(replace(m.relative_path, '/', '\'), '\') > 0
            THEN substr(
                replace(m.relative_path, '/', '\'),
                1,
                instr(replace(m.relative_path, '/', '\'), '\') - 1
            )
            ELSE replace(m.relative_path, '/', '\')
        END AS carpeta_periodo
    FROM rr_file_manifest AS m
)
SELECT
    source_path,
    relative_path,
    file_name,
    file_hash,
    file_size_bytes,
    modified_at,
    sheet_name,
    header_row_excel,
    row_count,
    column_count,
    period_year,
    period_month,
    period_week,
    period_label,
    (period_year * 1000 + period_month * 10 + period_week) AS period_order,
    carpeta_periodo,
    required_columns_ok,
    status,
    info_count,
    warning_count,
    error_count,
    loaded_at
FROM src
WHERE required_columns_ok = 1
  AND COALESCE(error_count, 0) = 0
  AND status <> 'ERROR'
  AND period_year IS NOT NULL
  AND period_month BETWEEN 1 AND 12
  AND period_week BETWEEN 1 AND 6
  AND carpeta_periodo GLOB '[0-1][0-9] - *';


CREATE VIEW v_rr_base_normalizada AS
SELECT
    r.id,
    r.source_path,
    r.relative_path,
    r.file_hash,
    r.source_row_excel,
    r.period_year,
    r.period_month,
    r.period_week,
    r.period_label,
    (r.period_year * 1000 + r.period_month * 10 + r.period_week) AS period_order,

    NULLIF(TRIM(r.cadena), '') AS cadena,
    NULLIF(TRIM(r.formato), '') AS formato,
    NULLIF(TRIM(r.region), '') AS region,
    NULLIF(TRIM(r.comuna), '') AS comuna,
    NULLIF(TRIM(r.cod_kpi_one), '') AS cod_kpi_one,
    NULLIF(TRIM(r.cod_b2b), '') AS cod_b2b,
    NULLIF(TRIM(r.local), '') AS local,
    NULLIF(TRIM(r.direccion), '') AS direccion,

    CAST(r.veces_por_semana AS REAL) AS veces_por_semana,

    NULLIF(TRIM(r.rutero), '') AS rutero,
    NULLIF(TRIM(r.jefe_operaciones), '') AS jefe_operaciones,
    NULLIF(TRIM(r.gestores), '') AS gestores,
    NULLIF(TRIM(r.cliente), '') AS cliente,
    NULLIF(TRIM(r.supervisor), '') AS supervisor,
    NULLIF(TRIM(r.reponedor), '') AS reponedor,

    COALESCE(CAST(r.lunes AS REAL), 0) AS lunes,
    COALESCE(CAST(r.martes AS REAL), 0) AS martes,
    COALESCE(CAST(r.miercoles AS REAL), 0) AS miercoles,
    COALESCE(CAST(r.jueves AS REAL), 0) AS jueves,
    COALESCE(CAST(r.viernes AS REAL), 0) AS viernes,
    COALESCE(CAST(r.sabado AS REAL), 0) AS sabado,
    COALESCE(CAST(r.domingo AS REAL), 0) AS domingo,
    CAST(r.visita_mensual AS REAL) AS visita_mensual,
    CAST(r.dif AS REAL) AS dif,

    NULLIF(TRIM(r.obs), '') AS obs,
    NULLIF(TRIM(r.aux), '') AS aux,
    NULLIF(TRIM(r.gg), '') AS gg,

    CASE
        WHEN UPPER(TRIM(COALESCE(r.rutero, ''))) = 'PITUTO' THEN 'PITUTO'
        WHEN UPPER(TRIM(COALESCE(r.rutero, ''))) = 'PROPAL' THEN 'PROPAL'
        WHEN SUBSTR(UPPER(TRIM(COALESCE(r.rutero, ''))), 1, 2) = 'BR' THEN 'BREDEN'
        WHEN SUBSTR(UPPER(TRIM(COALESCE(r.rutero, ''))), 2, 2) = 'MU' THEN 'MULTIMARCA'
        ELSE 'N/A'
    END AS modalidad,

    CASE
        WHEN UPPER(TRIM(COALESCE(r.rutero, ''))) IN (
            'CIERRE',
            'REMODELACIÓN',
            'REMODELACION',
            'POR INAGURAR',
            'POR INAUGURAR'
        ) THEN 'ESTADO'
        ELSE 'PERSONA'
    END AS tipo_rutero,

    CASE
        WHEN UPPER(TRIM(COALESCE(r.rutero, ''))) = 'CIERRE'
            THEN 'CIERRE'
        WHEN UPPER(TRIM(COALESCE(r.rutero, ''))) IN (
            'REMODELACIÓN',
            'REMODELACION'
        ) THEN 'REMODELACIÓN'
        WHEN UPPER(TRIM(COALESCE(r.rutero, ''))) IN (
            'POR INAGURAR',
            'POR INAUGURAR'
        ) THEN 'POR INAGURAR'
        ELSE NULL
    END AS estado_catastro,

    CASE
        WHEN NULLIF(TRIM(r.cadena), '') IS NOT NULL
         AND NULLIF(TRIM(r.cod_kpi_one), '') IS NOT NULL
        THEN NULLIF(TRIM(r.cadena), '') || CHAR(31) || NULLIF(TRIM(r.cod_kpi_one), '')
        ELSE NULL
    END AS local_key,

    CASE
        WHEN NULLIF(TRIM(r.cadena), '') IS NOT NULL
         AND NULLIF(TRIM(r.cod_kpi_one), '') IS NOT NULL
         AND NULLIF(TRIM(r.cliente), '') IS NOT NULL
        THEN NULLIF(TRIM(r.cadena), '') || CHAR(31)
             || NULLIF(TRIM(r.cod_kpi_one), '') || CHAR(31)
             || NULLIF(TRIM(r.cliente), '')
        ELSE NULL
    END AS local_cliente_key,

    r.extra_json,
    r.loaded_at
FROM rr_snapshot_raw AS r
INNER JOIN v_rr_fuentes_validas AS f
    ON f.source_path = r.source_path;


CREATE VIEW v_rr_periodos AS
WITH periodos AS (
    SELECT
        period_year,
        period_month,
        period_week,
        period_label,
        period_order,
        COUNT(*) AS archivos_fuente,
        SUM(row_count) AS filas_manifest,
        MAX(loaded_at) AS loaded_at
    FROM v_rr_fuentes_validas
    GROUP BY
        period_year,
        period_month,
        period_week,
        period_label,
        period_order
),
etiquetas AS (
    SELECT
        p.*,
        CASE period_month
            WHEN 1 THEN 'Enero'
            WHEN 2 THEN 'Febrero'
            WHEN 3 THEN 'Marzo'
            WHEN 4 THEN 'Abril'
            WHEN 5 THEN 'Mayo'
            WHEN 6 THEN 'Junio'
            WHEN 7 THEN 'Julio'
            WHEN 8 THEN 'Agosto'
            WHEN 9 THEN 'Septiembre'
            WHEN 10 THEN 'Octubre'
            WHEN 11 THEN 'Noviembre'
            WHEN 12 THEN 'Diciembre'
        END AS month_name,
        printf(
            '%04d-%02d',
            period_year,
            period_month
        ) AS month_label
    FROM periodos AS p
)
SELECT
    period_year,
    period_month,
    period_week,
    period_label,
    period_order,
    month_name,
    month_label,
    printf('%s · S%d', month_name, period_week) AS period_display,
    LAG(period_label) OVER (ORDER BY period_order) AS previous_period_label,
    LAG(period_order) OVER (ORDER BY period_order) AS previous_period_order,
    LEAD(period_label) OVER (ORDER BY period_order) AS next_period_label,
    CASE
        WHEN period_week = MIN(period_week) OVER (
            PARTITION BY period_year, period_month
        ) THEN 1 ELSE 0
    END AS is_first_week_month,
    CASE
        WHEN period_week = MAX(period_week) OVER (
            PARTITION BY period_year, period_month
        ) THEN 1 ELSE 0
    END AS is_last_week_month,
    CASE
        WHEN period_order = MAX(period_order) OVER ()
        THEN 1 ELSE 0
    END AS is_latest_period,
    archivos_fuente,
    filas_manifest,
    loaded_at
FROM etiquetas;
