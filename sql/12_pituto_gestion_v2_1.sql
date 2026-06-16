-- 12_pituto_gestion_v2_1.sql
-- Propósito:
--   Corregir la semántica de PITUTO dentro del dashboard.
--
-- Regla de negocio confirmada:
--   - PITUTO no es una ruta.
--   - PITUTO corresponde a una gestión puntual contratada para atender un local.
--   - La dotación real de PITUTO vive en otra base y no debe inferirse desde
--     RUTERO ni REPONEDOR de RUTA RUTERO.
--   - La unidad analítica oficial de PITUTO en esta base es LOCAL/CLIENTE.
--
-- Métricas válidas para PITUTO:
--   - locales PITUTO       = COUNT DISTINCT LOCAL.
--   - gestiones PITUTO     = COUNT DISTINCT LOCAL/CLIENTE.
--   - clientes PITUTO      = COUNT DISTINCT CLIENTE.
--   - carga PITUTO         = SUM(MAX(VECES POR SEMANA) por LOCAL/CLIENTE).
--
-- Métricas expresamente no válidas en esta base:
--   - rutas PITUTO.
--   - personas PITUTO.
--   - carga PITUTO por persona.

DROP VIEW IF EXISTS v_rr_gerencial_v2_1_actual;
DROP VIEW IF EXISTS v_rr_retail_trust_operacion_mensual_v2_1;
DROP VIEW IF EXISTS v_rr_retail_trust_operacion_semanal_v2_1;
DROP VIEW IF EXISTS v_rr_region_retail_trust_v2_1;
DROP VIEW IF EXISTS v_rr_pituto_mensual;
DROP VIEW IF EXISTS v_rr_pituto_cliente_region_semanal;
DROP VIEW IF EXISTS v_rr_pituto_region_semanal;
DROP VIEW IF EXISTS v_rr_pituto_cliente_semanal;
DROP VIEW IF EXISTS v_rr_pituto_resumen_semanal;
DROP VIEW IF EXISTS v_rr_pituto_gestion_semanal;

DROP TABLE IF EXISTS fact_rr_retail_trust_operacion_mensual_v2_1;
DROP TABLE IF EXISTS fact_rr_retail_trust_operacion_semanal_v2_1;
DROP TABLE IF EXISTS fact_rr_region_retail_trust_v2_1;
DROP TABLE IF EXISTS fact_rr_pituto_mensual;
DROP TABLE IF EXISTS fact_rr_pituto_cliente_region_semanal;
DROP TABLE IF EXISTS fact_rr_pituto_region_semanal;
DROP TABLE IF EXISTS fact_rr_pituto_cliente_semanal;
DROP TABLE IF EXISTS fact_rr_pituto_resumen_semanal;
DROP TABLE IF EXISTS fact_rr_pituto_gestion_semanal;


-- -------------------------------------------------------------------------
-- 1. Grano PITUTO: PERÍODO + LOCAL/CLIENTE
-- -------------------------------------------------------------------------
CREATE TABLE fact_rr_pituto_gestion_semanal AS
SELECT
    period_year,
    period_month,
    period_week,
    period_label,
    period_order,
    cadena,
    cod_kpi_one,
    cliente,
    local_key,
    local_cliente_key,
    local,
    formato,
    COALESCE(NULLIF(TRIM(region), ''), 'SIN REGIÓN') AS region,
    COALESCE(NULLIF(TRIM(comuna), ''), 'SIN COMUNA') AS comuna,
    carga_asignada AS carga_pituto,
    1 AS gestion_pituto,
    personas_distintas AS registros_persona_informados,
    rutas_distintas AS registros_rutero_informados,
    reponedores AS reponedores_informados_auditoria,
    ruteros AS ruteros_informados_auditoria
FROM v_rr_local_cliente_modalidad_semana
WHERE modalidad = 'PITUTO';

CREATE UNIQUE INDEX idx_fact_rr_pituto_gestion_key
    ON fact_rr_pituto_gestion_semanal(
        period_label,
        cadena,
        cod_kpi_one,
        cliente
    );
CREATE INDEX idx_fact_rr_pituto_gestion_period
    ON fact_rr_pituto_gestion_semanal(period_order, cliente, region);

CREATE VIEW v_rr_pituto_gestion_semanal AS
SELECT * FROM fact_rr_pituto_gestion_semanal;


-- -------------------------------------------------------------------------
-- 2. Resumen PITUTO semanal
-- -------------------------------------------------------------------------
CREATE TABLE fact_rr_pituto_resumen_semanal AS
SELECT
    period_year,
    period_month,
    period_week,
    period_label,
    period_order,
    COUNT(DISTINCT local_key) AS pituto_locales,
    COUNT(DISTINCT local_cliente_key) AS pituto_gestiones,
    COUNT(DISTINCT cliente) AS pituto_clientes,
    COUNT(DISTINCT cadena) AS pituto_cadenas,
    COUNT(DISTINCT region) AS pituto_regiones,
    SUM(carga_pituto) AS pituto_carga,
    ROUND(
        1.0 * COUNT(DISTINCT local_cliente_key)
        / NULLIF(COUNT(DISTINCT local_key), 0),
        4
    ) AS gestiones_por_local,
    ROUND(
        SUM(carga_pituto)
        / NULLIF(COUNT(DISTINCT local_cliente_key), 0),
        4
    ) AS carga_por_gestion
FROM v_rr_pituto_gestion_semanal
GROUP BY
    period_year,
    period_month,
    period_week,
    period_label,
    period_order;

CREATE UNIQUE INDEX idx_fact_rr_pituto_resumen_key
    ON fact_rr_pituto_resumen_semanal(period_label);

CREATE VIEW v_rr_pituto_resumen_semanal AS
SELECT * FROM fact_rr_pituto_resumen_semanal;


-- -------------------------------------------------------------------------
-- 3. PITUTO por cliente
-- -------------------------------------------------------------------------
CREATE TABLE fact_rr_pituto_cliente_semanal AS
WITH base AS (
    SELECT
        period_year,
        period_month,
        period_week,
        period_label,
        period_order,
        cliente,
        COUNT(DISTINCT local_key) AS pituto_locales,
        COUNT(DISTINCT local_cliente_key) AS pituto_gestiones,
        COUNT(DISTINCT cadena) AS pituto_cadenas,
        COUNT(DISTINCT region) AS pituto_regiones,
        SUM(carga_pituto) AS pituto_carga
    FROM v_rr_pituto_gestion_semanal
    GROUP BY
        period_year,
        period_month,
        period_week,
        period_label,
        period_order,
        cliente
),
ranked AS (
    SELECT
        base.*,
        SUM(pituto_gestiones) OVER (PARTITION BY period_label)
            AS pituto_gestiones_total,
        SUM(pituto_carga) OVER (PARTITION BY period_label)
            AS pituto_carga_total,
        DENSE_RANK() OVER (
            PARTITION BY period_label
            ORDER BY pituto_gestiones DESC, pituto_carga DESC, cliente
        ) AS ranking_gestiones
    FROM base
)
SELECT
    ranked.*,
    ROUND(
        100.0 * pituto_gestiones / NULLIF(pituto_gestiones_total, 0),
        4
    ) AS participacion_gestiones_pct,
    ROUND(
        100.0 * pituto_carga / NULLIF(pituto_carga_total, 0),
        4
    ) AS participacion_carga_pct,
    ROUND(
        pituto_carga / NULLIF(pituto_gestiones, 0),
        4
    ) AS carga_por_gestion
FROM ranked;

CREATE UNIQUE INDEX idx_fact_rr_pituto_cliente_key
    ON fact_rr_pituto_cliente_semanal(period_label, cliente);
CREATE INDEX idx_fact_rr_pituto_cliente_rank
    ON fact_rr_pituto_cliente_semanal(period_label, ranking_gestiones);

CREATE VIEW v_rr_pituto_cliente_semanal AS
SELECT * FROM fact_rr_pituto_cliente_semanal;


-- -------------------------------------------------------------------------
-- 4. PITUTO por región
-- -------------------------------------------------------------------------
CREATE TABLE fact_rr_pituto_region_semanal AS
WITH base AS (
    SELECT
        period_year,
        period_month,
        period_week,
        period_label,
        period_order,
        region,
        COUNT(DISTINCT local_key) AS pituto_locales,
        COUNT(DISTINCT local_cliente_key) AS pituto_gestiones,
        COUNT(DISTINCT cliente) AS pituto_clientes,
        COUNT(DISTINCT cadena) AS pituto_cadenas,
        SUM(carga_pituto) AS pituto_carga
    FROM v_rr_pituto_gestion_semanal
    GROUP BY
        period_year,
        period_month,
        period_week,
        period_label,
        period_order,
        region
),
ranked AS (
    SELECT
        base.*,
        SUM(pituto_gestiones) OVER (PARTITION BY period_label)
            AS pituto_gestiones_total,
        SUM(pituto_carga) OVER (PARTITION BY period_label)
            AS pituto_carga_total,
        DENSE_RANK() OVER (
            PARTITION BY period_label
            ORDER BY pituto_gestiones DESC, pituto_carga DESC, region
        ) AS ranking_gestiones
    FROM base
)
SELECT
    ranked.*,
    ROUND(
        100.0 * pituto_gestiones / NULLIF(pituto_gestiones_total, 0),
        4
    ) AS participacion_gestiones_pct,
    ROUND(
        100.0 * pituto_carga / NULLIF(pituto_carga_total, 0),
        4
    ) AS participacion_carga_pct,
    ROUND(
        1.0 * pituto_gestiones / NULLIF(pituto_locales, 0),
        4
    ) AS gestiones_por_local
FROM ranked;

CREATE UNIQUE INDEX idx_fact_rr_pituto_region_key
    ON fact_rr_pituto_region_semanal(period_label, region);
CREATE INDEX idx_fact_rr_pituto_region_rank
    ON fact_rr_pituto_region_semanal(period_label, ranking_gestiones);

CREATE VIEW v_rr_pituto_region_semanal AS
SELECT * FROM fact_rr_pituto_region_semanal;


-- -------------------------------------------------------------------------
-- 5. PITUTO cliente x región para drilldown
-- -------------------------------------------------------------------------
CREATE TABLE fact_rr_pituto_cliente_region_semanal AS
SELECT
    period_year,
    period_month,
    period_week,
    period_label,
    period_order,
    region,
    cliente,
    COUNT(DISTINCT local_key) AS pituto_locales,
    COUNT(DISTINCT local_cliente_key) AS pituto_gestiones,
    COUNT(DISTINCT cadena) AS pituto_cadenas,
    SUM(carga_pituto) AS pituto_carga,
    GROUP_CONCAT(DISTINCT cadena) AS cadenas
FROM v_rr_pituto_gestion_semanal
GROUP BY
    period_year,
    period_month,
    period_week,
    period_label,
    period_order,
    region,
    cliente;

CREATE UNIQUE INDEX idx_fact_rr_pituto_cliente_region_key
    ON fact_rr_pituto_cliente_region_semanal(period_label, region, cliente);

CREATE VIEW v_rr_pituto_cliente_region_semanal AS
SELECT * FROM fact_rr_pituto_cliente_region_semanal;


-- -------------------------------------------------------------------------
-- 6. PITUTO mensual: último corte disponible y promedio semanal
-- -------------------------------------------------------------------------
CREATE TABLE fact_rr_pituto_mensual AS
WITH promedio AS (
    SELECT
        period_year,
        period_month,
        COUNT(*) AS semanas_disponibles,
        AVG(pituto_locales) AS pituto_locales_promedio_semanal,
        AVG(pituto_gestiones) AS pituto_gestiones_promedio_semanal,
        AVG(pituto_clientes) AS pituto_clientes_promedio_semanal,
        AVG(pituto_carga) AS pituto_carga_promedio_semanal
    FROM v_rr_pituto_resumen_semanal
    GROUP BY period_year, period_month
),
corte AS (
    SELECT p.*
    FROM v_rr_pituto_resumen_semanal AS p
    INNER JOIN v_rr_periodos AS calendario
      ON calendario.period_label = p.period_label
    WHERE calendario.is_last_week_month = 1
)
SELECT
    c.period_year,
    c.period_month,
    printf('%04d-%02d', c.period_year, c.period_month) AS month_label,
    c.period_label AS corte_period_label,
    c.period_order AS corte_period_order,
    c.pituto_locales AS pituto_locales_corte,
    c.pituto_gestiones AS pituto_gestiones_corte,
    c.pituto_clientes AS pituto_clientes_corte,
    c.pituto_cadenas AS pituto_cadenas_corte,
    c.pituto_regiones AS pituto_regiones_corte,
    c.pituto_carga AS pituto_carga_corte,
    c.gestiones_por_local AS gestiones_por_local_corte,
    c.carga_por_gestion AS carga_por_gestion_corte,
    ROUND(p.pituto_locales_promedio_semanal, 4)
        AS pituto_locales_promedio_semanal,
    ROUND(p.pituto_gestiones_promedio_semanal, 4)
        AS pituto_gestiones_promedio_semanal,
    ROUND(p.pituto_clientes_promedio_semanal, 4)
        AS pituto_clientes_promedio_semanal,
    ROUND(p.pituto_carga_promedio_semanal, 4)
        AS pituto_carga_promedio_semanal,
    p.semanas_disponibles
FROM corte AS c
INNER JOIN promedio AS p
  ON p.period_year = c.period_year
 AND p.period_month = c.period_month;

CREATE UNIQUE INDEX idx_fact_rr_pituto_month_key
    ON fact_rr_pituto_mensual(month_label);

CREATE VIEW v_rr_pituto_mensual AS
SELECT * FROM fact_rr_pituto_mensual;


-- -------------------------------------------------------------------------
-- 7. Capacidad regional RT corregida
--    MULTIMARCA se mide por rutas/personas; PITUTO por gestiones/locales.
-- -------------------------------------------------------------------------
CREATE TABLE fact_rr_region_retail_trust_v2_1 AS
WITH mm AS (
    SELECT
        period_label,
        region,
        carga_asignada AS carga_multimarca,
        locales_asignados AS multimarca_locales,
        puntos_gestion_asignados AS multimarca_gestiones,
        clientes_asignados AS multimarca_clientes,
        personas_activas AS personas_multimarca_con_presencia,
        rutas_con_presencia AS rutas_multimarca
    FROM v_rr_region_modalidad_semanal
    WHERE modalidad = 'MULTIMARCA'
),
pituto AS (
    SELECT
        period_label,
        region,
        pituto_carga,
        pituto_locales,
        pituto_gestiones,
        pituto_clientes
    FROM v_rr_pituto_region_semanal
)
SELECT
    rt.period_year,
    rt.period_month,
    rt.period_week,
    rt.period_label,
    rt.period_order,
    rt.region,
    rt.carga_retail_trust,
    rt.participacion_rt_region_pct,
    rt.locales_retail_trust,
    rt.puntos_retail_trust,
    rt.clientes_retail_trust,
    COALESCE(mm.carga_multimarca, 0) AS carga_multimarca,
    COALESCE(mm.multimarca_locales, 0) AS multimarca_locales,
    COALESCE(mm.multimarca_gestiones, 0) AS multimarca_gestiones,
    COALESCE(mm.multimarca_clientes, 0) AS multimarca_clientes,
    COALESCE(mm.personas_multimarca_con_presencia, 0)
        AS personas_multimarca_con_presencia,
    COALESCE(mm.rutas_multimarca, 0) AS rutas_multimarca,
    ROUND(
        COALESCE(mm.carga_multimarca, 0)
        / NULLIF(mm.rutas_multimarca, 0),
        4
    ) AS carga_por_ruta_multimarca,
    ROUND(
        1.0 * COALESCE(mm.multimarca_locales, 0)
        / NULLIF(mm.rutas_multimarca, 0),
        4
    ) AS locales_por_ruta_multimarca,
    ROUND(
        1.0 * COALESCE(mm.multimarca_gestiones, 0)
        / NULLIF(mm.rutas_multimarca, 0),
        4
    ) AS gestiones_por_ruta_multimarca,
    COALESCE(p.pituto_carga, 0) AS pituto_carga,
    COALESCE(p.pituto_locales, 0) AS pituto_locales,
    COALESCE(p.pituto_gestiones, 0) AS pituto_gestiones,
    COALESCE(p.pituto_clientes, 0) AS pituto_clientes,
    ROUND(
        100.0 * COALESCE(p.pituto_gestiones, 0)
        / NULLIF(rt.puntos_retail_trust, 0),
        4
    ) AS peso_pituto_en_gestiones_rt_pct
FROM v_rr_region_retail_trust_semanal AS rt
LEFT JOIN mm
  ON mm.period_label = rt.period_label
 AND mm.region = rt.region
LEFT JOIN pituto AS p
  ON p.period_label = rt.period_label
 AND p.region = rt.region;

CREATE UNIQUE INDEX idx_fact_rr_region_rt_v21_key
    ON fact_rr_region_retail_trust_v2_1(period_label, region);

CREATE VIEW v_rr_region_retail_trust_v2_1 AS
SELECT * FROM fact_rr_region_retail_trust_v2_1;


-- -------------------------------------------------------------------------
-- 8. Operación Retail Trust semanal corregida
-- -------------------------------------------------------------------------
CREATE TABLE fact_rr_retail_trust_operacion_semanal_v2_1 AS
WITH rt AS (
    SELECT *
    FROM v_rr_servicio_semanal
    WHERE servicio_operativo = 'RETAIL TRUST'
),
mm AS (
    SELECT *
    FROM v_rr_modalidad_semanal
    WHERE modalidad = 'MULTIMARCA'
),
pituto AS (
    SELECT *
    FROM v_rr_pituto_resumen_semanal
)
SELECT
    rt.period_year,
    rt.period_month,
    rt.period_week,
    rt.period_label,
    rt.period_order,
    rt.carga_servicio AS carga_retail_trust,
    rt.locales_activos AS locales_retail_trust,
    rt.puntos_gestion AS gestiones_retail_trust,
    rt.clientes_activos AS clientes_retail_trust,
    mm.rutas_activas AS rutas_multimarca,
    mm.personas_activas AS personas_multimarca,
    mm.locales_asignados AS multimarca_locales,
    mm.local_cliente_asignados AS multimarca_gestiones,
    mm.clientes_asignados AS multimarca_clientes,
    mm.carga_asignada AS carga_multimarca,
    ROUND(
        mm.carga_asignada / NULLIF(mm.rutas_activas, 0),
        4
    ) AS carga_por_ruta_multimarca,
    ROUND(
        1.0 * mm.locales_asignados / NULLIF(mm.rutas_activas, 0),
        4
    ) AS locales_por_ruta_multimarca,
    ROUND(
        1.0 * mm.local_cliente_asignados / NULLIF(mm.rutas_activas, 0),
        4
    ) AS gestiones_por_ruta_multimarca,
    pituto.pituto_locales,
    pituto.pituto_gestiones,
    pituto.pituto_clientes,
    pituto.pituto_carga,
    pituto.gestiones_por_local AS pituto_gestiones_por_local,
    pituto.carga_por_gestion AS pituto_carga_por_gestion,
    ROUND(
        100.0 * pituto.pituto_gestiones
        / NULLIF(rt.puntos_gestion, 0),
        4
    ) AS peso_pituto_en_gestiones_rt_pct,
    ROUND(
        100.0 * mm.local_cliente_asignados
        / NULLIF(mm.local_cliente_asignados + pituto.pituto_gestiones, 0),
        4
    ) AS peso_multimarca_asignado_pct,
    ROUND(
        100.0 * pituto.pituto_gestiones
        / NULLIF(mm.local_cliente_asignados + pituto.pituto_gestiones, 0),
        4
    ) AS peso_pituto_asignado_pct,
    (
        mm.carga_asignada
        + pituto.pituto_carga
        - rt.carga_servicio
    ) AS solapamiento_carga_mm_pituto
FROM rt
INNER JOIN mm
  ON mm.period_label = rt.period_label
INNER JOIN pituto
  ON pituto.period_label = rt.period_label;

CREATE UNIQUE INDEX idx_fact_rr_rt_operacion_v21_key
    ON fact_rr_retail_trust_operacion_semanal_v2_1(period_label);

CREATE VIEW v_rr_retail_trust_operacion_semanal_v2_1 AS
SELECT * FROM fact_rr_retail_trust_operacion_semanal_v2_1;


-- -------------------------------------------------------------------------
-- 9. Operación Retail Trust mensual corregida
-- -------------------------------------------------------------------------
CREATE TABLE fact_rr_retail_trust_operacion_mensual_v2_1 AS
WITH promedio AS (
    SELECT
        period_year,
        period_month,
        COUNT(*) AS semanas_disponibles,
        AVG(carga_retail_trust) AS carga_rt_promedio_semanal,
        AVG(rutas_multimarca) AS rutas_mm_promedio_semanal,
        AVG(personas_multimarca) AS personas_mm_promedio_semanal,
        AVG(multimarca_locales) AS locales_mm_promedio_semanal,
        AVG(multimarca_gestiones) AS gestiones_mm_promedio_semanal,
        AVG(carga_por_ruta_multimarca) AS carga_por_ruta_mm_promedio,
        AVG(locales_por_ruta_multimarca) AS locales_por_ruta_mm_promedio,
        AVG(gestiones_por_ruta_multimarca) AS gestiones_por_ruta_mm_promedio,
        AVG(pituto_locales) AS pituto_locales_promedio_semanal,
        AVG(pituto_gestiones) AS pituto_gestiones_promedio_semanal,
        AVG(pituto_carga) AS pituto_carga_promedio_semanal
    FROM v_rr_retail_trust_operacion_semanal_v2_1
    GROUP BY period_year, period_month
),
corte AS (
    SELECT rt.*
    FROM v_rr_retail_trust_operacion_semanal_v2_1 AS rt
    INNER JOIN v_rr_periodos AS calendario
      ON calendario.period_label = rt.period_label
    WHERE calendario.is_last_week_month = 1
)
SELECT
    c.period_year,
    c.period_month,
    printf('%04d-%02d', c.period_year, c.period_month) AS month_label,
    c.period_label AS corte_period_label,
    c.period_order AS corte_period_order,
    c.carga_retail_trust AS carga_rt_corte,
    c.locales_retail_trust AS locales_rt_corte,
    c.gestiones_retail_trust AS gestiones_rt_corte,
    c.clientes_retail_trust AS clientes_rt_corte,
    c.rutas_multimarca AS rutas_mm_corte,
    c.personas_multimarca AS personas_mm_corte,
    c.multimarca_locales AS locales_mm_corte,
    c.multimarca_gestiones AS gestiones_mm_corte,
    c.carga_multimarca AS carga_mm_corte,
    c.carga_por_ruta_multimarca AS carga_por_ruta_mm_corte,
    c.locales_por_ruta_multimarca AS locales_por_ruta_mm_corte,
    c.gestiones_por_ruta_multimarca AS gestiones_por_ruta_mm_corte,
    c.pituto_locales AS pituto_locales_corte,
    c.pituto_gestiones AS pituto_gestiones_corte,
    c.pituto_clientes AS pituto_clientes_corte,
    c.pituto_carga AS pituto_carga_corte,
    c.pituto_gestiones_por_local,
    c.pituto_carga_por_gestion,
    c.peso_pituto_en_gestiones_rt_pct,
    c.solapamiento_carga_mm_pituto,
    ROUND(p.carga_rt_promedio_semanal, 4) AS carga_rt_promedio_semanal,
    ROUND(p.rutas_mm_promedio_semanal, 4) AS rutas_mm_promedio_semanal,
    ROUND(p.personas_mm_promedio_semanal, 4) AS personas_mm_promedio_semanal,
    ROUND(p.locales_mm_promedio_semanal, 4) AS locales_mm_promedio_semanal,
    ROUND(p.gestiones_mm_promedio_semanal, 4) AS gestiones_mm_promedio_semanal,
    ROUND(p.carga_por_ruta_mm_promedio, 4) AS carga_por_ruta_mm_promedio,
    ROUND(p.locales_por_ruta_mm_promedio, 4) AS locales_por_ruta_mm_promedio,
    ROUND(p.gestiones_por_ruta_mm_promedio, 4) AS gestiones_por_ruta_mm_promedio,
    ROUND(p.pituto_locales_promedio_semanal, 4)
        AS pituto_locales_promedio_semanal,
    ROUND(p.pituto_gestiones_promedio_semanal, 4)
        AS pituto_gestiones_promedio_semanal,
    ROUND(p.pituto_carga_promedio_semanal, 4)
        AS pituto_carga_promedio_semanal,
    p.semanas_disponibles
FROM corte AS c
INNER JOIN promedio AS p
  ON p.period_year = c.period_year
 AND p.period_month = c.period_month;

CREATE UNIQUE INDEX idx_fact_rr_rt_operacion_month_v21_key
    ON fact_rr_retail_trust_operacion_mensual_v2_1(month_label);

CREATE VIEW v_rr_retail_trust_operacion_mensual_v2_1 AS
SELECT * FROM fact_rr_retail_trust_operacion_mensual_v2_1;


-- -------------------------------------------------------------------------
-- 10. Fotografía gerencial V2.1
--     Conserva campos V2 por compatibilidad, pero agrega campos correctos.
--     El frontend no debe utilizar personas_pituto ni personas_retail_trust.
-- -------------------------------------------------------------------------
CREATE VIEW v_rr_gerencial_v2_1_actual AS
SELECT
    g.*,
    rt.rutas_multimarca AS rutas_multimarca_v21,
    rt.personas_multimarca AS personas_multimarca_v21,
    rt.multimarca_locales AS multimarca_locales_v21,
    rt.multimarca_gestiones AS multimarca_gestiones_v21,
    rt.carga_por_ruta_multimarca AS carga_por_ruta_multimarca_v21,
    rt.pituto_locales,
    rt.pituto_gestiones,
    rt.pituto_clientes,
    rt.pituto_carga,
    rt.pituto_gestiones_por_local,
    rt.pituto_carga_por_gestion,
    rt.peso_pituto_en_gestiones_rt_pct,
    rt.solapamiento_carga_mm_pituto
FROM v_rr_gerencial_v2_actual AS g
INNER JOIN v_rr_retail_trust_operacion_semanal_v2_1 AS rt
  ON rt.period_label = g.period_label;
