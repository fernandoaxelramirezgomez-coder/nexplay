# Evidencia del cambio al modelo de título (B+), 2026-09-21

El modelo pasó del conjunto `'compra'` (lado del juego + compras al año) al conjunto
`'juego'` (solo el lado del juego), entrenado siempre con el release **data-v1**. Estos
archivos son la salida de esa validación, corrida desde entornos limpios
(`preparar_entorno.py --force` en un worktree sin `datos/` ni `modelo/`).

## Procedencia del artefacto

| | |
|---|---|
| `modelo_version` | `logreg-juego-2026-09-21` |
| Datos de entrenamiento | data-v1, asset `nexplay_reproducible.db.xz`, sha256 `2ef8ef40330385af4c03cd072dccb20fc9a4b635e3929e513235c191d14e9ee7` |
| Filas / juegos | 123,972 / 83 |
| Features | `es_gratis`, `log_precio_final`, `descuento`, `metacritic_disponible`, `metacritic` (sin `log_num_games_owned`) |
| `mediana_metacritic` | 88.0 |
| Umbrales (tercios de scores OOF) | 0.2858 / 0.3916 |
| Bandas | master (83 juegos): 30/23/30 · frontend-angular (123 juegos): 43/37/43 |

El artefacto es idéntico en las dos ramas (mismos datos, mismo código).

## Archivos

- `entrenamiento-*.log`: salida de `preparar_entorno.py --force` en cada rama.
- `verificar-antes-*.txt`: `verificar_bandas.py` del modelo nuevo contra la referencia
  `'compra'`, antes de regenerarla (exit 1: los juegos que cambian de banda).
- `verificar-despues-*.txt`: la misma verificación contra la referencia regenerada (exit 0).
- `compra-*.json` y `juego-*.json`: banda y score de cada juego con el modelo anterior y con
  el nuevo, por el mismo camino que la API (`api.catalogo` → `scoring.predecir`), más la
  prueba de que el perfil ya no mueve el score (`prueba_perfil`: cuatro perfiles distintos,
  un solo valor por juego en B+). Con `compra-*.json` se reproduce la referencia anterior
  83/83 y 123/123.
- `prueba-externa.json`: los 40 títulos de data-v2 que no están en data-v1, puntuados con el
  artefacto de data-v1. 40/40 evaluables, sin errores ni features faltantes; 60,395 filas,
  prevalencia 2.34 %, PR-AUC 0.0356 contra 0.0234 del clasificador trivial. Esos títulos no
  intervienen en el entrenamiento, la elección de variables, los parámetros ni los umbrales.
- `verificacion-40-steam.csv`: Metacritic, descuento y precio de los 40 títulos nuevos,
  comparados en vivo contra `appdetails` de Steam el 2026-09-21.
- `simulacion_123.py` y `simulacion_123.txt`: la simulación de entrenar con los 123 (solo
  validación cruzada, sin escribir artefactos) y su salida completa.

## Los 40 títulos nuevos son prueba externa, no entrenamiento

El modelo se entrena con los 83 de data-v1. Los 40 títulos que llegaron con data-v2 se
puntúan con ese modelo, con sus umbrales y su mediana de Metacritic: **PR-AUC 0.0356
contra 0.0234 del clasificador trivial** (1.52 veces), sobre 60,395 reseñas con 2.34% de
prevalencia. Los 40 pasaron por inferencia uno por uno: 40 evaluables, 0 errores, 0
variables faltantes (`prueba-externa.json`).

Antes de decidirlo se verificó que esos 40 estuvieran tan limpios como los 83
(`verificacion-40-steam.csv`): mismo volumen por juego (1,500–1,599 reseñas, contra
682–1,599 de los originales), ninguno de pago sin precio —los dos que hay están entre los
83—, y su Metacritic coincide exactamente con lo que la página de Steam muestra hoy, así
que la ausencia en 10 de ellos no es un error de ingesta. Dos matices que valen para todo
el catálogo: `metacritic_disponible = 0` significa "Steam no muestra Metacritic", no "no
tiene crítica" (Forza Horizon 5 y Starfield la tienen), y el precio con su descuento es la
foto del día de ingesta (10 de los 40 estaban en oferta, contra 8 de los 83).

## Por qué no se entrena con los 123 (simulación, sin reentrenar)

`simulacion_123.py` compara los dos cortes solo con validación cruzada —sin escribir
ningún artefacto—, con el GroupKFold de producción y con 30 particiones aleatorias de los
juegos en 5 folds. Salida completa en `simulacion_123.txt`.

Con 123 juegos el ruido baja: la desviación entre folds del conjunto `'juego'` pasa de
0.0415 a 0.0264 en el GroupKFold de producción, y de 0.0402 a 0.0278 como promedio de las
30 particiones, alrededor de 31% menos. **Aun así, el lado del jugador sigue sin
distinguirse del ruido.** Con 123, `'compra'` aporta 3.8% de PR-AUC en promedio, pero su
intervalo del 95% va de −8.1% a +11.5%, la diferencia media es de +0.0022 de PR-AUC y en
el GroupKFold de producción `'compra'` sale peor (−5.1%). Gana en 24 de 30 particiones,
que suena a tendencia, pero las 30 particiones se calculan sobre los mismos datos: no son
30 pruebas independientes, así que ese conteo no es evidencia de una señal real.

**Decisión: el modelo se queda entrenado con los 83 de data-v1.** Lo que se ganaría con
123 es menos ruido; lo que se perdería es la única evaluación fuera de muestra que existe,
porque esos 40 títulos pasarían a ser entrenamiento y ya no quedaría ningún juego que el
modelo no haya visto. Mientras el aporte del perfil siga dentro del ruido, ese cambio no
compra nada que justifique quedarse sin prueba externa.

## Casos al filo del corte: no usar como demo

Dos juegos quedan a una fracción de milésima de un corte. Cualquier cambio mínimo en los
datos o en el reentrenamiento puede cambiarlos de banda, así que **no se usan como caso de
demostración** (portada, capturas, presentaciones):

| Juego | appid | Score | Banda | Distancia al corte |
|---|---|---|---|---|
| Hollow Knight | 367520 | 0.2857 | bajo | 0.00015 bajo el corte bajo/medio (0.2858) |
| Warframe | 230410 | 0.3918 | alto | 0.0002 sobre el corte medio/alto (0.3916) |

Warframe solo está en el catálogo de frontend-angular (data-v2); Hollow Knight, en las dos
ramas.
