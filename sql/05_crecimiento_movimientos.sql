-- 05_crecimiento_movimientos.sql
-- Propósito:
--   Explicar el crecimiento entre períodos consecutivos mediante altas,
--   bajas, permanencias y cambios de frecuencia.
--
-- Regla:
--   Cada período se compara contra el período anterior definido en
--   v_rr_periodos. No se comparan semanas por nombre de archivo.

DROP VIEW IF EXISTS v_rr_movimientos_asignacion;
DROP VIEW IF EXISTS v_rr_movimientos_personal;
DROP VIEW IF EXISTS v_rr_crecimiento_semanal;
DROP VIEW IF EXISTS v_rr_crecimiento_componentes;
DROP VIEW IF EXISTS v_rr_movimientos_local_cliente;
DROP TABLE IF EXISTS fact_rr_movimientos_asignacion;
DROP TABLE IF EXISTS fact_rr_movimientos_personal;
DROP TABLE IF EXISTS fact_rr_movimientos_local_cliente;

CREATE TABLE fact_rr_movimientos_local_cliente AS
WITH pares AS (
    SELECT
        period_label AS current_period_label,
        period_order AS current_period_order,
        previous_period_label,
        previous_period_order
    FROM v_rr_periodos
    WHERE previous_period_label IS NOT NULL
),
actual AS (
    SELECT
        pares.current_period_label,
        pares.current_period_order,
        pares.previous_period_label,
        c.cadena,
        c.cod_kpi_one,
        c.cliente,
        c.local_key,
        c.local_cliente_key,

        c.local AS local_actual,
        p.local AS local_anterior,

        c.veces_por_semana_contable AS frecuencia_actual,
        p.veces_por_semana_contable AS frecuencia_anterior,

        c.ruteros AS ruteros_actual,
        p.ruteros AS ruteros_anterior,

        c.reponedores AS reponedores_actual,
        p.reponedores AS reponedores_anterior,

        c.modalidades AS modalidades_actual,
        p.modalidades AS modalidades_anterior
    FROM pares
    INNER JOIN v_rr_local_cliente_semana AS c
        ON c.period_label = pares.current_period_label
    LEFT JOIN v_rr_local_cliente_semana AS p
        ON p.period_label = pares.previous_period_label
       AND p.cadena = c.cadena
       AND p.cod_kpi_one = c.cod_kpi_one
       AND p.cliente = c.cliente
),
retirados AS (
    SELECT
        pares.current_period_label,
        pares.current_period_order,
        pares.previous_period_label,
        p.cadena,
        p.cod_kpi_one,
        p.cliente,
        p.local_key,
        p.local_cliente_key,

        NULL AS local_actual,
        p.local AS local_anterior,

        NULL AS frecuencia_actual,
        p.veces_por_semana_contable AS frecuencia_anterior,

        NULL AS ruteros_actual,
        p.ruteros AS ruteros_anterior,

        NULL AS reponedores_actual,
        p.reponedores AS reponedores_anterior,

        NULL AS modalidades_actual,
        p.modalidades AS modalidades_anterior
    FROM pares
    INNER JOIN v_rr_local_cliente_semana AS p
        ON p.period_label = pares.previous_period_label
    LEFT JOIN v_rr_local_cliente_semana AS c
        ON c.period_label = pares.current_period_label
       AND c.cadena = p.cadena
       AND c.cod_kpi_one = p.cod_kpi_one
       AND c.cliente = p.cliente
    WHERE c.local_cliente_key IS NULL
),
universo AS (
    SELECT * FROM actual
    UNION ALL
    SELECT * FROM retirados
)
SELECT
    current_period_label AS period_label,
    current_period_order AS period_order,
    previous_period_label,

    cadena,
    cod_kpi_one,
    cliente,
    local_key,
    local_cliente_key,

    local_actual,
    local_anterior,

    frecuencia_actual,
    frecuencia_anterior,

    COALESCE(frecuencia_actual, 0)
        - COALESCE(frecuencia_anterior, 0)
        AS delta_volumen,

    CASE
        WHEN frecuencia_anterior IS NULL
         AND frecuencia_actual IS NOT NULL
            THEN 'NUEVO'
        WHEN frecuencia_actual IS NULL
         AND frecuencia_anterior IS NOT NULL
            THEN 'RETIRADO'
        WHEN frecuencia_actual > frecuencia_anterior
            THEN 'AUMENTA_FRECUENCIA'
        WHEN frecuencia_actual < frecuencia_anterior
            THEN 'DISMINUYE_FRECUENCIA'
        ELSE 'SIN_CAMBIO'
    END AS tipo_movimiento,

    ruteros_actual,
    ruteros_anterior,
    reponedores_actual,
    reponedores_anterior,
    modalidades_actual,
    modalidades_anterior,

    CASE
        WHEN COALESCE(ruteros_actual, '') <> COALESCE(ruteros_anterior, '')
        THEN 1 ELSE 0
    END AS posible_cambio_rutero,

    CASE
        WHEN COALESCE(reponedores_actual, '') <> COALESCE(reponedores_anterior, '')
        THEN 1 ELSE 0
    END AS posible_cambio_reponedor,

    CASE
        WHEN COALESCE(modalidades_actual, '') <> COALESCE(modalidades_anterior, '')
        THEN 1 ELSE 0
    END AS posible_cambio_modalidad
FROM universo;


CREATE INDEX idx_fact_rr_mov_lc_period
    ON fact_rr_movimientos_local_cliente(period_label, tipo_movimiento);

CREATE INDEX idx_fact_rr_mov_lc_cadena
    ON fact_rr_movimientos_local_cliente(period_label, cadena);

CREATE INDEX idx_fact_rr_mov_lc_cliente
    ON fact_rr_movimientos_local_cliente(period_label, cliente);

CREATE VIEW v_rr_movimientos_local_cliente AS
SELECT *
FROM fact_rr_movimientos_local_cliente;

CREATE VIEW v_rr_crecimiento_componentes AS
SELECT
    period_label,
    period_order,
    previous_period_label,
    tipo_movimiento,

    COUNT(*) AS casos,
    SUM(delta_volumen) AS efecto_volumen,

    COUNT(DISTINCT local_key) AS locales_involucrados,
    COUNT(DISTINCT cliente) AS clientes_involucrados,

    SUM(posible_cambio_rutero) AS casos_posible_cambio_rutero,
    SUM(posible_cambio_reponedor) AS casos_posible_cambio_reponedor,
    SUM(posible_cambio_modalidad) AS casos_posible_cambio_modalidad
FROM v_rr_movimientos_local_cliente
GROUP BY
    period_label,
    period_order,
    previous_period_label,
    tipo_movimiento;


CREATE VIEW v_rr_crecimiento_semanal AS
WITH movimientos AS (
    SELECT
        period_label,

        SUM(CASE
            WHEN tipo_movimiento = 'NUEVO'
            THEN casos ELSE 0
        END) AS nuevos_local_cliente,

        SUM(CASE
            WHEN tipo_movimiento = 'RETIRADO'
            THEN casos ELSE 0
        END) AS retirados_local_cliente,

        SUM(CASE
            WHEN tipo_movimiento = 'AUMENTA_FRECUENCIA'
            THEN casos ELSE 0
        END) AS aumentos_frecuencia,

        SUM(CASE
            WHEN tipo_movimiento = 'DISMINUYE_FRECUENCIA'
            THEN casos ELSE 0
        END) AS disminuciones_frecuencia,

        SUM(CASE
            WHEN tipo_movimiento = 'SIN_CAMBIO'
            THEN casos ELSE 0
        END) AS persistentes_sin_cambio,

        SUM(CASE
            WHEN tipo_movimiento = 'NUEVO'
            THEN efecto_volumen ELSE 0
        END) AS efecto_nuevos,

        SUM(CASE
            WHEN tipo_movimiento = 'RETIRADO'
            THEN efecto_volumen ELSE 0
        END) AS efecto_retirados,

        SUM(CASE
            WHEN tipo_movimiento = 'AUMENTA_FRECUENCIA'
            THEN efecto_volumen ELSE 0
        END) AS efecto_aumentos_frecuencia,

        SUM(CASE
            WHEN tipo_movimiento = 'DISMINUYE_FRECUENCIA'
            THEN efecto_volumen ELSE 0
        END) AS efecto_disminuciones_frecuencia,

        SUM(efecto_volumen) AS efecto_neto_movimientos
    FROM v_rr_crecimiento_componentes
    GROUP BY period_label
)
SELECT
    r.*,

    COALESCE(m.nuevos_local_cliente, 0) AS nuevos_local_cliente,
    COALESCE(m.retirados_local_cliente, 0) AS retirados_local_cliente,
    COALESCE(m.aumentos_frecuencia, 0) AS aumentos_frecuencia,
    COALESCE(m.disminuciones_frecuencia, 0) AS disminuciones_frecuencia,
    COALESCE(m.persistentes_sin_cambio, 0) AS persistentes_sin_cambio,

    COALESCE(m.efecto_nuevos, 0) AS efecto_nuevos,
    COALESCE(m.efecto_retirados, 0) AS efecto_retirados,
    COALESCE(m.efecto_aumentos_frecuencia, 0)
        AS efecto_aumentos_frecuencia,
    COALESCE(m.efecto_disminuciones_frecuencia, 0)
        AS efecto_disminuciones_frecuencia,
    COALESCE(m.efecto_neto_movimientos, 0)
        AS efecto_neto_movimientos,

    CASE
        WHEN r.delta_volumen_operativo
             = COALESCE(m.efecto_neto_movimientos, 0)
        THEN 1 ELSE 0
    END AS qa_delta_movimientos_cuadra
FROM v_rr_resumen_global_compare AS r
LEFT JOIN movimientos AS m
    ON m.period_label = r.period_label;


CREATE TABLE fact_rr_movimientos_personal AS
WITH pares AS (
    SELECT
        period_label AS current_period_label,
        period_order AS current_period_order,
        previous_period_label
    FROM v_rr_periodos
    WHERE previous_period_label IS NOT NULL
),
actual AS (
    SELECT
        pares.current_period_label,
        pares.current_period_order,
        pares.previous_period_label,
        c.modalidad,
        c.reponedor,

        c.rutas_distintas AS rutas_actual,
        p.rutas_distintas AS rutas_anterior,

        c.locales_asignados AS locales_actual,
        p.locales_asignados AS locales_anterior,

        c.local_cliente_asignados AS carteras_actual,
        p.local_cliente_asignados AS carteras_anterior,

        c.carga_persona AS carga_actual,
        p.carga_persona AS carga_anterior
    FROM pares
    INNER JOIN v_rr_persona_semana AS c
        ON c.period_label = pares.current_period_label
    LEFT JOIN v_rr_persona_semana AS p
        ON p.period_label = pares.previous_period_label
       AND p.modalidad = c.modalidad
       AND p.reponedor = c.reponedor
),
bajas AS (
    SELECT
        pares.current_period_label,
        pares.current_period_order,
        pares.previous_period_label,
        p.modalidad,
        p.reponedor,

        NULL AS rutas_actual,
        p.rutas_distintas AS rutas_anterior,

        NULL AS locales_actual,
        p.locales_asignados AS locales_anterior,

        NULL AS carteras_actual,
        p.local_cliente_asignados AS carteras_anterior,

        NULL AS carga_actual,
        p.carga_persona AS carga_anterior
    FROM pares
    INNER JOIN v_rr_persona_semana AS p
        ON p.period_label = pares.previous_period_label
    LEFT JOIN v_rr_persona_semana AS c
        ON c.period_label = pares.current_period_label
       AND c.modalidad = p.modalidad
       AND c.reponedor = p.reponedor
    WHERE c.reponedor IS NULL
),
universo AS (
    SELECT * FROM actual
    UNION ALL
    SELECT * FROM bajas
)
SELECT
    current_period_label AS period_label,
    current_period_order AS period_order,
    previous_period_label,
    modalidad,
    reponedor,

    rutas_actual,
    rutas_anterior,
    locales_actual,
    locales_anterior,
    carteras_actual,
    carteras_anterior,
    carga_actual,
    carga_anterior,

    COALESCE(carga_actual, 0)
        - COALESCE(carga_anterior, 0)
        AS delta_carga,

    CASE
        WHEN carga_anterior IS NULL
         AND carga_actual IS NOT NULL
            THEN 'ALTA_PERSONA'
        WHEN carga_actual IS NULL
         AND carga_anterior IS NOT NULL
            THEN 'BAJA_PERSONA'
        ELSE 'PERMANECE'
    END AS tipo_movimiento_persona
FROM universo;


CREATE INDEX idx_fact_rr_mov_personal_period
    ON fact_rr_movimientos_personal(
        period_label,
        modalidad,
        tipo_movimiento_persona
    );

CREATE INDEX idx_fact_rr_mov_personal_nombre
    ON fact_rr_movimientos_personal(period_label, reponedor);

CREATE VIEW v_rr_movimientos_personal AS
SELECT *
FROM fact_rr_movimientos_personal;

CREATE TABLE fact_rr_movimientos_asignacion AS
WITH pares AS (
    SELECT
        period_label AS current_period_label,
        period_order AS current_period_order,
        previous_period_label
    FROM v_rr_periodos
    WHERE previous_period_label IS NOT NULL
),
actual AS (
    SELECT
        pares.current_period_label,
        pares.current_period_order,
        pares.previous_period_label,

        c.modalidad,
        c.reponedor,
        c.rutero,
        c.cadena,
        c.cod_kpi_one,
        c.cliente,
        c.local_key,
        c.local_cliente_key,

        c.carga_asignada AS carga_actual,
        p.carga_asignada AS carga_anterior
    FROM pares
    INNER JOIN v_rr_persona_asignacion_semana AS c
        ON c.period_label = pares.current_period_label
    LEFT JOIN v_rr_persona_asignacion_semana AS p
        ON p.period_label = pares.previous_period_label
       AND p.modalidad = c.modalidad
       AND p.reponedor = c.reponedor
       AND p.rutero = c.rutero
       AND p.cadena = c.cadena
       AND p.cod_kpi_one = c.cod_kpi_one
       AND p.cliente = c.cliente
),
bajas AS (
    SELECT
        pares.current_period_label,
        pares.current_period_order,
        pares.previous_period_label,

        p.modalidad,
        p.reponedor,
        p.rutero,
        p.cadena,
        p.cod_kpi_one,
        p.cliente,
        p.local_key,
        p.local_cliente_key,

        NULL AS carga_actual,
        p.carga_asignada AS carga_anterior
    FROM pares
    INNER JOIN v_rr_persona_asignacion_semana AS p
        ON p.period_label = pares.previous_period_label
    LEFT JOIN v_rr_persona_asignacion_semana AS c
        ON c.period_label = pares.current_period_label
       AND c.modalidad = p.modalidad
       AND c.reponedor = p.reponedor
       AND c.rutero = p.rutero
       AND c.cadena = p.cadena
       AND c.cod_kpi_one = p.cod_kpi_one
       AND c.cliente = p.cliente
    WHERE c.reponedor IS NULL
),
universo AS (
    SELECT * FROM actual
    UNION ALL
    SELECT * FROM bajas
)
SELECT
    current_period_label AS period_label,
    current_period_order AS period_order,
    previous_period_label,

    modalidad,
    reponedor,
    rutero,
    cadena,
    cod_kpi_one,
    cliente,
    local_key,
    local_cliente_key,

    carga_actual,
    carga_anterior,

    COALESCE(carga_actual, 0)
        - COALESCE(carga_anterior, 0)
        AS delta_carga,

    CASE
        WHEN carga_anterior IS NULL
         AND carga_actual IS NOT NULL
            THEN 'ALTA_ASIGNACION'
        WHEN carga_actual IS NULL
         AND carga_anterior IS NOT NULL
            THEN 'BAJA_ASIGNACION'
        WHEN carga_actual > carga_anterior
            THEN 'AUMENTA_CARGA'
        WHEN carga_actual < carga_anterior
            THEN 'DISMINUYE_CARGA'
        ELSE 'SIN_CAMBIO'
    END AS tipo_movimiento_asignacion
FROM universo;

CREATE INDEX idx_fact_rr_mov_asig_period
    ON fact_rr_movimientos_asignacion(
        period_label,
        modalidad,
        tipo_movimiento_asignacion
    );

CREATE INDEX idx_fact_rr_mov_asig_persona
    ON fact_rr_movimientos_asignacion(
        period_label,
        reponedor
    );

CREATE INDEX idx_fact_rr_mov_asig_local
    ON fact_rr_movimientos_asignacion(
        period_label,
        cadena,
        cod_kpi_one,
        cliente
    );

CREATE VIEW v_rr_movimientos_asignacion AS
SELECT *
FROM fact_rr_movimientos_asignacion;
