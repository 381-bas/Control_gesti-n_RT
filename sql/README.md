# SQL

La lógica canónica del dashboard se implementa en tablas materializadas y vistas SQLite versionadas.

## Orden de aplicación

1. `01_periodos.sql`
2. `02_resumen_global.sql`
3. `03_cadenas_clientes.sql`
4. `04_personal_modalidad.sql`
5. `05_crecimiento_movimientos.sql`
6. `06_catastro.sql`
7. `07_dashboard_qa.sql`
8. `08_kpi_gerencial_v1.sql`
9. `09_kpi_gerencial_patch.sql`
10. `10_modelo_servicios_v2.sql`
11. `11_modelo_servicios_patch.sql`
12. `12_pituto_gestion_v2_1.sql`

## Modelo V2.1

El archivo 12 corrige PITUTO como gestión puntual y no como ruta o dotación.

Publica:

- `v_rr_pituto_gestion_semanal`
- `v_rr_pituto_resumen_semanal`
- `v_rr_pituto_cliente_semanal`
- `v_rr_pituto_region_semanal`
- `v_rr_pituto_cliente_region_semanal`
- `v_rr_pituto_mensual`
- `v_rr_region_retail_trust_v2_1`
- `v_rr_retail_trust_operacion_semanal_v2_1`
- `v_rr_retail_trust_operacion_mensual_v2_1`
- `v_rr_gerencial_v2_1_actual`

## Principio

Streamlit debe leer estas vistas y no recalcular reglas de negocio con pandas.

- MULTIMARCA se mide por rutas, personas, locales, puntos y carga.
- PITUTO se mide por locales y combinaciones LOCAL/CLIENTE.
- La dotación real PITUTO se incorporará únicamente desde su base externa.
- Breden Master y Propal permanecen como servicios independientes.
