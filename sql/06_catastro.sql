-- 06_catastro.sql
-- Propósito:
--   Mantener el catastro semanal de locales, incluyendo estados operativos
--   que no representan personas: CIERRE, REMODELACIÓN y POR INAGURAR.
--
-- No se fuerza una precedencia entre estados. Se publican banderas
-- independientes y la lista de estados detectados.

DROP VIEW IF EXISTS v_rr_catastro_estado_resumen;
DROP VIEW IF EXISTS v_rr_catastro_local_compare;
DROP VIEW IF EXISTS v_rr_catastro_local_semana;
DROP VIEW IF EXISTS v_rr_estado_local_semana;
DROP TABLE IF EXISTS fact_rr_catastro_local_semana;

CREATE VIEW v_rr_estado_local_semana AS
SELECT DISTINCT
    period_year,
    period_month,
    period_week,
    period_label,
    period_order,
    cadena,
    cod_kpi_one,
    local_key,
    MAX(local) OVER (
        PARTITION BY period_label, cadena, cod_kpi_one
    ) AS local,
    estado_catastro
FROM v_rr_base_normalizada
WHERE estado_catastro IS NOT NULL
  AND cadena IS NOT NULL
  AND cod_kpi_one IS NOT NULL;


CREATE TABLE fact_rr_catastro_local_semana AS
WITH llaves AS (
    SELECT
        period_year,
        period_month,
        period_week,
        period_label,
        period_order,
        cadena,
        cod_kpi_one,
        local_key,
        MAX(local) AS local,
        MAX(formato) AS formato,
        MAX(region) AS region,
        MAX(comuna) AS comuna,
        MAX(direccion) AS direccion
    FROM v_rr_base_normalizada
    WHERE cadena IS NOT NULL
      AND cod_kpi_one IS NOT NULL
    GROUP BY
        period_year,
        period_month,
        period_week,
        period_label,
        period_order,
        cadena,
        cod_kpi_one,
        local_key
),
operacion AS (
    SELECT
        period_label,
        cadena,
        cod_kpi_one,
        local_key,

        MAX(local) AS local,
        MAX(formato) AS formato,
        MAX(region) AS region,
        MAX(comuna) AS comuna,
        MAX(direccion) AS direccion,

        COUNT(*) AS local_cliente,
        COUNT(DISTINCT cliente) AS clientes_activos,
        SUM(veces_por_semana_contable) AS volumen_operativo,

        COUNT(DISTINCT modalidades) AS combinaciones_modalidad,
        GROUP_CONCAT(DISTINCT modalidades) AS modalidades
    FROM v_rr_local_cliente_semana
    GROUP BY
        period_label,
        cadena,
        cod_kpi_one,
        local_key
),
personas AS (
    SELECT
        period_label,
        cadena,
        cod_kpi_one,
        local_key,

        COUNT(DISTINCT CASE
            WHEN tipo_rutero = 'PERSONA'
             AND reponedor IS NOT NULL
            THEN reponedor
        END) AS personas_asignadas,

        COUNT(DISTINCT CASE
            WHEN tipo_rutero = 'PERSONA'
             AND rutero IS NOT NULL
            THEN rutero
        END) AS rutas_asignadas
    FROM v_rr_base_normalizada
    WHERE cadena IS NOT NULL
      AND cod_kpi_one IS NOT NULL
    GROUP BY
        period_label,
        cadena,
        cod_kpi_one,
        local_key
),
modalidades_local AS (
    SELECT
        period_label,
        cadena,
        cod_kpi_one,
        local_key,
        GROUP_CONCAT(DISTINCT modalidad) AS modalidades
    FROM v_rr_base_normalizada
    WHERE tipo_rutero = 'PERSONA'
      AND cadena IS NOT NULL
      AND cod_kpi_one IS NOT NULL
    GROUP BY
        period_label,
        cadena,
        cod_kpi_one,
        local_key
),
estados AS (
    SELECT
        period_label,
        cadena,
        cod_kpi_one,
        local_key,

        GROUP_CONCAT(DISTINCT estado_catastro) AS estados_catastro,

        MAX(CASE
            WHEN estado_catastro = 'CIERRE'
            THEN 1 ELSE 0
        END) AS flag_cierre,

        MAX(CASE
            WHEN estado_catastro = 'REMODELACIÓN'
            THEN 1 ELSE 0
        END) AS flag_remodelacion,

        MAX(CASE
            WHEN estado_catastro = 'POR INAGURAR'
            THEN 1 ELSE 0
        END) AS flag_por_inagurar
    FROM v_rr_estado_local_semana
    GROUP BY
        period_label,
        cadena,
        cod_kpi_one,
        local_key
)
SELECT
    k.period_year,
    k.period_month,
    k.period_week,
    k.period_label,
    k.period_order,
    k.cadena,
    k.cod_kpi_one,
    k.local_key,

    COALESCE(o.local, k.local) AS local,
    COALESCE(o.formato, k.formato) AS formato,
    COALESCE(o.region, k.region) AS region,
    COALESCE(o.comuna, k.comuna) AS comuna,
    COALESCE(o.direccion, k.direccion) AS direccion,

    COALESCE(o.local_cliente, 0) AS local_cliente,
    COALESCE(o.clientes_activos, 0) AS clientes_activos,
    COALESCE(o.volumen_operativo, 0) AS volumen_operativo,
    COALESCE(p.personas_asignadas, 0) AS personas_asignadas,
    COALESCE(p.rutas_asignadas, 0) AS rutas_asignadas,

    ml.modalidades,

    e.estados_catastro,
    COALESCE(e.flag_cierre, 0) AS flag_cierre,
    COALESCE(e.flag_remodelacion, 0) AS flag_remodelacion,
    COALESCE(e.flag_por_inagurar, 0) AS flag_por_inagurar,

    CASE
        WHEN e.local_key IS NULL
         AND COALESCE(p.personas_asignadas, 0) > 0
            THEN 'ACTIVO'
        WHEN e.local_key IS NOT NULL
         AND COALESCE(p.personas_asignadas, 0) > 0
            THEN 'ESTADO_CON_ASIGNACIÓN'
        WHEN e.local_key IS NOT NULL
         AND COALESCE(p.personas_asignadas, 0) = 0
            THEN 'ESTADO_SIN_ASIGNACIÓN'
        ELSE 'SIN_ASIGNACIÓN'
    END AS situacion_catastro
FROM llaves AS k
LEFT JOIN operacion AS o
    ON o.period_label = k.period_label
   AND o.cadena = k.cadena
   AND o.cod_kpi_one = k.cod_kpi_one
LEFT JOIN personas AS p
    ON p.period_label = k.period_label
   AND p.cadena = k.cadena
   AND p.cod_kpi_one = k.cod_kpi_one
LEFT JOIN modalidades_local AS ml
    ON ml.period_label = k.period_label
   AND ml.cadena = k.cadena
   AND ml.cod_kpi_one = k.cod_kpi_one
LEFT JOIN estados AS e
    ON e.period_label = k.period_label
   AND e.cadena = k.cadena
   AND e.cod_kpi_one = k.cod_kpi_one;


CREATE UNIQUE INDEX idx_fact_rr_catastro_key
    ON fact_rr_catastro_local_semana(
        period_label,
        cadena,
        cod_kpi_one
    );

CREATE INDEX idx_fact_rr_catastro_period
    ON fact_rr_catastro_local_semana(
        period_label,
        situacion_catastro
    );

CREATE INDEX idx_fact_rr_catastro_region
    ON fact_rr_catastro_local_semana(
        period_label,
        region
    );

CREATE VIEW v_rr_catastro_local_semana AS
SELECT *
FROM fact_rr_catastro_local_semana;

CREATE VIEW v_rr_catastro_local_compare AS
WITH base AS (
    SELECT
        c.*,

        LAG(period_label) OVER (
            PARTITION BY cadena, cod_kpi_one
            ORDER BY period_order
        ) AS previous_period_label,

        LAG(volumen_operativo) OVER (
            PARTITION BY cadena, cod_kpi_one
            ORDER BY period_order
        ) AS volumen_operativo_anterior,

        LAG(local_cliente) OVER (
            PARTITION BY cadena, cod_kpi_one
            ORDER BY period_order
        ) AS local_cliente_anterior,

        LAG(personas_asignadas) OVER (
            PARTITION BY cadena, cod_kpi_one
            ORDER BY period_order
        ) AS personas_asignadas_anterior,

        LAG(estados_catastro) OVER (
            PARTITION BY cadena, cod_kpi_one
            ORDER BY period_order
        ) AS estados_catastro_anterior
    FROM v_rr_catastro_local_semana AS c
)
SELECT
    base.*,

    volumen_operativo - volumen_operativo_anterior
        AS delta_volumen_operativo,

    local_cliente - local_cliente_anterior
        AS delta_local_cliente,

    personas_asignadas - personas_asignadas_anterior
        AS delta_personas_asignadas,

    CASE
        WHEN previous_period_label IS NULL
            THEN 'PRIMER_REGISTRO'
        WHEN COALESCE(estados_catastro, '')
             <> COALESCE(estados_catastro_anterior, '')
            THEN 'CAMBIA_ESTADO'
        WHEN volumen_operativo <> volumen_operativo_anterior
            THEN 'CAMBIA_VOLUMEN'
        WHEN local_cliente <> local_cliente_anterior
            THEN 'CAMBIA_CARTERA'
        WHEN personas_asignadas <> personas_asignadas_anterior
            THEN 'CAMBIA_DOTACIÓN'
        ELSE 'SIN_CAMBIO'
    END AS tipo_cambio_catastro
FROM base;


CREATE VIEW v_rr_catastro_estado_resumen AS
SELECT
    period_year,
    period_month,
    period_week,
    period_label,
    period_order,
    'CIERRE' AS estado_catastro,
    SUM(flag_cierre) AS locales
FROM v_rr_catastro_local_semana
GROUP BY
    period_year,
    period_month,
    period_week,
    period_label,
    period_order

UNION ALL

SELECT
    period_year,
    period_month,
    period_week,
    period_label,
    period_order,
    'REMODELACIÓN' AS estado_catastro,
    SUM(flag_remodelacion) AS locales
FROM v_rr_catastro_local_semana
GROUP BY
    period_year,
    period_month,
    period_week,
    period_label,
    period_order

UNION ALL

SELECT
    period_year,
    period_month,
    period_week,
    period_label,
    period_order,
    'POR INAGURAR' AS estado_catastro,
    SUM(flag_por_inagurar) AS locales
FROM v_rr_catastro_local_semana
GROUP BY
    period_year,
    period_month,
    period_week,
    period_label,
    period_order;
