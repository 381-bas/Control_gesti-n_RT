# Ruta 2 · Modelo SQL gerencial

## Objetivo

Transformar `rr_historico.sqlite` en una capa analítica estable para
Streamlit. La lógica de negocio permanece en SQLite; Streamlit solo consulta,
filtra, presenta y exporta.

## Secuencia de aplicación

```text
01_periodos.sql
02_resumen_global.sql
03_cadenas_clientes.sql
04_personal_modalidad.sql
05_crecimiento_movimientos.sql
06_catastro.sql
07_dashboard_qa.sql
```

## Capas

### Base normalizada

- `v_rr_fuentes_validas`
- `v_rr_base_normalizada`
- `v_rr_periodos`

Solo se incorporan archivos con columnas requeridas, sin errores de carga,
período completo y carpeta mensual con formato `NN - MES`.

### Operación

- `fact_rr_local_cliente_semana`
- `v_rr_local_cliente_semana`
- `fact_rr_resumen_global`
- `v_rr_resumen_global`
- `v_rr_resumen_global_compare`
- `v_rr_resumen_mensual`
- `v_rr_resumen_mensual_compare`

El volumen oficial se calcula mediante:

```text
MAX(VECES POR SEMANA)
por PERÍODO + CADENA + COD KPI ONE + CLIENTE
```

### Cadenas y clientes

- `v_rr_cadena_semanal`
- `v_rr_cliente_semanal`
- `v_rr_cadena_cliente_semanal`

Publican volumen, participación, Pareto, ranking, dotación y variaciones.

### Personas y modalidades

- `v_rr_persona_semana`
- `v_rr_modalidad_semanal`
- `v_rr_modalidad_semanal_compare`

`personas_activas` utiliza `COUNT(DISTINCT REPONEDOR)`.
`rutas_activas` utiliza `COUNT(DISTINCT RUTERO)`.

Los estados `CIERRE`, `REMODELACIÓN` y `POR INAGURAR` se excluyen de
dotación y permanecen en catastro.

`carga_asignada` es una métrica separada del volumen oficial. Puede ser mayor
cuando una cartera tiene asignaciones en más de una modalidad.

### Crecimiento

- `v_rr_movimientos_local_cliente`
- `v_rr_crecimiento_componentes`
- `v_rr_crecimiento_semanal`
- `v_rr_movimientos_personal`
- `v_rr_movimientos_asignacion`

Cada período se compara contra el período anterior definido en
`v_rr_periodos`.

Movimientos de cartera:

- `NUEVO`
- `RETIRADO`
- `AUMENTA_FRECUENCIA`
- `DISMINUYE_FRECUENCIA`
- `SIN_CAMBIO`

El efecto neto de movimientos debe cuadrar exactamente con el delta de
volumen.

### Catastro

- `v_rr_estado_local_semana`
- `v_rr_catastro_local_semana`
- `v_rr_catastro_local_compare`
- `v_rr_catastro_estado_resumen`

No se impone una precedencia artificial entre estados. Se conservan banderas
independientes.

### Calidad

- `v_rr_dashboard_qa`
- `v_rr_dashboard_metadata`

La pestaña de calidad de Streamlit consumirá directamente estos objetos.

## Materialización

Las agregaciones más costosas se reconstruyen como tablas `fact_rr_*`.
Las vistas públicas mantienen una interfaz estable para Streamlit.

La reconstrucción completa sobre 78.770 filas demoró aproximadamente
25–40 segundos en el entorno de prueba. Después de materializar:

| Consulta | Filas | Mediana |
|---|---:|---:|
| Resumen actual | 1 | < 0,01 s |
| Resumen mensual | 6 | < 0,01 s |
| Ranking cadenas | 11 | < 0,01 s |
| Top 20 clientes | 20 | < 0,01 s |
| Modalidades | 4 | < 0,01 s |
| Movimientos detallados | 3.572 | ~ 0,13 s |
| Catastro | 909 | ~ 0,01 s |

## Aplicación

```powershell
python scripts/aplicar_vistas.py
```

O con una base explícita:

```powershell
python scripts/aplicar_vistas.py `
  --db-path "C:\Users\basti\Documents\PORTALES\VSC\ANÁLISIS_RUTA_RUTERO\rr_historico.sqlite"
```

El script genera un backup previo, aplica los SQL, ejecuta `ANALYZE` y valida:

- existencia de vistas y facts;
- ausencia de duplicados en LOCAL/CLIENTE;
- ausencia de controles ERROR positivos;
- cuadre de todos los deltas de movimientos.

## Pruebas

```powershell
pytest -q
```

Fixture de aceptación:

```text
contracts/expected_2026_06_S3.json
```

Resultado de desarrollo:

```text
13 passed
```
