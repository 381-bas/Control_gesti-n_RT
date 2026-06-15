# Plan de limpieza de KPI gerenciales · Dashboard V1

## Propósito

Antes de rediseñar Streamlit o delegar la interfaz a Codex, cerrar un contrato de indicadores que responda una sola pregunta:

> ¿Dónde está concentrada la carga operativa actual y qué evidencia respalda ampliar la capacidad de rutas o dotación?

La portada será una sola página gerencial. El detalle quedará como respaldo desplegable.

---

## Alcance de la primera iteración

### 1. Situación operativa actual

Indicadores de cabecera:

- Carga operativa semanal.
- Locales cubiertos.
- Puntos de gestión `LOCAL/CLIENTE`.
- Clientes activos.
- Personas MULTIMARCA.
- Personas PITUTO.

Regla temporal:

- Fotografía actual = última semana disponible.
- No mostrar delta contra semana anterior en tarjetas.
- El comportamiento histórico se explica mediante tendencias mensuales.

### 2. Peso operativo por RETAIL

Mostrar para cada cadena:

- carga operativa;
- participación sobre el total;
- locales;
- puntos de gestión;
- clientes.

Visual principal:

- barra horizontal descendente;
- etiqueta `cantidad + porcentaje`.

### 3. Peso operativo por modalidad

Mostrar para MULTIMARCA, PITUTO, BREDEN y PROPAL:

- carga asignada;
- participación sobre la carga asignada total;
- personas;
- rutas;
- locales;
- puntos de gestión;
- carga por persona.

Precisión:

- `volumen_operativo` es la métrica oficial sin duplicar `LOCAL/CLIENTE`.
- `carga_asignada` sirve para distribución por modalidad y puede superar el volumen oficial cuando una gestión está compartida.

### 4. Peso operativo por región

Mostrar por región:

- carga operativa;
- participación sobre el total;
- locales;
- clientes;
- puntos de gestión.

Visual principal:

- barra horizontal descendente;
- etiqueta `cantidad + porcentaje`.

### 5. Capacidad regional

Mostrar por región:

- personas activas;
- rutas con presencia;
- clientes;
- puntos de gestión;
- carga por persona;
- carga por ruta;
- puntos de gestión por persona.

#### Regla pendiente que debe cerrarse antes de publicar

`RUTERO` no siempre equivale a una ruta física individual:

- MULTIMARCA y BREDEN suelen utilizar códigos de ruta específicos.
- PITUTO y PROPAL pueden utilizar códigos genéricos presentes en varias regiones.

Por lo tanto, el dashboard no publicará todavía un `% de rutas por región` sin definir una de estas alternativas:

1. **Presencias ruta-región:** cada combinación `REGIÓN + RUTERO` cuenta una vez.
2. **Ruta principal:** asignar cada RUTERO a la región donde concentra mayor carga.
3. **Estructura separada:** rutas MULTIMARCA/BREDEN por región y personas PITUTO/PROPAL por región.

La alternativa recomendada para V1 es la 3, porque evita presentar PITUTO y PROPAL como una sola ruta nacional.

### 6. Ratio de clientes por región

Publicar métricas separadas:

- clientes distintos por región;
- clientes por local;
- puntos de gestión por local;
- clientes por persona;
- puntos de gestión por persona.

No utilizar solo `COUNT(DISTINCT CLIENTE)` como medida de carga, porque no distingue cobertura ni frecuencia.

### 7. Tendencias mensuales

Mostrar cierre mensual y, como dato secundario, promedio semanal mensual para:

- carga operativa;
- locales;
- puntos de gestión;
- clientes;
- personas MULTIMARCA;
- personas PITUTO;
- carga MULTIMARCA;
- carga PITUTO;
- carga por persona;
- carga por ruta.

No sumar fotografías semanales para representar tamaño mensual.

---

## Fuera de alcance de V1

Se pospone para una segunda iteración:

- estatus de permanencia de cada cliente;
- locales mantenidos en el tiempo por cliente y cadena;
- clientes estables, transitorios o recurrentes;
- migraciones de modalidad por cliente;
- detalle histórico de gestión de un cliente seleccionado.

Primero se validará la distribución global y regional.

---

## Página gerencial V1

Orden de lectura:

1. Situación operativa actual.
2. Peso por RETAIL.
3. Peso por modalidad.
4. Peso por región.
5. Capacidad regional.
6. Tendencias mensuales.
7. Lectura operacional automática.
8. Detalle de respaldo en secciones desplegables.

La lectura operacional debe explicar hechos, no emitir recomendaciones automáticas sin umbrales aprobados.

Ejemplo:

> La carga y los puntos de gestión aumentan durante el año, mientras la dotación MULTIMARCA se mantiene estable. PITUTO presenta mayor variación y absorbe parte del ajuste operativo.

---

## Nuevos objetos SQL requeridos

- `v_rr_region_semanal`
- `v_rr_region_modalidad_semanal`
- `v_rr_region_capacidad_semanal`
- `v_rr_retail_mensual`
- `v_rr_region_mensual`
- `v_rr_modalidad_mensual`
- `v_rr_capacidad_mensual`

Todos deben incluir pruebas de unicidad y cuadre contra el volumen oficial.

---

## Criterios de aceptación antes de Codex

1. Cada KPI tiene nombre gerencial, fórmula, fuente SQL y grano.
2. Las participaciones suman 100% dentro de su universo.
3. Región y RETAIL cuadran con el volumen global.
4. Modalidad identifica claramente que usa carga asignada.
5. Personas y rutas no se mezclan.
6. PITUTO y PROPAL no se presentan como rutas físicas individuales.
7. La portada no muestra comparaciones semanales automáticas.
8. Las tendencias mensuales usan cierre mensual y promedio semanal cuando corresponda.
9. La vista detallada queda fuera de la lectura principal.
10. El fixture de aceptación contiene los valores de la última semana y cierres mensuales.

---

## Handoff posterior a Codex

Codex recibirá únicamente después de aprobar los KPI:

- contrato de métricas;
- vistas SQL cerradas;
- fixture de aceptación;
- orden visual de la página;
- gráficos requeridos;
- criterios de responsive y exportación;
- prohibición de recalcular métricas en Python o JavaScript.

Su tarea será diseño e implementación visual, no interpretación del negocio.
