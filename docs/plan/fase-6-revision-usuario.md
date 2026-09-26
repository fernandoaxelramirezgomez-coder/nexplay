# Fase 6 — Revisión del usuario final

> **Léelo antes de empezar cualquier sesión de trabajo.** Es el plan vivo de la ronda: en
> cada ALTO se marcan las casillas hechas y este archivo va en el mismo commit que el
> código de esa fase.
>
> Reglas de la ronda, en corto:
> - **El usuario final es la ley.** Todo lo que pidió se hace, aunque cambie decisiones
>   anteriores.
> - **No se toca la validez del modelo**: de título, entrenado con data-v1. Lo que se
>   muestre como recomendación o sugerencia va etiquetado como tal y separado del riesgo
>   estimado.
> - **Antes de programar cada fase**, mockup (HTML o captura) y visto bueno. Después se
>   ejecuta, y la fase cierra con ALTO: capturas + pruebas + commit.
> - **Sin llamadas a OpenAI**: las pruebas con IA las hace el dueño del proyecto.
> - **Tareas largas** (descarga de datos, capturas de las tres resoluciones) en segundo
>   plano, siguiendo con lo demás, y se reporta cuando terminen.
>
> Estado: plan guardado el 2026-09-25. Fase en curso: **6A**. Hechos los puntos 2
> (tipografía) y 6 (nombre del riesgo). **Pendientes de la confirmación del dueño sobre el
> mockup**: 1 (fondos), 3 (logo), 4 (botones) y 5 (menú). Las capturas del mockup no se
> versionan; salen con `python docs/plan/mockups/capturar_mockup.py`.

---

Mensaje completo de la revisión, tal como llegó:

Primero, guarda este mensaje completo como docs/plan/fase-6-revision-usuario.md, con
una casilla [ ] por punto numerado. En cada ALTO marcas las hechas y haces commit del
archivo junto con el código. En sesiones nuevas lee ese archivo antes de empezar.
Las tareas largas (descarga de datos, capturas de las tres resoluciones) córrelas en
segundo plano y sigue con lo demás; reporta cuando terminen.

Llegó una revisión de un usuario final que probó las nueve vistas. Regla de esta ronda:
EL USUARIO FINAL ES LA LEY. Todo lo que pidió se hace, aunque cambie decisiones
anteriores. Lo único que no se toca es la validez del modelo: sigue siendo de título,
entrenado con data-v1, y lo que se muestre como recomendación o sugerencia se etiqueta
como tal, separado del riesgo estimado. Todo lo demás está abierto.

Trabaja por fases con ALTO al final de cada una (capturas + pruebas + commit por fase).
No lances llamadas a OpenAI: las pruebas con IA las hago yo. Antes de programar cada
fase, muéstrame en una pantalla el diseño que propones (mockup en HTML o captura) y
espera mi visto bueno; después ejecuta.

═══════════════════════════════════════════════════════════════
FASE 6A — Identidad visual (aplica a todas las vistas)
═══════════════════════════════════════════════════════════════
REFERENCIA OBLIGATORIA: https://omoggle.com/ — visítala y toma de ella:
- Título de vista gigante en mayúsculas con degradado metálico sobre fondo oscuro.
- Fondo de degradado profundo (negro azulado → morado) con un brillo suave detrás del
  contenido principal, no un color plano.
- Una acción principal por pantalla, en una tarjeta grande con icono, título enorme y
  una sola llamada a la acción con flecha ("Buscar un juego →").
- Botones secundarios como tarjetas anchas: icono a la izquierda, título en mayúsculas
  con letter-spacing, subtítulo de una línea, chevron a la derecha, y un color propio
  por botón (por ejemplo: Explorar cian, Comparar dorado, Nia morado, Panorama verde).
- Etiquetas en mayúsculas espaciadas solo para acciones; texto normal para lectura.
- Toggle de tema como botón redondo flotante.
No copies su contenido ni su marca: copia la jerarquía y el trato de los botones.

El usuario no vio el logo, no vio los títulos de las vistas, no distinguió el título del
texto y el fondo le pareció el mismo en todas partes.

- [ ] 1. Fondos: espacio/futurista, distinto por contexto (inicio, explorar, ficha, perfil,
   Nia, panorama, comparar). Que se vean bien en PC, iPad y teléfono (1440, 1024, 390).
   Sin imágenes con derechos: genera los fondos con CSS/SVG (gradientes, estrellas,
   nebulosas, partículas) o arte propio. Guarda cada uno como asset y documenta su origen.
- [x] 2. Tipografía nueva: una fuente display con carácter para títulos (gamer/futurista,
   legible) y una de lectura clara para el cuerpo. Títulos de vista con el tratamiento
   de omoggle (grande, mayúsculas, degradado). Cuerpo nunca menor a 16 px; nada de
   "letras chiquitas" en descripciones ni notas.
- [ ] 3. Logo: más grande y acomodado al ancho de la barra en modo expandido y contraído.
- [ ] 4. Botones: sistema propio con estilo omoggle (tarjeta ancha con icono, título,
   subtítulo, chevron y color por acción), más botones compactos para acciones
   pequeñas. Estados hover/activo/deshabilitado inconfundibles. Que se distingan del
   fondo en los dos temas.
- [ ] 5. Etiquetas de las vistas (ítems del menú y encabezados): revisar nombres y estilo para
   que se entiendan sin contexto; icono + nombre + una línea de subtítulo en el menú
   expandido.
- [x] 6. Renombrar "banda" y "Riesgo general". El usuario no sabe qué es "banda". Propón tres
   nombres cortos (p. ej. "Riesgo de arrepentirte: bajo/medio/alto", "Señal de
   arrepentimiento") con una explicación de una línea al pasar el cursor. Cambia el
   vocabulario en todo el sitio y en el prompt de Nia de una sola vez.

═══════════════════════════════════════════════════════════════
FASE 6B — Inicio, Explorar y Ficha
═══════════════════════════════════════════════════════════════
INICIO
- [ ] 7. La descripción bajo el título no se distingue: subir tamaño y contraste y separarla
   del título. Una sola acción principal (buscar) en tarjeta grande estilo omoggle; las
   cuatro tarjetas de "Qué puedes hacer aquí" como botones anchos con color propio.
- [ ] 8. Enlaces a las fuentes: Steam (appreviews y appdetails) y Metacritic, visibles, y en
   la sección "Fuentes" (fase 6E).

EXPLORAR
- [ ] 9. Carrusel de videos de los juegos (los tráilers que ya usa la ficha), arriba de los
   estantes, silenciado, con controles visibles y bien acomodado en las tres
   resoluciones.
- [ ] 10. Cada tarjeta con color/sombreado según su nivel de riesgo (verde, ámbar, rosa) y, si
    se puede sacar el color dominante de la portada, usarlo en el borde.
- [ ] 11. Título de la vista chico: aplicar la tipografía de la fase 6A.

FICHA DE JUEGO
- [ ] 12. Bug: "Ver más" aparece aunque la descripción sea corta. Solo si hay texto oculto.
- [ ] 13. Botones del video casi no se ven: más grandes, con fondo, siempre visibles en
    pantallas táctiles.
- [ ] 14. Bloques con distinción clara: cada sección (motivos, factores, tu perfil, opinión,
    comentarios) con contenedor, tipografía y color de encabezado propios.
- [ ] 15. "Por qué te tocaría a ti" más visible: tarjeta destacada con resumen del perfil
    (respuestas en chips) y las tres líneas. Sin perfil, llamado claro a crearlo.
- [ ] 16. Botones (Comparar, Ver en Steam, Preguntar, Enviar) con el sistema de la fase 6A.

═══════════════════════════════════════════════════════════════
FASE 6C — Perfil
═══════════════════════════════════════════════════════════════
El usuario no supo que podía definir su perfil, no vio el botón de guardar, no se dio
cuenta de que estaba activo, no entendió "tolerancia a la fricción" y le pareció feo.

- [ ] 17. Descubrimiento: la primera vez, invitación visible en Inicio y en la ficha
    ("Cuéntanos cómo juegas · 1 minuto") e indicador claro en el menú de si el perfil
    está activo (no solo un punto).
- [ ] 18. Rediseño futurista de los filtros: opciones como tarjetas/segmentos grandes con
    icono, no texto plano. Sin letras chicas.
- [ ] 19. Cada pregunta explicada en una línea justo bajo su título, no en un párrafo al
    final. "Tolerancia a la fricción: ¿cuánto aguantas bugs, curva de aprendizaje y
    dificultad antes de dejar un juego?". Igual para Plataforma.
- [ ] 20. Plataforma: selección múltiple con logo/color de cada una (PC, PlayStation, Xbox,
    Nintendo).
- [ ] 21. Nueva pregunta: rango de gasto por juego, con 4 rangos en MXN. Se guarda y se usa en
    las sugerencias.
- [ ] 22. Botón de guardar siempre visible (fijo) y confirmación "Perfil guardado y activo".
- [ ] 23. Las sugerencias usan TODO el perfil, no solo los géneros: gasto (precio dentro del
    rango), horas (juegos que rinden en sesiones cortas si juega poco), tolerancia
    (menos peso a juegos con motivos de bugs/dificultad si es baja) y plataforma. Se
    recalculan en vivo al cambiar cualquier filtro. Etiqueta: "Sugerencias según tu
    perfil" (no cambian el riesgo del juego).

═══════════════════════════════════════════════════════════════
FASE 6D — Comparar
═══════════════════════════════════════════════════════════════
- [ ] 24. Nota al inicio: "Compara hasta 4 juegos lado a lado", visible antes de elegir.
- [ ] 25. Juegos sin Metacritic: completar con el sentimiento de las reseñas de Steam que ya
    tenemos (porcentaje positivo y resumen de Steam), con la nota "Sin crítica
    especializada; esto viene de N reseñas de jugadores". Si hay comentarios del público
    en NexPlay, mostrarlos ahí con la misma advertencia.
- [ ] 26. Evaluar una fuente adicional de crítica (OpenCritic u otra con API pública) para los
    juegos sin Metacritic. Propón fuente, licencia y costo antes de integrarla.

═══════════════════════════════════════════════════════════════
FASE 6E — Panorama, Cómo funciona y Fuentes
═══════════════════════════════════════════════════════════════
- [ ] 27. Panorama como tablero: cada gráfica con título de una línea (qué se ve) y
    conclusión de una línea; el texto largo detrás de ⓘ; cada gráfica con su fuente.
- [ ] 28. Cómo funciona: pasos visuales, una línea por paso, texto largo colapsado.
- [ ] 29. Sección "Fuentes" (en Cómo funciona y en el pie): Steam, Metacritic y las que se
    agreguen, con enlace, fecha de descarga y qué se toma de cada una.

═══════════════════════════════════════════════════════════════
FASE 6F — Nia (personalidad, entendimiento y presencia)
═══════════════════════════════════════════════════════════════
Lo que dijo el usuario: parece una grabadora, es triste y seria, no resume lo que ella
misma dijo, no entiende las preguntas, su texto no es legible y la burbuja no la muestra.

- [x] 30. Bug prioritario: el textarea no se vacía al enviar (el contador vuelve a 0 pero el
    texto viejo se queda y se concatena con lo siguiente). Arreglar y cubrir en el
    recorrido: dos preguntas seguidas, la segunda llega sola.
- [ ] 31. Personalidad: cercana y cálida, con emojis moderados (1–3 por respuesta), saluda,
    tono de amiga gamer. Respuestas ≤60 palabras con un remate que invite a seguir.
    Fuente de lectura clara en el chat, 16–17 px.
- [ ] 32. Memoria: mandar el historial completo (con tope de tokens) para que resuma, retome y
    responda "resume lo que me dijiste". Casos de prueba: "resume", "¿y cuál de esos…?",
    "lo que dijiste antes".
- [ ] 33. Entendimiento: ampliar el modo demostración con sinónimos y variantes (baratos,
    caros, gratis, para jugar poco, difícil, fácil, nuevo, reciente, nombres con y sin
    acento, "compara X y Y", "¿cuál me compro?") y en modo IA probar un set de 25
    preguntas reales; registrar cuáles falla.
- [ ] 34. Elegir juego: cuando Nia necesita un juego, lo pide con un mensaje de color/contorno
    distinto y muestra un buscador dentro del chat.
- [ ] 35. Burbuja: Nia más grande y visible; al abrirla saluda ("¡Hola! ¿Qué juego estás
    viendo? 👀"). En cada vista manda un mensaje contextual: en Explorar ofrece filtrar,
    en la ficha explicar ese juego, en Perfil sugerencias, en Comparar resumir la
    comparación. Un mensaje por vista, no insistente.
- [ ] 36. Recomendaciones según perfil: Nia puede sugerir juegos usando el perfil (géneros,
    gasto, horas, tolerancia), etiquetado "sugerencia según tu perfil", con el riesgo de
    cada juego al lado, nunca como "cómprate este".
- [ ] 37. Internet: herramienta de búsqueda web (la de OpenAI o una API de búsqueda) para
    tendencias, streamers/youtubers y novedades. Reglas: solo cuando la pregunta lo pide,
    máximo 1 búsqueda por respuesta, citar fuente con enlace, decir cuándo un dato viene
    de internet y no del catálogo. Propón costo por consulta y tope diario antes de
    activarla.
- [ ] 38. Verificar la API de OpenAI para este tipo de respuestas: modelo, tokens máximos,
    temperatura, y que los emojis no rompan el filtro de markdown.

═══════════════════════════════════════════════════════════════
FASE 6G — Catálogo más grande y vista de críticas
═══════════════════════════════════════════════════════════════
- [ ] 39. Ampliar a ~400 juegos: los más relevantes del año y con crítica. Pipeline data-v3:
    appdetails para todos (el modelo es de título y puede puntuarlos como a los 40 no
    vistos), appreviews donde se pueda (para motivos), y marcar en la ficha cuándo un
    juego tiene riesgo estimado pero todavía no motivos. Estimar tiempo y espacio antes
    de correrlo; correr la descarga en segundo plano. data-v1 no se toca.
- [ ] 40. Juegos actuales: estante "Lo más nuevo" en Explorar y en las sugerencias.
- [ ] 41. Nueva vista "Críticas": los más recomendados según la crítica y según los jugadores,
    con filtros por género y año, y su riesgo al lado. Con enlace a las fuentes.
- [ ] 42. Juegos vistos por streamers/youtubers: depende del punto 37. Si el usuario dice a
    quién sigue, Nia busca qué está jugando y lo cruza con el catálogo.

═══════════════════════════════════════════════════════════════
Verificación de toda la ronda
═══════════════════════════════════════════════════════════════
- capturar_ui.py en 1440, 1024 y 390, claro y oscuro, con los fondos nuevos y el
  contraste medido en cada uno.
- Recorrido de usuario nuevo: entra, crea perfil, explora, abre una ficha, compara dos,
  le pregunta a Nia dos cosas y vota. Todo sin leer instrucciones.
- Medir antes y después: palabras por vista, tamaño mínimo de fuente, contraste mínimo.

Empieza guardando este plan en docs/plan/fase-6-revision-usuario.md, luego la 6A, y
detente en su ALTO con el mockup de la identidad visual.

---

## Notas de ejecución

- **Punto de partida medido antes de la 6A** (2026-09-25): `--texto-caption` vale 14 px y
  lo usan 22 componentes; el carrusel del inicio tiene textos de 10 y 11 px.
  *Corrección:* una primera versión de esta nota decía que Inter y JetBrains Mono no se
  cargaban. Era falso: se cargan como paquetes `@fontsource` desde el arreglo `styles` de
  `frontend/angular.json`, y la búsqueda solo había mirado `src/styles/` e `index.html`.
- **La referencia**: omoggle.com se pinta en el cliente, así que se leyó su CSS. De ahí
  sale: fondo casi negro con una rejilla cian/morada a ~5 %, brillos por color al 40 %
  (morado, azul, cian, dorado), títulos en degradado blanco → cian claro a peso 900 con
  sombra de brillo, etiquetas de acción en monoespaciada espaciada, y en tema claro los
  títulos pasan a tinta sólida.
- **Pendientes de propuesta antes de tocar nada**: 26 (fuente de crítica: licencia y
  costo), 37 (búsqueda web: costo por consulta y tope diario), 39 (catálogo de ~400:
  tiempo y espacio estimados).
- La fase 5c (poses de Nia) queda absorbida por la 6F.
- **Mockup 6A** (2026-09-25): medido por la propia página en 1440, 1024 y 390, claro y
  oscuro: 0 contrastes que no pasan, sin desborde, letra mínima 16 px. Para que el texto
  de nota pase 4.5:1 sobre la zona más clara, la nebulosa se gradúa por color: 0.40 en los
  morados (inicio, ficha, Nia), 0.34 en perfil, 0.24 en panorama y 0.20 en explorar y
  comparar, que son claros. Con 0.35 parejo, la nota caía a 2.74:1 en explorar.
- **Notas para programar la 6A**: el botón de tema flotante tiene que reservar su esquina
  como ya lo hace la burbuja de Nia; en teléfono, el espaciado de 0.14 em parte «Preguntar
  a Nia» en dos líneas y conviene bajarlo; la ⓘ no puede escribirse como carácter (Inter
  no tiene U+24D8), va dibujada, como ya se hace en `compartido/nota-info.ts`.
- **Decisiones del dueño para la 6A** (2026-09-25): títulos en **Chakra Petch**, instalada
  por `@fontsource` como Inter y JetBrains Mono, con «Panorama del catálogo» y «Cómo
  funciona NexPlay» en dos líneas como máximo a 390 px. La banda se llama **«Riesgo de
  arrepentimiento: bajo / medio / alto»**, con el tooltip «Qué tan seguido un juego deja
  reseñas negativas en sus primeras dos horas. Es del juego, no de ti.»; en Cómo funciona
  y en la metodología se mantiene «señal proxy» como término técnico. Todo texto sube a
  16 px mínimo en esta fase. **Fondos, colores y menú: pendientes de su confirmación.**
- **6A, puntos 2 y 6 hechos** (2026-09-25):
  - Chakra Petch 600/700 instalada por `@fontsource` como las otras (en `angular.json`).
    Todos los `h1` de vista en mayúsculas con el degradado; en claro, tinta sólida.
    `--texto-caption` pasó de 14 a 16 px y el carrusel dejó sus 10 y 11 px: ninguna de las
    nueve vistas tiene texto bajo 16 px. «Panorama del catálogo» y «Cómo funciona
    NexPlay» ocupan dos líneas a 390 px, con el tamaño completo de 40 px.
  - Quedan para la 6B, porque su texto cambia ahí: el título-frase de Explorar (punto 11) y
    el del inicio (punto 7), que hoy conservan su tamaño propio, y el nombre del juego en
    la ficha, que con nombres largos ocupa tres líneas a 390 px.
  - El nivel se llama «Riesgo de arrepentimiento: bajo / medio / alto» en las nueve vistas
    y en el prompt de Nia, con la explicación de una línea al pasar el cursor por la
    píldora. «Señal proxy» sigue en Cómo funciona y en la metodología. En el backend, las
    herramientas de Nia devuelven `riesgo` en vez de `banda`, para que el modelo no tenga
    la palabra delante; los identificadores del contrato (`banda_riesgo`) no cambian.
  - El recorrido de capturas comprueba ahora, en cada corrida, el piso de 16 px y la
    ausencia de «banda» y «Riesgo general» en las nueve vistas, y los dos títulos a 390.
  - El texto más grande movió tres cosas, ya corregidas: la barra volvió a caber en 674 px
    de alto (los rótulos de grupo quedan tenues y a 12 px entre grupos), la columna del
    valor de las gráficas pasó a 7 rem porque «60% de 10» ya no cabía, y el control de la
    burbuja mide ahora el centro de la parte visible de cada control, con muestreo cada
    40 px y no cada 120: antes contaba como tapada la franja de una tarjeta a medio salir
    de la pantalla y, a la vez, podía no ver un botón entero entre dos muestras.
  - Dos defectos que salieron al revisar las capturas y ya están cubiertos por el
    recorrido: en el carrusel del inicio, la píldora «Riesgo de arrepentimiento: bajo» se
    cortaba contra el borde de la tarjeta (ahora va debajo del nombre; el recorrido busca
    píldoras recortadas en las nueve vistas), y la burbuja de Nia sí tapaba la píldora
    «Comparar» de la tarjeta cortada de cada estante al bajar por Explorar. Esto último era
    el punto 9 del bloque 1, que se había dado por hecho: el muestreo cada 120 px lo
    escondía. En escritorio los estantes terminan ahora 64 px antes del borde, en la
    columna de la burbuja; comprobado a 1024, 1280, 1440 y 1920. Si en la 6F la burbuja
    crece (punto 35), esa reserva tiene que crecer con ella.
- **Punto 30 adelantado de la 6F** (2026-09-25), por ser bug prioritario y no tener diseño
  que aprobar. Reproducido de forma determinista escribiendo y pulsando Enter en la misma
  tarea de JavaScript: pasaba en `/nia` **y en la ficha**. Causa: `[value]="texto()"` solo
  escribe en el DOM cuando el valor cambia respecto al último pintado; si se envía antes de
  que Angular pinte lo escrito, volver a '' no se detecta como cambio. El campo se vacía a
  mano al enviar. El recorrido lo cubre con la misma técnica, y se probó que el control
  falla sin el arreglo (cuatro PROBLEMA) y pasa con él.
