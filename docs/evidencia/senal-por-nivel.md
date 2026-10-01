# ¿Cuánta más señal hay en riesgo alto, y en qué juegos?

El Inicio muestra que los juegos de riesgo alto tienen **4.2×** más reseñas con señal de
arrepentimiento temprano (Y=1: menos de 120 minutos jugados y voto negativo) que los de
riesgo bajo. Antes de ponerlo en una tarjeta se revisó de dónde sale esa cifra, porque los
123 juegos no son todos iguales frente al modelo:

- en los **83 de data-v1** la señal fue la etiqueta con la que se entrenó: ahí el cociente
  describe lo que el modelo ya aprendió;
- en los **40 que nunca vio**, el cociente sí evalúa algo.

## Resultado

| Corte | Nivel | Juegos | Reseñas | Con señal | Señal |
|---|---|---:|---:|---:|---:|
| Catálogo (123) | bajo | 43 | 64,896 | 664 | 1.02 % |
| | medio | 37 | 55,796 | 730 | 1.31 % |
| | alto | 43 | 63,675 | 2,732 | 4.29 % |
| data-v1 (83) | bajo | 30 | 45,198 | 298 | 0.66 % |
| | medio | 23 | 34,698 | 386 | 1.11 % |
| | alto | 30 | 44,076 | 2,030 | 4.61 % |
| Externos (40) | bajo | 13 | 19,698 | 366 | 1.86 % |
| | medio | 14 | 21,098 | 344 | 1.63 % |
| | alto | 13 | 19,599 | 702 | 3.58 % |

| Corte | Cociente alto/bajo | Intervalo 95 % (remuestreo de juegos) |
|---|---:|---|
| Catálogo (123) | **4.19×** | 2.66× a 6.44× |
| data-v1 (83) | 6.99× | 4.15× a 11.13× |
| Externos (40) | **1.93×** | 0.87× a 3.50× |

## Qué se decidió

La regla del dueño (2026-09-26): si en los 40 la diferencia es clara, 2× o más, la tarjeta
muestra esa cifra «en 40 juegos que el modelo nunca vio»; si no, se queda el 4.2× de los
123 con la frase «El modelo asigna el riesgo con datos del juego, sin leer las reseñas».

En los 40 sale **1.93×**, justo debajo de 2×, y con 13 juegos por nivel su intervalo va de
0.87× a 3.50×: la dirección se mantiene, pero la cifra no es firme. Por la regla, la tarjeta
del Inicio usa **4.2×** con la frase **«El modelo asigna el riesgo con datos del juego, sin
leer las reseñas»**. La frase anterior («El modelo no vio esas reseñas») era falsa para los
83 de entrenamiento, donde la señal fue justamente la etiqueta.

Lo que hay que decir en voz alta si se cita el 4.2×: la mayor parte viene de los 83 de
entrenamiento (6.99×); fuera de ellos la diferencia existe y es más chica (1.93×). Es la
misma lectura que el PR-AUC externo ya reportado (0.0356 contra 0.0234 del trivial): hay
señal, y es modesta.

## Cómo se reproduce

```
cd backend && python calidad/senal_por_nivel.py > ../docs/evidencia/senal-por-nivel.txt
```

Solo lee `datos/nexplay.db` y `prueba-externa.json`. Los niveles salen de `api.catalogo`, el
mismo camino que sirve la API. El intervalo remuestrea juegos dentro de cada nivel (2,000
repeticiones, semilla 42), porque la unidad que generaliza es el juego, no la reseña.
