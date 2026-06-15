# Streamlit App

Primera interfaz del dashboard gerencial.

## Alcance inicial

- resumen gerencial;
- evolución semanal;
- ranking de cadenas y clientes;
- ratios por modalidad;
- movimientos de crecimiento;
- catastro de estados;
- calidad de datos.

## Regla de implementación

La aplicación debe:

- conectarse a SQLite en modo lectura;
- consumir únicamente vistas SQL publicadas;
- utilizar caché para consultas;
- mantener filtros consistentes entre páginas;
- permitir exportar el detalle visible;
- no redefinir métricas con pandas.
