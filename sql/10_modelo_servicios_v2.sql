-- 10_modelo_servicios_v2.sql
-- Propósito:
--   Separar la operación en servicios reales:
--     1) RETAIL TRUST: MULTIMARCA + PITUTO.
--     2) BREDEN MASTER: servicio independiente.
--     3) PROPAL: servicio independiente.
--
-- Reglas:
--   - El total empresa conserva todos los registros.
--   - El peso por servicio deduplica LOCAL/CLIENTE dentro de cada servicio.
--   - La capacidad regional de Retail Trust usa:
--       MULTIMARCA -> rutas estructurales por RUTERO.
--       PITUTO     -> capacidad flexible por REPONEDOR.
--   - BREDEN MASTER y PROPAL no participan en la presión de rutas RT.

DROP VIEW IF EXISTS v_rr_gerencial_v2_actual;
DROP VIEW IF EXISTS v_rr_retail_trust_mensual;
DROP VIEW IF EXISTS v_rr_servicio_mensual;
DROP VIEW IF EXISTS v_rr_region_retail_trust_semanal;
DROP VIEW IF EXISTS v_rr_servicio_semanal;
DROP VIEW IF EXISTS v_rr_servicio_local_cliente_semana;

DROP TABLE IF EXISTS fact_rr_retail_trust_mensual;
DROP TABLE IF EXISTS fact_rr_servicio_mensual;
DROP TABLE IF EXISTS fact_rr_region_retail_trust_semanal;
DROP TABLE IF EXISTS fact_rr_servicio_semanal;
DROP TABLE IF EXISTS fact_rr_servicio_local_cliente_semana;

CREATE TABLE fact_rr_servicio_local_cliente_semana AS
WITH clasificado AS (
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
        region,
        comuna,
        modalidad,
        carga_asignada,
        CASE
            WHEN modalidad IN ('MULTIMARCA', 'PITUTO') THEN 'RETAIL TRUST'
            WHEN modalidad = 'BREDEN' THEN 'BREDEN MASTER'
            WHEN modalidad = 'PROPAL' THEN 'PROPAL'
            ELSE 'OTROS'
        END AS servicio_operativo
    FROM v_rr_local_cliente_modalidad_semana
)
SELECT
    period_year,
    period_month,
    period_week,
    period_label,
    period_order,
    servicio_operativo,
    cadena,
    cod_kpi_one,
    cliente,
    local_key,
    local_cliente_key,
    MAX(local) AS local,
    MAX(formato) AS formato,
    COALESCE(MAX(NULLIF(TRIM(region), '')), 'SIN REGIÓN') AS region,
    MAX(comuna) AS comuna,
    MAX(carga_asignada) AS carga_servicio_contable,
    SUM(carga_asignada) AS carga_modalidades_asignada,
    COUNT(DISTINCT modalidad) AS modalidades_presentes,
    GROUP_CONCAT(DISTINCT modalidad) AS modalidades
FROM clasificado
WHERE servicio_operativo <> 'OTROS'
GROUP BY
    period_year,
    period_month,
    period_week,
    period_label,
    period_order,
    servicio_operativo,
    cadena,
    cod_kpi_one,
    cliente,
    local_key,
    local_cliente_key;

CREATE UNIQUE INDEX idx_fact_rr_servicio_lc_key
    ON fact_rr_servicio_local_cliente_semana(
        period_label,
        servicio_operativo,
        cadena,
        cod_kpi_one,
        cliente
    );
CREATE INDEX idx_fact_rr_servicio_lc_period
    ON fact_rr_servicio_local_cliente_semana(period_label, servicio_operativo);
CREATE VIEW v_rr_servicio_local_cliente_semana AS
SELECT * FROM fact_rr_servicio_local_cliente_semana;

CREATE TABLE fact_rr_servicio_semanal AS
WITH operacion AS (
    SELECT
        period_year,
        period_month,
        period_week,
        period_label,
        period_order,
        servicio_operativo,
        SUM(carga_servicio_contable) AS carga_servicio,
        SUM(carga_modalidades_asignada) AS carga_modalidades_asignada,
        COUNT(DISTINCT local_key) AS locales_activos,
        COUNT(*) AS puntos_gestion,
        COUNT(DISTINCT cliente) AS clientes_activos
    FROM v_rr_servicio_local_cliente_semana
    GROUP BY
        period_year,
        period_month,
        period_week,
        period_label,
        period_order,
        servicio_operativo
),
dotacion AS (
    SELECT
        period_label,
        CASE
            WHEN modalidad IN ('MULTIMARCA', 'PITUTO') THEN 'RETAIL TRUST'
            WHEN modalidad = 'BREDEN' THEN 'BREDEN MASTER'
            WHEN modalidad = 'PROPAL' THEN 'PROPAL'
        END AS servicio_operativo,
        COUNT(DISTINCT reponedor) AS personas_activas,
        COUNT(DISTINCT rutero) AS codigos_ruta,
        COUNT(DISTINCT CASE WHEN modalidad = 'MULTIMARCA' THEN rutero END)
            AS rutas_multimarca,
        COUNT(DISTINCT CASE WHEN modalidad = 'PITUTO' THEN reponedor END)
            AS personas_pituto,
        COUNT(DISTINCT CASE WHEN modalidad = 'BREDEN' THEN rutero END)
            AS rutas_breden,
        COUNT(DISTINCT CASE WHEN modalidad = 'PROPAL' THEN reponedor END)
            AS personas_propal
    FROM v_rr_base_normalizada
    WHERE tipo_rutero = 'PERSONA'
      AND modalidad IN ('MULTIMARCA', 'PITUTO', 'BREDEN', 'PROPAL')
      AND reponedor IS NOT NULL
    GROUP BY
        period_label,
        CASE
            WHEN modalidad IN ('MULTIMARCA', 'PITUTO') THEN 'RETAIL TRUST'
            WHEN modalidad = 'BREDEN' THEN 'BREDEN MASTER'
            WHEN modalidad = 'PROPAL' THEN 'PROPAL'
        END
),
base AS (
    SELECT
        o.*,
        COALESCE(d.personas_activas, 0) AS personas_activas,
        COALESCE(d.codigos_ruta, 0) AS codigos_ruta,
        COALESCE(d.rutas_multimarca, 0) AS rutas_multimarca,
        COALESCE(d.personas_pituto, 0) AS personas_pituto,
        COALESCE(d.rutas_breden, 0) AS rutas_breden,
        COALESCE(d.personas_propal, 0) AS personas_propal,
        SUM(o.carga_servicio) OVER (PARTITION BY o.period_label)
            AS carga_servicios_total
    FROM operacion AS o
    LEFT JOIN dotacion AS d
      ON d.period_label = o.period_label
     AND d.servicio_operativo = o.servicio_operativo
)
SELECT
    base.*,
    ROUND(
        100.0 * carga_servicio / NULLIF(carga_servicios_total, 0),
        4
    ) AS participacion_servicio_pct,
    ROUND(
        carga_servicio / NULLIF(personas_activas, 0),
        4
    ) AS carga_por_persona,
    ROUND(
        1.0 * puntos_gestion / NULLIF(personas_activas, 0),
        4
    ) AS puntos_por_persona
FROM base;

CREATE UNIQUE INDEX idx_fact_rr_servicio_key
    ON fact_rr_servicio_semanal(period_label, servicio_operativo);
CREATE VIEW v_rr_servicio_semanal AS
SELECT * FROM fact_rr_servicio_semanal;

CREATE TABLE fact_rr_region_retail_trust_semanal AS
WITH operacion AS (
    SELECT
        period_year,
        period_month,
        period_week,
        period_label,
        period_order,
        region,
        SUM(carga_servicio_contable) AS carga_retail_trust,
        COUNT(DISTINCT local_key) AS locales_retail_trust,
        COUNT(*) AS puntos_retail_trust,
        COUNT(DISTINCT cliente) AS clientes_retail_trust
    FROM v_rr_servicio_local_cliente_semana
    WHERE servicio_operativo = 'RETAIL TRUST'
    GROUP BY
        period_year,
        period_month,
        period_week,
        period_label,
        period_order,
        region
),
asignacion AS (
    SELECT
        period_label,
        COALESCE(NULLIF(TRIM(region), ''), 'SIN REGIÓN') AS region,
        SUM(CASE WHEN modalidad = 'MULTIMARCA' THEN carga_asignada ELSE 0 END)
            AS carga_multimarca,
        SUM(CASE WHEN modalidad = 'PITUTO' THEN carga_asignada ELSE 0 END)
            AS carga_pituto
    FROM v_rr_region_modalidad_semanal
    WHERE modalidad IN ('MULTIMARCA', 'PITUTO')
    GROUP BY period_label, COALESCE(NULLIF(TRIM(region), ''), 'SIN REGIÓN')
),
dotacion AS (
    SELECT
        period_label,
        COALESCE(NULLIF(TRIM(region), ''), 'SIN REGIÓN') AS region,
        COUNT(DISTINCT CASE WHEN modalidad = 'MULTIMARCA' THEN rutero END)
            AS rutas_multimarca,
        COUNT(DISTINCT CASE WHEN modalidad = 'MULTIMARCA' THEN reponedor END)
            AS personas_multimarca,
        COUNT(DISTINCT CASE WHEN modalidad = 'PITUTO' THEN reponedor END)
            AS personas_pituto,
        COUNT(DISTINCT CASE
            WHEN modalidad IN ('MULTIMARCA', 'PITUTO') THEN reponedor
        END) AS personas_retail_trust
    FROM v_rr_base_normalizada
    WHERE tipo_rutero = 'PERSONA'
      AND modalidad IN ('MULTIMARCA', 'PITUTO')
    GROUP BY
        period_label,
        COALESCE(NULLIF(TRIM(region), ''), 'SIN REGIÓN')
),
base AS (
    SELECT
        o.*,
        COALESCE(a.carga_multimarca, 0) AS carga_multimarca,
        COALESCE(a.carga_pituto, 0) AS carga_pituto,
        COALESCE(d.rutas_multimarca, 0) AS rutas_multimarca,
        COALESCE(d.personas_multimarca, 0) AS personas_multimarca,
        COALESCE(d.personas_pituto, 0) AS personas_pituto,
        COALESCE(d.personas_retail_trust, 0) AS personas_retail_trust,
        SUM(o.carga_retail_trust) OVER (PARTITION BY o.period_label)
            AS carga_retail_trust_total
    FROM operacion AS o
    LEFT JOIN asignacion AS a
      ON a.period_label = o.period_label
     AND a.region = o.region
    LEFT JOIN dotacion AS d
      ON d.period_label = o.period_label
     AND d.region = o.region
)
SELECT
    base.*,
    ROUND(
        100.0 * carga_retail_trust / NULLIF(carga_retail_trust_total, 0),
        4
    ) AS participacion_rt_region_pct,
    ROUND(
        carga_multimarca / NULLIF(rutas_multimarca, 0),
        4
    ) AS carga_por_ruta_multimarca,
    ROUND(
        carga_pituto / NULLIF(personas_pituto, 0),
        4
    ) AS carga_pituto_por_persona,
    ROUND(
        carga_retail_trust / NULLIF(personas_retail_trust, 0),
        4
    ) AS carga_rt_por_persona,
    ROUND(
        1.0 * puntos_retail_trust / NULLIF(personas_retail_trust, 0),
        4
    ) AS puntos_rt_por_persona
FROM base;

CREATE UNIQUE INDEX idx_fact_rr_region_rt_key
    ON fact_rr_region_retail_trust_semanal(period_label, region);
CREATE VIEW v_rr_region_retail_trust_semanal AS
SELECT * FROM fact_rr_region_retail_trust_semanal;

CREATE TABLE fact_rr_servicio_mensual AS
WITH promedio AS (
    SELECT
        period_year,
        period_month,
        servicio_operativo,
        COUNT(*) AS semanas_disponibles,
        AVG(carga_servicio) AS carga_promedio_semanal,
        AVG(locales_activos) AS locales_promedio_semanal,
        AVG(puntos_gestion) AS puntos_promedio_semanal,
        AVG(clientes_activos) AS clientes_promedio_semanal,
        AVG(personas_activas) AS personas_promedio_semanal
    FROM v_rr_servicio_semanal
    GROUP BY period_year, period_month, servicio_operativo
),
corte AS (
    SELECT s.*
    FROM v_rr_servicio_semanal AS s
    INNER JOIN v_rr_periodos AS p
      ON p.period_label = s.period_label
    WHERE p.is_last_week_month = 1
)
SELECT
    c.period_year,
    c.period_month,
    printf('%04d-%02d', c.period_year, c.period_month) AS month_label,
    c.period_label AS corte_period_label,
    c.period_order AS corte_period_order,
    c.servicio_operativo,
    c.carga_servicio AS carga_corte,
    c.participacion_servicio_pct AS participacion_corte_pct,
    c.locales_activos AS locales_corte,
    c.puntos_gestion AS puntos_corte,
    c.clientes_activos AS clientes_corte,
    c.personas_activas AS personas_corte,
    c.rutas_multimarca AS rutas_multimarca_corte,
    c.personas_pituto AS personas_pituto_corte,
    c.rutas_breden AS rutas_breden_corte,
    c.personas_propal AS personas_propal_corte,
    ROUND(p.carga_promedio_semanal, 4) AS carga_promedio_semanal,
    ROUND(p.locales_promedio_semanal, 4) AS locales_promedio_semanal,
    ROUND(p.puntos_promedio_semanal, 4) AS puntos_promedio_semanal,
    ROUND(p.clientes_promedio_semanal, 4) AS clientes_promedio_semanal,
    ROUND(p.personas_promedio_semanal, 4) AS personas_promedio_semanal,
    p.semanas_disponibles
FROM corte AS c
INNER JOIN promedio AS p
  ON p.period_year = c.period_year
 AND p.period_month = c.period_month
 AND p.servicio_operativo = c.servicio_operativo;

CREATE UNIQUE INDEX idx_fact_rr_servicio_month_key
    ON fact_rr_servicio_mensual(month_label, servicio_operativo);
CREATE VIEW v_rr_servicio_mensual AS
SELECT * FROM fact_rr_servicio_mensual;

CREATE TABLE fact_rr_retail_trust_mensual AS
WITH servicio AS (
    SELECT *
    FROM v_rr_servicio_mensual
    WHERE servicio_operativo = 'RETAIL TRUST'
),
modalidad AS (
    SELECT
        month_label,
        MAX(CASE WHEN modalidad = 'MULTIMARCA' THEN carga_cierre END)
            AS carga_multimarca_corte,
        MAX(CASE WHEN modalidad = 'MULTIMARCA' THEN personas_cierre END)
            AS personas_multimarca_corte,
        MAX(CASE WHEN modalidad = 'MULTIMARCA' THEN locales_cierre END)
            AS locales_multimarca_corte,
        MAX(CASE WHEN modalidad = 'MULTIMARCA' THEN puntos_cierre END)
            AS puntos_multimarca_corte,
        MAX(CASE WHEN modalidad = 'PITUTO' THEN carga_cierre END)
            AS carga_pituto_corte,
        MAX(CASE WHEN modalidad = 'PITUTO' THEN personas_cierre END)
            AS personas_pituto_corte,
        MAX(CASE WHEN modalidad = 'PITUTO' THEN locales_cierre END)
            AS locales_pituto_corte,
        MAX(CASE WHEN modalidad = 'PITUTO' THEN puntos_cierre END)
            AS puntos_pituto_corte
    FROM v_rr_modalidad_mensual
    WHERE modalidad IN ('MULTIMARCA', 'PITUTO')
    GROUP BY month_label
)
SELECT
    s.*,
    m.carga_multimarca_corte,
    m.personas_multimarca_corte,
    m.locales_multimarca_corte,
    m.puntos_multimarca_corte,
    m.carga_pituto_corte,
    m.personas_pituto_corte,
    m.locales_pituto_corte,
    m.puntos_pituto_corte,
    ROUND(
        100.0 * m.carga_multimarca_corte
        / NULLIF(m.carga_multimarca_corte + m.carga_pituto_corte, 0),
        4
    ) AS peso_multimarca_dentro_rt_pct,
    ROUND(
        100.0 * m.carga_pituto_corte
        / NULLIF(m.carga_multimarca_corte + m.carga_pituto_corte, 0),
        4
    ) AS peso_pituto_dentro_rt_pct
FROM servicio AS s
LEFT JOIN modalidad AS m
  ON m.month_label = s.month_label;

CREATE UNIQUE INDEX idx_fact_rr_rt_month_key
    ON fact_rr_retail_trust_mensual(month_label);
CREATE VIEW v_rr_retail_trust_mensual AS
SELECT * FROM fact_rr_retail_trust_mensual;

CREATE VIEW v_rr_gerencial_v2_actual AS
WITH latest AS (
    SELECT period_label
    FROM v_rr_periodos
    WHERE is_latest_period = 1
),
servicios AS (
    SELECT
        MAX(CASE WHEN servicio_operativo = 'RETAIL TRUST' THEN carga_servicio END)
            AS carga_retail_trust,
        MAX(CASE WHEN servicio_operativo = 'RETAIL TRUST' THEN personas_activas END)
            AS personas_retail_trust,
        MAX(CASE WHEN servicio_operativo = 'RETAIL TRUST' THEN participacion_servicio_pct END)
            AS peso_retail_trust_pct,
        MAX(CASE WHEN servicio_operativo = 'BREDEN MASTER' THEN carga_servicio END)
            AS carga_breden_master,
        MAX(CASE WHEN servicio_operativo = 'BREDEN MASTER' THEN personas_activas END)
            AS personas_breden_master,
        MAX(CASE WHEN servicio_operativo = 'BREDEN MASTER' THEN rutas_breden END)
            AS rutas_breden_master,
        MAX(CASE WHEN servicio_operativo = 'BREDEN MASTER' THEN participacion_servicio_pct END)
            AS peso_breden_master_pct,
        MAX(CASE WHEN servicio_operativo = 'PROPAL' THEN carga_servicio END)
            AS carga_propal,
        MAX(CASE WHEN servicio_operativo = 'PROPAL' THEN personas_activas END)
            AS personas_propal,
        MAX(CASE WHEN servicio_operativo = 'PROPAL' THEN participacion_servicio_pct END)
            AS peso_propal_pct,
        MAX(carga_servicios_total) AS carga_servicios_total
    FROM v_rr_servicio_semanal
    WHERE period_label = (SELECT period_label FROM latest)
),
modalidad_rt AS (
    SELECT
        MAX(CASE WHEN modalidad = 'MULTIMARCA' THEN carga_asignada END)
            AS carga_multimarca,
        MAX(CASE WHEN modalidad = 'PITUTO' THEN carga_asignada END)
            AS carga_pituto,
        MAX(CASE WHEN modalidad = 'MULTIMARCA' THEN personas_activas END)
            AS personas_multimarca,
        MAX(CASE WHEN modalidad = 'PITUTO' THEN personas_activas END)
            AS personas_pituto
    FROM v_rr_modalidad_semanal
    WHERE period_label = (SELECT period_label FROM latest)
      AND modalidad IN ('MULTIMARCA', 'PITUTO')
)
SELECT
    g.*,
    s.carga_retail_trust,
    s.personas_retail_trust,
    s.peso_retail_trust_pct,
    s.carga_breden_master,
    s.personas_breden_master,
    s.rutas_breden_master,
    s.peso_breden_master_pct,
    s.carga_propal,
    s.personas_propal,
    s.peso_propal_pct,
    s.carga_servicios_total,
    m.carga_multimarca,
    m.carga_pituto,
    m.personas_multimarca,
    m.personas_pituto,
    ROUND(
        100.0 * m.carga_multimarca
        / NULLIF(m.carga_multimarca + m.carga_pituto, 0),
        4
    ) AS peso_multimarca_dentro_rt_pct,
    ROUND(
        100.0 * m.carga_pituto
        / NULLIF(m.carga_multimarca + m.carga_pituto, 0),
        4
    ) AS peso_pituto_dentro_rt_pct
FROM v_rr_gerencial_actual AS g
CROSS JOIN servicios AS s
CROSS JOIN modalidad_rt AS m
WHERE g.period_label = (SELECT period_label FROM latest);
