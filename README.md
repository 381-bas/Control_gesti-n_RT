# Control de Gestión RT

Proyecto para consolidar y analizar históricamente la operación **RUTA RUTERO** de RT.

## Objetivo

Construir una fuente única de datos y una página gerencial que permita revisar:

- carga operativa actual;
- concentración por RETAIL, modalidad y región;
- capacidad estructural y flexible;
- comportamiento mensual;
- detalle operativo como respaldo.

## Fuente canónica

La lógica oficial vive en **SQLite** mediante tablas materializadas y vistas SQL. Streamlit consume esa capa y no redefine las reglas de negocio.

```text
Excel semanales
      ↓
Python · ingesta y QA
      ↓
rr_historico.sqlite
      ↓
Facts + vistas SQL gerenciales
      ↓
Streamlit local
```

## Universo inicial validado

- Período: enero a junio de 2026.
- Archivos semanales: 23.
- Filas históricas: 78.770.
- Combinaciones semanales LOCAL/CLIENTE consolidadas: 76.635.
- Hoja fuente: `RUTA RUTERO`.

## Reglas confirmadas

### Carga operativa

```text
CADENA + COD KPI ONE + CLIENTE
MAX(VECES POR SEMANA)
```

### Modalidad derivada desde RUTERO

```text
RUTERO = PITUTO              → PITUTO
RUTERO = PROPAL              → PROPAL
Primeros 2 caracteres = BR   → BREDEN
Caracteres 2 y 3 = MU        → MULTIMARCA
Cualquier otro valor         → N/A
```

Los valores `CIERRE`, `REMODELACIÓN` y `POR INAGURAR` son estados de catastro, no personas.

### Personas y capacidad regional

```text
PERSONAS = COUNT(DISTINCT REPONEDOR)
RUTAS ESTRUCTURALES = COUNT(DISTINCT RUTERO)
                       para MULTIMARCA y BREDEN
CAPACIDAD FLEXIBLE = COUNT(DISTINCT REPONEDOR)
                     para PITUTO y PROPAL
```

## Aplicar el modelo SQL

Crea `.env` desde `.env.example` y ejecuta:

```powershell
python scripts/aplicar_vistas.py
```

El proceso:

1. crea un backup consistente de SQLite;
2. aplica los archivos SQL versionados;
3. reconstruye las tablas `fact_rr_*`;
4. ejecuta `ANALYZE`;
5. valida objetos, unicidad, participaciones y cuadres.

## Ejecutar el dashboard local

```powershell
& C:\Users\basti\AppData\Local\Python\pythoncore-3.14-64\python.exe `
  -m streamlit run streamlit_app\app.py
```

La aplicación se abre normalmente en:

```text
http://localhost:8501
```

## Página gerencial V1

La lectura principal queda en una sola página:

1. Situación operativa actual.
2. Peso por RETAIL y modalidad.
3. Peso y capacidad por región.
4. Tendencias mensuales.
5. Lectura operacional automática.
6. Detalle desplegable y exportable.

No se muestran comparaciones automáticas contra la semana anterior. La tendencia principal utiliza cierre mensual y promedio semanal del mes.

## Pruebas

```powershell
python -m pytest -q
```

Fixture gerencial:

```text
contracts/expected_2026_06_S3.json
```

Contrato de KPI:

```text
contracts/dashboard_kpi_v1.yml
```

Documentación:

```text
docs/RUTA_2_SQL.md
docs/PLAN_LIMPIEZA_KPI_GERENCIAL_V1.md
streamlit_app/README.md
```

## Seguridad de datos

La base SQLite, archivos Excel y salidas con información operativa no se versionan en Git. La aplicación local abre SQLite en modo lectura.

## Estado

- **Ruta 1 · Bootstrap:** completada.
- **Ruta 2 · Modelo SQL:** completada y validada.
- **Ruta 3 · Página gerencial V1:** implementada; pendiente de validación visual y de negocio.
- **Siguiente etapa:** congelar el contrato aprobado y entregar el diseño a Codex para la versión HTML.
