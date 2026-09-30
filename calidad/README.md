# calidad/

Lo que comprueba que nada se rompió. Nada de esto corre en producción.

- `capturar_ui.py`: recorre la UI con Playwright, guarda capturas en `docs/capturas/` y reporta
  problemas (necesita la API y el frontend corriendo, y `requirements-dev.txt`).
- `verificar_nia.py`: revisa a Nia sin gastar llamadas; sale 1 si algo falla.
- `preguntas_nia.py`: las 25 preguntas contra una API levantada.

No va aquí: tareas sobre el contenido de los usuarios (`operacion/`) ni el entorno
(`despliegue/`).
