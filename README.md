# Control de Gestión RT

Proyecto para consolidar y analizar históricamente la operación **RUTA RUTERO** de RT.

## Objetivo

Construir una fuente única de datos y un dashboard gerencial que permita analizar:

- crecimiento semanal y mensual;
- volumen operativo por cadena, cliente y local;
- frecuencia consolidada por LOCAL/CLIENTE;
- dotación y carga por modalidad;
- altas, bajas y cambios de frecuencia;
- catastro de estados operativos;
- calidad y trazabilidad de las cargas.

## Fuente canónica

La lógica oficial vive en **SQLite** mediante tablas materializadas y vistas SQL. Streamlit será la primera interfaz de visualización y no debe recalcular reglas de negocio.

```text
Excel semanales
      ↓
Python · ingesta y QA
      ↓
rr_historico.sqlite
      ↓
Facts + vistas SQL gerenciales
      ↓
Streamlit
```

## Universo inicial validado

- Período: enero a junio de 2026.
- Archivos semanales: 23.
- Filas históricas: 78.770.
- Combinaciones semanales LOCAL/CLIENTE consolidadas: 76.635.
- Hoja fuente: `RUTA RUTERO`.

## Reglas confirmadas

### Frecuencia operativa

Para cada período:

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

### Personas y rutas

```text
PERSONAS = COUNT(DISTINCT REPONEDOR)
RUTAS    = COUNT(DISTINCT RUTERO)
```

## Estructura

```text
Control_gesti-n_RT/
├── README.md
├── .gitignore
├── requirements.txt
├── .env.example
├── data/
├── docs/
├── scripts/
├── sql/
├── contracts/
├── streamlit_app/
└── tests/
```

## Aplicar el modelo SQL

Crea `.env` desde `.env.example` y ejecuta:

```powershell
python scripts/aplicar_vistas.py
```

El proceso:

1. crea un backup consistente de SQLite;
2. aplica `sql/01_...` a `sql/07_...`;
3. reconstruye las tablas `fact_rr_*`;
4. ejecuta `ANALYZE`;
5. valida objetos, unicidad, QA y cuadre de movimientos.

## Pruebas

```powershell
pytest -q
```

Resultado de desarrollo de la Ruta 2:

```text
13 passed
0 controles ERROR positivos
0 deltas sin cuadrar
0 duplicados en la clave analítica LOCAL/CLIENTE
```

Fixture gerencial:

```text
contracts/expected_2026_06_S3.json
```

Documentación técnica:

```text
docs/RUTA_2_SQL.md
```

## Rendimiento

Las consultas principales quedaron materializadas para consumo de Streamlit:

- resumen global y mensual: menos de 0,01 s en la prueba local;
- rankings de cadenas y clientes: menos de 0,01 s;
- modalidades: menos de 0,01 s;
- catastro de 909 locales: alrededor de 0,01 s;
- movimientos detallados de 3.572 registros: alrededor de 0,13 s.

La evidencia se conserva en `contracts/performance_route2.json`.

## Seguridad de datos

La base SQLite, archivos Excel y salidas con información operativa no se versionan en Git.

## Estado

- **Ruta 1 · Bootstrap:** completada.
- **Ruta 2 · Modelo SQL gerencial:** completada y validada.
- **Próximo bloque:** MVP Streamlit conectado exclusivamente a las vistas publicadas.
