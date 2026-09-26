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
> Estado: plan guardado el 2026-09-25. **6A** (puntos 1 a 6), **6B** (7 a 16) y **6C** (17 a
> 23) hechas el 2026-09-26 y subidas (`abed851`). **6D** hecha (24 y 25) y subida
> (`4dd4ec1`); el 26 está evaluado y decidido (IGDB), con la corrida de cobertura esperando
> `TWITCH_CLIENT_ID` y `TWITCH_CLIENT_SECRET` en `.env`. **6E** hecha (27 a 29). Pulido: P1,
> P2 y P4 a P11 pendientes. Las capturas no se versionan: las de la app salen
> con `python herramientas/capturar_ui.py` y las del mockup con
> `python docs/plan/mockups/capturar_mockup.py`.

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

- [x] 1. Fondos: espacio/futurista, distinto por contexto (inicio, explorar, ficha, perfil,
   Nia, panorama, comparar). Que se vean bien en PC, iPad y teléfono (1440, 1024, 390).
   Sin imágenes con derechos: genera los fondos con CSS/SVG (gradientes, estrellas,
   nebulosas, partículas) o arte propio. Guarda cada uno como asset y documenta su origen.
- [x] 2. Tipografía nueva: una fuente display con carácter para títulos (gamer/futurista,
   legible) y una de lectura clara para el cuerpo. Títulos de vista con el tratamiento
   de omoggle (grande, mayúsculas, degradado). Cuerpo nunca menor a 16 px; nada de
   "letras chiquitas" en descripciones ni notas.
- [x] 3. Logo: más grande y acomodado al ancho de la barra en modo expandido y contraído.
- [x] 4. Botones: sistema propio con estilo omoggle (tarjeta ancha con icono, título,
   subtítulo, chevron y color por acción), más botones compactos para acciones
   pequeñas. Estados hover/activo/deshabilitado inconfundibles. Que se distingan del
   fondo en los dos temas.
- [x] 5. Etiquetas de las vistas (ítems del menú y encabezados): revisar nombres y estilo para
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
- [x] 7. La descripción bajo el título no se distingue: subir tamaño y contraste y separarla
   del título. Una sola acción principal (buscar) en tarjeta grande estilo omoggle; las
   cuatro tarjetas de "Qué puedes hacer aquí" como botones anchos con color propio.
- [x] 8. Enlaces a las fuentes: Steam (appreviews y appdetails) y Metacritic, visibles, y en
   la sección "Fuentes" (fase 6E).

EXPLORAR
- [x] 9. Carrusel de videos de los juegos (los tráilers que ya usa la ficha), arriba de los
   estantes, silenciado, con controles visibles y bien acomodado en las tres
   resoluciones.
- [x] 10. Cada tarjeta con color/sombreado según su nivel de riesgo (verde, ámbar, rosa) y, si
    se puede sacar el color dominante de la portada, usarlo en el borde.
- [x] 11. Título de la vista chico: aplicar la tipografía de la fase 6A.

FICHA DE JUEGO
- [x] 12. Bug: "Ver más" aparece aunque la descripción sea corta. Solo si hay texto oculto.
- [x] 13. Botones del video casi no se ven: más grandes, con fondo, siempre visibles en
    pantallas táctiles.
- [x] 14. Bloques con distinción clara: cada sección (motivos, factores, tu perfil, opinión,
    comentarios) con contenedor, tipografía y color de encabezado propios.
- [x] 15. "Por qué te tocaría a ti" más visible: tarjeta destacada con resumen del perfil
    (respuestas en chips) y las tres líneas. Sin perfil, llamado claro a crearlo.
- [x] 16. Botones (Comparar, Ver en Steam, Preguntar, Enviar) con el sistema de la fase 6A.

═══════════════════════════════════════════════════════════════
FASE 6C — Perfil
═══════════════════════════════════════════════════════════════
El usuario no supo que podía definir su perfil, no vio el botón de guardar, no se dio
cuenta de que estaba activo, no entendió "tolerancia a la fricción" y le pareció feo.

- [x] 17. Descubrimiento: la primera vez, invitación visible en Inicio y en la ficha
    ("Cuéntanos cómo juegas · 1 minuto") e indicador claro en el menú de si el perfil
    está activo (no solo un punto).
- [x] 18. Rediseño futurista de los filtros: opciones como tarjetas/segmentos grandes con
    icono, no texto plano. Sin letras chicas.
- [x] 19. Cada pregunta explicada en una línea justo bajo su título, no en un párrafo al
    final. "Tolerancia a la fricción: ¿cuánto aguantas bugs, curva de aprendizaje y
    dificultad antes de dejar un juego?". Igual para Plataforma.
- [x] 20. Plataforma: selección múltiple con logo/color de cada una (PC, PlayStation, Xbox,
    Nintendo).
- [x] 21. Nueva pregunta: rango de gasto por juego, con 4 rangos en MXN. Se guarda y se usa en
    las sugerencias.
- [x] 22. Botón de guardar siempre visible (fijo) y confirmación "Perfil guardado y activo".
- [x] 23. Las sugerencias usan TODO el perfil, no solo los géneros: gasto (precio dentro del
    rango), horas (juegos que rinden en sesiones cortas si juega poco), tolerancia
    (menos peso a juegos con motivos de bugs/dificultad si es baja) y plataforma. Se
    recalculan en vivo al cambiar cualquier filtro. Etiqueta: "Sugerencias según tu
    perfil" (no cambian el riesgo del juego).

═══════════════════════════════════════════════════════════════
FASE 6D — Comparar
═══════════════════════════════════════════════════════════════
- [x] 24. Nota al inicio: "Compara hasta 4 juegos lado a lado", visible antes de elegir.
- [x] 25. Juegos sin Metacritic: completar con el sentimiento de las reseñas de Steam que ya
    tenemos (porcentaje positivo y resumen de Steam), con la nota "Sin crítica
    especializada; esto viene de N reseñas de jugadores". Si hay comentarios del público
    en NexPlay, mostrarlos ahí con la misma advertencia.
- [ ] 26. Evaluar una fuente adicional de crítica (OpenCritic u otra con API pública) para los
    juegos sin Metacritic. Propón fuente, licencia y costo antes de integrarla.

═══════════════════════════════════════════════════════════════
FASE 6E — Panorama, Cómo funciona y Fuentes
═══════════════════════════════════════════════════════════════
- [x] 27. Panorama como tablero: cada gráfica con título de una línea (qué se ve) y
    conclusión de una línea; el texto largo detrás de ⓘ; cada gráfica con su fuente.
- [x] 28. Cómo funciona: pasos visuales, una línea por paso, texto largo colapsado.
- [x] 29. Sección "Fuentes" (en Cómo funciona y en el pie): Steam, Metacritic y las que se
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
- **6A, puntos 1, 3, 4 y 5** (2026-09-26), con la paleta que aprobó el dueño:
  - **Fondos (1)**: cada vista pone su color de acción en `data-vista` del armazón
    (inicio cian, explorar y la ficha turquesa, comparar dorado, Nia violeta, perfil rosa,
    panorama lima, historial y Cómo funciona gris azulado). El fondo es solo CSS: brillo
    detrás del contenido, tres capas de estrellas, dos nebulosas del color de la vista,
    rejilla fina y el degradado de `--fondo` a `--fondo-2`. Los alias (`--neon`,
    `--cta-fondo`, `--acento-sistema`) se re-declaran en cada `[data-vista]`: declarados
    solo en `:root`, se resolvían ahí y el menú de Panorama salía cian.
  - **Logo y menú (3 y 5)**: el menú lleva icono en el color de su vista, nombre y una línea
    (Qué es NexPlay, Los N juegos, Hasta 4 lado a lado, Tu asistente, Cómo juegas tú, Lo que
    ya viste, Los datos en gráficas, Método y fuentes). Sin rótulos de grupo, como en el
    mockup: los grupos se separan con un filete y su nombre queda en el `aria-label` de cada
    lista. El logo ocupa el ancho de la barra (231 × 200) en pantallas altas y cede hasta
    146 × 126 a 674 px de alto, que es lo único que se achica para que todo quepa; encogida,
    queda solo la marca, recortada del mismo PNG. El punto de perfil activo pasó a píldora
    con los géneros declarados («Perfil activo · Acción, Rol»), en el rosa de Tu perfil
    porque el verde es del riesgo. El botón de encoger bajó al pie, junto al de tema.
  - **Botones (4)**, en `base.css`: `.boton-cta` con el color de la vista y texto #0B0F1F en
    los dos temas; `.boton-fantasma` en `--superficie-2` con `--borde-control`;
    `.boton-texto` como enlace (cian y subrayado); `.compacto` (pastilla de 44 px) y
    `.tarjeta-accion` (icono, título en mayúsculas, una línea, chevron) con el color de la
    vista a la que llevan (`data-tono`). Hover levanta y enciende el filo, activo se hunde
    con borde interior, deshabilitado pierde el color y el borde pasa a punteado. Los
    cuatro accesos del inicio ya son tarjetas de acción; la acción principal del inicio
    («Buscar un juego →» en tarjeta grande) se hace con el resto del inicio en la 6B.
  - **Contraste**: el recorrido mide ahora 175 pares por tema —toda la paleta, y por vista
    lo que depende del color de acción (botón principal, ítem activo del menú, insignias,
    tarjetas de acción, compactos y el texto sobre la nebulosa en su punto más claro)—, con
    las capas translúcidas compuestas. La primera medición dio 32 pares bajo el mínimo
    (9 en oscuro, 23 en claro). Casi todos eran filetes translúcidos del color de la vista
    (tarjeta de acción al 45 %, compacto y píldora de perfil al 55 %: 1.2 a 2.9:1) y el
    filo de la tarjeta de riesgo en claro, hecho con el color vivo. Se resolvieron con
    filetes opacos: el tono mezclado con la superficie al 60 % en oscuro y al 72 % en claro
    (`--mezcla-filo`), y el filo de riesgo con su tinta (`--banda-*-filo`). El compacto se
    pintaba translúcido y, sobre `--fondo-2` en claro, su texto bajaba a 4.30:1: ahora es
    opaco sobre la superficie. Y el ámbar claro #AC500A, que la paleta anterior daba por
    4.51:1 sobre `--fondo-2`, medido en el navegador da 4.49: pasa a #AA4F0A (4.57).
    Resultado: 0 de 350 pares bajo el mínimo; lo más justo, el filo de riesgo alto en oscuro
    al 60 % que pidió el dueño (3.00:1) y el enlace sobre `--fondo-2` en claro (4.53:1).
  - **Chakra Petch no se estaba cargando en el servidor de desarrollo**: el `ng serve` que
    corría era anterior al cambio de `angular.json`, que no se relee en caliente. Las
    medidas de la 6A anteriores a esta nota se hicieron con la fuente de respaldo; con el
    servidor reiniciado se repitieron todas en este recorrido.
  - El recorrido pasa a las tres resoluciones de la fase (1440, 1024 y 390) en los dos
    temas y guarda lo que se ve al entrar a cada vista en `docs/capturas/angular/vistas/`.
    La prueba de 674 px de alto mide ahora sin perfil, con la píldora de perfil y encogida,
    y que ningún subtítulo del menú se corte.
- **Decisiones del dueño al cerrar la 6A** (2026-09-26): aprueba los ajustes a la paleta
  de la tabla del reporte (tintas claras, ámbar #AA4F0A, estados claros, botón principal
  con el color vivo en claro, `--borde-control` aparte, filetes opacos, nebulosa graduada).
  El botón de tema **se queda al pie del menú como pastilla, sin flotante**. La acción
  principal del inicio («Buscar un juego →» en tarjeta grande) se hace en la **6B**.
- **Mockup 6B** (2026-09-26): medido por la propia página en 1440, 1024 y 390, claro y
  oscuro: 0 contrastes que no pasan (219 textos y filos por tema), sin desborde, letra
  mínima 16 px. Lo que salió al medir: el texto de color (sobrelínea, enlaces, la palabra
  del veredicto en el color del riesgo) puesto directo sobre la nebulosa bajaba a 3.3–3.9:1
  en su punto más claro; la regla aprobada solo cubría `--texto` y `--texto-2`. En el
  mockup ese texto va en etiqueta o en panel. Para el punto 10 hay dos variantes, porque la
  revisión pide el color de la portada en el borde y la paleta aprobada pone ahí el del
  riesgo al 60 %: A (recomendada) conserva la paleta y usa la portada para el halo; B pone
  la portada en el filo, aclarado hasta 3:1.
- **Decisiones del dueño sobre el mockup 6B** (2026-09-26): tarjetas en la variante A,
  más el color dominante de la portada como resplandor detrás de la imagen, siempre
  visible (también en táctil), sin tocar el filo: filo y sombreado son solo del riesgo. La
  regla del texto sobre la nebulosa se aplica en todas las vistas y entra al comprobador.
  «Buscar un juego →» con el campo vacío lleva a Explorar. Los tráileres dejan de pasar
  solos al pasar el cursor o al tocar uno, y solo suena el que la persona activó.
- **6B hecha** (2026-09-26):
  - **Inicio (7, 8)**: la entrada en texto pleno de 22 px con el filo del color de la
    vista; la tarjeta «Buscar un juego» es la única acción principal (vacío → Explorar,
    nombre exacto → su ficha, lo demás → Explorar filtrado; `dominio/busqueda.ts`); salen
    «Ver los 123 juegos» y «Ver el panorama completo». En teléfono: título, buscar,
    entrada, ejemplo. «De dónde salen los datos» abre con las tres fuentes enlazadas
    (appreviews, appdetails, Metacritic).
  - **Explorar (9, 10, 11)**: el título con el tratamiento de la 6A. Seis tráileres arriba
    de los estantes, dos por nivel, los más reseñados en Steam (`dominio/trailers.ts`, con
    `/panorama`, sin tocar la API). Arrancan mudos y pasan solos al terminar; con el cursor
    o el foco encima se quedan, y desde que se toca uno, las flechas o un control, ya no
    pasan solos. Cada tráiler arranca mudo. El escenario es la misma portada ancha de la
    ficha en modo carrusel; en tableta y teléfono la lista pasa a una tira que se desliza
    (a 1024 px, al lado del escenario, ya no cabían el nombre y el nivel). Las tarjetas llevan el filo del riesgo (60 %, 75 % en claro) y
    un velo del color del nivel abajo; detrás, el resplandor del color dominante de su
    portada, calculado en el navegador (las portadas de Steam traen
    `access-control-allow-origin: *`) cuando la tarjeta está por verse, y guardado por
    juego. «Comparar» pasa a compacto dorado.
  - **Ficha (12 a 16)**: «Ver más» solo si el recorte esconde texto (se mide al pintar y
    al cambiar de ancho). La barra del video, siempre a la vista, con fondo propio,
    botones de 48 px y «Tráiler · sin sonido». Con «reducir movimiento» el tráiler no se
    pide solo y un botón «Ver el tráiler» lo trae. El veredicto y la descripción van en un
    panel con el filo y la barra del riesgo. Cada sección es un bloque con icono, título,
    una línea y color propio: motivos cian, factores gris azulado, tu perfil rosa
    (destacado, con lo declarado en chips, tres líneas con icono y «Afinidad · no cambia el
    riesgo»; sin perfil, la tarjeta «Crear tu perfil»), tu opinión azul y comentarios
    turquesa, que ahora es su propio bloque. Comparar y Ver en Steam son compactos; Nia
    lleva su violeta en cualquier vista (su botón principal y sus sugerencias).
  - **Regla del texto sobre la nebulosa**: el recorrido mide cada texto visible de las 9
    vistas, en los dos temas y los tres anchos, contra su fondo real; sin panel, contra el
    punto más claro de la nebulosa. La primera medición encontró 28 fallas, todas en claro:
    el enlace del pie «Metodología» (3.6–4.2:1, pasa a compacto) y el chip elegido de
    Panorama (4.21:1: la letra queda en color de texto y lo elegido lo marca la barra de
    color). La sobrelínea de las vistas va en etiqueta.
  - **Dos fallos previos que salieron al probar**: con la predicción en error, leer su
    valor lanzaba y tumbaba el pintado de toda la ficha (el aviso «No se pudo calcular el
    riesgo» nunca se veía); y sin volumen guardado, `Number(null)` daba 0 y la corredera
    del tráiler arrancaba en cero.
  - **La columna de Nia en la ficha a 674 px de alto**: con los bloques nuevos, el campo
    con «Preguntar» quedaba 49 px por debajo de la ventana (lo detectó el recorrido). Todo
    lo que va entre la cabecera de Nia y el campo se desplaza ahora como un solo bloque
    dentro de la columna, y el campo se queda abajo, a la vista.
- **6B aprobada y subida** (2026-09-26, `77e00d2`). **Pulido anotado por el dueño**, para
  hacerlo sin detener las fases:
  - [ ] P1. Título del inicio: máximo 3 líneas por debajo de 1440 px (bajar un escalón el
    tamaño o acortar a «Descubre qué podría frustrarte en las primeras 2 horas»).
  - [ ] P2. Explorar: el buscador y los chips de género van arriba del escenario de
    tráileres.
  - [x] P3. Ficha: la nota de plataforma («El lado del juego transfiere…») sale del panel
    del veredicto y va a «Por qué te tocaría a ti», en una línea: «Tu plataforma es Xbox;
    el riesgo se calcula con reseñas de Steam.»
  - [ ] P4. El recorrido no debe pisar el perfil guardado del navegador: que use uno propio.
  - [ ] P5. El indicador «Tráiler · sin sonido» solo se muestra con el cursor sobre el video.
  - [ ] P6. Razón de género en las sugerencias, más corta: «Rol · 39 de 123 juegos».
  - [ ] P7. La barra de guardar dice «Cambios sin guardar» cuando lo del formulario difiere
    de lo guardado.
  - [ ] P8. El precio en las razones de las sugerencias, con el mismo formato que el resto
    («$283.00 MXN»).
  - [ ] P9. Las barras de motivos en Comparar no usan dorado (se confunde con el ámbar del
    riesgo medio): el cian de la ficha o un tono que no se parezca al riesgo.
  - [ ] P10. En Comparar, «Segunda opinión» se reduce a la primera oración: motivos y crítica
    ya están en la tabla y en sus bloques.
  - [ ] P11. Las tarjetas de título de cada columna de Comparar no dejan espacio vacío:
    llevan portada o el nombre pasa a encabezado de la primera tarjeta.
- **Mockup 6C** (2026-09-26): medido por la propia página en 1440, 1024 y 390, claro y
  oscuro: 0 contrastes que no pasan (154 textos y filos por tema), sin desborde, letra
  mínima 16 px. Lo que salió de revisar los datos antes de dibujar:
  - Los 123 juegos del catálogo son solo de PC (`plataformas: ['pc']`): la plataforma no
    puede filtrar sugerencias. Se usa en la ficha, en la línea del pulido P3.
  - Las horas sí tienen dato: la mediana de horas jugadas de las reseñas positivas de cada
    juego separa bien a los cortos (A Short Hike 3.8 h, Portal 5.1 h, Unpacking 5.4 h; la
    mediana del catálogo es 33 h). Hay que sumarla a `/panorama`, leyendo la base sin
    tocarla.
  - Tramos de gasto hechos con el catálogo: hasta $200 hay 31 juegos (más 7 gratuitos),
    entre $200 y $500 hay 42, entre $500 y $1,000 hay 32, y más de $1,000 hay 9.
  - simple-icons (CC0) retiró el logotipo de Xbox en su versión 13: las plataformas van
    con iconos propios y el color de cada marca, sin logotipos oficiales.
- **Decisiones del dueño sobre el mockup 6C** (2026-09-26): sí al campo nuevo de
  `/panorama` (mediana de horas en reseñas positivas), también en la ficha técnica como
  «Horas típicas: N h»; el contrato sigue con una plataforma y la nota de la ficha la arma
  el frontend con todas las marcadas; v3 → v4 con los perfiles anteriores activos, la
  píldora «Perfil activo · 1 pregunta nueva» y el gasto «Falta responder». Si el gasto deja
  vacías las sugerencias, se avisa y se relaja el tope; «Ahora no» se recuerda; el gasto va
  «por juego»; P5 se queda en el pulido.
- **6C hecha** (2026-09-26):
  - **API**: `/panorama` suma `horas_al_recomendar` por juego: la mediana de
    `playtime_at_review` de las reseñas positivas, en horas, leída de la base en modo solo
    lectura (None con menos de 10 positivas; hoy los 123 la tienen). Es descriptiva y no
    entra al modelo. La ficha técnica la muestra como «Horas típicas».
  - **Descubrimiento (17)**: invitación en el inicio mientras no haya perfil, con «Ahora
    no» recordado (`nexplay.invitacion-perfil.v1`); la píldora del menú está siempre: sin
    perfil es un enlace punteado «Sin perfil · Crear · 1 min», con perfil dice sus géneros o
    «1 pregunta nueva». En ese caso va en dos renglones y el logo cede 20 px para que la
    barra siga cabiendo en 674.
  - **Formulario (18 a 22)**: seis preguntas en bloques con número, una línea de
    explicación y su estado; las respuestas son tarjetas grandes con icono, nombre, detalle
    y ✓ (la fricción con un medidor). Plataforma de selección múltiple, con iconos propios y
    el color de la marca solo en el icono. Pregunta nueva «Cuánto pagas por juego», en cuatro
    tramos cuyo detalle dice cuántos juegos del catálogo caben. La barra de guardar va fija
    abajo, dice cuántas faltan (las nombra si son una o dos) y, al guardar, «✓ Perfil
    guardado y activo»; en /perfil la burbuja de Nia sube encima de ella.
  - **Sugerencias (23)**: «Sugerencias según tu perfil», etiquetadas «No cambian el riesgo
    del juego», en vivo con lo que se está respondiendo. Géneros (cobertura), gasto (tope,
    gratuitos siempre; si deja la lista vacía, se relaja y se avisa), horas (si juega poco,
    antes los que se recomiendan con menos de 20 h) y fricción (si le pesa, después los que
    se quejan de bugs, rendimiento, dificultad o controles). Cada tarjeta dice sus razones
    —lo que no cumple, en gris— y el riesgo aparte; el riesgo no ordena. La plataforma no
    filtra porque el catálogo es solo de PC; si solo hay consolas marcadas, lo dice. Con el
    catálogo actual el relajo del tope no llega a darse (todos los géneros tienen algo de
    $200 o menos); lo cubren las pruebas de `sugerencias.spec.ts`.
  - **P3**: la nota de plataforma salió del panel del veredicto; «Por qué te tocaría a ti»
    lleva la línea «Juegas en PC y Xbox; el riesgo se calcula con reseñas de Steam.» con
    todas las marcadas (solo si hay alguna consola). A la API sigue viajando una plataforma:
    PC si está marcada y, si no, la primera.
  - El perfil guardado pasa a `nexplay.perfil.v4`; los v3 se migran al leerlos.
- **Mockup 6D** (2026-09-26): medido por la propia página en 1440, 1024 y 390, claro y
  oscuro: 0 contrastes que no pasan, sin desborde, letra mínima 16 px. Datos: 33 juegos del
  catálogo no tienen Metacritic; el total de reseñas de Steam y las positivas ya están en
  `resumen_resenas` (p. ej. Black Myth: Wukong, 94 % de 87,051; WILD HEARTS™, 54 % de
  5,182, «Variadas»). Punto 26, evaluado sin integrar: OpenCritic (crítica propia; por
  RapidAPI, plan gratis de 25 búsquedas y 200 consultas al día; Ultra 19 USD y Mega 50 USD
  al mes; las condiciones de atribución y de guardar datos se leen con la cuenta), IGDB
  (`aggregated_rating`, gratis no comercial, 4 consultas por segundo) y RAWG (su crítica es
  la misma nota de Metacritic y sus términos prohíben guardar los datos). Recomendado:
  OpenCritic, con una corrida previa que solo mida cobertura sobre los 33.
- **Decisiones del dueño sobre el mockup 6D** (2026-09-26): el porcentaje positivo de Steam
  nunca usa los colores del riesgo; la fuente adicional es IGDB (`aggregated_rating`), con
  una corrida de cobertura previa sobre los 33 juegos sin Metacritic: con la mitad o más se
  integra rotulada como fuente secundaria y fuera del modelo, si no se queda solo Steam; el
  bloque «Crítica y público» también en la ficha técnica de los juegos sin Metacritic; con
  Metacritic y Steam a la vez se muestran los dos («Metacritic 82 · Steam 94 % positivas
  (87,051 reseñas)»).
- **6D hecha** (2026-09-26):
  - **API**: `/panorama` suma `positivas_en_steam` por juego (de `resumen_resenas`, leída
    en solo lectura; 122 de 123 la tienen). Descriptivo, no entra al modelo.
  - **Comparar (24)**: la nota «Compara hasta 4 juegos lado a lado», con una línea de qué
    se compara, va arriba siempre, con y sin juegos; el conteo, a su lado en una pastilla.
    La tabla va en un panel.
  - **Sin Metacritic (25)**: la fila de crítica de la tabla dice «Sin crítica especializada ·
    Steam 94 % positivas (87,051 reseñas)» o, con Metacritic, «Metacritic 96 · Steam 84 %
    positivas (647,245 reseñas)». Cada columna suma el bloque «Crítica y público»
    (`compartido/critica-publico.ts`): el porcentaje y el resumen de Steam en español, la
    advertencia «Sin crítica especializada; esto viene de N reseñas de jugadores» y, si hay,
    lo de NexPlay (promedio de estrellas, valoraciones, el último comentario) con la
    advertencia que cuenta valoraciones y comentarios por separado. El porcentaje y su barra
    van en el azul de la opinión; el recorrido comprueba que no coinciden con ningún color
    del riesgo.
  - **Ficha técnica**: la fila de crítica usa la misma línea. En los juegos sin Metacritic
    dice «Sin crítica especializada» y el bloque va dentro de la ficha técnica, sin caja
    propia: como bloque aparte en la columna, le quitaba tanto alto a Nia que su chat
    quedaba casi sin espacio. Lo de NexPlay no se repite ahí: la ficha ya tiene «Tu
    opinión» y «Comentarios».
  - **IGDB (26)**: `herramientas/cobertura_igdb.py` lee `TWITCH_CLIENT_ID` y
    `TWITCH_CLIENT_SECRET` (con pydantic_settings, sin imprimirlas), busca por appid de Steam
    los juegos sin Metacritic y cuenta cuántos tienen `aggregated_rating`; el umbral es 17 de
    33. Con `--guardar` y si pasa, escribe `datos/critica_igdb.json` (archivo nuevo; la base
    no se toca). Primera corrida: faltan las dos variables, así que no se consultó IGDB. La
    integración en la API y en el bloque se hace solo si pasa.
    Segunda corrida (2026-09-26, después del aviso de que ya estaban): tampoco las encuentra;
    `.env` no se ha modificado desde el 2026-09-20 20:45. No se consultó IGDB ni se guardó
    nada.
- **Mockup 6E** (2026-09-26): medido por la propia página en 1440, 1024 y 390, claro y
  oscuro: 0 contrastes que no pasan, sin desborde, letra mínima 16 px. Cifras de hoy, de
  `/panorama` y de la base en solo lectura: riesgo 43 / 37 / 43; riesgo alto por género
  (con 5 juegos o más) de Casual 60 % a Estrategia 15 %; precio mediano $179.49 / $359.00
  / $579.99; 100 de 123 lanzados de 2016 en adelante (2023, el año con más: 18); reseñas
  escritas antes de 2 h, 4 %; señal por nivel 1.02 % / 1.31 % / 4.29 %. Descargas: juegos
  (appdetails, `cc=mx`) y reseñas (appreviews, en inglés, las más recientes) del 14 al 21
  sep 2026. Propone un campo nuevo en `/panorama` con esas fechas, de solo lectura, para
  las tarjetas de Fuentes y el pie.
- **Decisiones del dueño sobre el mockup 6E** (2026-09-26): aprobado. Panorama conserva «Qué
  dice Steam de esos mismos juegos», con la conclusión de los 23 de 43 en riesgo alto con
  reseñas muy positivas. La gráfica sin Metacritic concluye con la evidencia de
  `docs/evidencia/metacritic-por-banda.md`: entre los 90 con nota, la señal sigue subiendo
  por nivel (1.02 → 1.31 → 2.52 %). Fuentes suma una tarjeta «Servicios» para OpenAI (Nia) y
  las tipografías (OFL); IGDB entra como cuarta fuente, «secundaria», solo si pasa la
  cobertura.
- **¿Barras o pastel?** (pregunta del dueño, 2026-09-26): las gráficas se quedan como están.
  Un pastel solo cabe en una parte de un todo con pocas categorías, y aquí:
  - «Cómo se reparte el riesgo» es la única candidata, pero sus tres tajadas (35 / 30 / 35 %,
    126° / 108° / 126°) no se distinguen a ojo, y con el filtro de nivel queda un círculo
    entero. Las barras se comparan por largo y conservan el orden bajo → alto.
  - Géneros, precio, sin Metacritic, gratuitos y señal por nivel son tasas o medianas por
    nivel: no suman 100 %, así que un pastel sería incorrecto.
  - «Qué se menciona» suma más de 100 % (una reseña cae en varias categorías).
  - Años y horas al reseñar son tramos ordenados: un pastel pierde el orden.
  - Steam por nivel y motivo por juego comparan la composición de tres niveles: la barra
    apilada al 100 % ya es la alternativa correcta al pastel.
- **6E hecha** (2026-09-26):
  - **API**: `/panorama` suma `descargas` (`appdetails` y `appreviews`, cada una con `desde` y
    `hasta`), de `descargado_en` de `juegos` y `resenas` en solo lectura: hoy, del 14 al 21
    sep 2026 (UTC).
  - **Panorama (27)**: cuatro cifras clave de toda la muestra (123 juegos, 184,367 reseñas,
    4,126 con señal, 33 sin Metacritic), filtros en panel y doce tarjetas en dos columnas
    (una bajo 900 px). Cada tarjeta trae título, conclusión, ⓘ y fuente. La ⓘ abre el
    texto largo dentro de la tarjeta, sin taparla. Las conclusiones son funciones de
    `dominio/conclusiones-panorama.ts`, con pruebas, y se recalculan con el corte: con
    Estrategia, el reparto dice «Pesa más el riesgo medio: 10 en bajo, 12 en medio y 4 en
    alto». La ⓘ de la gráfica sin Metacritic dice que con nota y en riesgo alto hay 10
    juegos y que esa cifra es una pista, no una conclusión. Los años, en media tarjeta,
    rotulan solo 2004, 2016 y 2026; cada columna dice su cifra al pasar el cursor.
  - **Cómo funciona (28)**: cuatro pasos con el icono y el color del menú, una frase cada
    uno y su texto de antes en «Ver más», cerrado. La metodología queda en tres frases y
    «Leer la metodología completa», cerrado; `#titulo-metodologia` sigue igual.
  - **Fuentes (29)**: `dominio/fuentes.ts` es la lista única que leen el inicio y Cómo
    funciona. Hay tres tarjetas de datos con qué se toma, cuánto y cuándo se descargó, y
    una de Servicios: OpenAI, que recibe la pregunta, la conversación y los datos del juego
    pero no el perfil, y Chakra Petch, Inter y JetBrains Mono, con OFL 1.1 según su
    `package.json`. El pie de todas las vistas dice «Fuentes: Steam (appreviews y
    appdetails) y Metacritic, descargadas del 14 al 21 sep 2026.», con «Ver fuentes →».
  - **De paso**: `PanoramaStore.datos` ya no lanza si `/panorama` falla; el pie lo lee en
    todas las vistas.
