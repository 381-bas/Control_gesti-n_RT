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

## Capa gerencial V1

Los archivos 08 y 09 publican:

- `v_rr_region_semanal`
- `v_rr_region_modalidad_semanal`
- `v_rr_region_capacidad_semanal`
- `v_rr_retail_mensual`
- `v_rr_region_mensual`
- `v_rr_modalidad_mensual`
- `v_rr_capacidad_mensual`
- `v_rr_gerencial_actual`

## Principio

Streamlit debe leer estas vistas y no recalcular reglas de negocio con pandas.

Cada archivo SQL debe incluir:

- propósito;
- grano de la vista;
- definición de métricas;
- dependencias;
- validaciones asociadas.
