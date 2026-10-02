# Dudas resueltas sin preguntar

Decisiones que tomé al reestructurar el documento a nueve secciones (2026-10-01), cuando el dueño
pidió trabajar de corrido. En cada caso elegí la opción conservadora. Formato: qué decidí, por qué y
la alternativa.

## Etapa 1: nueve secciones y lo escrito, condensado

1. **F10, el diagrama de arquitectura, se queda.**
   - Por qué: sostiene dos decisiones de la sección 8, que después de la ingesta nada vuelve a
     consultar Steam y que el build verifica sha256 y bandas. Ocupa poco más de un quinto de página.
   - Alternativa: cambiarlo por una frase y ahorrar ese espacio.
2. **La razón de Mantel-Haenszel pasa de 2.62 a 2.6.**
   - Por qué: la regla de redondeo da un decimal a los cocientes y dos a los extremos de un
     intervalo, y la razón de riesgos es un cociente. Sus extremos siguen en 1.84 y 4.12.
   - Alternativa: dejar 2.62 si la regla solo aplica a los cocientes contra el trivial.
3. **`verificar_cifras.py` acepta «notebook 00, §3.4».**
   - Por qué: la regla de remitir al notebook escribe números con punto que no son cifras. La
     excepción es estrecha (`notebook 0[01], §N.N`) y solo vale en esa forma.
   - Alternativa: escribir «sección 3.4 del notebook 00» con una macro por referencia.
4. **`tables/cifras.tex` lleva solo las macros que el texto usa, y la lista canónica también.**
   - Por qué: el generador sigue calculando las demás, porque protegen aserciones (las bandas de
     referencia, `UMBRAL_TIPICO`, las palabras del texto), pero no las escribe. `verificar_cifras.py`
     falla si una canónica no se usa. Así se cumple «las cifras que ya no aparezcan salen de la lista».
   - Alternativa: borrar del generador cada cálculo sin uso, con lo que también se irían esas aserciones.
5. **Las cifras de veteranos y novatos salieron de la lista en la etapa 1 y vuelven en la etapa 2.**
   - Por qué: en la etapa 1 ningún texto las usaba todavía, y la verificación de cada etapa tiene que
     dar exit 0.
   - Alternativa: escribir antes el planteamiento, saltándose el orden de las etapas.
6. **Las antiguas secciones son ahora subsecciones, y sus subsecciones, párrafos con título.** Se
   conservan todos los `\label`.
   - Por qué: así no se rompe ninguna referencia cruzada, y el índice sigue con una sola página.
   - Alternativa: renumerar las etiquetas, lo que obliga a revisar cada `\ref`.
7. **El marcador de la Parte A reserva una caja de 11 cm.**
   - Por qué: junto con su párrafo ocupa unas 0.75 páginas, como pidió el dueño, y el conteo de
     páginas ya la incluye.
   - Alternativa: un marcador de una línea, con el riesgo de que el resultado de la rama
     `modelos-texto` no quepa.
8. **La sección 5 queda unas 0.6 páginas sobre su presupuesto.**
   - Por qué: F2 y la tabla descriptiva no se recortan. Lo que se recortó fueron las notas al pie
     largas y la altura de F2, F3 y F4, y el texto se condensó.
   - Alternativa: quitar F4 y dejar sus cifras en el texto, pero F4 sostiene la evidencia sólida de
     la crítica.
9. **La tabla descriptiva da los porcentajes de reseñas con perfil público** (40.1 % en data-v1), el
   complemento del 59.9 % de privados que cita la sección 4.
   - Por qué: el dueño pidió el porcentaje de perfiles públicos.
   - Alternativa: dar los privados en la tabla también.
10. **En la sección 6, «valores extremos» dice que no se recorta ninguno.**
    - Por qué: es lo que hace el código. El precio entra en logaritmo, los rangos imposibles no
      tienen casos, y de los minutos solo importa si quedan antes o después de los 120.
    - Alternativa: medir y reportar valores atípicos, que sería contenido nuevo.
