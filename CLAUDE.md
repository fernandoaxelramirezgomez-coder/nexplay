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

**Datos.** Reseñas ingestadas desde la API `appreviews` de Steam, publicadas en releases
con tag fijo. **Entrenamiento: 83 títulos** (release data-v1, 123,972 reseñas); el modelo se
entrena siempre con ese corte. **Catálogo servido: 123 títulos** (data-v2 en
`frontend-angular`; `master` sirve data-v1). Los 40 títulos que no están en data-v1 son
prueba externa: nunca entran al entrenamiento, a la elección de variables ni a los umbrales.

**Modelo de título.** `conjunto='juego'` (`logreg-juego-`): gratuidad, precio, descuento y
cobertura/nota de crítica. El riesgo es del juego, igual para cualquier persona; el perfil
declarado **no cambia el riesgo**, sirve para afinidad. `/prediccion` sigue recibiendo el
perfil por compatibilidad.

**Perfiles privados.** `author.num_games_owned == 0` es bandera de privacidad, no
biblioteca vacía. No imputar como cero.

## Arquitectura

La raíz solo tiene carpetas: cada una es un paso del flujo o una salida generada.

```
api/           FastAPI. Contrato estable, lógica delgada.
  main.py         endpoints
  schemas.py      modelos Pydantic de entrada y salida
  scoring.py      carga el modelo y predice
  catalogo.py     búsqueda de juegos
  nia.py          chat con el modelo de lenguaje, con respaldo por reglas
frontend/      Angular: el único frontend
notebook/      la narrativa ejecutable (clona un tag fijo, no depende de estas rutas)

ingesta/       ingesta_steam.py y appids.txt: bajar datos de Steam
modelado/      entrenar_baseline.py, entrenar_modelo.py, verificar_bandas.py
publicacion/   extracto_datos.py y extracto_reproducible.py: lo que va a un release
herramientas/  preparar_entorno.py (la entrada del proyecto), exportar_valoraciones.py,
               moderar_comentarios.py, capturar_ui.py, recortar_nia.py

modelo/        artefactos entrenados (.pkl), no versionados
datos/         SQLite: nexplay.db, tablas `juegos` y `resenas` (más `resumen_resenas`
               y `progreso`), no versionado
extracto/      lo que se sube a un release, no versionado
registros/     lo que deja la ingesta al correr, no versionado
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
formulario de alta, no se infiere. No entra al modelo: sirve para contar qué tanto encaja un
juego con quien lo declaró (afinidad), nunca para mover el riesgo. Variables que recoge:

- compras al año (sustituto de `num_games_owned`; el modelo de título no la usa)
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
