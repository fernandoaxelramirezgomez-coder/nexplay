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

## Etapa 2: introducción, planteamiento y estrategia

11. **`verificar_cifras.py` ignora las medidas de diseño**, como `0.49\textwidth` o `6.6cm`.
    - Por qué: las figuras con capturas y la tabla de la rúbrica necesitan anchos, y un ancho no es
      una cifra del análisis. La excepción solo cubre números seguidos de una unidad de longitud.
    - Alternativa: definir un macro de ancho en `main.tex` por cada uso.
12. **Veteranos y novatos aparecen con su matiz.**
    - Por qué: la experiencia sí se asocia con la señal dentro de cada juego (2.6 [1.84, 4.12]),
      pero el sitio no la usa para mover el riesgo. El texto dice las dos cosas y remite a la
      decisión B+, en lugar de callar la asociación.
    - Alternativa: citar solo «la señal no viene de la inexperiencia».
13. **La usabilidad no dice «menos de un minuto».**
    - Por qué: no hay una medición que lo respalde. Solo afirma lo que se ve en el código y en las
      capturas: la banda sin porcentaje, la evidencia por factor, el número de reseñas detrás de
      cada motivo, los controles de 44 px (tomados de `base.css`) y los dos temas.
    - Alternativa: medir el tiempo de una consulta con usuarios, que sería contenido nuevo.
14. **En el recorrido, los porcentajes de motivos se dan sobre las reseñas clasificadas, con sus
    conteos** (48 % de 33, de 113).
    - Por qué: así los calcula `/explicacion` y así los muestra la ficha.
    - Alternativa: darlos sobre todas las reseñas con la señal, que no coincidiría con la captura.
15. **La captura de Nia va en la sección 8 y no en la 3.**
    - Por qué: la sección 3 ya lleva dos figuras de capturas, y Nia se explica en la interfaz.
    - Alternativa: una tercera figura de capturas en la estrategia, que se pasaría de su presupuesto.

## Etapa 3: resolución y conclusiones

16. **Las pruebas del frontend se nombran sin dar su número.**
    - Por qué: cinco de ellas dependen de la API en el puerto 8000 desde `fc310c5` (es un pendiente
      de cierre que se arregla desde master), así que un conteo de `ng test` hoy dependería de tener
      la API levantada. Las cifras de Nia sí salen del repo y de `docs/evidencia/nia-pruebas.md`.
    - Alternativa: correr `ng test` con la API y citar el conteo.
    - **Resuelta en master** (`d936f9a`): las pruebas simulan el catálogo y el perfil, y ya no
      dependen de la API. El texto sigue sin dar el conteo.
17. **La corrida de trampas de Nia se cita como la del 30 de septiembre**, con una nota de que se
    repite sobre el tag de entrega.
    - Por qué: es la última que hay, y `correr_trampas.py` con clave es un pendiente de cierre.
    - Alternativa: no citarla hasta tener la del tag.
18. **Las limitaciones incluyen que no hubo un estudio con usuarios externos.**
    - Por qué: el plan lo tenía en la lista, y la sección de usabilidad no afirma nada que dependa de
      él.
    - Alternativa: dejarlo solo en los siguientes pasos.
19. **«Qué se concluye» repite la frase de la sobredispersión que aprobó el dueño para la sección 5**:
    la varianza es unas 107 veces la esperada si todos los juegos tuvieran la misma tasa.
    - Por qué: «veces más de lo que daría el azar» fue la formulación que el dueño pidió cambiar.

## Etapa 4: referencias, anexo y resumen

20. **El total quedó en 25 páginas, tres por debajo de la meta.**
    - Por qué: se condensó lo escrito y se escribió lo que faltaba dentro de cada presupuesto, sin
      agregar contenido nuevo para llenar.
    - Alternativa: devolver al documento alguna tabla que se fue al notebook, como la de 83 contra
      40 o la de correlaciones.
21. **El anexo lleva el sha256 de cada archivo tal como lo publica GitHub.**
    - Por qué: el generador lo compara con el que usa el código (las bases contra `RELEASES` y los
      extractos contra el notebook 01) y falla si no coincide. En la tabla, los archivos se llaman
      «base» y «extracto»; el pie de la tabla de releases da su nombre completo.
    - Alternativa: el nombre completo del archivo en cada renglón, que no cabe a lo ancho.
22. **El commit del tag `codigo-v3` sale de git (`codigo-v3^{commit}`).** Desde el 2026-10-02, el tag
    sale del `CODIGO_REF` de los notebooks (entrada 25).
    - Por qué: el tag es anotado, y `git rev-parse codigo-v3` da el objeto del tag (`37cdc56`), no el
      commit (`9b64795`). El generador comprueba que la corrida de Colab clonó ese mismo commit.
    - Alternativa: escribir el commit a mano, lo que la regla de las cifras no permite.
23. **`\fechaentrega` sigue en el 30 de septiembre de 2026.**
    - Por qué: fijarla a la fecha de entrega es un pendiente de cierre.

## Ronda del 2026-10-02: la Parte A y la lectura para negocio

Al traer master (`codigo-v6`) a `documento`. Las del dueño van marcadas así; las demás las decidí yo.

24. **Todo PR-AUC con tres cifras significativas** (del dueño). Su desviación, intervalo o diferencia
    llevan los decimales de la estimación. Los scores y los umbrales de banda siguen con cuatro.
    - Por qué: con tres decimales, 0.069 / 0.022 da 3.1 contra el 3.2× publicado. Con la regla solo
      cambia el fold 1, de 0.1459 a 0.146. `verificar_cifras.py` la comprueba en cada macro `PRAUC*`.
    - Alternativa: tres decimales fijos, con los cocientes descuadrados.
25. **El tag y el commit del anexo son identificadores, no cifras canónicas** (del dueño).
    - Por qué: salen del `CODIGO_REF` de los tres notebooks y de `git rev-parse`, así que siguen al
      tag de entrega. `verificar_cifras.py` los compara con los notebooks y con git, no con un valor
      fijo.
    - Alternativa: escribir `codigo-v6` en la lista canónica, que habría que cambiar en cada tag.
26. **En 7.6, la tabla de bandas OOF del 01 reemplaza la comparación por cobertura de crítica** (del
    dueño). Se quedan los 33 de 43 sin nota y los casos al filo.
    - El título dice OOF, y una oración explica por qué sus bandas de data-v1 (27, 27 y 29) no son
      las servidas (30, 23 y 30).
27. **Las tres figuras nuevas salen de las salidas guardadas en el tag, no de las de Colab.**
    - Por qué: en Colab el 02 apaga la exportación y sus gráficas quedan como HTML, sin PNG. El
      generador comprueba que cada celda de la que toma una cifra imprimió en Colab el mismo texto
      que en el tag. Solo difieren celdas que el documento no usa: el entorno, los tipos de pandas y
      el cuarto decimal de MiniLM por fold.
    - Alternativa: rehacer las figuras, lo que el dueño descartó.
28. **El anexo cita solo la corrida vigente de Colab, la de `codigo-v6`.**
    - Por qué: es la del código entregado. Las de `codigo-v3` y `codigo-v4` se quedan en
      `docs/evidencia/colab/` como historial. El generador falla si el commit de esa corrida no es el
      que clonan los notebooks, así que un tag de entrega nuevo obliga a correrlos otra vez en Colab.
    - Alternativa: citar también las anteriores, que no prueban nada que la vigente no pruebe.
29. **Nia: solo el mecanismo de la etiqueta «Con IA» / «Sin IA»** (del dueño). La evidencia llega
    después: la salida de `verificar_nia.py --openai` y una captura de producción.
30. **El aviso «Mean of empty slice» no se menciona** (del dueño). En Colab no aparece (0 salidas a
    stderr); solo salía en una copia local.
31. **Las 35 de 40 palabras van en 7.9; la limitación de 9.1 remite ahí sin repetir la cifra.**
    - Por qué: la regla de remitir a la sección 7 cuando las conclusiones tocan lo que ya mostró.
32. **«La décima parte de las negativas», no «el 10 %».**
    - Por qué: es el corte, no una cifra del análisis, y escrito con dígitos sería un número a mano.
    - Alternativa: una macro para el corte.
33. **En 7.4, «fuera de pliegue» pasa a «fuera de fold (OOF)».** Es el término de la tabla de 7.6 y
    de los notebooks.
34. **Los cortes de las bandas son los percentiles 33.3 y 66.7 de los scores fuera de fold de las reseñas
    de entrenamiento, no «tercios»** (del dueño). En el catálogo quedan 43, 37 y 43.
    - El generador lee esos percentiles del `np.percentile` de `backend/modelado/entrenar_modelo.py`
      (con `ast`) y corta con ellos, así que el texto y los umbrales siguen al código.
    - «Tercios del catálogo» no estaba en el documento. Estaba en el frontend y en Nia; **lo corrigió master**
      en `54e1983` (`codigo-v7`), y `backend/calidad/verificar_niveles.py` vigila que no vuelva.

## Ronda del 2026-10-02, madrugada: `codigo-v7`

35. **`documento` se rebasó sobre master (`codigo-v7`, `54e1983`)** (del dueño), en lugar de otro merge.
    - Los 34 commits propios se reaplicaron sin merges. Los conflictos fueron de rutas: `calidad/` pasó a
      `backend/calidad/` en la reorganización (con `merge.directoryRenames=true`) y el README de la raíz. Se
      resolvieron con la redacción del merge que el rebase descarta.
    - El árbol final es idéntico al de fusionar master con el `documento` anterior (`git merge-tree`,
      `dc638dce`). El `documento` anterior queda en la rama `respaldo-documento-antes-del-rebase`.
36. **La evidencia de `verificar_nia.py --openai` se reemplazó por la corrida que sí usó `codigo-v7`.**
    - La anterior se commiteó a las 03:25 y el tag se creó a las 03:29:33, así que no pudo correr sobre él.
      La nueva corrió de 03:29:39 a 03:31:32 en un clon con `54e1983`.
    - La macro `FechaCorridaNiaIA` sigue en «2 de octubre de 2026»: las dos corridas son de ese día, y la
      fecha sale del nombre del archivo.
37. **8.2 nombra el verificador de niveles** (del dueño), en el orden de `make test`.
