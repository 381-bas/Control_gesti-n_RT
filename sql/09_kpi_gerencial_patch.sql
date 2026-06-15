-- 09_kpi_gerencial_patch.sql
-- Evita nombres duplicados en la vista gerencial actual. Las personas por
-- modalidad ya están publicadas en v_rr_resumen_global; este objeto agrega
-- únicamente concentración y carga asignada.

DROP VIEW IF EXISTS v_rr_gerencial_actual;

CREATE VIEW v_rr_gerencial_actual AS
WITH latest AS (
    SELECT period_label
    FROM v_rr_periodos
    WHERE is_latest_period = 1
),
retail AS (
    SELECT
        SUM(CASE WHEN ranking_volumen = 1 THEN participacion_volumen_pct ELSE 0 END)
            AS concentracion_top1_retail_pct,
        SUM(CASE WHEN ranking_volumen <= 2 THEN participacion_volumen_pct ELSE 0 END)
            AS concentracion_top2_retail_pct
    FROM v_rr_cadena_semanal
    WHERE period_label = (SELECT period_label FROM latest)
),
region AS (
    SELECT
        SUM(CASE WHEN ranking_volumen = 1 THEN participacion_volumen_pct ELSE 0 END)
            AS concentracion_top1_region_pct,
        SUM(CASE WHEN ranking_volumen <= 2 THEN participacion_volumen_pct ELSE 0 END)
            AS concentracion_top2_region_pct
    FROM v_rr_region_semanal
    WHERE period_label = (SELECT period_label FROM latest)
),
modalidad AS (
    SELECT
        MAX(CASE WHEN modalidad = 'MULTIMARCA' THEN carga_asignada END)
            AS carga_multimarca,
        MAX(CASE WHEN modalidad = 'PITUTO' THEN carga_asignada END)
            AS carga_pituto,
        SUM(carga_asignada) AS carga_asignada_total
    FROM v_rr_modalidad_semanal
    WHERE period_label = (SELECT period_label FROM latest)
)
SELECT
    r.*,
    retail.concentracion_top1_retail_pct,
    retail.concentracion_top2_retail_pct,
    region.concentracion_top1_region_pct,
    region.concentracion_top2_region_pct,
    modalidad.carga_multimarca,
    modalidad.carga_pituto,
    modalidad.carga_asignada_total,
    ROUND(
        100.0 * modalidad.carga_multimarca
        / NULLIF(modalidad.carga_asignada_total, 0),
        4
    ) AS peso_multimarca_pct,
    ROUND(
        100.0 * modalidad.carga_pituto
        / NULLIF(modalidad.carga_asignada_total, 0),
        4
    ) AS peso_pituto_pct
FROM v_rr_resumen_global AS r
CROSS JOIN retail
CROSS JOIN region
CROSS JOIN modalidad
WHERE r.period_label = (SELECT period_label FROM latest);
