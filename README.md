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

La lógica oficial vive en **SQLite** mediante tablas y vistas SQL. Streamlit será la primera interfaz de visualización y no debe recalcular reglas de negocio.

```text
Excel semanales
      ↓
Python · ingesta y QA
      ↓
rr_historico.sqlite
      ↓
Vistas SQL gerenciales
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

## Estructura inicial

```text
Control_gesti-n_RT/
├── README.md
├── .gitignore
├── requirements.txt
├── .env.example
├── data/
├── scripts/
├── sql/
├── contracts/
├── streamlit_app/
└── tests/
```

## Seguridad de datos

La base SQLite, archivos Excel y salidas con información operativa no se versionan en Git.

## Estado

**Fase 1 · Bootstrap del repositorio**

Próximo bloque: creación y validación de las vistas SQL gerenciales antes de construir la interfaz Streamlit.
