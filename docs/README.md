# docs/

Solo documentación. Nada de lo que necesitan la API, el modelo o el frontend vive aquí. Los scripts de
`backend/calidad/` escriben aquí las capturas y la evidencia, y dos de ellos (`metacritic_por_banda.py` y
`senal_por_nivel.py`) leen `evidencia/prueba-externa.json`.

- `evidencia/`: los resultados de cada validación y de cada decisión medida, con el nombre del script de
  `backend/calidad/` (o `backend/analisis/`) que los reproduce.
- `capturas/`: capturas de la UI. Las genera `backend/calidad/capturar_ui.py` y no se versionan, salvo
  `captura-interfaz.png`, la del README.
- `diagramas/`: los diagramas del README. Cada uno tiene su fuente en Mermaid (`NN-nombre.mmd`) y dos SVG, uno
  oscuro (`NN-nombre.svg`) y uno claro (`NN-nombre-claro.svg`); el README muestra el que va con el tema de quien lo
  lee. Si cambias un `.mmd`, regenera sus dos SVG desde la raíz (con `-p` y un JSON con `executablePath`, usa un
  Chrome que ya tengas en lugar de bajar otro):

  ```bash
  for n in 01-arquitectura 02-ficha-de-un-juego; do
    npx -y @mermaid-js/mermaid-cli@12.0.0 -i docs/diagramas/$n.mmd -o docs/diagramas/$n.svg \
      -t dark -b transparent -c docs/diagramas/mermaid.json
    npx -y @mermaid-js/mermaid-cli@12.0.0 -i docs/diagramas/$n.mmd -o docs/diagramas/$n-claro.svg \
      -t default -b transparent -c docs/diagramas/mermaid.json
  done
  ```
- `diseno/`: las referencias de estilo de la interfaz (`referencia-estilo.md` y `referencia-neon.md`).
- `historial/`: planes, revisiones por fase y mockups de cómo se llegó aquí. No se citan desde el README y
  conservan las rutas de cuando se escribieron.

No va aquí: valores de referencia que lee el código (`backend/referencias/`), scripts ni recursos del
frontend (la hoja de Nia está en `frontend/fuentes/`).
