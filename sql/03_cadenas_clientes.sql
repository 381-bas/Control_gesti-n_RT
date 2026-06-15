-- 03_cadenas_clientes.sql
-- Propósito:
--   Publicar rankings gerenciales semanales de cadenas y clientes.
--
-- Granos:
--   v_rr_cadena_semanal         : PERÍODO + CADENA.
--   v_rr_cliente_semanal        : PERÍODO + CLIENTE.
--   v_rr_cadena_cliente_semanal : PERÍODO + CADENA + CLIENTE.

DROP VIEW IF EXISTS v_rr_cadena_cliente_semanal;
DROP VIEW IF EXISTS v_rr_cliente_semanal;
DROP VIEW IF EXISTS v_rr_cadena_semanal;
DROP TABLE IF EXISTS fact_rr_cadena_cliente_semanal;
DROP TABLE IF EXISTS fact_rr_cliente_semanal;
DROP TABLE IF EXISTS fact_rr_cadena_semanal;

CREATE TABLE fact_rr_cadena_semanal AS
WITH operacion AS (
    SELECT
        period_year,
        period_month,
        period_week,
        period_label,
        period_order,
        cadena,

        SUM(veces_por_semana_contable) AS volumen_operativo,
        COUNT(DISTINCT local_key) AS locales_activos,
        COUNT(*) AS local_cliente,
        COUNT(DISTINCT cliente) AS clientes_activos,
        AVG(veces_por_semana_contable) AS intensidad_servicio
    FROM v_rr_local_cliente_semana
    GROUP BY
        period_year,
        period_month,
        period_week,
        period_label,
        period_order,
        cadena
),
dotacion AS (
    SELECT
        period_label,
        cadena,

        COUNT(DISTINCT CASE
            WHEN tipo_rutero = 'PERSONA'
             AND reponedor IS NOT NULL
            THEN reponedor
        END) AS personas_activas,

        COUNT(DISTINCT CASE
            WHEN tipo_rutero = 'PERSONA'
             AND rutero IS NOT NULL
            THEN rutero
        END) AS rutas_activas
    FROM v_rr_base_normalizada
    WHERE cadena IS NOT NULL
    GROUP BY period_label, cadena
),
base AS (
    SELECT
        o.*,
        COALESCE(d.personas_activas, 0) AS personas_activas,
        COALESCE(d.rutas_activas, 0) AS rutas_activas,

        ROUND(
            100.0 * o.volumen_operativo
            / NULLIF(
                SUM(o.volumen_operativo) OVER (
                    PARTITION BY o.period_label
                ),
                0
            ),
            4
        ) AS participacion_volumen_pct,

        DENSE_RANK() OVER (
            PARTITION BY o.period_label
            ORDER BY o.volumen_operativo DESC, o.cadena
        ) AS ranking_volumen,

        SUM(o.volumen_operativo) OVER (
            PARTITION BY o.period_label
            ORDER BY o.volumen_operativo DESC, o.cadena
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS volumen_acumulado,

        SUM(o.volumen_operativo) OVER (
            PARTITION BY o.period_label
        ) AS volumen_total_periodo
    FROM operacion AS o
    LEFT JOIN dotacion AS d
        ON d.period_label = o.period_label
       AND d.cadena = o.cadena
),
comparado AS (
    SELECT
        base.*,

        LAG(period_label) OVER (
            PARTITION BY cadena
            ORDER BY period_order
        ) AS previous_period_label,

        LAG(volumen_operativo) OVER (
            PARTITION BY cadena
            ORDER BY period_order
        ) AS volumen_operativo_anterior,

        LAG(locales_activos) OVER (
            PARTITION BY cadena
            ORDER BY period_order
        ) AS locales_activos_anterior,

        LAG(local_cliente) OVER (
            PARTITION BY cadena
            ORDER BY period_order
        ) AS local_cliente_anterior,

        LAG(personas_activas) OVER (
            PARTITION BY cadena
            ORDER BY period_order
        ) AS personas_activas_anterior
    FROM base
)
SELECT
    comparado.*,

    ROUND(
        100.0 * volumen_acumulado
        / NULLIF(volumen_total_periodo, 0),
        4
    ) AS participacion_acumulada_pct,

    ROUND(
        1.0 * local_cliente / NULLIF(locales_activos, 0),
        4
    ) AS densidad_cartera,

    ROUND(
        volumen_operativo / NULLIF(locales_activos, 0),
        4
    ) AS volumen_por_local,

    ROUND(
        volumen_operativo / NULLIF(personas_activas, 0),
        4
    ) AS volumen_por_persona,

    ROUND(
        1.0 * locales_activos / NULLIF(personas_activas, 0),
        4
    ) AS locales_por_persona,

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

    local_cliente - local_cliente_anterior
        AS delta_local_cliente,

    personas_activas - personas_activas_anterior
        AS delta_personas_activas
FROM comparado;


CREATE UNIQUE INDEX idx_fact_rr_cadena_key
    ON fact_rr_cadena_semanal(period_label, cadena);

CREATE INDEX idx_fact_rr_cadena_rank
    ON fact_rr_cadena_semanal(period_label, ranking_volumen);

CREATE VIEW v_rr_cadena_semanal AS
SELECT *
FROM fact_rr_cadena_semanal;

CREATE TABLE fact_rr_cliente_semanal AS
WITH operacion AS (
    SELECT
        period_year,
        period_month,
        period_week,
        period_label,
        period_order,
        cliente,

        SUM(veces_por_semana_contable) AS volumen_operativo,
        COUNT(DISTINCT local_key) AS locales_activos,
        COUNT(DISTINCT cadena) AS cadenas_activas,
        COUNT(*) AS local_cliente,
        AVG(veces_por_semana_contable) AS intensidad_servicio
    FROM v_rr_local_cliente_semana
    GROUP BY
        period_year,
        period_month,
        period_week,
        period_label,
        period_order,
        cliente
),
dotacion AS (
    SELECT
        period_label,
        cliente,

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
    WHERE cliente IS NOT NULL
    GROUP BY period_label, cliente
),
base AS (
    SELECT
        o.*,
        COALESCE(d.personas_asignadas, 0) AS personas_asignadas,
        COALESCE(d.rutas_asignadas, 0) AS rutas_asignadas,

        ROUND(
            100.0 * o.volumen_operativo
            / NULLIF(
                SUM(o.volumen_operativo) OVER (
                    PARTITION BY o.period_label
                ),
                0
            ),
            4
        ) AS participacion_volumen_pct,

        DENSE_RANK() OVER (
            PARTITION BY o.period_label
            ORDER BY o.volumen_operativo DESC, o.cliente
        ) AS ranking_volumen,

        SUM(o.volumen_operativo) OVER (
            PARTITION BY o.period_label
            ORDER BY o.volumen_operativo DESC, o.cliente
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS volumen_acumulado,

        SUM(o.volumen_operativo) OVER (
            PARTITION BY o.period_label
        ) AS volumen_total_periodo
    FROM operacion AS o
    LEFT JOIN dotacion AS d
        ON d.period_label = o.period_label
       AND d.cliente = o.cliente
),
comparado AS (
    SELECT
        base.*,

        LAG(period_label) OVER (
            PARTITION BY cliente
            ORDER BY period_order
        ) AS previous_period_label,

        LAG(volumen_operativo) OVER (
            PARTITION BY cliente
            ORDER BY period_order
        ) AS volumen_operativo_anterior,

        LAG(locales_activos) OVER (
            PARTITION BY cliente
            ORDER BY period_order
        ) AS locales_activos_anterior,

        LAG(cadenas_activas) OVER (
            PARTITION BY cliente
            ORDER BY period_order
        ) AS cadenas_activas_anterior,

        LAG(personas_asignadas) OVER (
            PARTITION BY cliente
            ORDER BY period_order
        ) AS personas_asignadas_anterior
    FROM base
)
SELECT
    comparado.*,

    ROUND(
        100.0 * volumen_acumulado
        / NULLIF(volumen_total_periodo, 0),
        4
    ) AS participacion_acumulada_pct,

    ROUND(
        volumen_operativo / NULLIF(locales_activos, 0),
        4
    ) AS volumen_por_local,

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

    cadenas_activas - cadenas_activas_anterior
        AS delta_cadenas_activas,

    personas_asignadas - personas_asignadas_anterior
        AS delta_personas_asignadas
FROM comparado;


CREATE UNIQUE INDEX idx_fact_rr_cliente_key
    ON fact_rr_cliente_semanal(period_label, cliente);

CREATE INDEX idx_fact_rr_cliente_rank
    ON fact_rr_cliente_semanal(period_label, ranking_volumen);

CREATE VIEW v_rr_cliente_semanal AS
SELECT *
FROM fact_rr_cliente_semanal;

CREATE TABLE fact_rr_cadena_cliente_semanal AS
SELECT
    period_year,
    period_month,
    period_week,
    period_label,
    period_order,
    cadena,
    cliente,

    SUM(veces_por_semana_contable) AS volumen_operativo,
    COUNT(DISTINCT local_key) AS locales_activos,
    COUNT(*) AS local_cliente,
    AVG(veces_por_semana_contable) AS intensidad_servicio,

    ROUND(
        100.0 * SUM(veces_por_semana_contable)
        / NULLIF(
            SUM(SUM(veces_por_semana_contable)) OVER (
                PARTITION BY period_label, cadena
            ),
            0
        ),
        4
    ) AS participacion_en_cadena_pct,

    DENSE_RANK() OVER (
        PARTITION BY period_label, cadena
        ORDER BY SUM(veces_por_semana_contable) DESC, cliente
    ) AS ranking_cliente_en_cadena
FROM v_rr_local_cliente_semana
GROUP BY
    period_year,
    period_month,
    period_week,
    period_label,
    period_order,
    cadena,
    cliente;

CREATE UNIQUE INDEX idx_fact_rr_cc_key
    ON fact_rr_cadena_cliente_semanal(
        period_label,
        cadena,
        cliente
    );

CREATE INDEX idx_fact_rr_cc_rank
    ON fact_rr_cadena_cliente_semanal(
        period_label,
        cadena,
        ranking_cliente_en_cadena
    );

CREATE VIEW v_rr_cadena_cliente_semanal AS
SELECT *
FROM fact_rr_cadena_cliente_semanal;
