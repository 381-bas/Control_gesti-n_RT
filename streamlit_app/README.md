# Dashboard Streamlit · Ruta 3

Primera interfaz local del dashboard gerencial de Control de Gestión RT.

## Ejecución

Desde la raíz del repositorio:

```powershell
& C:\Users\basti\AppData\Local\Python\pythoncore-3.14-64\python.exe `
  -m streamlit run streamlit_app\app.py
```

La aplicación abrirá normalmente:

```text
http://localhost:8501
```

## Fuente

La aplicación lee `RR_DB_PATH` desde `.env` y abre SQLite en modo lectura.
Antes de ejecutarla, la capa de la Ruta 2 debe estar aplicada:

```powershell
python scripts\aplicar_vistas.py
```

## Vistas funcionales

1. **Resumen gerencial**
   - KPI globales y ratios;
   - evolución semanal;
   - ranking de cadenas y clientes;
   - estructura por modalidad;
   - tabla ejecutiva exportable.

2. **Cadenas y clientes**
   - Pareto de cadenas;
   - variación contra período seleccionable;
   - drilldown de clientes por cadena;
   - ranking y exportación.

3. **Modalidades y dotación**
   - personas y rutas;
   - carga asignada;
   - carga por persona;
   - evolución semanal;
   - ratios estructurales.

4. **Crecimiento y movimientos**
   - nuevos y retirados;
   - cambios de frecuencia;
   - waterfall de volumen;
   - comparación entre dos períodos cualesquiera;
   - detalle exportable.

5. **Catastro y calidad**
   - filtros de cadena, región y situación;
   - estados operativos;
   - detalle de locales;
   - QA por período.

## Principios

- SQLite se abre con `mode=ro` y `PRAGMA query_only=ON`.
- La aplicación no modifica datos.
- El volumen oficial proviene de las facts de la Ruta 2.
- Los comparativos y movimientos se resuelven mediante SQL.
- Las consultas se cachean durante cinco minutos y se invalidan cuando cambia la base.
- Cada tabla visible puede descargarse en CSV.

## Archivo principal

Para una eventual publicación en Streamlit Community Cloud:

```text
streamlit_app/app.py
```

La publicación cloud requiere reemplazar la ruta SQLite local por una fuente accesible desde internet.
