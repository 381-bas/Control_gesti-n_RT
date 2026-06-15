-- 04_personal_modalidad.sql
-- Propósito:
--   Separar dotación, rutas y carga asignada por modalidad.
--
-- Precisión metodológica:
--   volumen_operativo = métrica oficial sin duplicar LOCAL/CLIENTE.
--   carga_asignada    = distribución de carga por modalidad; puede superar
--                       el volumen oficial cuando una cartera se comparte
--                       entre modalidades.
--
-- Granos:
--   v_rr_local_cliente_modalidad_semana : PERÍODO + LOCAL/CLIENTE + MODALIDAD.
--   v_rr_persona_asignacion_semana      : PERÍODO + PERSONA + LOCAL/CLIENTE.
--   v_rr_persona_semana                 : PERÍODO + MODALIDAD + PERSONA.
--   v_rr_modalidad_semanal              : PERÍODO + MODALIDAD.

DROP VIEW IF EXISTS v_rr_modalidad_semanal_compare;
DROP VIEW IF EXISTS v_rr_modalidad_semanal;
DROP VIEW IF EXISTS v_rr_persona_semana;
DROP VIEW IF EXISTS v_rr_persona_asignacion_semana;
DROP VIEW IF EXISTS v_rr_local_cliente_modalidad_semana;
DROP TABLE IF EXISTS fact_rr_modalidad_semanal;
DROP TABLE IF EXISTS fact_rr_persona_asignacion_semana;
DROP TABLE IF EXISTS fact_rr_local_cliente_modalidad_semana;

CREATE TABLE fact_rr_local_cliente_modalidad_semana AS
SELECT
    period_year,
    period_month,
    period_week,
    period_label,
    period_order,

    cadena,
    cod_kpi_one,
    cliente,
    modalidad,

    cadena || CHAR(31) || cod_kpi_one AS local_key,
    cadena || CHAR(31) || cod_kpi_one || CHAR(31) || cliente
        AS local_cliente_key,

    MAX(local) AS local,
    MAX(formato) AS formato,
    MAX(region) AS region,
    MAX(comuna) AS comuna,

    MAX(veces_por_semana) AS carga_asignada,
    COUNT(*) AS filas_origen,
    COUNT(DISTINCT rutero) AS rutas_distintas,
    COUNT(DISTINCT reponedor) AS personas_distintas,
    GROUP_CONCAT(DISTINCT rutero) AS ruteros,
    GROUP_CONCAT(DISTINCT reponedor) AS reponedores
FROM v_rr_base_normalizada
WHERE tipo_rutero = 'PERSONA'
  AND cadena IS NOT NULL
  AND cod_kpi_one IS NOT NULL
  AND cliente IS NOT NULL
  AND modalidad IS NOT NULL
  AND veces_por_semana IS NOT NULL
GROUP BY
    period_year,
    period_month,
    period_week,
    period_label,
    period_order,
    cadena,
    cod_kpi_one,
    cliente,
    modalidad;


CREATE UNIQUE INDEX idx_fact_rr_lcm_key
    ON fact_rr_local_cliente_modalidad_semana(
        period_label,
        cadena,
        cod_kpi_one,
        cliente,
        modalidad
    );

CREATE INDEX idx_fact_rr_lcm_period_modalidad
    ON fact_rr_local_cliente_modalidad_semana(
        period_label,
        modalidad
    );

CREATE VIEW v_rr_local_cliente_modalidad_semana AS
SELECT *
FROM fact_rr_local_cliente_modalidad_semana;

CREATE TABLE fact_rr_persona_asignacion_semana AS
SELECT
    period_year,
    period_month,
    period_week,
    period_label,
    period_order,

    modalidad,
    reponedor,
    rutero,
    cadena,
    cod_kpi_one,
    cliente,

    cadena || CHAR(31) || cod_kpi_one AS local_key,
    cadena || CHAR(31) || cod_kpi_one || CHAR(31) || cliente
        AS local_cliente_key,

    MAX(local) AS local,
    MAX(region) AS region,
    MAX(comuna) AS comuna,
    MAX(veces_por_semana) AS carga_asignada,
    COUNT(*) AS filas_origen
FROM v_rr_base_normalizada
WHERE tipo_rutero = 'PERSONA'
  AND reponedor IS NOT NULL
  AND modalidad IS NOT NULL
  AND cadena IS NOT NULL
  AND cod_kpi_one IS NOT NULL
  AND cliente IS NOT NULL
  AND veces_por_semana IS NOT NULL
GROUP BY
    period_year,
    period_month,
    period_week,
    period_label,
    period_order,
    modalidad,
    reponedor,
    rutero,
    cadena,
    cod_kpi_one,
    cliente;


CREATE UNIQUE INDEX idx_fact_rr_pa_key
    ON fact_rr_persona_asignacion_semana(
        period_label,
        modalidad,
        reponedor,
        rutero,
        cadena,
        cod_kpi_one,
        cliente
    );

CREATE INDEX idx_fact_rr_pa_period_persona
    ON fact_rr_persona_asignacion_semana(
        period_label,
        modalidad,
        reponedor
    );

CREATE INDEX idx_fact_rr_pa_period_local
    ON fact_rr_persona_asignacion_semana(
        period_label,
        cadena,
        cod_kpi_one
    );

CREATE VIEW v_rr_persona_asignacion_semana AS
SELECT *
FROM fact_rr_persona_asignacion_semana;

CREATE VIEW v_rr_persona_semana AS
SELECT
    period_year,
    period_month,
    period_week,
    period_label,
    period_order,
    modalidad,
    reponedor,

    COUNT(DISTINCT rutero) AS rutas_distintas,
    COUNT(DISTINCT cadena) AS cadenas_asignadas,
    COUNT(DISTINCT local_key) AS locales_asignados,
    COUNT(DISTINCT local_cliente_key) AS local_cliente_asignados,
    COUNT(DISTINCT cliente) AS clientes_asignados,
    SUM(carga_asignada) AS carga_persona,

    ROUND(
        SUM(carga_asignada)
        / NULLIF(COUNT(DISTINCT local_key), 0),
        4
    ) AS carga_por_local,

    ROUND(
        1.0 * COUNT(DISTINCT local_cliente_key)
        / NULLIF(COUNT(DISTINCT local_key), 0),
        4
    ) AS densidad_cartera_persona,

    GROUP_CONCAT(DISTINCT rutero) AS ruteros,
    GROUP_CONCAT(DISTINCT cadena) AS cadenas
FROM v_rr_persona_asignacion_semana
GROUP BY
    period_year,
    period_month,
    period_week,
    period_label,
    period_order,
    modalidad,
    reponedor;


CREATE TABLE fact_rr_modalidad_semanal AS
WITH carga AS (
    SELECT
        period_year,
        period_month,
        period_week,
        period_label,
        period_order,
        modalidad,

        SUM(carga_asignada) AS carga_asignada,
        COUNT(DISTINCT local_key) AS locales_asignados,
        COUNT(DISTINCT local_cliente_key) AS local_cliente_asignados,
        COUNT(DISTINCT cliente) AS clientes_asignados
    FROM v_rr_local_cliente_modalidad_semana
    GROUP BY
        period_year,
        period_month,
        period_week,
        period_label,
        period_order,
        modalidad
),
dotacion AS (
    SELECT
        period_label,
        modalidad,

        COUNT(DISTINCT reponedor) AS personas_activas,
        COUNT(DISTINCT rutero) AS rutas_activas,
        COUNT(DISTINCT cadena) AS cadenas_asignadas
    FROM v_rr_base_normalizada
    WHERE tipo_rutero = 'PERSONA'
      AND reponedor IS NOT NULL
      AND modalidad IS NOT NULL
    GROUP BY period_label, modalidad
)
SELECT
    c.period_year,
    c.period_month,
    c.period_week,
    c.period_label,
    c.period_order,
    c.modalidad,

    COALESCE(d.personas_activas, 0) AS personas_activas,
    COALESCE(d.rutas_activas, 0) AS rutas_activas,
    COALESCE(d.cadenas_asignadas, 0) AS cadenas_asignadas,

    c.locales_asignados,
    c.local_cliente_asignados,
    c.clientes_asignados,
    c.carga_asignada,

    ROUND(
        c.carga_asignada
        / NULLIF(d.personas_activas, 0),
        4
    ) AS carga_por_persona,

    ROUND(
        1.0 * c.locales_asignados
        / NULLIF(d.personas_activas, 0),
        4
    ) AS locales_por_persona,

    ROUND(
        1.0 * c.local_cliente_asignados
        / NULLIF(d.personas_activas, 0),
        4
    ) AS carteras_por_persona,

    ROUND(
        1.0 * c.clientes_asignados
        / NULLIF(d.personas_activas, 0),
        4
    ) AS clientes_por_persona,

    ROUND(
        c.carga_asignada
        / NULLIF(c.local_cliente_asignados, 0),
        4
    ) AS intensidad_servicio_asignada
FROM carga AS c
LEFT JOIN dotacion AS d
    ON d.period_label = c.period_label
   AND d.modalidad = c.modalidad;


CREATE UNIQUE INDEX idx_fact_rr_modalidad_key
    ON fact_rr_modalidad_semanal(period_label, modalidad);

CREATE INDEX idx_fact_rr_modalidad_order
    ON fact_rr_modalidad_semanal(period_order, modalidad);

CREATE VIEW v_rr_modalidad_semanal AS
SELECT *
FROM fact_rr_modalidad_semanal;

CREATE VIEW v_rr_modalidad_semanal_compare AS
WITH base AS (
    SELECT
        m.*,

        LAG(period_label) OVER (
            PARTITION BY modalidad
            ORDER BY period_order
        ) AS previous_period_label,

        LAG(personas_activas) OVER (
            PARTITION BY modalidad
            ORDER BY period_order
        ) AS personas_activas_anterior,

        LAG(rutas_activas) OVER (
            PARTITION BY modalidad
            ORDER BY period_order
        ) AS rutas_activas_anterior,

        LAG(locales_asignados) OVER (
            PARTITION BY modalidad
            ORDER BY period_order
        ) AS locales_asignados_anterior,

        LAG(local_cliente_asignados) OVER (
            PARTITION BY modalidad
            ORDER BY period_order
        ) AS local_cliente_asignados_anterior,

        LAG(carga_asignada) OVER (
            PARTITION BY modalidad
            ORDER BY period_order
        ) AS carga_asignada_anterior
    FROM v_rr_modalidad_semanal AS m
)
SELECT
    base.*,

    personas_activas - personas_activas_anterior
        AS delta_personas_activas,

    rutas_activas - rutas_activas_anterior
        AS delta_rutas_activas,

    locales_asignados - locales_asignados_anterior
        AS delta_locales_asignados,

    local_cliente_asignados - local_cliente_asignados_anterior
        AS delta_local_cliente_asignados,

    carga_asignada - carga_asignada_anterior
        AS delta_carga_asignada,

    ROUND(
        100.0 * (
            carga_asignada - carga_asignada_anterior
        ) / NULLIF(carga_asignada_anterior, 0),
        4
    ) AS delta_carga_asignada_pct,

    ROUND(
        100.0 * (
            personas_activas - personas_activas_anterior
        ) / NULLIF(personas_activas_anterior, 0),
        4
    ) AS delta_personas_activas_pct
FROM base;
