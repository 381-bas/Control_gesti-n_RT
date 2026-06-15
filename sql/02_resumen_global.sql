-- 02_resumen_global.sql
-- Propósito:
--   Consolidar la unidad LOCAL/CLIENTE por semana y publicar los KPI
--   gerenciales globales con comparación contra el período anterior.
--
-- Regla oficial de volumen:
--   MAX(VECES POR SEMANA) por
--   PERÍODO + CADENA + COD KPI ONE + CLIENTE.

DROP VIEW IF EXISTS v_rr_resumen_mensual_compare;
DROP VIEW IF EXISTS v_rr_resumen_mensual;
DROP VIEW IF EXISTS v_rr_resumen_global_compare;
DROP VIEW IF EXISTS v_rr_resumen_global;
DROP VIEW IF EXISTS v_rr_local_cliente_semana;
DROP TABLE IF EXISTS fact_rr_resumen_global;
DROP TABLE IF EXISTS fact_rr_local_cliente_semana;

CREATE TABLE fact_rr_local_cliente_semana AS
SELECT
    period_year,
    period_month,
    period_week,
    period_label,
    period_order,

    cadena,
    cod_kpi_one,
    cliente,

    cadena || CHAR(31) || cod_kpi_one AS local_key,
    cadena || CHAR(31) || cod_kpi_one || CHAR(31) || cliente
        AS local_cliente_key,

    MAX(local) AS local,
    MAX(formato) AS formato,
    MAX(region) AS region,
    MAX(comuna) AS comuna,
    MAX(direccion) AS direccion,
    MAX(cod_b2b) AS cod_b2b,

    MAX(veces_por_semana) AS veces_por_semana_contable,
    MIN(veces_por_semana) AS veces_por_semana_min,
    MAX(veces_por_semana) AS veces_por_semana_max,

    MAX(
        lunes + martes + miercoles + jueves
        + viernes + sabado + domingo
    ) AS programacion_semanal_max,

    SUM(
        lunes + martes + miercoles + jueves
        + viernes + sabado + domingo
    ) AS programacion_semanal_asignada,

    COUNT(*) AS filas_origen,
    COUNT(DISTINCT rutero) AS rutas_distintas,
    COUNT(DISTINCT reponedor) AS personas_distintas,
    COUNT(DISTINCT modalidad) AS modalidades_distintas,
    COUNT(DISTINCT local) AS nombres_local_distintos,

    GROUP_CONCAT(DISTINCT rutero) AS ruteros,
    GROUP_CONCAT(DISTINCT reponedor) AS reponedores,
    GROUP_CONCAT(DISTINCT modalidad) AS modalidades,

    MAX(loaded_at) AS loaded_at
FROM v_rr_base_normalizada
WHERE cadena IS NOT NULL
  AND cod_kpi_one IS NOT NULL
  AND cliente IS NOT NULL
  AND veces_por_semana IS NOT NULL
GROUP BY
    period_year,
    period_month,
    period_week,
    period_label,
    period_order,
    cadena,
    cod_kpi_one,
    cliente;


CREATE UNIQUE INDEX idx_fact_rr_lc_key
    ON fact_rr_local_cliente_semana(
        period_label,
        cadena,
        cod_kpi_one,
        cliente
    );

CREATE INDEX idx_fact_rr_lc_period
    ON fact_rr_local_cliente_semana(period_order, period_label);

CREATE INDEX idx_fact_rr_lc_cadena
    ON fact_rr_local_cliente_semana(period_label, cadena);

CREATE INDEX idx_fact_rr_lc_cliente
    ON fact_rr_local_cliente_semana(period_label, cliente);

CREATE INDEX idx_fact_rr_lc_local
    ON fact_rr_local_cliente_semana(period_label, local_key);

CREATE VIEW v_rr_local_cliente_semana AS
SELECT *
FROM fact_rr_local_cliente_semana;

CREATE TABLE fact_rr_resumen_global AS
WITH operacion AS (
    SELECT
        period_year,
        period_month,
        period_week,
        period_label,
        period_order,

        SUM(veces_por_semana_contable) AS volumen_operativo,
        COUNT(DISTINCT local_key) AS locales_activos,
        COUNT(*) AS local_cliente,
        COUNT(DISTINCT cliente) AS clientes_activos,
        COUNT(DISTINCT cadena) AS cadenas_activas,

        AVG(veces_por_semana_contable) AS intensidad_servicio_directa,
        SUM(programacion_semanal_max) AS programacion_semanal_max,
        SUM(programacion_semanal_asignada) AS programacion_semanal_asignada,

        SUM(
            CASE WHEN filas_origen > 1 THEN 1 ELSE 0 END
        ) AS local_cliente_repetidos,

        SUM(
            CASE
                WHEN veces_por_semana_min <> veces_por_semana_max
                THEN 1 ELSE 0
            END
        ) AS local_cliente_frecuencia_diversa
    FROM v_rr_local_cliente_semana
    GROUP BY
        period_year,
        period_month,
        period_week,
        period_label,
        period_order
),
dotacion AS (
    SELECT
        period_label,

        COUNT(DISTINCT CASE
            WHEN tipo_rutero = 'PERSONA'
             AND reponedor IS NOT NULL
            THEN reponedor
        END) AS personas_activas,

        COUNT(DISTINCT CASE
            WHEN tipo_rutero = 'PERSONA'
             AND rutero IS NOT NULL
            THEN rutero
        END) AS rutas_activas,

        COUNT(DISTINCT CASE
            WHEN tipo_rutero = 'PERSONA'
             AND modalidad = 'MULTIMARCA'
             AND reponedor IS NOT NULL
            THEN reponedor
        END) AS personas_multimarca,

        COUNT(DISTINCT CASE
            WHEN tipo_rutero = 'PERSONA'
             AND modalidad = 'PITUTO'
             AND reponedor IS NOT NULL
            THEN reponedor
        END) AS personas_pituto,

        COUNT(DISTINCT CASE
            WHEN tipo_rutero = 'PERSONA'
             AND modalidad = 'BREDEN'
             AND reponedor IS NOT NULL
            THEN reponedor
        END) AS personas_breden,

        COUNT(DISTINCT CASE
            WHEN tipo_rutero = 'PERSONA'
             AND modalidad = 'PROPAL'
             AND reponedor IS NOT NULL
            THEN reponedor
        END) AS personas_propal
    FROM v_rr_base_normalizada
    GROUP BY period_label
),
estados AS (
    SELECT
        period_label,

        COUNT(DISTINCT CASE
            WHEN estado_catastro = 'CIERRE'
            THEN local_key
        END) AS locales_cierre,

        COUNT(DISTINCT CASE
            WHEN estado_catastro = 'REMODELACIÓN'
            THEN local_key
        END) AS locales_remodelacion,

        COUNT(DISTINCT CASE
            WHEN estado_catastro = 'POR INAGURAR'
            THEN local_key
        END) AS locales_por_inagurar
    FROM v_rr_base_normalizada
    GROUP BY period_label
)
SELECT
    o.period_year,
    o.period_month,
    o.period_week,
    o.period_label,
    o.period_order,

    o.volumen_operativo,
    o.locales_activos,
    o.local_cliente,
    o.clientes_activos,
    o.cadenas_activas,

    COALESCE(d.personas_activas, 0) AS personas_activas,
    COALESCE(d.rutas_activas, 0) AS rutas_activas,

    COALESCE(d.personas_multimarca, 0) AS personas_multimarca,
    COALESCE(d.personas_pituto, 0) AS personas_pituto,
    COALESCE(d.personas_breden, 0) AS personas_breden,
    COALESCE(d.personas_propal, 0) AS personas_propal,

    COALESCE(e.locales_cierre, 0) AS locales_cierre,
    COALESCE(e.locales_remodelacion, 0) AS locales_remodelacion,
    COALESCE(e.locales_por_inagurar, 0) AS locales_por_inagurar,

    o.local_cliente_repetidos,
    o.local_cliente_frecuencia_diversa,
    o.programacion_semanal_max,
    o.programacion_semanal_asignada,

    ROUND(
        o.volumen_operativo / NULLIF(o.local_cliente, 0),
        4
    ) AS intensidad_servicio,

    ROUND(
        1.0 * o.local_cliente / NULLIF(o.locales_activos, 0),
        4
    ) AS densidad_cartera,

    ROUND(
        o.volumen_operativo / NULLIF(o.locales_activos, 0),
        4
    ) AS volumen_por_local,

    ROUND(
        o.volumen_operativo / NULLIF(d.personas_activas, 0),
        4
    ) AS volumen_por_persona,

    ROUND(
        1.0 * o.locales_activos / NULLIF(d.personas_activas, 0),
        4
    ) AS locales_por_persona,

    ROUND(
        1.0 * o.local_cliente / NULLIF(d.personas_activas, 0),
        4
    ) AS carteras_por_persona
FROM operacion AS o
LEFT JOIN dotacion AS d
    ON d.period_label = o.period_label
LEFT JOIN estados AS e
    ON e.period_label = o.period_label;


CREATE UNIQUE INDEX idx_fact_rr_resumen_period
    ON fact_rr_resumen_global(period_label);

CREATE INDEX idx_fact_rr_resumen_order
    ON fact_rr_resumen_global(period_order);

CREATE VIEW v_rr_resumen_global AS
SELECT *
FROM fact_rr_resumen_global;

CREATE VIEW v_rr_resumen_global_compare AS
WITH base AS (
    SELECT
        r.*,
        LAG(period_label) OVER (
            ORDER BY period_order
        ) AS previous_period_label,

        LAG(volumen_operativo) OVER (
            ORDER BY period_order
        ) AS volumen_operativo_anterior,

        LAG(locales_activos) OVER (
            ORDER BY period_order
        ) AS locales_activos_anterior,

        LAG(local_cliente) OVER (
            ORDER BY period_order
        ) AS local_cliente_anterior,

        LAG(clientes_activos) OVER (
            ORDER BY period_order
        ) AS clientes_activos_anterior,

        LAG(personas_activas) OVER (
            ORDER BY period_order
        ) AS personas_activas_anterior,

        LAG(rutas_activas) OVER (
            ORDER BY period_order
        ) AS rutas_activas_anterior,

        FIRST_VALUE(volumen_operativo) OVER (
            ORDER BY period_order
        ) AS volumen_base,

        FIRST_VALUE(locales_activos) OVER (
            ORDER BY period_order
        ) AS locales_base,

        FIRST_VALUE(local_cliente) OVER (
            ORDER BY period_order
        ) AS local_cliente_base,

        FIRST_VALUE(personas_activas) OVER (
            ORDER BY period_order
        ) AS personas_base
    FROM v_rr_resumen_global AS r
)
SELECT
    base.*,

    volumen_operativo - volumen_operativo_anterior
        AS delta_volumen_operativo,

    ROUND(
        100.0 * (
            volumen_operativo - volumen_operativo_anterior
        ) / NULLIF(volumen_operativo_anterior, 0),
        4
    ) AS delta_volumen_operativo_pct,

    locales_activos - locales_activos_anterior
        AS delta_locales_activos,

    ROUND(
        100.0 * (
            locales_activos - locales_activos_anterior
        ) / NULLIF(locales_activos_anterior, 0),
        4
    ) AS delta_locales_activos_pct,

    local_cliente - local_cliente_anterior
        AS delta_local_cliente,

    ROUND(
        100.0 * (
            local_cliente - local_cliente_anterior
        ) / NULLIF(local_cliente_anterior, 0),
        4
    ) AS delta_local_cliente_pct,

    clientes_activos - clientes_activos_anterior
        AS delta_clientes_activos,

    personas_activas - personas_activas_anterior
        AS delta_personas_activas,

    ROUND(
        100.0 * (
            personas_activas - personas_activas_anterior
        ) / NULLIF(personas_activas_anterior, 0),
        4
    ) AS delta_personas_activas_pct,

    rutas_activas - rutas_activas_anterior
        AS delta_rutas_activas,

    ROUND(
        100.0 * volumen_operativo
        / NULLIF(volumen_base, 0),
        4
    ) AS indice_volumen_base_100,

    ROUND(
        100.0 * locales_activos
        / NULLIF(locales_base, 0),
        4
    ) AS indice_locales_base_100,

    ROUND(
        100.0 * local_cliente
        / NULLIF(local_cliente_base, 0),
        4
    ) AS indice_local_cliente_base_100,

    ROUND(
        100.0 * personas_activas
        / NULLIF(personas_base, 0),
        4
    ) AS indice_personas_base_100,

    ROUND(
        AVG(volumen_operativo) OVER (
            ORDER BY period_order
            ROWS BETWEEN 3 PRECEDING AND CURRENT ROW
        ),
        4
    ) AS volumen_promedio_movil_4s
FROM base;

CREATE VIEW v_rr_resumen_mensual AS
WITH promedio AS (
    SELECT
        r.period_year,
        r.period_month,
        printf('%04d-%02d', r.period_year, r.period_month) AS month_label,
        COUNT(*) AS semanas_disponibles,

        AVG(r.volumen_operativo) AS volumen_promedio_semanal,
        AVG(r.locales_activos) AS locales_promedio_semanal,
        AVG(r.local_cliente) AS local_cliente_promedio_semanal,
        AVG(r.clientes_activos) AS clientes_promedio_semanal,
        AVG(r.personas_activas) AS personas_promedio_semanal,
        AVG(r.rutas_activas) AS rutas_promedio_semanal
    FROM v_rr_resumen_global AS r
    GROUP BY r.period_year, r.period_month
),
cierre AS (
    SELECT
        r.period_year,
        r.period_month,
        r.period_label AS cierre_period_label,
        r.period_order AS cierre_period_order,

        r.volumen_operativo AS volumen_cierre,
        r.locales_activos AS locales_cierre,
        r.local_cliente AS local_cliente_cierre,
        r.clientes_activos AS clientes_cierre,
        r.personas_activas AS personas_cierre,
        r.rutas_activas AS rutas_cierre,

        r.intensidad_servicio AS intensidad_servicio_cierre,
        r.densidad_cartera AS densidad_cartera_cierre,
        r.volumen_por_persona AS volumen_por_persona_cierre
    FROM v_rr_resumen_global AS r
    INNER JOIN v_rr_periodos AS p
        ON p.period_label = r.period_label
    WHERE p.is_last_week_month = 1
)
SELECT
    p.period_year,
    p.period_month,
    p.month_label,
    p.semanas_disponibles,

    c.cierre_period_label,
    c.cierre_period_order,

    c.volumen_cierre,
    c.locales_cierre,
    c.local_cliente_cierre,
    c.clientes_cierre,
    c.personas_cierre,
    c.rutas_cierre,

    ROUND(p.volumen_promedio_semanal, 4) AS volumen_promedio_semanal,
    ROUND(p.locales_promedio_semanal, 4) AS locales_promedio_semanal,
    ROUND(p.local_cliente_promedio_semanal, 4)
        AS local_cliente_promedio_semanal,
    ROUND(p.clientes_promedio_semanal, 4)
        AS clientes_promedio_semanal,
    ROUND(p.personas_promedio_semanal, 4)
        AS personas_promedio_semanal,
    ROUND(p.rutas_promedio_semanal, 4)
        AS rutas_promedio_semanal,

    c.intensidad_servicio_cierre,
    c.densidad_cartera_cierre,
    c.volumen_por_persona_cierre
FROM promedio AS p
INNER JOIN cierre AS c
    ON c.period_year = p.period_year
   AND c.period_month = p.period_month;


CREATE VIEW v_rr_resumen_mensual_compare AS
WITH base AS (
    SELECT
        m.*,

        LAG(month_label) OVER (
            ORDER BY period_year, period_month
        ) AS previous_month_label,

        LAG(volumen_cierre) OVER (
            ORDER BY period_year, period_month
        ) AS volumen_cierre_anterior,

        LAG(locales_cierre) OVER (
            ORDER BY period_year, period_month
        ) AS locales_cierre_anterior,

        LAG(local_cliente_cierre) OVER (
            ORDER BY period_year, period_month
        ) AS local_cliente_cierre_anterior,

        LAG(personas_cierre) OVER (
            ORDER BY period_year, period_month
        ) AS personas_cierre_anterior
    FROM v_rr_resumen_mensual AS m
)
SELECT
    base.*,

    volumen_cierre - volumen_cierre_anterior
        AS delta_volumen_cierre,

    ROUND(
        100.0 * (
            volumen_cierre - volumen_cierre_anterior
        ) / NULLIF(volumen_cierre_anterior, 0),
        4
    ) AS delta_volumen_cierre_pct,

    locales_cierre - locales_cierre_anterior
        AS delta_locales_cierre,

    local_cliente_cierre - local_cliente_cierre_anterior
        AS delta_local_cliente_cierre,

    personas_cierre - personas_cierre_anterior
        AS delta_personas_cierre
FROM base;
