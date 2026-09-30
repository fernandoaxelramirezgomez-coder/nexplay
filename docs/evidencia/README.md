# Evidencia del cambio al modelo de título (B+), 2026-09-21

El modelo pasó del conjunto `'compra'` (lado del juego + compras al año) al conjunto
`'juego'` (solo el lado del juego), entrenado siempre con el release **data-v1**. Estos
archivos son la salida de esa validación, corrida desde entornos limpios
(`herramientas/preparar_entorno.py --force` en un worktree sin `datos/` ni `modelo/`).

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

Los scripts que reproducen cada resultado viven en `backend/calidad/` (o `backend/analisis/`) y se
corren desde `backend/`. Los logs y las salidas `.txt` son el registro de lo que se corrió, con las
rutas de entonces.

- `entrenamiento-*.log`: salida de `herramientas/preparar_entorno.py --force` en cada rama.
- `verificar-antes-*.txt`: `backend/modelado/verificar_bandas.py` del modelo nuevo contra la referencia
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
- `bootstrap-prueba-externa.json`: el intervalo de ese 1.52×, remuestreando los 40 títulos
  con reemplazo (2,000 réplicas, semilla 42; PR-AUC entre la prevalencia de cada réplica).
  IC 95 %: 1.03× a 2.33×; en 27 de las 2,000 réplicas el cociente no pasa de 1. Script:
  `calidad/bootstrap_prueba_externa.py`, que antes comprueba que el punto coincida con
  `prueba-externa.json`.
- `verificacion-40-steam.csv`: Metacritic, descuento y precio de los 40 títulos nuevos,
  comparados en vivo contra `appdetails` de Steam el 2026-09-21.
- `simulacion_123.txt` (script: `backend/calidad/simulacion_123.py`): la simulación de entrenar con los 123 (solo
  validación cruzada, sin escribir artefactos) y su salida completa.
- `metacritic-por-banda.md` y `metacritic-por-banda.txt` (script: `backend/calidad/metacritic_por_banda.py`): la
  tasa real de arrepentimiento temprano por banda y por cobertura de crítica, separada
  entre los 83 de data-v1 (descriptiva: el modelo ya los vio) y los 40 externos. Responde
  si la banda alta es solo «no tiene nota de Metacritic», con la advertencia de que «alto
  con nota» son 10 juegos en todo el catálogo.
- `senal-por-nivel.md` y `senal-por-nivel.txt` (script: `backend/calidad/senal_por_nivel.py`): cuántas veces más
  señal hay en riesgo alto que en bajo, en los 123, en los 83 de entrenamiento y en los 40 que
  el modelo no vio (4.19×, 6.99× y 1.93×), y por qué la tarjeta del Inicio dice lo que dice.
- `valoraciones-nia.md` (script: `backend/calidad/valoraciones_nia.py`): los votos 👍/👎 a las respuestas de Nia,
  agrupados por modo y por versión del prompt (el hash de su texto), con la cobertura —qué
  proporción de respuestas recibe voto— y el reparto de motivos del 👎. Incluye qué se
  guarda y los 180 días que se conserva.
- `senal-por-biblioteca.md` y `.json`: veteranos (20 juegos o más) contra novatos (1 a 19) en
  data-v1, con perfil público: 2.89 % contra 0.67 % por reseña, diferencia +2.22 pp
  [+1.30, +3.26]. Tiene el prerregistro, la robustez con cuartiles y por qué se retiró la cifra
  que se citaba antes. Script: `calidad/senal_por_biblioteca.py`.
- `nia-pruebas.md`: las pruebas de Nia con la clave real de OpenAI. Cubre la regresión de 25
  preguntas y las tres rondas de trampas y legítimas (`calidad/preguntas_trampa.json`), con las
  respuestas por modelo separadas de las respuestas por reglas. Solo conteos y ejemplos
  redactados: sin texto de respuestas ni de personas.
- `antes-del-reembolso.md` y `antes-del-reembolso.txt`: las pruebas A (anticipación) y B
  (confianza) de la mejora «Antes de que cierre tu reembolso», contra criterios fijados antes
  de correr (`docs/historial/mejoras/01-antes-del-reembolso.md`). Script:
  `backend/analisis/antes_del_reembolso.py`. Resultado: no se construye.
- `modelos-texto-prerregistro.md` y `modelos-texto.json` (script: `backend/analisis/texto.py`): la Parte A de
  los modelos de texto. La pregunta es si el texto de las reseñas negativas distingue las tempranas de las
  tardías. La pregunta, la máscara de duraciones, los cinco modelos y la regla se commitearon antes del código
  (`6bbcea6`). El JSON salió de `59694a6`, con el árbol limpio.
  - Resultado: rama 3, y se guarda TF-IDF + LR.
  - TF-IDF + LR saca un PR-AUC de 0.369 contra 0.161 del trivial (2.30×, IC 2.05 a 2.53) y le saca +0.184 a la
    regla «refund» (IC 0.137 a 0.205).
  - NB y MiniLM quedan por debajo de TF-IDF + LR, con intervalos que no tocan el 0.
  - Leer la duración sin máscara le sumaba +0.013. Es la sensibilidad y queda fuera de la regla.
  - Nada de esto entra al score de riesgo.
  - Lo reproduce `notebooks/02_modelos_texto.ipynb`.
- `verificar-factores-hoy.txt`: la salida de `backend/calidad/verificar_factores.py` el 2026-09-30,
  antes de la ronda «explicar el riesgo». El primer factor ya es el de mayor aporte en los 123
  juegos. Fallan la evidencia por factor y los avisos (gratis y precio imputado), porque el
  contrato todavía no existe.
- `colab/`: las corridas de los notebooks en Colab, byte por byte.
  - La vigente es la de los tres, del 2026-10-02 con `codigo-v6`.
  - Quedan como historial la del 00 y el 01 (2026-09-30, `codigo-v3`) y la del 02 (2026-10-01, `codigo-v4`).
  - Incluye la comparación de la del 2026-09-30 con una corrida local (`make notebooks`).
- `sugerencias-afinidad.md`: qué son las sugerencias por afinidad de `/perfil` y por qué,
  a diferencia del modelo de riesgo, **no se pueden validar** contra ningún resultado real.

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

`backend/calidad/simulacion_123.py` compara los dos cortes solo con validación cruzada —sin escribir
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

## Partición congelada contra la de scikit-learn 1.6.1 (prerregistrada), 2026-09-30

GroupKFold reparte los juegos por tamaño, y 73 de los 83 de data-v1 empatan en 1,500 reseñas. Cada
versión de scikit-learn desempata distinto (el desempate estable llega en la 1.9.0): la 1.6.1 de Colab
deja solo 12 de los 83 juegos en el mismo fold que la partición congelada
(`backend/referencias/particion_gkf_data-v1.csv`), que es la que usa toda evaluación del proyecto.

`backend/calidad/particion_alternativa.py` se commiteó antes de correrlo (`fba2af7`) y `particion-alternativa.json`
salió de él sin editarlo, en el entorno de Colab (Python 3.13.15, scikit-learn 1.6.1, numpy 2.1.3,
pandas 2.2.3, SciPy 1.16.3), con el código en `1a020b7` y el árbol limpio. Es descriptivo: no fija un
criterio de pasa o no pasa, y la cifra de Colab ya se conocía antes de escribirlo.

| Partición | PR-AUC por fold, modelo / trivial | Media ± std | Folds donde gana el modelo |
|---|---|---|---|
| Congelada (CSV) | 0.1459 / 0.0253 · 0.0367 / 0.0187 · 0.0809 / 0.0255 · 0.0436 / 0.0236 · 0.0399 / 0.0163 | 0.0694 ± 0.0415 | 5 de 5 |
| GroupKFold de scikit-learn 1.6.1 | 0.1364 / 0.0299 · 0.0843 / 0.0167 · 0.0594 / 0.0336 · 0.0104 / 0.0079 · 0.0555 / 0.0219 | 0.0692 ± 0.0412 | 5 de 5 |

Con otro reparto de los juegos la media casi no cambia, pero cada fold sí: el ruido entre folds (~0.04)
es mucho mayor que la diferencia entre particiones. En las dos el modelo supera al trivial en los 5
folds; el margen más chico es 0.0104 contra 0.0079, en un fold con 202 reseñas con señal. La sección 3.2
de `00_exploracion` mide lo mismo con 20 particiones al azar (de 0.0477 a 0.0873).
