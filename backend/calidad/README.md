# calidad/

Lo que comprueba que nada se rompió y lo que reproduce la evidencia de `docs/evidencia/`. Nada de esto
corre en producción. Todo se corre desde `backend/`; `make test`, desde la raíz, junta los cinco
verificadores con las pruebas del frontend.

Verificadores (salen con 1 si algo falla):

- `verificar_nia.py`: revisa a Nia sin gastar llamadas.
- `verificar_factores.py`: la regla de «Qué mueve esta estimación» en los 123 juegos.
- `verificar_niveles.py`: una sola definición de los niveles (percentiles 33.3 y 66.7 de las estimaciones
  fuera de pliegue del entrenamiento) y ningún texto de frontend/src ni de api con la anterior.
- `verificar_preparar_entorno.py`: que `preparar_entorno.py --force` no pise una base que no salió de un
  release. Sin red, en un directorio temporal.
- `correr_notebooks.py`: ejecuta el 00 y el 01 con el último commit en una carpeta temporal y compara sus
  salidas con las guardadas, sin tocarlas (`make notebooks`). Sale con 1 solo si un notebook no termina;
  las celdas distintas las lista con su diff.

Contra la app levantada:

- `capturar_ui.py`: recorre la UI con Playwright, guarda capturas en `docs/capturas/` y reporta problemas.
  Necesita la API y el frontend corriendo, y `requirements-dev.txt`.
- `preguntas_nia.py`: las 25 preguntas a Nia contra una API levantada.
- `preguntas_trampa.json`: las 24 trampas, 8 legítimas y dos conversaciones para Nia con modelo, con la
  categoría y el comportamiento esperado de cada una. Se corren contra una API con clave (gasta OpenAI); el
  resumen está en `docs/evidencia/nia-pruebas.md`.

Evidencia (cada script escribe o reproduce un archivo de `docs/evidencia/`):

- `metacritic_por_banda.py` y `senal_por_nivel.py`: la señal real por banda, con y sin nota de la crítica.
- `simulacion_123.py`: qué pasaría si se entrenara con los 123 juegos, solo con validación cruzada.
- `valoraciones_nia.py`: los votos a las respuestas de Nia.
- `particion_alternativa.py`: el PR-AUC con la partición de scikit-learn 1.6.1 (prerregistrado; corre solo
  con esa versión).
- `bootstrap_prueba_externa.py`: el intervalo del PR-AUC externo entre el del trivial, remuestreando los 40
  títulos (`bootstrap-prueba-externa.json`).
- `senal_por_biblioteca.py`: la señal de veteranos contra novatos en data-v1 (perfiles públicos), por reseña
  y promedio por juego, con bootstrap sobre juegos (`senal-por-biblioteca.json`).

No va aquí: tareas sobre el contenido de los usuarios (`operacion/`) ni el entorno (`despliegue/`).
