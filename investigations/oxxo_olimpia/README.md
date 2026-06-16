# Trazabilidad focalizada

Rama de análisis para CASO Y CIA en OXXO y, como segunda derivada, OLIMPIA en JUMBO Región Metropolitana.

## Objetivo principal

Cuantificar el ingreso de salas de CASO Y CIA en OXXO alrededor de junio S1-S2, identificar los RUTERO afectados y comparar la carga de cada ruta antes y después del ingreso.

La evidencia debe incluir locales, puntos LOCAL/CLIENTE, frecuencia, región, comuna, RUTERO, REPONEDOR, primeras apariciones y permanencia hasta el último corte.

## Segunda derivada

Medir el ingreso de OLIMPIA en JUMBO Región Metropolitana y su aporte adicional de locales, puntos de gestión, carga y rutas con presencia.

## Fuente

La extracción consulta rr_historico.sqlite mediante las vistas v_rr_periodos, v_rr_local_cliente_semana, v_rr_persona_asignacion_semana y v_rr_base_normalizada.

## Ejecución

Desde la raíz del repositorio:

```powershell
python -m pytest -q tests/test_trazabilidad_oxxo_olimpia.py tests/test_trazabilidad_oxxo_olimpia_v2.py
python scripts/exportar_trazabilidad_oxxo_olimpia_v2.py
```

El launcher V2 corrige el caso en que la semana de mayor alta coincide con el último corte disponible.

La salida se guarda en exports y se comprime en un ZIP listo para análisis en Claude.

## Regla

Si los valores reales difieren de la referencia verbal de aproximadamente 14 locales y 4 a 5 rutas, prevalece la evidencia de la base.