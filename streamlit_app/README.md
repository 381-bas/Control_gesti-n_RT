# Dashboard Streamlit · Página gerencial V2

## Preparación

Desde la raíz del repositorio:

```powershell
git pull origin main
python scripts/aplicar_vistas.py
```

El archivo `10_modelo_servicios_v2.sql` separa:

- Retail Trust: MULTIMARCA + PITUTO.
- Breden Master: servicio independiente.
- Propal: servicio independiente.

## Ejecución

```powershell
python -m streamlit run streamlit_app/app.py
```

Dirección local habitual: `http://localhost:8501`.

## Estructura

1. Situación operativa total empresa.
2. Concentración por RETAIL y servicio.
3. Composición del servicio Retail Trust.
4. Capacidad regional Retail Trust.
5. Comportamiento mensual global y por servicio.
6. Lectura operacional basada en datos.
7. Respaldo desplegable y exportable.

## Reglas

- El total empresa incluye Retail Trust, Breden Master y Propal.
- Retail Trust agrupa MULTIMARCA y PITUTO.
- MULTIMARCA se mide como capacidad estructural por rutas.
- PITUTO se mide como capacidad flexible por personas.
- Breden Master y Propal no participan en la presión de rutas RT.
- La fotografía corresponde a la última semana disponible.
- Los gráficos mensuales usan el último corte disponible del mes.
- Streamlit consume vistas SQLite y no recalcula métricas.
- La base se abre en modo lectura.

## Validación

```powershell
python -m pytest -q
```

Contrato funcional: `contracts/dashboard_kpi_v2.yml`.
