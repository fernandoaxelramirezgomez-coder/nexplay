# docs/

Solo documentación. Nada de lo que necesitan la API, el modelo o el frontend vive aquí. Los scripts de
`backend/calidad/` escriben aquí las capturas y la evidencia, y dos de ellos (`metacritic_por_banda.py` y
`senal_por_nivel.py`) leen `evidencia/prueba-externa.json`.

- `evidencia/`: los resultados de cada validación y de cada decisión medida, con el nombre del script de
  `backend/calidad/` (o `backend/analisis/`) que los reproduce.
- `capturas/`: capturas de la UI. Las genera `backend/calidad/capturar_ui.py` y no se versionan, salvo
  `captura-interfaz.png`, la del README.
- `diseno/`: las referencias de estilo de la interfaz (`referencia-estilo.md` y `referencia-neon.md`).
- `historial/`: planes, revisiones por fase y mockups de cómo se llegó aquí. No se citan desde el README y
  conservan las rutas de cuando se escribieron.

No va aquí: valores de referencia que lee el código (`backend/referencias/`), scripts ni recursos del
frontend (la hoja de Nia está en `frontend/fuentes/`).
