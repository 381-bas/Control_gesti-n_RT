# Dashboard Streamlit · Página gerencial V2.1

## Preparación

Desde la raíz del repositorio:

```powershell
git pull origin feature/dashboard-control-gestion-v2-1
python scripts/aplicar_vistas.py
```

El archivo `12_pituto_gestion_v2_1.sql` corrige PITUTO como gestión por LOCAL/CLIENTE.

## Ejecución

```powershell
python -m streamlit run streamlit_app/app.py
```

Dirección local habitual: `http://localhost:8501`.

## Estructura

1. Situación operativa total empresa.
2. Concentración por RETAIL y servicio.
3. Estructura MULTIMARCA y gestión PITUTO.
4. Capacidad regional MULTIMARCA y presencia PITUTO.
5. Comportamiento mensual.
6. Lectura operacional basada en datos.
7. Respaldo desplegable y exportable.

## Reglas

- El total empresa incluye Retail Trust, Breden Master y Propal.
- Retail Trust agrupa MULTIMARCA y PITUTO.
- MULTIMARCA se mide como capacidad estructural por rutas.
- PITUTO no es ruta ni dotación en esta base.
- PITUTO se mide por locales y combinaciones LOCAL/CLIENTE.
- La dotación real de PITUTO se administra en otra base.
- Breden Master y Propal no participan en la presión de rutas RT.
- La fotografía corresponde a la última semana disponible.
- Los gráficos mensuales usan el último corte disponible del mes.
- Streamlit consume vistas SQLite y no recalcula métricas.
- La base se abre en modo lectura.

## Validación

```powershell
python -m pytest -q
```

Documentación del PATCH: `docs/PATCH_PITUTO_V2_1.md`.
