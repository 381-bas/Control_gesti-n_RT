# SQL

La lógica canónica del dashboard se implementará en vistas SQLite versionadas.

## Orden previsto

1. `01_periodos.sql`
2. `02_resumen_global.sql`
3. `03_cadenas_clientes.sql`
4. `04_personal_modalidad.sql`
5. `05_crecimiento_movimientos.sql`
6. `06_catastro.sql`
7. `07_dashboard_qa.sql`

## Principio

Streamlit debe leer estas vistas y no recalcular reglas de negocio con pandas.

Cada archivo SQL deberá incluir:

- propósito;
- grano de la vista;
- definición de métricas;
- dependencias;
- consultas QA asociadas.
