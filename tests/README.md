# Tests

Las pruebas deben validar la paridad entre SQLite, contratos y Streamlit.

## Cobertura mínima

- períodos disponibles y orden correcto;
- ausencia de duplicados en claves analíticas;
- volumen consolidado mediante MAX(VECES POR SEMANA);
- exclusión de estados en indicadores de personas y rutas;
- consistencia de modalidad derivada;
- comparación actual versus período anterior;
- fixture gerencial de referencia.

## Regla de aceptación

Las diferencias numéricas entre la vista SQL y el resultado esperado deben ser cero.
