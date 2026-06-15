# Contracts

Esta carpeta define el contrato compartido entre SQLite, Streamlit y futuras interfaces web.

## Archivos previstos

- `metricas.yml`: definición, fuente y grano de cada indicador.
- `filtros.yml`: filtros permitidos y dependencias.
- `columnas.yml`: nombres técnicos y etiquetas gerenciales.
- `expected_2026_06_S3.json`: fixture de aceptación.

## Regla

Una métrica no se considera publicada hasta que tenga:

1. definición de negocio;
2. fuente SQL;
3. grano;
4. comportamiento temporal;
5. prueba de aceptación.
