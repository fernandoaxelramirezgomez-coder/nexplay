# ¿La banda alta es solo «no tiene nota de Metacritic»?

De los 43 juegos de riesgo alto del catálogo servido, **33 no tienen nota de Metacritic**,
y en las bandas baja y media no hay ninguno sin ella. La duda es legítima: si la cobertura
de crítica arrastra la banda, la banda no estaría diciendo nada más que «no lo cubrió la
prensa».

Separando por corte, los datos dicen que no, pero con un matiz que hay que decir en voz
alta. La separación no es un adorno: en los 83 títulos de **data-v1** el modelo ya vio la
respuesta durante el entrenamiento, así que su tabla es descriptiva; los **40 títulos que
nunca vio** son los únicos que evalúan algo. Juntar los 123 en una sola tabla mezcla las
dos cosas, y por eso la versión anterior de esta tabla se retiró.

«Con señal» son las reseñas con arrepentimiento temprano (`playtime_at_review < 120` y
`voted_up = 0`); la prevalencia es esa cuenta sobre las reseñas descargadas del juego.

## data-v1: los 83 títulos con los que se entrenó el modelo

| Banda | Cobertura | Juegos | Reseñas | Con señal | Prevalencia |
|---|---|---:|---:|---:|---:|
| bajo | con nota | 30 | 45,198 | 298 | **0.66 %** |
| medio | con nota | 23 | 34,698 | 386 | **1.11 %** |
| alto | con nota | 7 | 10,599 | 231 | **2.18 %** |
| alto | sin nota | 23 | 33,477 | 1,799 | **5.37 %** |
| **total** | | **83** | **123,972** | **2,714** | **2.19 %** |

Esta tabla es **descriptiva del corte de entrenamiento**, no una medida de desempeño.

## Los 40 títulos que el modelo nunca vio

| Banda | Cobertura | Juegos | Reseñas | Con señal | Prevalencia |
|---|---|---:|---:|---:|---:|
| bajo | con nota | 13 | 19,698 | 366 | **1.86 %** |
| medio | con nota | 14 | 21,098 | 344 | **1.63 %** |
| alto | con nota | 3 | 4,500 | 149 | **3.31 %** |
| alto | sin nota | 10 | 15,099 | 553 | **3.66 %** |
| **total** | | **40** | **60,395** | **1,412** | **2.34 %** |

Los totales de este corte cuadran con `prueba-externa.json`: 40 títulos, 60,395 filas y
1,412 positivos.

## Qué se lee aquí, en orden de importancia

1. **Entre los juegos que sí tienen nota, la banda sigue ordenando la tasa real.** En
   data-v1, 0.66 → 1.11 → 2.18 %; en los 40 no vistos, la banda alta con nota (3.31 %)
   queda por encima de las otras dos. No tener cobertura de crítica es una señal fuerte
   por sí sola —5.37 % contra 0.66 % en data-v1—, pero no es la única que mueve la banda.
2. **Fuera del entrenamiento, bajo y medio se invierten** (1.86 % contra 1.63 %). Solo la
   banda alta se sostiene. Es coherente con el PR-AUC externo ya reportado, 0.0356 contra
   0.0234 del clasificador trivial: hay señal, y es modesta.
3. **«Alto con nota» son 10 juegos en total** —7 de data-v1 y 3 externos—. Con esa n, esa
   fila es una pista y no una conclusión: mueve un puñado de títulos, y basta uno con
   muchas reseñas para cambiarla. Así hay que presentarla, y por eso no se usa para
   afirmar nada sobre el modelo por sí sola.

## Cómo se reproduce

```
python docs/evidencia/metacritic_por_banda.py
```

`metacritic_por_banda.py` solo lee: `datos/nexplay.db` para las reseñas y la nota de cada
juego, y `prueba-externa.json` para saber cuáles son los 40 títulos externos. Las bandas
salen del mismo camino que sirve la API (`api.catalogo` → `scoring.prediccion_de_titulo`),
así que la tabla cambia si cambia el modelo. La consulta que cuenta la señal es:

```sql
SELECT appid, COUNT(*),
       SUM(CASE WHEN playtime_at_review < 120 AND voted_up = 0 THEN 1 ELSE 0 END)
FROM resenas GROUP BY appid
```

`metacritic-por-banda.txt` es la salida completa de la última corrida, con los cuadres.
