# Dashboard Streamlit · Página gerencial V1

## Preparación

Desde la raíz del repositorio:

```powershell
git pull origin main
python scripts/aplicar_vistas.py
```

## Ejecución

```powershell
python -m streamlit run streamlit_app/app.py
```

Dirección local habitual: `http://localhost:8501`.

## Estructura

1. Situación operativa actual.
2. Concentración por RETAIL y modalidad.
3. Distribución territorial y capacidad regional.
4. Comportamiento mensual.
5. Lectura operacional basada en datos.
6. Respaldo desplegable y exportable.

## Reglas

- La fotografía actual corresponde a la última semana disponible.
- No se muestran deltas automáticos contra la semana anterior.
- Las tendencias utilizan cierre mensual y promedio semanal.
- MULTIMARCA/BREDEN representan rutas estructurales.
- PITUTO/PROPAL representan capacidad flexible por persona.
- Streamlit consume vistas SQLite y no recalcula métricas.
- La base se abre en modo lectura.

## Validación

```powershell
python -m pytest -q
```

Contrato funcional: `contracts/dashboard_kpi_v1.yml`.
