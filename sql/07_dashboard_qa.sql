-- 07_dashboard_qa.sql
-- Propósito:
--   Publicar controles de calidad y metadatos visibles desde Streamlit.

DROP VIEW IF EXISTS v_rr_dashboard_metadata;
DROP VIEW IF EXISTS v_rr_dashboard_qa;
DROP TABLE IF EXISTS fact_rr_dashboard_qa;

CREATE TABLE fact_rr_dashboard_qa AS
WITH qa_origen AS (
    SELECT
        f.period_label,
        f.period_order,
        q.severity,
        q.issue_type AS check_name,
        COALESCE(SUM(q.affected_rows), COUNT(*)) AS affected_count,
        MAX(q.detail) AS detail
    FROM rr_qa_issues AS q
    INNER JOIN v_rr_fuentes_validas AS f
        ON f.source_path = q.source_path
    GROUP BY
        f.period_label,
        f.period_order,
        q.severity,
        q.issue_type
),
archivos AS (
    SELECT
        period_label,
        period_order,
        'INFO' AS severity,
        'ARCHIVOS_FUENTE' AS check_name,
        COUNT(*) AS affected_count,
        'Cantidad de archivos semanales válidos del período.' AS detail
    FROM v_rr_fuentes_validas
    GROUP BY period_label, period_order
),
filas AS (
    SELECT
        period_label,
        period_order,
        'INFO' AS severity,
        'FILAS_RAW' AS check_name,
        COUNT(*) AS affected_count,
        'Filas fuente incluidas en el universo canónico.' AS detail
    FROM v_rr_base_normalizada
    GROUP BY period_label, period_order
),
claves_vacias AS (
    SELECT
        period_label,
        period_order,
        'ERROR' AS severity,
        'CLAVES_REQUERIDAS_VACIAS' AS check_name,
        SUM(
            CASE
                WHEN cadena IS NULL
                  OR cod_kpi_one IS NULL
                  OR cliente IS NULL
                THEN 1 ELSE 0
            END
        ) AS affected_count,
        'Filas sin CADENA, COD KPI ONE o CLIENTE.' AS detail
    FROM v_rr_base_normalizada
    GROUP BY period_label, period_order
),
frecuencia_invalida AS (
    SELECT
        period_label,
        period_order,
        'ERROR' AS severity,
        'FRECUENCIA_NULA_O_NEGATIVA' AS check_name,
        SUM(
            CASE
                WHEN veces_por_semana IS NULL
                  OR veces_por_semana < 0
                THEN 1 ELSE 0
            END
        ) AS affected_count,
        'Frecuencias nulas o negativas en la base normalizada.' AS detail
    FROM v_rr_base_normalizada
    GROUP BY period_label, period_order
),
duplicado_tecnico AS (
    SELECT
        period_label,
        period_order,
        'ERROR' AS severity,
        'DUPLICADO_TECNICO_ARCHIVO_FILA' AS check_name,
        COALESCE(SUM(cantidad - 1), 0) AS affected_count,
        'Duplicados de la clave técnica SOURCE_PATH + SOURCE_ROW_EXCEL.' AS detail
    FROM (
        SELECT
            period_label,
            period_order,
            source_path,
            source_row_excel,
            COUNT(*) AS cantidad
        FROM v_rr_base_normalizada
        GROUP BY
            period_label,
            period_order,
            source_path,
            source_row_excel
        HAVING COUNT(*) > 1
    )
    GROUP BY period_label, period_order
),
repeticiones AS (
    SELECT
        period_label,
        period_order,
        'INFO' AS severity,
        'LOCAL_CLIENTE_CON_MULTIPLES_FILAS' AS check_name,
        SUM(CASE WHEN filas_origen > 1 THEN 1 ELSE 0 END)
            AS affected_count,
        'Combinaciones LOCAL/CLIENTE consolidadas mediante MAX de frecuencia.'
            AS detail
    FROM v_rr_local_cliente_semana
    GROUP BY period_label, period_order
),
frecuencia_diversa AS (
    SELECT
        period_label,
        period_order,
        'WARN' AS severity,
        'LOCAL_CLIENTE_FRECUENCIA_DIVERSA' AS check_name,
        SUM(
            CASE
                WHEN veces_por_semana_min <> veces_por_semana_max
                THEN 1 ELSE 0
            END
        ) AS affected_count,
        'Combinaciones con más de una frecuencia fuente; se usa MAX.'
            AS detail
    FROM v_rr_local_cliente_semana
    GROUP BY period_label, period_order
),
modalidad_na AS (
    SELECT
        period_label,
        period_order,
        CASE
            WHEN tipo_rutero = 'ESTADO' THEN 'INFO'
            ELSE 'WARN'
        END AS severity,
        CASE
            WHEN tipo_rutero = 'ESTADO'
                THEN 'MODALIDAD_NA_ESTADO_CATASTRO'
            ELSE 'MODALIDAD_NA_NO_ESTADO'
        END AS check_name,
        COUNT(*) AS affected_count,
        CASE
            WHEN tipo_rutero = 'ESTADO'
                THEN 'Filas N/A que corresponden a estados de catastro.'
            ELSE 'Filas N/A que no corresponden a estados reconocidos.'
        END AS detail
    FROM v_rr_base_normalizada
    WHERE modalidad = 'N/A'
    GROUP BY
        period_label,
        period_order,
        tipo_rutero
),
cuadre_movimientos AS (
    SELECT
        period_label,
        period_order,
        'ERROR' AS severity,
        'DELTA_MOVIMIENTOS_NO_CUADRA' AS check_name,
        CASE
            WHEN previous_period_label IS NULL THEN 0
            WHEN qa_delta_movimientos_cuadra = 1 THEN 0
            ELSE 1
        END AS affected_count,
        'El efecto neto de movimientos debe igualar el delta de volumen.'
            AS detail
    FROM v_rr_crecimiento_semanal
)
SELECT * FROM qa_origen
UNION ALL SELECT * FROM archivos
UNION ALL SELECT * FROM filas
UNION ALL SELECT * FROM claves_vacias
UNION ALL SELECT * FROM frecuencia_invalida
UNION ALL SELECT * FROM duplicado_tecnico
UNION ALL SELECT * FROM repeticiones
UNION ALL SELECT * FROM frecuencia_diversa
UNION ALL SELECT * FROM modalidad_na
UNION ALL SELECT * FROM cuadre_movimientos;


CREATE INDEX idx_fact_rr_qa_period
    ON fact_rr_dashboard_qa(period_label, severity, check_name);

CREATE VIEW v_rr_dashboard_qa AS
SELECT *
FROM fact_rr_dashboard_qa;

CREATE VIEW v_rr_dashboard_metadata AS
WITH latest AS (
    SELECT *
    FROM v_rr_periodos
    WHERE is_latest_period = 1
),
conteos AS (
    SELECT
        COUNT(*) AS archivos_validos,
        SUM(row_count) AS filas_manifest,
        MIN(period_label) AS primer_periodo,
        MAX(period_label) AS ultimo_periodo,
        MAX(loaded_at) AS ultima_carga
    FROM v_rr_fuentes_validas
),
qa AS (
    SELECT
        SUM(CASE
            WHEN severity = 'ERROR' AND affected_count > 0
            THEN 1 ELSE 0
        END) AS controles_error,

        SUM(CASE
            WHEN severity = 'WARN' AND affected_count > 0
            THEN 1 ELSE 0
        END) AS controles_warn,

        SUM(CASE
            WHEN severity = 'INFO' AND affected_count > 0
            THEN 1 ELSE 0
        END) AS controles_info
    FROM v_rr_dashboard_qa
)
SELECT
    l.period_label AS latest_period_label,
    l.period_order AS latest_period_order,
    l.previous_period_label,
    c.primer_periodo,
    c.ultimo_periodo,
    c.archivos_validos,
    c.filas_manifest,
    c.ultima_carga,
    COALESCE(q.controles_error, 0) AS controles_error,
    COALESCE(q.controles_warn, 0) AS controles_warn,
    COALESCE(q.controles_info, 0) AS controles_info
FROM latest AS l
CROSS JOIN conteos AS c
CROSS JOIN qa AS q;
