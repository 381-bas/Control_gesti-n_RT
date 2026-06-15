-- 11_modelo_servicios_patch.sql
-- Evita columnas duplicadas heredadas desde v_rr_gerencial_actual.

DROP VIEW IF EXISTS v_rr_gerencial_v2_actual;

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
            AS personas_propal_servicio,
        MAX(CASE WHEN servicio_operativo = 'PROPAL' THEN participacion_servicio_pct END)
            AS peso_propal_pct,
        MAX(carga_servicios_total) AS carga_servicios_total
    FROM v_rr_servicio_semanal
    WHERE period_label = (SELECT period_label FROM latest)
),
modalidad_rt AS (
    SELECT
        MAX(CASE WHEN modalidad = 'MULTIMARCA' THEN carga_asignada END)
            AS carga_multimarca_rt,
        MAX(CASE WHEN modalidad = 'PITUTO' THEN carga_asignada END)
            AS carga_pituto_rt
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
    s.personas_propal_servicio,
    s.peso_propal_pct,
    s.carga_servicios_total,
    m.carga_multimarca_rt,
    m.carga_pituto_rt,
    ROUND(
        100.0 * m.carga_multimarca_rt
        / NULLIF(m.carga_multimarca_rt + m.carga_pituto_rt, 0),
        4
    ) AS peso_multimarca_dentro_rt_pct,
    ROUND(
        100.0 * m.carga_pituto_rt
        / NULLIF(m.carga_multimarca_rt + m.carga_pituto_rt, 0),
        4
    ) AS peso_pituto_dentro_rt_pct
FROM v_rr_gerencial_actual AS g
CROSS JOIN servicios AS s
CROSS JOIN modalidad_rt AS m
WHERE g.period_label = (SELECT period_label FROM latest);
