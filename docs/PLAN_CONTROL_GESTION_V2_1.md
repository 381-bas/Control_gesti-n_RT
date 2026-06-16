# Plan de mejora · Control de Gestión V2.1

## Rama

`feature/dashboard-control-gestion-v2-1`

Esta rama parte desde la V2 aprobada de servicios. La investigación OXXO/OLIMPIA permanece aislada en `analysis/trazabilidad-caso-oxxo-olimpia-jumbo`.

## Objetivo

Convertir el dashboard en una lectura gerencial más directa para responder:

1. dónde se concentra la operación;
2. cómo cambia la cobertura;
3. si la estructura MULTIMARCA absorbe la carga con rutas estables;
4. qué parte de la variación es flexible mediante PITUTO;
5. dónde existe presión regional que requiere redistribución operacional.

## Iteración V2.1

### 1. Presión de capacidad MULTIMARCA

Incorporar tendencia mensual de:

- rutas MULTIMARCA;
- personas MULTIMARCA;
- locales MULTIMARCA;
- puntos LOCAL/CLIENTE MULTIMARCA;
- carga MULTIMARCA;
- carga por ruta;
- locales por ruta;
- puntos por ruta.

Este bloque será el principal respaldo para evaluar capacidad estructural.

### 2. Separación visual por servicio

- Mantener total empresa en la cabecera.
- Mantener Retail Trust como MULTIMARCA + PITUTO.
- Mostrar Breden Master y Propal como servicios independientes.
- Usar gráficos pequeños separados para servicios de menor escala.
- No mezclar Breden Master ni Propal con la presión de rutas Retail Trust.

### 3. Capacidad regional limpia

- Mostrar Top 8 regiones y agrupar el resto como `OTRAS REGIONES`.
- Exigir base mínima de dos rutas para rankings de carga por ruta.
- Mostrar siempre el denominador: rutas, personas, locales y puntos.
- Renombrar dotación regional como `personas con presencia`.
- No sumar personas entre regiones.

### 4. Tendencias temporales

- Usar `último corte disponible del mes`.
- Mantener promedio semanal como referencia secundaria.
- Separar carga, cobertura y capacidad para evitar dobles ejes difíciles de interpretar.
- Destacar relación entre crecimiento de locales, puntos, carga y rutas.

### 5. Lectura operacional automática

Publicar hechos verificables:

- cambio de locales y puntos durante el año;
- cambio de rutas MULTIMARCA;
- cambio de carga por ruta;
- estabilidad o variación de personas MULTIMARCA;
- variabilidad de PITUTO;
- regiones con mayor carga por ruta con base suficiente.

No emitir recomendaciones automáticas ni inventar umbrales.

### 6. Respaldo operativo

Agregar tablas desplegables por:

- región;
- ruta;
- RETAIL;
- cliente;
- modalidad;
- servicio.

Cada tabla debe permitir exportación CSV.

### 7. Calidad y claridad

- Mantener QA fuera de la lectura principal.
- Marcar cortes parciales.
- Mostrar universo y denominador de cada porcentaje.
- Evitar métricas duplicadas o con impacto gerencial nulo.

## Integración posterior de trazabilidad OXXO

La investigación OXXO no se incorporará todavía como KPI principal. Se diseñará después como un módulo reutilizable de `Impacto de incorporaciones`, con:

- cliente y cadena seleccionables;
- altas por semana;
- rutas afectadas;
- comparación pre / alta / último corte;
- locales, puntos y carga incremental;
- catastro de salas;
- presión concurrente de otros clientes.

CASO Y CIA/OXXO será el primer caso de validación del módulo. OLIMPIA/JUMBO RM quedará como presión concurrente secundaria.

## Secuencia

1. Crear vistas mensuales de presión MULTIMARCA.
2. Validar cuadres y denominadores.
3. Rediseñar bloques temporales y regionales.
4. Ajustar narrativa automática.
5. Validar visualmente Streamlit.
6. Congelar contrato V2.1.
7. Diseñar módulo genérico de impacto de incorporaciones.
8. Entregar contrato a Codex para réplica HTML.

## Criterios de aceptación

- La portada se entiende en menos de 30 segundos.
- El total empresa y la capacidad Retail Trust no se mezclan.
- La presión MULTIMARCA se explica con carga, locales y puntos por ruta.
- PITUTO se interpreta como capacidad flexible por personas.
- Los rankings regionales muestran su base de cálculo.
- Los servicios independientes mantienen visibilidad sin distorsionar escalas.
- El dashboard no recomienda personal automáticamente.
- La trazabilidad OXXO permanece como módulo posterior y reutilizable.
