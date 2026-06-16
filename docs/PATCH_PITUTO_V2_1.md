# PATCH PITUTO · V2.1

## Corrección de negocio

PITUTO no representa una ruta operativa. Es una gestión puntual contratada para atender un local y su dotación real se controla en otra base.

Por lo tanto, `RUTERO = PITUTO` no debe interpretarse como:

- una ruta;
- una persona;
- una unidad de dotación;
- una base válida para calcular carga por persona.

## Unidad analítica válida

En RUTA RUTERO, PITUTO se mide mediante:

```text
LOCAL PITUTO   = CADENA + COD KPI ONE
GESTIÓN PITUTO = CADENA + COD KPI ONE + CLIENTE
```

Una sala puede tener más de una gestión PITUTO cuando existen varios clientes en el mismo local.

## Indicadores publicados

### Resumen

- locales PITUTO;
- gestiones PITUTO;
- clientes PITUTO;
- cadenas PITUTO;
- regiones PITUTO;
- carga asignada PITUTO;
- gestiones por local;
- carga por gestión.

### Cliente

- gestiones PITUTO por cliente;
- locales PITUTO por cliente;
- regiones y cadenas;
- carga PITUTO;
- participación sobre las gestiones PITUTO totales.

### Región

- gestiones PITUTO por región;
- locales PITUTO;
- clientes PITUTO;
- carga PITUTO;
- participación regional.

### Cliente × región

Drilldown para identificar qué clientes explican la gestión PITUTO de cada región.

## MULTIMARCA

MULTIMARCA mantiene su tratamiento estructural:

- rutas distintas;
- personas con asignación;
- locales;
- puntos LOCAL/CLIENTE;
- carga;
- carga, locales y puntos por ruta.

## Objetos SQL

El archivo `sql/12_pituto_gestion_v2_1.sql` crea:

- `v_rr_pituto_gestion_semanal`
- `v_rr_pituto_resumen_semanal`
- `v_rr_pituto_cliente_semanal`
- `v_rr_pituto_region_semanal`
- `v_rr_pituto_cliente_region_semanal`
- `v_rr_pituto_mensual`
- `v_rr_region_retail_trust_v2_1`
- `v_rr_retail_trust_operacion_semanal_v2_1`
- `v_rr_retail_trust_operacion_mensual_v2_1`
- `v_rr_gerencial_v2_1_actual`

## Cambios visuales

La portada reemplaza:

```text
Personas PITUTO
Carga PITUTO por persona
Dotación Retail Trust = MULTIMARCA + PITUTO
```

por:

```text
Locales PITUTO
Gestiones PITUTO
Clientes PITUTO
Gestiones PITUTO por cliente
Gestiones PITUTO por región
```

La cantidad real de personas PITUTO se incorporará solo cuando se conecte la base específica que administra esas contrataciones.

## Integración futura

Cuando la segunda base esté disponible, se podrá cruzar mediante una clave de asignación y agregar:

- personas PITUTO reales;
- costo por gestión;
- vigencia de contratación;
- cobertura persona–local;
- rotación y continuidad.

Hasta entonces, esos indicadores quedan expresamente fuera del dashboard.