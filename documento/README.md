# documento/

El documento final en LaTeX: el texto que entrega el proyecto, con cada criterio de la rúbrica
localizable desde el índice.

- `main.tex`: preámbulo, portada, resumen, índice y un `\input` por sección.
- `sections/`: una sección por archivo (`00-resumen.tex` … `17-siguientes-pasos.tex`, `anexo.tex`).
- `tables/`: tablas y `cifras.tex`, las macros `\cifra…` con cada número del texto. Las genera
  `generar_figuras.py`: **ninguna cifra se escribe a mano**.
- `figures/`: figuras que genera `generar_figuras.py`, las capturas (copiadas de
  `docs/capturas/documento/`) y los escudos de la portada.
- `references.bib`: solo referencias abiertas y verificadas antes de citarlas.
- `generar_figuras.py`: de los releases (verificados por sha256) y `docs/evidencia/` a `figures/` y
  `tables/`. Necesita `documento/requirements-documento.txt`.
- `verificar_cifras.py`: compara `cifras.tex` con la lista canónica y falla si una sección trae un
  número con decimales o con % fuera de una macro.
- `capturar_recorrido.py`: las capturas del recorrido (PAYDAY 3 contra Dead Space), provisionales
  hasta regenerarlas desde el tag de entrega.

Compilar, desde la raíz: `make doc`. Hace estos pasos y copia el PDF a
`documento/documento-entregafinal.pdf`, el único PDF de esta carpeta que se versiona:

```
.venv/bin/python documento/generar_figuras.py
.venv/bin/python documento/verificar_cifras.py
cd documento && latexmk        # LuaLaTeX + biber; el PDF queda en documento/build/main.pdf
```

No va aquí: evidencia nueva (`docs/evidencia/` con su script en `backend/calidad/`) ni cambios al
modelo o a la API.
