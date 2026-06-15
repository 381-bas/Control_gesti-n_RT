# Control de Gestión RT

Proyecto para consolidar y analizar históricamente la operación **RUTA RUTERO** de RT.

## Objetivo

Construir una fuente única de datos y una página gerencial que permita revisar:

- carga operativa total de la empresa;
- concentración por RETAIL, servicio y región;
- capacidad estructural y flexible de Retail Trust;
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

### Servicios operativos

```text
RETAIL TRUST  = MULTIMARCA + PITUTO
BREDEN MASTER = BREDEN
PROPAL        = PROPAL
```

Retail Trust corresponde al servicio de reposición de mercaderistas. MULTIMARCA representa su estructura permanente y PITUTO su capacidad flexible. Breden Master y Propal son servicios independientes y no se incorporan a la presión de rutas de Retail Trust.

### Capacidad Retail Trust

```text
RUTAS MULTIMARCA = COUNT(DISTINCT RUTERO)
PERSONAS PITUTO   = COUNT(DISTINCT REPONEDOR)
```

## Aplicar el modelo SQL

Crea `.env` desde `.env.example` y ejecuta:

```powershell
python scripts/aplicar_vistas.py
```

El proceso aplica automáticamente todos los archivos SQL versionados, incluyendo `10_modelo_servicios_v2.sql` y `11_modelo_servicios_patch.sql`.

## Ejecutar el dashboard local

```powershell
& C:\Users\basti\AppData\Local\Python\pythoncore-3.14-64\python.exe `
  -m streamlit run streamlit_app\app.py
```

Dirección local habitual:

```text
http://localhost:8501
```

## Página gerencial V2

La lectura principal queda en una sola página:

1. Situación operativa total empresa.
2. Peso por RETAIL y servicio.
3. Composición MULTIMARCA/PITUTO dentro de Retail Trust.
4. Capacidad regional de Retail Trust.
5. Tendencias mensuales globales y por servicio.
6. Lectura operacional automática.
7. Detalle desplegable y exportable.

La fotografía corresponde a la última semana disponible. Los gráficos mensuales utilizan el último corte disponible de cada mes y no comparaciones automáticas contra la semana anterior.

## Pruebas

```powershell
python -m pytest -q
```

Contratos:

```text
contracts/expected_2026_06_S3.json
contracts/dashboard_kpi_v2.yml
```

## Seguridad de datos

La base SQLite, archivos Excel y salidas con información operativa no se versionan en Git. La aplicación local abre SQLite en modo lectura.

## Estado

- **Ruta 1 · Bootstrap:** completada.
- **Ruta 2 · Modelo SQL:** completada y validada.
- **Ruta 3 · Página gerencial V2:** implementada; pendiente de validación visual y de negocio.
- **Siguiente etapa:** congelar el contrato aprobado y entregar el diseño a Codex para la versión HTML.
