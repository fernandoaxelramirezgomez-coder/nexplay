# ¿Sirven los motivos para decir qué revisar antes del reembolso?

Pruebas A y B de la mejora 01, «Antes de que cierre tu reembolso»
([ficha](../plan/mejoras/01-antes-del-reembolso.md)). Los criterios se fijaron y se
commitearon **antes** de correr (`7b0ba52`); aquí solo se miden.

```bash
python analisis/antes_del_reembolso.py > docs/evidencia/antes-del-reembolso.txt
```

Baja data-v1 y data-v2 con su sha256. Usa las mismas palabras clave de `/explicacion`
(`analisis/motivos.py`) y la semilla 42. Dos corridas dan la misma salida.
[Salida completa](antes-del-reembolso.txt).

**Datos.** 921 quejas con motivo en los 83 juegos de data-v1 y 423 en los 40 externos. Una
queja con motivo es una reseña con señal de arrepentimiento temprano que menciona al menos
una categoría.

## A · Anticipación

¿El motivo principal de la mitad vieja de las quejas de un juego está entre los dos
principales de la mitad nueva? Se compara contra una línea base: el mismo motivo para todos
los juegos (salió «rendimiento»).

**En los 83 (data-v1):**

| Criterio | Pide | Salió | ¿Cumple? |
|---|---|---|---|
| Juegos evaluables (≥ 10 quejas) | ≥ 20 | 15 | no |
| Acierto propio | ≥ 70 % | 60.0 % | no |
| Ventaja sobre la base (acierto de la base: 60.0 %) | ≥ 10 puntos | +0.0 | no |
| IC 95 % de la ventaja | > 0 | [−26.7, +26.7] | no |

Con menos de 20 evaluables, **A no es concluyente**, y eso no cuenta como éxito.

Además, el acierto propio y el de la base empatan en los tres tamaños (no es criterio):

| Quejas con motivo | Juegos | Propio | Base |
|---|---|---|---|
| 10–15 | 2 | 50.0 % | 50.0 % |
| 16–30 | 5 | 60.0 % | 60.0 % |
| más de 30 | 8 | 62.5 % | 62.5 % |

**En los 40 externos (data-v2):** 13 evaluables. El acierto propio es 84.6 % y el de la base
69.2 %, así que **confirma** según su criterio (≥ 60 % y ≥ la base). Pero confirma algo que
en los 83 no se pudo concluir.

## B · Confianza

¿Con cuántas quejas el motivo principal se mantiene en el 80 % de las réplicas? Se midió en
9 juegos de referencia de los 83, los que tienen ≥ 30 quejas con motivo, con 1,000 réplicas
por juego y por tamaño.

| k quejas | p25 | Mediana | p75 |
|---|---|---|---|
| 5 | 53.2 % | 58.2 % | 60.2 % |
| 10 | 53.9 % | 68.4 % | 73.0 % |
| 15 | 58.2 % | 69.9 % | 78.6 % |
| 20 | 59.2 % | 77.1 % | 83.8 % |
| 25 | 63.3 % | 78.2 % | 86.5 % |
| 30 | 63.0 % | 80.5 % | 88.5 % |

- **N = 30**, y la ficha pide ≤ 20.
- **Solo 13 de los 123 juegos** tienen al menos 30 quejas con motivo (9 de los 83 y 4 de los
  40), y la ficha pide ≥ 30.
- WILD HEARTS llega (213 quejas), Hades no (1) y Apex Legends tampoco (4).
- **B no pasa.**

## Qué se decide

Según la regla fijada en la ficha, **no se construye**: B falla y A no concluye en los 83. Los
motivos siguen en `/explicacion` como «lo que más mencionan», sin prometer qué revisar. La
maqueta y la prueba con personas (C) no se hacen.

**Lectura, sin mover los criterios:**
- Falta de datos: las palabras clave clasifican solo una parte de las quejas, así que pocos
  juegos llegan a tener suficientes.
- Además, en los 83 el motivo propio de cada juego no anticipa mejor que decir
  «rendimiento» para todos, ni siquiera en los juegos con más de 30 quejas.
- Si la Parte B de los modelos de texto clasifica más quejas con un modelo, A y B se repiten
  con los mismos criterios, como dice la ficha.
