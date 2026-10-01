# publicacion/

Lo que se sube a un release: `extracto_datos.py` (el Parquet sin texto que lee el notebook 01)
y `extracto_reproducible.py` (la copia sanitizada de la base, sin `steamid`, que baja
`despliegue/preparar_entorno.py`). Cada extracto nuevo va en un tag nuevo.

No va aquí: la ingesta (`ingesta/`) ni la descarga (`despliegue/utilidades.py`).
