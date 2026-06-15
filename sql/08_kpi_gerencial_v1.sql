-- 08_kpi_gerencial_v1.sql
-- Propósito:
--   Publicar la capa limpia de KPI para la página gerencial V1:
--   concentración actual por RETAIL, modalidad y región; capacidad regional;
--   y tendencias mensuales de cierre y promedio semanal.
--
-- Reglas:
--   - Volumen oficial: frecuencia consolidada de v_rr_local_cliente_semana.
--   - Modalidad: carga asignada; puede superar el volumen oficial.
--   - Rutas estructurales: RUTERO distintos de MULTIMARCA y BREDEN.
--   - Capacidad flexible: REPONEDOR distintos de PITUTO y PROPAL.

DROP VIEW IF EXISTS v_rr_gerencial_actual;
DROP VIEW IF EXISTS v_rr_capacidad_mensual;
DROP VIEW IF EXISTS v_rr_modalidad_mensual;
DROP VIEW IF EXISTS v_rr_region_mensual;
DROP VIEW IF EXISTS v_rr_retail_mensual;
DROP VIEW IF EXISTS v_rr_region_capacidad_semanal;
DROP VIEW IF EXISTS v_rr_region_modalidad_semanal;
DROP VIEW IF EXISTS v_rr_region_semanal;

DROP TABLE IF EXISTS fact_rr_capacidad_mensual;
DROP TABLE IF EXISTS fact_rr_modalidad_mensual;
DROP TABLE IF EXISTS fact_rr_region_mensual;
DROP TABLE IF EXISTS fact_rr_retail_mensual;
DROP TABLE IF EXISTS fact_rr_region_capacidad_semanal;
DROP TABLE IF EXISTS fact_rr_region_modalidad_semanal;
DROP TABLE IF EXISTS fact_rr_region_semanal;

CREATE TABLE fact_rr_region_semanal AS
WITH base AS (
    SELECT
        period_year,
        period_month,
        period_week,
        period_label,
        period_order,
        COALESCE(NULLIF(TRIM(region), ''), 'SIN REGIÓN') AS region,
        SUM(veces_por_semana_contable) AS volumen_operativo,
        COUNT(DISTINCT local_key) AS locales_activos,
        COUNT(*) AS puntos_gestion,
        COUNT(DISTINCT cliente) AS clientes_activos,
        AVG(veces_por_semana_contable) AS frecuencia_media_punto
    FROM v_rr_local_cliente_semana
    GROUP BY
        period_year,
        period_month,
        period_week,
        period_label,
        period_order,
        COALESCE(NULLIF(TRIM(region), ''), 'SIN REGIÓN')
),
ranked AS (
    SELECT
        base.*,
        SUM(volumen_operativo) OVER (
            PARTITION BY period_label
        ) AS volumen_total_periodo,
        DENSE_RANK() OVER (
            PARTITION BY period_label
            ORDER BY volumen_operativo DESC, region
        ) AS ranking_volumen
    FROM base
)
SELECT
    ranked.*,
    ROUND(
        100.0 * volumen_operativo / NULLIF(volumen_total_periodo, 0),
        4
    ) AS participacion_volumen_pct,
    ROUND(
        1.0 * puntos_gestion / NULLIF(locales_activos, 0),
        4
    ) AS puntos_por_local,
    ROUND(
        1.0 * clientes_activos / NULLIF(locales_activos, 0),
        4
    ) AS clientes_por_local,
    ROUND(
        volumen_operativo / NULLIF(locales_activos, 0),
        4
    ) AS carga_por_local
FROM ranked;

CREATE UNIQUE INDEX idx_fact_rr_region_key
    ON fact_rr_region_semanal(period_label, region);
CREATE INDEX idx_fact_rr_region_rank
    ON fact_rr_region_semanal(period_label, ranking_volumen);
CREATE VIEW v_rr_region_semanal AS
SELECT * FROM fact_rr_region_semanal;

CREATE TABLE fact_rr_region_modalidad_semanal AS
WITH carga AS (
    SELECT
        period_year,
        period_month,
        period_week,
        period_label,
        period_order,
        COALESCE(NULLIF(TRIM(region), ''), 'SIN REGIÓN') AS region,
        modalidad,
        SUM(carga_asignada) AS carga_asignada,
        COUNT(DISTINCT local_key) AS locales_asignados,
        COUNT(*) AS puntos_gestion_asignados,
        COUNT(DISTINCT cliente) AS clientes_asignados
    FROM v_rr_local_cliente_modalidad_semana
    WHERE modalidad IN ('MULTIMARCA', 'PITUTO', 'BREDEN', 'PROPAL')
    GROUP BY
        period_year,
        period_month,
        period_week,
        period_label,
        period_order,
        COALESCE(NULLIF(TRIM(region), ''), 'SIN REGIÓN'),
        modalidad
),
dotacion AS (
    SELECT
        period_label,
        COALESCE(NULLIF(TRIM(region), ''), 'SIN REGIÓN') AS region,
        modalidad,
        COUNT(DISTINCT reponedor) AS personas_activas,
        COUNT(DISTINCT rutero) AS rutas_con_presencia
    FROM v_rr_base_normalizada
    WHERE tipo_rutero = 'PERSONA'
      AND modalidad IN ('MULTIMARCA', 'PITUTO', 'BREDEN', 'PROPAL')
      AND reponedor IS NOT NULL
    GROUP BY
        period_label,
        COALESCE(NULLIF(TRIM(region), ''), 'SIN REGIÓN'),
        modalidad
),
base AS (
    SELECT
        c.*,
        COALESCE(d.personas_activas, 0) AS personas_activas,
        COALESCE(d.rutas_con_presencia, 0) AS rutas_con_presencia,
        SUM(c.carga_asignada) OVER (
            PARTITION BY c.period_label
        ) AS carga_asignada_total_periodo,
        SUM(c.carga_asignada) OVER (
            PARTITION BY c.period_label, c.region
        ) AS carga_asignada_total_region
    FROM carga AS c
    LEFT JOIN dotacion AS d
      ON d.period_label = c.period_label
     AND d.region = c.region
     AND d.modalidad = c.modalidad
)
SELECT
    base.*,
    ROUND(
        100.0 * carga_asignada / NULLIF(carga_asignada_total_periodo, 0),
        4
    ) AS participacion_carga_total_pct,
    ROUND(
        100.0 * carga_asignada / NULLIF(carga_asignada_total_region, 0),
        4
    ) AS participacion_carga_region_pct,
    ROUND(
        carga_asignada / NULLIF(personas_activas, 0),
        4
    ) AS carga_por_persona,
    ROUND(
        1.0 * puntos_gestion_asignados / NULLIF(personas_activas, 0),
        4
    ) AS puntos_por_persona
FROM base;

CREATE UNIQUE INDEX idx_fact_rr_region_modalidad_key
    ON fact_rr_region_modalidad_semanal(period_label, region, modalidad);
CREATE INDEX idx_fact_rr_region_modalidad_period
    ON fact_rr_region_modalidad_semanal(period_label, modalidad, region);
CREATE VIEW v_rr_region_modalidad_semanal AS
SELECT * FROM fact_rr_region_modalidad_semanal;

CREATE TABLE fact_rr_region_capacidad_semanal AS
WITH dotacion AS (
    SELECT
        period_year,
        period_month,
        period_week,
        period_label,
        period_order,
        COALESCE(NULLIF(TRIM(region), ''), 'SIN REGIÓN') AS region,
        COUNT(DISTINCT CASE
            WHEN modalidad IN ('MULTIMARCA', 'BREDEN')
            THEN rutero
        END) AS rutas_estructurales,
        COUNT(DISTINCT CASE
            WHEN modalidad IN ('MULTIMARCA', 'BREDEN')
            THEN reponedor
        END) AS personas_estructurales,
        COUNT(DISTINCT CASE
            WHEN modalidad IN ('PITUTO', 'PROPAL')
            THEN reponedor
        END) AS personas_flexibles,
        COUNT(DISTINCT CASE
            WHEN modalidad IN ('MULTIMARCA', 'PITUTO', 'BREDEN', 'PROPAL')
            THEN reponedor
        END) AS personas_con_presencia
    FROM v_rr_base_normalizada
    WHERE tipo_rutero = 'PERSONA'
    GROUP BY
        period_year,
        period_month,
        period_week,
        period_label,
        period_order,
        COALESCE(NULLIF(TRIM(region), ''), 'SIN REGIÓN')
),
carga AS (
    SELECT
        period_label,
        region,
        SUM(CASE
            WHEN modalidad IN ('MULTIMARCA', 'BREDEN')
            THEN carga_asignada ELSE 0
        END) AS carga_estructural,
        SUM(CASE
            WHEN modalidad IN ('PITUTO', 'PROPAL')
            THEN carga_asignada ELSE 0
        END) AS carga_flexible,
        SUM(carga_asignada) AS carga_asignada_total
    FROM v_rr_region_modalidad_semanal
    GROUP BY period_label, region
),
base AS (
    SELECT
        r.period_year,
        r.period_month,
        r.period_week,
        r.period_label,
        r.period_order,
        r.region,
        r.ranking_volumen,
        r.volumen_operativo,
        r.participacion_volumen_pct,
        r.locales_activos,
        r.puntos_gestion,
        r.clientes_activos,
        r.frecuencia_media_punto,
        r.puntos_por_local,
        r.clientes_por_local,
        r.carga_por_local,
        COALESCE(c.carga_estructural, 0) AS carga_estructural,
        COALESCE(c.carga_flexible, 0) AS carga_flexible,
        COALESCE(c.carga_asignada_total, 0) AS carga_asignada_total,
        COALESCE(d.rutas_estructurales, 0) AS rutas_estructurales,
        COALESCE(d.personas_estructurales, 0) AS personas_estructurales,
        COALESCE(d.personas_flexibles, 0) AS personas_flexibles,
        COALESCE(d.personas_con_presencia, 0) AS personas_con_presencia
    FROM v_rr_region_semanal AS r
    LEFT JOIN carga AS c
      ON c.period_label = r.period_label
     AND c.region = r.region
    LEFT JOIN dotacion AS d
      ON d.period_label = r.period_label
     AND d.region = r.region
)
SELECT
    base.*,
    ROUND(
        100.0 * rutas_estructurales
        / NULLIF(SUM(rutas_estructurales) OVER (PARTITION BY period_label), 0),
        4
    ) AS distribucion_presencia_rutas_pct,
    ROUND(
        carga_estructural / NULLIF(rutas_estructurales, 0),
        4
    ) AS carga_por_ruta_estructural,
    ROUND(
        carga_flexible / NULLIF(personas_flexibles, 0),
        4
    ) AS carga_flexible_por_persona,
    ROUND(
        volumen_operativo / NULLIF(personas_con_presencia, 0),
        4
    ) AS volumen_oficial_por_persona,
    ROUND(
        1.0 * puntos_gestion / NULLIF(personas_con_presencia, 0),
        4
    ) AS puntos_por_persona
FROM base;

CREATE UNIQUE INDEX idx_fact_rr_region_capacidad_key
    ON fact_rr_region_capacidad_semanal(period_label, region);
CREATE INDEX idx_fact_rr_region_capacidad_rank
    ON fact_rr_region_capacidad_semanal(period_label, ranking_volumen);
CREATE VIEW v_rr_region_capacidad_semanal AS
SELECT * FROM fact_rr_region_capacidad_semanal;

CREATE TABLE fact_rr_retail_mensual AS
WITH promedio AS (
    SELECT
        period_year,
        period_month,
        cadena,
        COUNT(*) AS semanas_disponibles,
        AVG(volumen_operativo) AS volumen_promedio_semanal,
        AVG(locales_activos) AS locales_promedio_semanal,
        AVG(local_cliente) AS puntos_promedio_semanal,
        AVG(clientes_activos) AS clientes_promedio_semanal
    FROM v_rr_cadena_semanal
    GROUP BY period_year, period_month, cadena
),
cierre AS (
    SELECT c.*
    FROM v_rr_cadena_semanal AS c
    INNER JOIN v_rr_periodos AS p
      ON p.period_label = c.period_label
    WHERE p.is_last_week_month = 1
)
SELECT
    c.period_year,
    c.period_month,
    printf('%04d-%02d', c.period_year, c.period_month) AS month_label,
    c.period_label AS cierre_period_label,
    c.period_order AS cierre_period_order,
    c.cadena,
    c.ranking_volumen AS ranking_cierre,
    c.volumen_operativo AS volumen_cierre,
    c.participacion_volumen_pct AS participacion_cierre_pct,
    c.locales_activos AS locales_cierre,
    c.local_cliente AS puntos_cierre,
    c.clientes_activos AS clientes_cierre,
    ROUND(p.volumen_promedio_semanal, 4) AS volumen_promedio_semanal,
    ROUND(p.locales_promedio_semanal, 4) AS locales_promedio_semanal,
    ROUND(p.puntos_promedio_semanal, 4) AS puntos_promedio_semanal,
    ROUND(p.clientes_promedio_semanal, 4) AS clientes_promedio_semanal,
    p.semanas_disponibles
FROM cierre AS c
INNER JOIN promedio AS p
  ON p.period_year = c.period_year
 AND p.period_month = c.period_month
 AND p.cadena = c.cadena;

CREATE UNIQUE INDEX idx_fact_rr_retail_month_key
    ON fact_rr_retail_mensual(month_label, cadena);
CREATE VIEW v_rr_retail_mensual AS
SELECT * FROM fact_rr_retail_mensual;

CREATE TABLE fact_rr_region_mensual AS
WITH promedio AS (
    SELECT
        period_year,
        period_month,
        region,
        COUNT(*) AS semanas_disponibles,
        AVG(volumen_operativo) AS volumen_promedio_semanal,
        AVG(locales_activos) AS locales_promedio_semanal,
        AVG(puntos_gestion) AS puntos_promedio_semanal,
        AVG(clientes_activos) AS clientes_promedio_semanal,
        AVG(rutas_estructurales) AS rutas_promedio_semanal,
        AVG(personas_flexibles) AS personas_flexibles_promedio_semanal
    FROM v_rr_region_capacidad_semanal
    GROUP BY period_year, period_month, region
),
cierre AS (
    SELECT r.*
    FROM v_rr_region_capacidad_semanal AS r
    INNER JOIN v_rr_periodos AS p
      ON p.period_label = r.period_label
    WHERE p.is_last_week_month = 1
)
SELECT
    c.period_year,
    c.period_month,
    printf('%04d-%02d', c.period_year, c.period_month) AS month_label,
    c.period_label AS cierre_period_label,
    c.period_order AS cierre_period_order,
    c.region,
    c.ranking_volumen AS ranking_cierre,
    c.volumen_operativo AS volumen_cierre,
    c.participacion_volumen_pct AS participacion_cierre_pct,
    c.locales_activos AS locales_cierre,
    c.puntos_gestion AS puntos_cierre,
    c.clientes_activos AS clientes_cierre,
    c.rutas_estructurales AS rutas_estructurales_cierre,
    c.personas_flexibles AS personas_flexibles_cierre,
    c.carga_por_ruta_estructural AS carga_por_ruta_cierre,
    c.puntos_por_persona AS puntos_por_persona_cierre,
    ROUND(p.volumen_promedio_semanal, 4) AS volumen_promedio_semanal,
    ROUND(p.locales_promedio_semanal, 4) AS locales_promedio_semanal,
    ROUND(p.puntos_promedio_semanal, 4) AS puntos_promedio_semanal,
    ROUND(p.clientes_promedio_semanal, 4) AS clientes_promedio_semanal,
    ROUND(p.rutas_promedio_semanal, 4) AS rutas_promedio_semanal,
    ROUND(p.personas_flexibles_promedio_semanal, 4)
        AS personas_flexibles_promedio_semanal,
    p.semanas_disponibles
FROM cierre AS c
INNER JOIN promedio AS p
  ON p.period_year = c.period_year
 AND p.period_month = c.period_month
 AND p.region = c.region;

CREATE UNIQUE INDEX idx_fact_rr_region_month_key
    ON fact_rr_region_mensual(month_label, region);
CREATE VIEW v_rr_region_mensual AS
SELECT * FROM fact_rr_region_mensual;

CREATE TABLE fact_rr_modalidad_mensual AS
WITH promedio AS (
    SELECT
        period_year,
        period_month,
        modalidad,
        COUNT(*) AS semanas_disponibles,
        AVG(carga_asignada) AS carga_promedio_semanal,
        AVG(personas_activas) AS personas_promedio_semanal,
        AVG(rutas_activas) AS rutas_promedio_semanal,
        AVG(locales_asignados) AS locales_promedio_semanal,
        AVG(local_cliente_asignados) AS puntos_promedio_semanal,
        AVG(clientes_asignados) AS clientes_promedio_semanal
    FROM v_rr_modalidad_semanal
    GROUP BY period_year, period_month, modalidad
),
cierre AS (
    SELECT m.*
    FROM v_rr_modalidad_semanal AS m
    INNER JOIN v_rr_periodos AS p
      ON p.period_label = m.period_label
    WHERE p.is_last_week_month = 1
),
totales AS (
    SELECT
        period_label,
        SUM(carga_asignada) AS carga_total_cierre
    FROM cierre
    GROUP BY period_label
)
SELECT
    c.period_year,
    c.period_month,
    printf('%04d-%02d', c.period_year, c.period_month) AS month_label,
    c.period_label AS cierre_period_label,
    c.period_order AS cierre_period_order,
    c.modalidad,
    c.carga_asignada AS carga_cierre,
    ROUND(
        100.0 * c.carga_asignada / NULLIF(t.carga_total_cierre, 0),
        4
    ) AS participacion_carga_cierre_pct,
    c.personas_activas AS personas_cierre,
    c.rutas_activas AS rutas_cierre,
    c.locales_asignados AS locales_cierre,
    c.local_cliente_asignados AS puntos_cierre,
    c.clientes_asignados AS clientes_cierre,
    c.carga_por_persona AS carga_por_persona_cierre,
    ROUND(p.carga_promedio_semanal, 4) AS carga_promedio_semanal,
    ROUND(p.personas_promedio_semanal, 4) AS personas_promedio_semanal,
    ROUND(p.rutas_promedio_semanal, 4) AS rutas_promedio_semanal,
    ROUND(p.locales_promedio_semanal, 4) AS locales_promedio_semanal,
    ROUND(p.puntos_promedio_semanal, 4) AS puntos_promedio_semanal,
    ROUND(p.clientes_promedio_semanal, 4) AS clientes_promedio_semanal,
    p.semanas_disponibles
FROM cierre AS c
INNER JOIN totales AS t
  ON t.period_label = c.period_label
INNER JOIN promedio AS p
  ON p.period_year = c.period_year
 AND p.period_month = c.period_month
 AND p.modalidad = c.modalidad;

CREATE UNIQUE INDEX idx_fact_rr_modalidad_month_key
    ON fact_rr_modalidad_mensual(month_label, modalidad);
CREATE VIEW v_rr_modalidad_mensual AS
SELECT * FROM fact_rr_modalidad_mensual;

CREATE TABLE fact_rr_capacidad_mensual AS
WITH modalidad AS (
    SELECT
        month_label,
        MAX(CASE WHEN modalidad = 'MULTIMARCA' THEN carga_cierre END)
            AS carga_multimarca_cierre,
        MAX(CASE WHEN modalidad = 'MULTIMARCA' THEN personas_cierre END)
            AS personas_multimarca_cierre,
        MAX(CASE WHEN modalidad = 'MULTIMARCA' THEN locales_cierre END)
            AS locales_multimarca_cierre,
        MAX(CASE WHEN modalidad = 'MULTIMARCA' THEN puntos_cierre END)
            AS puntos_multimarca_cierre,
        MAX(CASE WHEN modalidad = 'PITUTO' THEN carga_cierre END)
            AS carga_pituto_cierre,
        MAX(CASE WHEN modalidad = 'PITUTO' THEN personas_cierre END)
            AS personas_pituto_cierre,
        MAX(CASE WHEN modalidad = 'PITUTO' THEN locales_cierre END)
            AS locales_pituto_cierre,
        MAX(CASE WHEN modalidad = 'PITUTO' THEN puntos_cierre END)
            AS puntos_pituto_cierre,
        MAX(CASE WHEN modalidad = 'MULTIMARCA' THEN carga_promedio_semanal END)
            AS carga_multimarca_promedio,
        MAX(CASE WHEN modalidad = 'PITUTO' THEN carga_promedio_semanal END)
            AS carga_pituto_promedio
    FROM v_rr_modalidad_mensual
    GROUP BY month_label
)
SELECT
    g.*,
    m.carga_multimarca_cierre,
    m.personas_multimarca_cierre,
    m.locales_multimarca_cierre,
    m.puntos_multimarca_cierre,
    ROUND(
        m.carga_multimarca_cierre / NULLIF(m.personas_multimarca_cierre, 0),
        4
    ) AS carga_por_persona_multimarca,
    m.carga_pituto_cierre,
    m.personas_pituto_cierre,
    m.locales_pituto_cierre,
    m.puntos_pituto_cierre,
    ROUND(
        m.carga_pituto_cierre / NULLIF(m.personas_pituto_cierre, 0),
        4
    ) AS carga_por_persona_pituto,
    m.carga_multimarca_promedio,
    m.carga_pituto_promedio
FROM v_rr_resumen_mensual AS g
LEFT JOIN modalidad AS m
  ON m.month_label = g.month_label;

CREATE UNIQUE INDEX idx_fact_rr_capacidad_month_key
    ON fact_rr_capacidad_mensual(month_label);
CREATE VIEW v_rr_capacidad_mensual AS
SELECT * FROM fact_rr_capacidad_mensual;

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
        MAX(CASE WHEN modalidad = 'MULTIMARCA' THEN personas_activas END)
            AS personas_multimarca,
        MAX(CASE WHEN modalidad = 'PITUTO' THEN carga_asignada END)
            AS carga_pituto,
        MAX(CASE WHEN modalidad = 'PITUTO' THEN personas_activas END)
            AS personas_pituto,
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
    modalidad.personas_multimarca,
    modalidad.carga_pituto,
    modalidad.personas_pituto,
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
