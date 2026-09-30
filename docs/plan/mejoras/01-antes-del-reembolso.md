# Mejora 01 · «Antes de que cierre tu reembolso»

Un bloque en la ficha del juego con los dos motivos que más mencionan las negativas tempranas
de ese juego, convertidos en una lista de qué revisar en las primeras 2 horas. Esta ficha
valida la idea **antes** de construirla.

Los criterios de éxito (parte 4) se fijaron y se commitearon antes de correr cualquier
prueba; el hash de ese commit queda en la parte 6. No se ajustan después de ver resultados.

## 1. Dónde aplica

- En la ficha del juego (`/juego/:appid`), junto a los motivos de las reseñas.
- Solo en los juegos con al menos **N** quejas con motivo. N sale de la prueba B.
- En los juegos gratis el título es «En tus primeras horas»: no hay reembolso que cuidar,
  pero sí las mismas primeras horas.

## 2. Qué promete

> Lo que más mencionan quienes dejaron una reseña negativa antes de 2 horas de juego, para
> que lo revises mientras todavía puedes pedir el reembolso.

No promete predecir la experiencia de nadie ni recomienda comprar o no comprar. Tampoco
promete el reembolso: lo decide Steam. Es una señal de reseñas, no una confirmación de que
alguien se arrepintió.

Qué revisar en cada motivo (es el texto que se prueba con personas en C):

| Motivo | Qué revisar |
|---|---|
| rendimiento | Que corra estable en tu equipo: cuadros por segundo, tirones y cierres |
| bugs | Errores que te traben o te hagan perder avance |
| dificultad | Si la dificultad o el grind te frustran desde el principio |
| controles | Que los controles respondan bien con tu mando o teclado |
| contenido | Si lo que ofrece te alcanza o se vuelve repetitivo |
| precio | Si lo que incluye vale lo que pagaste (DLC, microtransacciones). En juegos gratis: si las compras dentro del juego te frenan |

## 3. Cómo se comprueba

**Definiciones comunes.**

- **Queja con motivo:** reseña con señal de arrepentimiento temprano (negativa, escrita antes
  de 120 minutos de juego) que menciona al menos una categoría según `analisis/motivos.py`,
  las mismas palabras clave de `/explicacion`.
- **Motivo principal:** el más mencionado. **Dos principales:** los dos más mencionados.
- **Empates:** se deciden por el orden fijo rendimiento, bugs, dificultad, controles,
  contenido, precio.
- `/explicacion` ordena hoy por frecuencia redondeada a 2 decimales; las pruebas usan los
  conteos exactos. Si el bloque se construye, la API debe ordenar igual que las pruebas.

**A · Anticipación.** ¿Lo que se quejaba la gente antes sigue siendo lo que se queja después?

- Por juego, las quejas con motivo se ordenan por `timestamp_created`: la mitad vieja son
  las primeras ⌊n/2⌋ y la nueva, el resto. Un juego es evaluable si tiene n ≥ 10.
- **Acierto propio:** % de juegos evaluables donde el motivo principal de la mitad vieja está
  entre los dos principales de la nueva.
- **Línea base:** un solo motivo para todos los juegos, el más mencionado en las mitades
  viejas juntas de los 83 evaluables. Su acierto es el % de juegos donde ese motivo está
  entre los dos principales de la mitad nueva.
- Los umbrales se fijan con los 83 de data-v1; los 40 externos de data-v2 solo confirman.
- Reporte adicional, **no es criterio**: el acierto propio y el de la base por tamaño del
  juego (10–15, 16–30 y más de 30 quejas con motivo), en los 83 y en los 40, para distinguir
  falta de datos de una idea que no sirve.

**B · Confianza.** ¿Con cuántas quejas el motivo principal deja de ser azar?

- **Juegos de referencia:** los de los 83 con ≥ 30 quejas con motivo. Si son menos de 8, se
  baja a ≥ 20 y la rejilla llega hasta 20.
- Para k = 5, 10, 15, 20, 25 y 30: 1,000 réplicas por juego tomando k quejas con reemplazo
  (semilla 42). **Estabilidad:** % de réplicas cuyo motivo principal coincide con el del
  juego completo.
- **N:** el menor k donde la estabilidad mediana de los juegos de referencia es ≥ 80 %.
- Se reporta N y cuántos de los 123 juegos tienen ≥ N quejas con motivo (83 y 40 por
  separado), con WILD HEARTS, Hades y Apex Legends nombrados.

**C · Personas** (la corre el equipo, no un script).

- 5 personas que compran en Steam, con una maqueta estática del bloque para WILD HEARTS,
  Hades y Apex Legends (gratis) y un guion de 5 minutos. La maqueta y el guion solo se hacen
  si A y B pasan.

A y B: `analisis/antes_del_reembolso.py`, con la salida en `docs/evidencia/`.

## 4. Criterio de éxito (fijado antes de mirar)

**A en los 83 (data-v1).** Éxito si se cumplen las cuatro:

1. al menos 20 juegos evaluables;
2. acierto propio ≥ 70 %;
3. acierto propio − acierto de la base ≥ 10 puntos;
4. el IC 95 % de esa diferencia (bootstrap pareado sobre juegos, 1,000 réplicas, semilla 42)
   queda por encima de 0.

Con menos de 20 evaluables, A es **no concluyente** y no cuenta como éxito.

**A en los 40 externos (data-v2).** No se usan para fijar nada: el mismo mínimo de 10 y la
misma línea base (su motivo sale de los 83). **Confirma** si el acierto propio es ≥ 60 % y
≥ al de la base. Con menos de 8 evaluables, **no alcanza a concluir**.

**B.** Éxito si N ≤ 20 y al menos 30 de los 123 juegos llegan a N. Si ningún k de la rejilla
llega al 80 %, falla.

**C.** Éxito si se cumplen las cuatro:

- al menos 4 de 5 dicen con sus palabras qué revisarían en sus primeras 2 horas;
- como mucho 1 de 5 entiende que el bloque garantiza el reembolso o predice su propia
  experiencia;
- al menos 3 de 5 dicen que lo usarían;
- **neutralidad: 0 de 5** lo entienden como «cómpralo» o «no lo compres». Es la línea del
  proyecto y no admite ni un caso.

**Regla de decisión.** Se construye si A pasa en los 83, B pasa, C pasa, y los 40 externos
confirman o no alcanzan a concluir; en ese último caso esta ficha lo dice: «no confirmado en
juegos externos». Si los 40 alcanzan a concluir y no confirman, no se construye.

## 5. Qué pasa si falla

- **A falla en los 83:** no se construye. Los motivos siguen en `/explicacion` como «lo que
  más mencionan», sin prometer qué revisar.
- **Los 40 concluyen y no confirman:** no se construye; lo fijado con los 83 no transfiere.
- **B falla:** no se construye; con pocos juegos por encima de N el bloque sería una excepción.
- **C falla:** se reescribe el texto y se repite C con otras 5 personas; no se construye con
  el texto actual.
- **Si la Parte B de los modelos de texto cambia los motivos a un modelo,** A y B se repiten.

## 6. Resultado

Corrido el 2026-09-30 con los criterios del commit `7b0ba52`, sin cambiarlos.

```bash
python analisis/antes_del_reembolso.py > docs/evidencia/antes-del-reembolso.txt
```

Detalle en [docs/evidencia/antes-del-reembolso.md](../../evidencia/antes-del-reembolso.md).

| Prueba | Resultado | Contra el criterio |
|---|---|---|
| A en los 83 | 15 juegos evaluables; acierto propio 60.0 %, igual que la base («rendimiento» para todos); ventaja +0.0 puntos, IC [−26.7, +26.7] | **no concluyente** (pide ≥ 20 evaluables); tampoco cumple el 70 % ni los +10 puntos |
| A en los 40 | 13 evaluables; propio 84.6 %, base 69.2 % | confirma, pero sobre algo que en los 83 no se concluyó |
| B | N = 30 quejas con motivo; 13 de los 123 juegos llegan (9 de los 83, 4 de los 40) | **no pasa** (pide N ≤ 20 y ≥ 30 juegos) |
| C | no se hace | la maqueta y el guion solo iban si A y B pasaban |

**Decisión: no se construye.** Los motivos siguen en `/explicacion` como «lo que más
mencionan», sin prometer qué revisar.

- En los 83, el acierto propio empata con la base en los tres tamaños (10–15, 16–30 y más de
  30 quejas). No es solo falta de datos: con estas palabras clave, el motivo de cada juego no
  anticipa mejor que un motivo general.
- Si la Parte B de los modelos de texto clasifica más quejas con un modelo, A y B se repiten
  con estos mismos criterios.

---

## Aparte: la regla de «Qué mueve esta estimación»

Decisión del equipo (2026-09-30), para la ronda «explicar el riesgo». Reemplaza las
anteriores: «efecto menor», «Nia empieza siempre por la crítica» y ocultar el precio imputado.

- **Orden por aporte real, siempre.** El primer factor es el que más aporta según el modelo,
  en los 123 juegos: la explicación es fiel a lo que el modelo calculó.
- **Nivel de evidencia en cada factor**, según el bootstrap del EDA
  (`notebook/00_exploracion.ipynb`, §3.4):
  - la crítica (cobertura y nota) lleva «evidencia sólida»;
  - precio, descuento y gratuidad llevan «evidencia débil: con 83 juegos no se distingue de
    cero». No se usa «efecto menor»: habla del tamaño, y en algunos juegos el efecto sí es
    grande.
- **Juegos gratis:** una nota explícita de que en data-v1 había solo 2 gratis, así que el
  modelo extrapola.
- **GTA V Legacy y New World** (de pago, sin precio): el factor de precio sale primero, como
  lo calculó el modelo, con el texto «Precio no disponible: el modelo lo toma como 0» y la
  marca de evidencia débil. Junto al veredicto, el aviso «Estimación menos confiable: a este
  juego le falta el precio y el modelo lo tomó como 0, lo que tiende a bajar su riesgo
  estimado».
- **Nia sigue la misma regla:** nombra el factor que más aportó y, si es de evidencia débil,
  lo dice. Si le preguntan por el riesgo de GTA V Legacy o New World, da el mismo aviso.

**Prueba automática:** `calidad/verificar_factores.py`, en los 123 juegos:

1. el primer factor es el de mayor aporte, sin excepciones;
2. todo factor de precio, descuento o gratuidad lleva evidencia débil;
3. todo factor de crítica lleva evidencia sólida;
4. los juegos gratis llevan la nota de extrapolación;
5. los juegos con precio imputado llevan el aviso en el veredicto, y su primer factor es el
   precio.

Fija el contrato que implementa la ronda: `FactorPrediccion.evidencia` (`"solida"` o
`"debil"`) y `PrediccionRiesgo.avisos` (`codigo` y `texto`; códigos `gratis_extrapola` y
`precio_imputado`). Hasta esa ronda falla a propósito. La parte de interfaz la cubrirán en
esa ronda un spec de `frontend/src/app/dominio/factores.ts` (que deje de ocultar el precio
imputado y pinte evidencia y avisos) y un chequeo en `calidad/capturar_ui.py`.
