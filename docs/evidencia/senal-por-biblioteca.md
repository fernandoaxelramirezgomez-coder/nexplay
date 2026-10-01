# ¿Dejan más señal los veteranos que los novatos?

Sí. En data-v1, entre las reseñas con perfil público, los veteranos (20 juegos o más) dejan
**2.89 %** de reseñas con señal de arrepentimiento temprano y los novatos (1 a 19 juegos)
**0.67 %**, **por reseña**. La diferencia es de **+2.22 puntos**, con un IC 95 % de +1.30 a
+3.26 por bootstrap sobre juegos. Con el promedio de las tasas por juego da lo mismo en
dirección: 2.72 % contra 0.97 %, diferencia +1.75 puntos [+0.98, +2.71].

La diferencia se sostiene dentro de cada juego. Comparando a los dos grupos en el mismo
juego, la razón de Mantel-Haenszel es 2.62, con IC 95 % [1.84, 4.12]. Es menor que la razón
cruda (4.30), porque los veteranos también se concentran en juegos con más señal.

De aquí sale el encuadre: el riesgo está en el título y no en la inexperiencia de quien compra.
Cuando el documento cite esta diferencia, dirá que es por reseña.

## Resultado

Salida de `calidad/senal_por_biblioteca.py` (`ef9f0b7`) en
`docs/evidencia/senal-por-biblioteca.json`. Hay 49,749 reseñas con perfil público; las otras
74,223 son perfiles privados y quedan fuera.

| Grupo | Juegos | Reseñas | Con señal | Por reseña | Promedio por juego |
|---|---:|---:|---:|---:|---:|
| Novatos (1–19 juegos) | 83 | 4,916 | 33 | **0.67 %** | 0.97 % |
| Veteranos (≥ 20) | 83 | 44,833 | 1,295 | **2.89 %** | 2.72 % |
| Diferencia, IC 95 % | | | | **+2.22 pp** [+1.30, +3.26] | +1.75 pp [+0.98, +2.71] |
| Cociente | | | | 4.30× | 2.81× |

**Regla para citarla** (fijada antes de correr): la diferencia por reseña es positiva y su IC no
cruza el cero, así que **se cita**. El promedio por juego cuenta la misma historia, con una
diferencia menor.

**Robustez con cuartiles** de `num_games_owned` en perfiles públicos. Q1 son 46 juegos o
menos; Q4, más de 245:

| Grupo | Reseñas | Con señal | Por reseña | Promedio por juego |
|---|---:|---:|---:|---:|
| Q1 | 12,507 | 124 | 0.99 % | 1.69 % |
| Q4 | 12,417 | 611 | 4.92 % | 3.43 % |
| Diferencia, IC 95 % | | | +3.93 pp [+2.20, +5.69] | +1.73 pp [+1.16, +2.36] |

La dirección se sostiene con otro corte. El cociente por reseña (4.96×) queda muy por encima
del promedio por juego (2.02×): los veteranos se concentran en juegos con más señal. Si esa
concentración explica toda la diferencia o solo parte, lo responde el análisis estratificado
por juego (abajo).

## Análisis estratificado por juego

**Pregunta:** ¿la diferencia se sostiene dentro de cada juego, o viene de que los veteranos
compran juegos con más señal?

**Prerregistro** (commiteado antes de la primera corrida):
- **Datos y grupos:** los mismos de arriba. Data-v1 con perfiles públicos; novatos de 1 a 19
  juegos y veteranos con 20 o más; la misma señal.
- **Método:** razón de riesgos de Mantel-Haenszel, veteranos contra novatos, estratificada por
  appid. En cada juego k, con a y n1 las señales y reseñas de veteranos, c y n0 las de novatos,
  y N = n1 + n0: RR_MH = Σ a·n0/N / Σ c·n1/N.
- **Qué juegos aportan:** solo los que tienen reseñas de los dos grupos (juegos informativos).
  Se reporta cuántos son.
- **IC 95 %:** bootstrap sobre appid, 2,000 réplicas con reemplazo y semilla 42. Una réplica
  sin señales de novatos en sus juegos informativos tiene razón infinita: se cuenta, y entra al
  percentil como +∞ sin interpolar (numpy, `method="inverted_cdf"`).
- **Regla para la frase del documento:**
  - si el IC queda completo por encima de 1: «La diferencia se sostiene dentro de cada juego»;
  - si el IC cruza el 1: «Parte de la diferencia puede venir de qué juegos compra cada grupo»;
  - si quedara completo por debajo de 1 (caso no previsto): se reporta al dueño antes de
    escribir ninguna frase.
- **Salida:** `docs/evidencia/senal-por-biblioteca-estratificada.json`, con
  `backend/calidad/senal_por_biblioteca_estratificada.py`.

**Resultado** (`94df3b6`, `docs/evidencia/senal-por-biblioteca-estratificada.json`):

| | Valor |
|---|---|
| Juegos informativos (con reseñas de los dos grupos) | **83 de 83**; 81 con alguna señal |
| Señales en esos juegos | veteranos 1,295; novatos 33 |
| Razón cruda, por reseña | 4.30 |
| **Razón de Mantel-Haenszel por juego** | **2.62**, IC 95 % **[1.84, 4.12]** |
| Réplicas con razón infinita | 0 de 2,000 |

El IC queda completo por encima de 1, así que según la regla la frase del documento es:
**«La diferencia se sostiene dentro de cada juego.»**

Dentro de un mismo juego, los veteranos dejan unas 2.6 veces más señal que los novatos. La
razón cruda, 4.3, es mayor porque además los veteranos se concentran en juegos con más señal:
esa mezcla explica parte de la diferencia cruda, pero no toda. Los novatos suman solo 33
señales; el intervalo ya lo refleja, porque remuestrea juegos enteros.

Como comprobación, el punto se recalculó con un bucle por juego, independiente de la versión
vectorizada del script, y dio el mismo 2.623.

## La cifra anterior (retirada)

El plan de entrega citaba **1.34 % contra 0.45 %**. Venía de un cálculo del **14 de septiembre**
(01:32 UTC), hecho con la base a medio ingestar, dos días antes de publicar data-v1:
- 106,495 reseñas en total, en tres grupos: 64,787 privadas, 4,630 de novatos y 37,078 de
  veteranos;
- 1,107 con señal, una tasa global de alrededor de 1.0 %. En data-v1 son 123,972 reseñas y
  2.19 %.

Ningún release conserva ese corte, así que **no se puede reproducir**.
- El prerregistro (`9a394e9`) pedía reproducir esas cifras antes de citar nada. No se
  reprodujo, y se reportó al dueño antes de cambiar nada.
- Otras lecturas plausibles de novato y veterano tampoco las dan, en data-v1 ni en data-v2:
  contar los privados como novatos o usar las reseñas del autor en vez de los juegos. Se
  probaron solo como diagnóstico y no se adoptó ninguna.
- **Decisión del dueño:** citar la misma definición sobre data-v1 y retirar la cifra anterior
  del repo. Esta sección es el único lugar donde aparece.

## Prerregistro (commiteado en `9a394e9`, antes de la primera corrida)

- **Datos:** reseñas de data-v1 (83 juegos, sha256 `2ef8ef40…9ee7`) con perfil público,
  `num_games_owned > 0`. El 0 es bandera de privacidad, no una biblioteca vacía.
- **Grupos:** novatos, de 1 a 19 juegos; veteranos, 20 o más.
- **Señal:** `playtime_at_review < 120` y `voted_up = 0`, la misma Y del modelo.
- **Dos medidas:** por reseña, y promedio de las tasas por juego con cada juego pesando igual.
- **Incertidumbre:** IC 95 % de la diferencia por bootstrap sobre juegos (2,000 réplicas con
  reemplazo, semilla 42).
- **Reproducción:** reproducir las cifras del corte del 14 de septiembre antes de citar; si no,
  reportarlo antes de cambiar nada. No se cumplió (ver arriba).
- **Cita:** se cita si la diferencia por reseña es positiva y su IC no cruza el cero; si el
  promedio por juego cuenta otra historia, se dice junto a la cifra.
- **Robustez:** cuartiles, Q4 contra Q1, separados del resultado principal.

**Límite que ya se sabe:** `num_games_owned` describe al autor cuando se descargó la reseña,
no cuando compró el juego. Es contexto del encuadre y no entra al modelo de título, que es del
juego y vale igual para cualquier persona.

## Cómo se reproduce

```
cd backend && python calidad/senal_por_biblioteca.py [--cache DIR]
```

Baja data-v1 con su sha256 (`backend/despliegue/utilidades.py::descargar_verificado`), lee las reseñas
con `backend/modelado/entrenar_baseline.py::cargar_datos` y escribe
`docs/evidencia/senal-por-biblioteca.json`. No toca `backend/datos/` ni `backend/modelo/`.
