# Prompt base para Claude · PDF gerencial integrado

Actúa como analista senior de control de gestión y diseñador de informes ejecutivos.

Debes construir un informe gerencial autoexplicativo, orientado a una decisión de aumento de capacidad en las zonas más afectadas. El documento debe poder comprenderse sin exposición oral adicional.

## Fuentes a utilizar

1. Dashboard Control de Gestión V2.1.
2. Informe validado CASO Y CIA/OXXO y OLIMPIA/JUMBO RM.
3. Evolutivo de CENTRO DE COSTO.
4. Horas extra de los últimos dos meses.

## Objetivo

Integrar evidencia operacional y económica para determinar si la presión observada es suficiente, recurrente y territorialmente concentrada como para justificar un aumento de personal.

No reutilices como conclusión final la frase previa “sin requerir personal adicional”. Esa conclusión pertenecía a una etapa anterior. El nuevo análisis debe reevaluar la necesidad de capacidad con costos y horas extra incorporados.

## Reglas de negocio

- MULTIMARCA se analiza por rutas, personas, locales, puntos LOCAL/CLIENTE y carga.
- PITUTO no es una ruta. Se analiza por locales, combinaciones LOCAL/CLIENTE, clientes, región y carga.
- La dotación PITUTO real se administra en otra base y no debe inferirse desde RUTA RUTERO.
- Carga oficial y carga asignada deben permanecer separadas.
- Breden Master y Propal no se mezclan con la capacidad de rutas Retail Trust.
- No sumes personas entre regiones.
- No atribuyas causalidad sin evidencia de cruce.
- Toda cifra debe indicar período, universo y denominador.

## Corrección obligatoria del informe OXXO/OLIMPIA

El informe anterior utilizó `PITUTO` dentro de rankings y conteos de rutas. Debe corregirse:

- `PITUTO` no se contabiliza como ruta.
- OXXO registra 17 rutas MULTIMARCA afectadas más 3 locales gestionados mediante PITUTO.
- En S3, OXXO tiene presencia en 22 rutas MULTIMARCA más la categoría PITUTO, no 23 rutas estructurales.
- De las altas OXXO, 61 locales corresponden a MULTIMARCA y 3 a PITUTO.
- Diez rutas MULTIMARCA reciben OXXO por primera vez con 29 locales; siete rutas MULTIMARCA preexistentes suman 32 locales; PITUTO agrega 3 locales.
- OLIMPIA registra 18 rutas MULTIMARCA con 19 locales, más 2 locales PITUTO.
- La presión coincidente corresponde a 7 rutas MULTIMARCA con 20 locales y 36 unidades de carga directa, más una categoría PITUTO con 5 locales y 9 unidades de carga.

No presentes `PITUTO` como ruta en tablas, gráficos, subtítulos ni conclusiones.

## Evidencia ya validada

CASO Y CIA/OXXO:

- Pasa de 30 a 94 locales en 2026-06-S3.
- Incorpora 64 locales nuevos.
- Afecta 17 rutas MULTIMARCA y 3 locales PITUTO.
- EMU-6, DMU-8, HMU-3 y HMU-4 absorben 37 altas.
- EMU-6 incorpora 14 locales.
- Diez rutas MULTIMARCA reciben OXXO por primera vez y siete amplían cobertura.
- El 90,6% de las altas corresponde a Región Metropolitana.

OLIMPIA/JUMBO RM:

- Ingresa en 2026-06-S2.
- Incorpora 21 locales con frecuencia 3.
- Se distribuye en 18 rutas MULTIMARCA; 2 locales quedan bajo gestión PITUTO.
- Siete rutas MULTIMARCA coinciden con impacto OXXO; existe además una coincidencia en la categoría PITUTO.
- Las cuatro rutas OXXO más afectadas no coinciden con OLIMPIA.

## Análisis requerido

1. Situación global actual.
2. Tendencia de cobertura, puntos y carga.
3. Presión por ruta MULTIMARCA.
4. Gestión PITUTO por cliente y región.
5. Impacto OXXO.
6. Impacto OLIMPIA.
7. Evolución de centros de costo.
8. Evolución de horas extra.
9. Cruce operación–costos–horas extra.
10. Priorización territorial.
11. Escenario actual vs. escenario con aumento de personal.
12. Recomendación gerencial.

## Estructura del PDF

### 1. Portada

Título, período analizado y propósito.

### 2. Resumen ejecutivo

Máximo una página. Debe incluir:

- problema;
- evidencia principal;
- impacto económico;
- zonas prioritarias;
- decisión solicitada.

### 3. Operación global

Tarjetas y tendencias del dashboard V2.1.

### 4. Capacidad MULTIMARCA

Mostrar rutas, locales, puntos y carga por ruta.

### 5. Gestión PITUTO

Mostrar locales y LOCAL/CLIENTE por cliente y región. No mostrar rutas PITUTO ni personas PITUTO.

### 6. Incorporaciones recientes

Separar OXXO y OLIMPIA. Mostrar cronología, rutas MULTIMARCA, gestión PITUTO, regiones y carga incremental.

### 7. Costos

Mostrar evolución de centros de costo, variación absoluta y porcentual, y centros que explican el aumento.

### 8. Horas extra

Mostrar cantidad, costo, distribución territorial y recurrencia.

### 9. Cruce integrado

Crear una matriz por zona o ruta con:

- crecimiento de locales;
- crecimiento de puntos;
- variación de carga;
- horas extra;
- costo incremental;
- nivel de presión.

### 10. Priorización

Clasificar las zonas en alta, media o baja prioridad. Explicar el criterio utilizado. No inventar umbrales: construirlos desde la distribución observada o declararlos como supuestos.

### 11. Escenario de capacidad

Comparar:

- continuidad con estructura actual;
- redistribución operacional;
- incorporación de personal.

Cuando exista costo de contratación, comparar costo esperado con horas extra y sobrecostos actuales.

### 12. Conclusión gerencial

Redactar una solicitud concreta, proporcionada y respaldada por datos. Diferenciar claramente hecho, interpretación y recomendación.

## Requisitos visuales

- Formato ejecutivo, limpio y sobrio.
- Máximo 12 páginas más anexos.
- Una idea principal por página.
- Gráficos con etiquetas directas.
- Tablas limitadas a cifras de decisión.
- Usar anexos para catastro y detalle.
- No saturar con texto.
- Resaltar cifras críticas y variaciones.

## Entrega

Genera:

1. contenido completo del informe;
2. propuesta de gráficos por página;
3. texto de cada título y subtítulo;
4. notas metodológicas;
5. conclusión gerencial;
6. lista de datos faltantes o inconsistencias;
7. especificación lista para producir el PDF.

No cierres una recomendación definitiva si faltan costos, horas extra o claves de cruce. En ese caso, entrega una conclusión provisional y señala exactamente qué dato falta.
