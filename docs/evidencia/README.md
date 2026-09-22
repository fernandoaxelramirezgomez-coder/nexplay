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
