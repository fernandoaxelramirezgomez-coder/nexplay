# NexPlay

Estima el riesgo de arrepentimiento temprano al comprar un videojuego, antes de la compra.
Proyecto del Módulo V del Diplomado en Ciencia de Datos, FES Acatlán (UNAM).

## Contexto que no debe reinventarse

**Variable objetivo.** `Y = 1` si `playtime_at_review < 120` minutos **y** `voted_up == 0`.
Se llama *arrepentimiento temprano*. El umbral de 120 minutos no es arbitrario: es la
ventana de reembolso de Steam. Nunca renombrar esto como "abandono" ni como
"insatisfacción".

**Es una proxy.** Steam no observa arrepentimiento. Al redactar textos, gráficas o
respuestas de la API, decir "señal de arrepentimiento temprano", nunca "el usuario se
arrepintió".

**Validación.** `GroupKFold` agrupando por `appid`. El modelo debe generalizar a juegos
que no vio. Nunca usar `train_test_split` simple: fuga garantizada.

**Métrica principal.** PR-AUC. La clase está desbalanceada, accuracy no sirve.

**Datos.** 119,791 reseñas de 71 juegos, ingestadas desde la API `appreviews` de Steam.
Capa A (42 juegos) para contraste novato/veterano. Capa B (29) multiplataforma.

**Perfiles privados.** `author.num_games_owned == 0` es bandera de privacidad, no
biblioteca vacía. No imputar como cero.

## Arquitectura

```
api/        FastAPI. Contrato estable, lógica delgada.
  main.py       endpoints
  schemas.py    modelos Pydantic de entrada y salida
  scoring.py    carga el modelo y predice
  catalogo.py   búsqueda de juegos
modelo/     artefactos entrenados (.pkl), no versionados
datos/      SQLite: nexplay.db, tablas `juegos` y `resenas` (más `resumen_resenas`
            y `progreso`), no versionado
ui/         Gradio
```

**Regla de oro del back:** `scoring.py` expone una función con firma estable.
Hoy devuelve un valor simulado; mañana carga el modelo real. Nada fuera de ese archivo
debe cambiar cuando el modelo esté listo.

## Endpoints

- `GET  /catalogo?q=` — busca juegos por nombre
- `POST /perfil` — recibe el formulario de alta, devuelve el perfil derivado
- `POST /prediccion` — recibe perfil + appid, devuelve riesgo y nivel
- `GET  /explicacion/{appid}` — motivos de insatisfacción más frecuentes de ese juego

## El perfil del jugador

No hay API de consola que dé historial del jugador, así que el perfil se **declara** en un
formulario de alta, no se infiere. Variables que recoge:

- compras al año (sustituto de `num_games_owned`)
- horas por semana disponibles
- tolerancia a la fricción
- etiquetas preferidas y rechazadas, usando **el vocabulario de tags de Steam**, no
  categorías inventadas
- plataforma

## Convenciones

- Python 3, FastAPI, pydantic v2.
- Nombres de variables y funciones en español, igual que el resto del proyecto.
- Comentarios solo donde la intención no sea obvia. Nada de comentarios que repitan el
  código.
- Sin `print` en la API: usar `logging`.
- Todo lo que entre por la API se valida con Pydantic. Nunca confiar en el cliente.

## No hacer

- No mezclar el corpus de Metacritic con los datos de entrenamiento. Es fuente
  secundaria, solo para comparar motivos entre plataformas.
- No usar Kaggle como fuente. La rúbrica lo prohíbe.
- No prometer un score de riesgo entrenado con datos de PlayStation o Xbox. No existe
  esa fuente. El lado del juego transfiere; el lado del jugador viene del formulario.
- No tocar `datos/` ni `modelo/` sin avisar.
