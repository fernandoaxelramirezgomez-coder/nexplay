# Reorganización: de 9 vistas a 5

> Rama: `reorganizacion-5-vistas`, creada desde `barra-lateral-y-tema` en `6144ce7`.
> Estado: Etapa B hecha (`fc310c5`, sin push). Etapa C (Inicio de negocio): el carrusel con
> Nia, la etiqueta y los cuadritos ya están en la app. El resto del mockup
> `docs/plan/mockups/r2-inicio-negocio.html` espera visto bueno.

Mensaje completo del dueño, tal como llegó, con una casilla por punto:

---

Cambio de rumbo por la exposición: el profesor pide 5 minutos y vamos a reorganizar
la app de 9 vistas a 5. Antes de tocar nada, guarda lo actual:

## PASO 0 — Guardar lo que hay

- [x] 1. En barra-lateral-y-tema, haz commit de cualquier cambio pendiente (incluido el plan)
   con el mensaje "chore: cierre de la fase 6F antes de reorganizar vistas".
   *No había nada pendiente: la 6F y su plan ya estaban en `31af7a4`, así que no se hizo
   un commit vacío.*
- [x] 2. Push de barra-lateral-y-tema y confirma con git ls-remote que el remoto coincide
   con HEAD. *`31af7a4`, igual en el remoto.*
- [x] 3. En docs/plan/fase-6-revision-usuario.md anota: "Pausado: búsqueda web (37), IGDB
   (26, pendiente de credenciales), corridas con IA antes/después y pulido P1–P13.
   Se retoma después de la reorganización." Commit y push de eso también. *`6144ce7`,
   igual en el remoto.*
- [x] 4. Crea la rama nueva desde ahí: git switch -c reorganizacion-5-vistas y súbela con
   git push -u origin reorganizacion-5-vistas.
- [x] 5. Guarda este mensaje completo como docs/plan/reorganizacion-5-vistas.md con una
   casilla por punto, y commitéalo en la rama nueva.

## OBJETIVO

Pasar de 9 vistas a 5, una por minuto de la exposición, en este orden de menú:
1. Inicio  2. Explorar (+ ficha)  3. Nia  4. Comparar  5. Perfil

Panorama, Cómo funciona e Historial dejan de ser vistas del menú. No se borra código
de datos ni de la API: /panorama sigue existiendo porque el Inicio lee de ahí.

## R1 — Menú

- [x] Cinco entradas, en ese orden, con el color de cada vista que ya existe.
- [x] Quita del menú Panorama, Cómo funciona e Historial.
- [x] Las rutas /panorama, /como-funciona y /historial redirigen: /panorama y
  /como-funciona a /#metodologia (el panel del pie del Inicio), /historial a
  /perfil#actividad. Así no se rompe ningún enlace viejo.

## R2 — Inicio nuevo, de arriba abajo

- [x] 1. Título + una línea ("Descubre qué podría frustrarte en las primeras 2 horas") y el
   buscador como acción principal. Igual que hoy.
- [x] 2. "Qué encontramos": tres tarjetas grandes, cada una con una cifra y una frase,
   calculadas desde /panorama (no escritas a mano):
   - "43 de 123": juegos con riesgo alto de arrepentimiento.
   - Mediana de precio alto vs bajo ("$580 vs $179"): los de riesgo alto cuestan
     el triple que los de riesgo bajo.
   - "23 de 43": juegos de riesgo alto con reseñas muy o extremadamente positivas en
     Steam. Frase: "La crítica general no ve lo que pasa en las primeras dos horas."
     Esta va al final del trío.
- [x] 3. "Cómo lo sabemos": una franja de cuatro cifras en una línea: 123 juegos ·
   184,367 reseñas · 4,126 con señal de arrepentimiento · probado con 40 juegos que
   el modelo no vio. También desde la API.
- [x] 4. Pie: la línea de fuentes con fecha y un botón "Ver metodología" que abre un panel
   desplegable (ancla #metodologia) con las tres tarjetas de metodología y las
   tarjetas de fuentes y servicios que ya existen en Cómo funciona. Reutiliza esos
   componentes, no los reescribas.
- [x] Se quitan del Inicio: las cuatro tarjetas de "Qué puedes hacer aquí" y el bloque
  largo de "De dónde salen los datos".
- [x] La invitación a crear perfil (6C) se queda.

## R3 — Perfil absorbe Historial

- [x] Al final de Perfil, una sección "Tu actividad" (ancla #actividad) con lo que hoy
  muestra Historial y su botón de borrar. Plegada por defecto.

## R4 — Lo que no cambia

- [x] Explorar, la ficha, Nia y Comparar quedan como están.
- [x] Las gráficas de Panorama que no pasan al Inicio no se borran del repo: sus
  componentes se quedan sin ruta. Anota en el plan que su lugar es el reporte escrito
  y docs/evidencia/.

## VERIFICACIÓN

- [x] npx ng test --watch=false y build sin advertencias.
- [x] capturar_ui.py adaptado a 5 vistas + ficha, en 1440, 1024 y 390, dos temas:
  contraste, nebulosa, letra mínima 16 px, barra a 674 px sin scroll.
- [x] Comprueba las tres redirecciones y que las cifras del Inicio coincidan con curl a
  /panorama.
- [x] Mide el alto del Inicio antes y después, y cuántas palabras tiene.

- [x] Muéstrame primero un mockup del Inicio nuevo (como en la fase 6) y espera mi visto
  bueno. Después ejecuta, commit en reorganizacion-5-vistas, y detente en el ALTO sin
  hacer push hasta que lo valide.

---

## Decisiones del dueño sobre el plan (2026-09-26)

1. **La primera tarjeta de «Qué encontramos» deja de ser «43 de 123»**, porque sale del
   propio corte: los niveles son tercios del score. Queda **«4.2×»**: «Los juegos de riesgo
   alto tienen 4 veces más reseñas de arrepentimiento temprano que los de riesgo bajo
   (4.29 % vs 1.02 %). El modelo no vio esas reseñas para asignar el riesgo.» Se calcula
   desde la API. El trío va en este orden: 4.2×, más del triple de precio y 23 de 43.
2. **El carrusel de ejemplo se queda.**
3. **El panel de metodología vive en el pie global** y se abre igual desde cualquier vista.
   Dentro lleva la línea «Los niveles bajo/medio/alto son tercios del score del modelo.»

## Notas de ejecución

- **Precio:** la razón de las medianas es 3.23 ($579.99 contra $179.49). La frase se
  calcula y dice «más del triple».
- **De dónde sale cada cifra:** los niveles y los precios viven en `/catalogo`; las
  reseñas y el consenso de Steam, en `/panorama`. Todo se calcula en la API.
- **«40 juegos que el modelo no vio»:** para que salga de la API, `/panorama` suma los
  metadatos del modelo que trae `modelo/nexplay.pkl`, en solo lectura. Son 123 del
  catálogo menos 83 de entrenamiento.
- **Medida de antes** (el Inicio de hoy, tema oscuro, `registros/inicio-antes.json`):

  | Ancho | Alto del documento | Palabras en el contenido | Palabras en el pie |
  |---|---|---|---|
  | 1440 | 2,507 px | 489 | 24 |
  | 1024 | 3,025 px | 489 | 24 |
  | 390 | 4,426 px | 483 | 24 |

- **Mockup** (2026-09-26), medido por la propia página en 1440, 1024 y 390, claro y
  oscuro: 0 contrastes que no pasan, sin desborde, letra mínima de 16 px. Cifras
  recalculadas con la API:
  - señal en riesgo alto 4.29 % y en bajo 1.02 % (razón 4.19, «4.2×»);
  - medianas de precio $579.99 y $179.49 (razón 3.23, «más del triple»);
  - 23 de 43 juegos de riesgo alto con reseñas muy o extremadamente positivas;
  - 123 juegos, 184,367 reseñas, 4,126 con señal, y 40 = 123 − 83 que no vio el modelo.

## Antes de la tarjeta del 4.2× (pedido del dueño, 2026-09-26)

El mismo cociente (señal en riesgo alto / señal en riesgo bajo), por corte
(`docs/evidencia/senal-por-nivel.md`, `senal_por_nivel.py`):

| Corte | Bajo: juegos · con señal / reseñas | Alto: juegos · con señal / reseñas | Cociente |
|---|---|---|---:|
| Catálogo (123) | 43 · 664 / 64,896 (1.02 %) | 43 · 2,732 / 63,675 (4.29 %) | 4.19× |
| data-v1 (83) | 30 · 298 / 45,198 (0.66 %) | 30 · 2,030 / 44,076 (4.61 %) | 6.99× |
| Externos (40) | 13 · 366 / 19,698 (1.86 %) | 13 · 702 / 19,599 (3.58 %) | **1.93×** |

En los 40 que el modelo nunca vio queda debajo de 2× (intervalo por juegos 0.87×–3.50×).
Por la regla del dueño, la tarjeta usa **4.2×** con la frase «El modelo asigna el riesgo con
datos del juego, sin leer las reseñas».

## Etapa B hecha (2026-09-26)

- **API:** `scoring.ficha_del_modelo()` y `/panorama.modelo` (versión, `data-v1`, 83 juegos,
  123,972 reseñas), leídos del artefacto en solo lectura. «40 que el modelo no vio» es 123 − 83.
- **R1:**
  - Menú de cinco (Inicio, Explorar, Nia, Comparar, Tu perfil) en una sola lista.
  - `/panorama` y `/como-funciona` → `/#metodologia`; `/historial` → `/perfil#actividad`,
    con `redirectTo` a una función.
- **R2:**
  - «Qué encontramos» (`inicio/hallazgos.ts`) y «Cómo lo sabemos»
    (`inicio/como-lo-sabemos.ts`) se calculan en `dominio/hallazgos-inicio.ts`, con pruebas.
  - Salieron `inicio/accesos.ts` y `inicio/fuentes-datos.ts`; su lista de fuentes sigue en
    `dominio/fuentes.ts`.
  - El pie de todas las vistas tiene «Ver metodología», que despliega ahí mismo
    `como-funciona/metodologia.ts` (sacado de Cómo funciona, con la línea de los tercios) y
    `como-funciona/fuentes.ts`, tal cual.
  - La ficha: «Cómo calculamos esta estimación» abre ese panel sin salir de la ficha.
- **R3:** «Tu actividad», plegada al final de Tu perfil, con `app-historial` incrustado (sin
  su título de página) y su botón de borrar.
- **R4:** los componentes de Panorama (`panorama/*`) y la página de Cómo funciona quedan en
  el repo sin ruta. **Su lugar es el reporte escrito y `docs/evidencia/`**: ahí van las
  gráficas que no pasaron al Inicio.
- **Medida del Inicio** (`registros/inicio-antes.json` → `registros/inicio-despues.json`):

  | Ancho | Alto antes | Alto después | Palabras antes | Palabras después |
  |---|---:|---:|---:|---:|
  | 1440 | 2,507 px | 1,825 px (−27 %) | 489 | 262 (−46 %) |
  | 1024 | 3,025 px | 2,439 px (−19 %) | 489 | 262 |
  | 390 | 4,426 px | 3,241 px (−27 %) | 483 | 256 |
- **Recorrido completo:** salida 0, ninguna línea PROBLEMA; `/nia` pedido 11 veces, 11
  interceptadas y 0 en la API. Menú de cinco, cifras del Inicio iguales a `/catalogo` +
  `/panorama`, las tres redirecciones con su sección abierta, contraste de 175 pares por
  tema, nebulosa y letra de 16 px o más en las 5 vistas, la ficha y los 2 paneles, y la barra
  en 674 px sin scroll.

## Etapa C: un Inicio que venda (pedido del dueño, 2026-09-26)

«Siento que es mucha información, perdemos al usuario por tanto contexto; piénsalo como un
negocio. Los apartados se ven amontonados.»

- **Diagnóstico:**
  - dos titulares compiten (el `h1` en 5 líneas y «BUSCAR UN JUEGO» en mayúsculas);
  - 7 bloques con borde separados por el mismo aire;
  - tarjetas con 4 textos cada una;
  - dos llamadas a la acción seguidas.
- **Propuesta** (mockup `r2-inicio-negocio.html`):
  - la búsqueda dentro del encabezado, con los atajos «Prueba con» (el más reseñado en
    Steam de cada nivel: Team Fortress 2, Terraria y HELLDIVERS™ 2);
  - «Qué encontramos» y «Cómo lo sabemos» en un solo panel: tres cifras de una línea y una
    línea de confianza con «Ver metodología»;
  - el perfil al final;
  - 88 px entre zonas.
- **Medido en el mockup:**
  - 176 palabras con el carrusel (hoy 262, −33 %);
  - alto estimado ~1,300 px (hoy 1,825);
  - la búsqueda y los atajos terminan a ~500 px de 900 (1440) y ~660 de 844 (390);
  - el título, la búsqueda y las tres cifras caben en la primera pantalla a 1440×900;
  - 0 contrastes que no pasan, sin desborde, letra mínima de 16 px.
- La meta de 150 palabras no se alcanza con el carrusel (36 palabras). Bajar de ahí pide
  quitar la sobrelínea y acortar la invitación al perfil de la 6C: decisión del dueño.
- **Pedidos directos (2026-09-26), ya en la app sin commit:**
  - la etiqueta del Inicio dice «🎮 Segunda opinión»;
  - bajo la descripción, los cuadritos Gratis · Sin registro · <1 minuto · 123 juegos
    (`dominio/ofertas-inicio.ts`, con pruebas; «Confidencial» no va, porque las preguntas a
    Nia se guardan 180 días).
- **El carrusel del Inicio con Nia** (pedido directo, 2026-09-26; ya en la app, sin commit).
  Primero se propuso en el mockup como «Así opina Nia». El dueño lo pidió en el carrusel de
  verdad («Así se ve una segunda opinión») y dio el título: «Análisis crítico con nuestra
  asistente Nia», con otra letra y limpio.
  - `inicio/carrusel-ejemplo.ts`:
    - título en la letra del texto (18 px, sin mayúsculas ni mono), con «Nia» en su
      violeta;
    - las flechas y la posición pasan al pie del panel;
    - por diapositiva: la mascota del nivel, tu pregunta con la portada chica, el globo de
      Nia (el mismo `globo-nia` del resto del sitio), la píldora de riesgo, «Ver su ficha»
      y «Seguir con Nia» (`/nia?appid=`).
  - Las cuatro diapositivas van apiladas en la misma celda y solo se ve la activa. El
    panel mide lo que la más larga, así que no brinca al rotar: el alto es el mismo en las
    cuatro a 1440, 1280, 1024, 768 y 390.
  - Se quedan la rotación de 7 s, la pausa con el ratón o el foco, «reducir movimiento» y
    los `data-testid` de los controles.
  - Una sola petición por visita, `GET /nia/opiniones`. Sin opiniones queda tu pregunta
    con «Pregúntale a Nia →».
  - Prueba de componente `inicio/carrusel-ejemplo.spec.ts`.
  - En el recorrido, `_angular_carrusel` comprueba por diapositiva la mascota del nivel,
    la pregunta, que la opinión nombre el riesgo de `/catalogo` y los enlaces. También que
    el carrusel no hace ninguna consulta al chat (POST /nia).
- **La opinión de Nia** (lo que se propuso en el mockup):
  - la mascota del nivel del juego (`nia/ficha-bajo|medio|alto.png`, que no se usaban) y
    su opinión corta, con «Ver su ficha» y «Seguir con Nia»;
  - la opinión sale de la regla `nia_reglas.opinion_corta` por
    `GET /nia/opiniones?appids=…` (hasta 6, validado): sin modelo de lenguaje y sin
    guardar nada;
  - ejemplo: «WILD HEARTS™ tiene riesgo alto 😬 Tiende a generar más arrepentimiento
    temprano que el resto del catálogo; en sus reseñas negativas lo que más sale es
    rendimiento. ¿Te cuento más?».
- **Medida del mockup con todo:**
  - 194 palabras (hoy 262, −26 %);
  - alto estimado ~1,400 px;
  - el botón de búsqueda termina a ~490 px de 900 (1440), ~400 de 1366 (1024) y ~655 de
    844 (390);
  - 0 contrastes que no pasan, sin desborde, letra de 16 px o más.

### «¿Por qué elegir NexPlay?» en lugar de «Buscar un juego» (pedido del dueño, 2026-09-26)

«Donde dice Buscar un juego, cambiarlo por la funcionalidad de nuestro sitio, lo que nos
diferencia de otros sitios, y mostrar nuestras herramientas: que diga por qué elegir.»

- **Decisión del dueño:** el buscador sale del Inicio; para buscar está Explorar.
- **Mockup** `docs/plan/mockups/r3-por-que-elegir.html`:
  - una línea con la diferencia: «Steam te da una nota general; NexPlay mira las primeras
    dos horas, justo la ventana de reembolso.»;
  - una tarjeta destacada, «Riesgo en las primeras 2 horas», con la aclaración de señal
    comparativa y la única acción principal del Inicio, «Explorar los 123 juegos →»;
  - cuatro herramientas como enlaces enteros, con el color y el icono de su vista:
    - Por qué se arrepienten (la ficha de WILD HEARTS™);
    - Nia, tu asistente;
    - Compara lado a lado;
    - Encaja contigo.
- **Medido en el mockup** (1440, 1024 y 390, claro y oscuro):
  - 0 desbordes y 0 contrastes que no pasan;
  - letra mínima de 16 px;
  - la sección tiene 110 palabras y la tarjeta que reemplaza tenía 32, así que el Inicio
    pasaría de 287 a unas 365.
- **Punto abierto:** la invitación al perfil queda debajo y repite «Encaja contigo».
- **Respuesta del dueño:** «sigue con el punto 2 primero y luego vemos cómo queda a ver si
  lo dejamos así». La invitación sale del Inicio; el largo se revisa viéndolo en la app.
- **En la app** (sin commit hasta el ALTO):
  - `dominio/herramientas-inicio.ts`, con pruebas: la destacada, la diferencia y las
    cuatro herramientas;
  - `inicio/por-que-elegir.ts`;
  - salen `inicio/invitacion-perfil.ts` y `dominio/busqueda.ts` (con su prueba), que ya
    nadie usaba, y la entrada `pausado` del carrusel, que era para el buscador;
  - el teléfono deja el orden forzado: sin el buscador, el orden natural es el bueno;
  - «2 horas» con espacio que no se corta;
  - en el recorrido, `_angular_6b` comprueba una sola acción principal, que lleva a
    `/explorar` con el número de `/catalogo`, los enlaces de las cuatro herramientas y
    que ya no hay buscador. `_angular_6c` comprueba que la invitación salió y que
    «Encaja contigo» lleva a `/perfil`.
- **Medida en la app:**
  - la sección tiene 116 palabras;
  - el Inicio pasa de 287 a 348 palabras;
  - de alto mide 2,026 px a 1440, 2,921 a 1024 y 3,954 a 390;
  - sin desborde ni errores de consola en los dos temas.
- **Ajustes del dueño sobre la app:** «déjalo un poco más abajo, centra el texto y que
  separe el texto de arriba con una nave de Star Wars apuntando hacia abajo, y que si le
  dan clic haga scroll hacia esta sección»; después, «¿no estaba el Halcón Milenario?».
  - No hay emoji del Halcón Milenario (Unicode no tiene naves de Star Wars). Se probó
    un dibujo en SVG y el dueño prefirió el cohete: «mejor deja el cohete».
  - Queda 🚀 girado 135° para que apunte hacia abajo, en un botón de 64 px en medio de
    una línea que se desvanece a los lados. Baja y sube dos veces al cargar (4.8 s) y se
    queda quieto: una animación infinita distrae y WCAG 2.2.2 pide poder detener lo que
    se mueve más de 5 s. Con «reducir movimiento» no se mueve.
  - Al tocarlo, la sección sube hasta 24 px del borde en escritorio y hasta 72 px en el
    teléfono (debajo de la barra fija), y el foco pasa al título.
  - El título y la línea de la diferencia van centrados.
  - El recorrido (`_angular_6b`) comprueba que el clic deja la sección arriba de la
    pantalla.
- **El buscador vuelve** (pedido del dueño): «separa más Qué encontramos del texto de
  arriba… tráete la búsqueda abajo, deja las 4 etiquetas… pon una frase adelantando al
  usuario». Después precisó: «no, arriba de Qué encontramos, pero que cubra todo el
  renglón, haz un diseño bonito».
  - La banda va a todo lo ancho, entre «¿Por qué elegir NexPlay?» y «Qué encontramos», y
    hace de separación entre las dos.
  - Lleva la lupa, el título «¿Estás por comprar un juego?» (en la letra de los títulos,
    con el degradado), «Búscalo y mira su riesgo de arrepentimiento temprano antes de
    pagar.» y el campo con «Buscar →» a la misma altura.
  - El fondo tiene un resplandor cian (Inicio) y violeta (Nia).
  - «Buscar →» vuelve a ser la única acción principal; «Explorar los 123 juegos →» pasa a
    secundaria.
  - Vuelven `dominio/busqueda.ts` y su prueba. El recorrido vuelve a probar los tres
    destinos del buscador.
  - El cohete flota sin parar, como pidió el dueño, y se detiene con el cursor o el foco.
    En el recorrido el clic va forzado, porque Playwright espera a que el botón se quede
    quieto.
  - Medido:
    - 372 palabras en el Inicio;
    - alto de 2,565 px a 1440, 3,443 a 1024 y 4,555 a 390;
    - sin desborde ni errores de consola.

### Explorar (pedidos del dueño, 2026-09-26)

- **Título:** «Encuentra tu próximo juego». Primero se probó «Explora por riesgo»; el dueño
  dijo que el de antes, «Explora por género y nivel de riesgo», eran muchas palabras.
- **Tráileres:** sale la barra «Tráiler N de 6 · dos por nivel…» con sus flechas, porque
  «no se ve bien» y la lista ya deja elegir cualquiera. Qué tráiler se ve se sigue
  anunciando, solo para el lector de pantalla.
- **Separación:** una nave 📚 debajo de los tráileres, igual que el 🚀 del Inicio. Al
  tocarla baja a «¿Qué juego estás pensando comprar?», que ahora es un título centrado,
  con el buscador al centro y los géneros debajo.
  - Los dos usan el componente compartido `compartido/separador-nave.ts`.
- **Géneros:** van en un panel «Filtra por género», en una rejilla de tarjetas iguales.
  - Cada tarjeta lleva su emoji (Acción 💥, Aventura 🗺️, Carreras 🏎️, Rol 🧙…) y cuántos
    juegos tiene. Eso vive en `dominio/generos.ts`, con pruebas.
  - El elegido se rellena con el color de la vista, no uno por género: los colores del
    riesgo ya están en cada tarjeta.
  - En el teléfono, una tira que se desliza.
- **Pie:** en `/explorar` va sin «Ver metodología», solo con la línea de fuentes. La
  ficha lo conserva porque lo abre desde sus factores.
- **Recorrido:**
  - los tráileres eligen el siguiente en la lista, sin flechas;
  - la nave 📚 baja a la búsqueda;
  - el pie trae «Ver metodología» en todas las vistas menos `/explorar`.
- **La nave 📚 en la primera pantalla** (pedido del dueño): el título va en un renglón y
  un poco más chico que en las otras vistas; la lista de tráileres, más compacta
  (miniaturas de 96 px); y en tableta el video no pasa del alto que deja ver la nave.
  - Medido: la nave termina a 674 px de 900 (1440), 644 de 768 (1366), 625 de 800 (1280),
    742 de 768 (1024) y 721 de 844 (390).
- **Dos arreglos que salieron en el recorrido:**
  - El « juegos» oculto de cada género se posicionaba respecto a la página y la tira del
    teléfono no lo recortaba, así que la página se desplazaba 1,900 px a lo ancho. Ahora
    cada tarjeta lo contiene (`position: relative`).
  - El armazón empezaba con la ruta del router, que dice «/» hasta terminar la primera
    navegación, y el pie de Explorar alcanzaba a mostrar «Ver metodología». Ahora parte
    de la dirección real (`Location.path()`).
- **Géneros sin salto y de a varios** (pedido del dueño: «eligiendo el género te
  scrollea arriba, eso no debe pasar, y te debe dejar seleccionar más de un género»).
  - **El salto:** lo causaba `scrollPositionRestoration: 'enabled'`, que sube en cada
    navegación, y cada filtro del catálogo (cada género y cada tecla) es una navegación.
    Ahora `desplazamiento.ts` sube al principio solo al cambiar de pantalla. Atrás y
    adelante devuelven la posición guardada, y las anclas las sigue bajando el router.
  - **Varios géneros:** `?genero=Acción,Rol`. Basta con tener uno de los elegidos, así
    que Acción + Rol trae los de acción y los de rol. «Todos» limpia la selección y el
    panel avisa «(puedes elegir varios)».
  - Probado: Acción y Rol → 91 de 123, la página se queda en su lugar, teclear tampoco
    la mueve, la ficha abre arriba y atrás vuelve a donde estaba.

### Habla con Nia (pedido del dueño, 2026-09-26)

«Hay demasiado texto, sintetízalo y mejora el diseño; quita las advertencias y que si el
usuario se desvía del tema diga esas advertencias, no antes; que pueda o no seleccionar un
texto que pueda preguntar; y anima a Nia.»

- **Menos texto:**
  - arriba solo el título y «Pregúntale por cualquiera de los 123 juegos.»;
  - el panel dice «Elige un juego (opcional)», sin las frases de antes;
  - el saludo va en una línea;
  - la intro del chat de la ficha también va en una línea y sin advertencia.
- **Las advertencias solo fuera de tema:**
  - salen «Nia responde solo con los datos del catálogo» y «No escribas datos
    personales…» fijos;
  - la API marca `fuera_de_tema` cuando la pregunta no encaja con nada del catálogo. La
    marca sale de las reglas del modo demostración, también con IA, sin llamar a ningún
    modelo;
  - solo entonces Nia dice, dentro de su respuesta: «Solo hablo de los juegos del
    catálogo y no te digo si comprarlos o no. No escribas datos personales: tus preguntas
    se guardan 180 días.»
  - De las 25 preguntas de la 6F, la regla marca solo la 22 («¿qué juego me ayuda a
    estudiar la naturaleza?»). Las 25 pasan en demostración, con la API de prueba en
    :8010 sin clave y su base en el scratchpad.
- **Si la respuesta es con IA o sin ella:** ahora es una etiqueta junto al contador («Con
  IA» / «Sin IA · demostración»), no un aviso.
- **Preguntas para tocar:** se quedan las fichas de arranque («¿Qué juegos de acción
  tienen riesgo bajo?», «¿Hay algo gratis?», «¿De dónde salen los datos?»). Son
  opcionales: se puede escribir directo.
- **Nia animada:** flota sobre un halo violeta. Mientras responde cambia a su cara de
  pensar («…») y se mece; al terminar vuelve a saludar. Con «reducir movimiento» queda
  quieta.

### «Qué encontramos», rediseñado para el negocio (pedido del dueño, 2026-09-26)

«No me gusta y no me dice nada al negocio; quiero que el usuario solo tenga en cuenta la
información que necesita y aporte a la vista; menos texto y dale espacio.»

- **Mockup** `docs/plan/mockups/r4-antes-de-pagar.html`:
  - el título «Antes de pagar, esto importa»;
  - tres cifras grandes con una línea cada una:
    - 4.2× más señal de arrepentimiento temprano en los de riesgo alto;
    - 3× más caros son los de riesgo alto: pagar más no te protege;
    - 53 % de los de riesgo alto tienen reseñas muy positivas: la nota no basta;
  - al pie del mismo panel, una línea de confianza con «Ver metodología»;
  - se queda la frase acordada: el riesgo sale de datos del juego, sin leer las reseñas.
- **Medido:**
  - 56 palabras, contra 128 de hoy («Qué encontramos» y «Cómo lo sabemos»);
  - 0 desbordes y 0 contrastes que no pasan en 1440, 1024 y 390, claro y oscuro.
  - La primera versión tenía la línea de confianza sobre la nebulosa y su enlace no
    pasaba en claro (3.90:1); ahora va dentro del panel.
- **Para decidir:** si «Cómo lo sabemos» sale como sección aparte (propuesta) o se queda
  en una fila debajo.
- **Cambio del dueño sobre el mockup:** pidió verlo en gráficas dinámicas con los datos
  reales. Eligió una gráfica de barras con pestañas y un histograma de precios por
  nivel, con botones para ver uno a la vez.
  - **En la app** (sin commit hasta el visto bueno):
    - `inicio/antes-de-pagar.ts`, en lugar de «Qué encontramos» y «Cómo lo sabemos»;
    - `inicio/histograma-precios.ts`;
    - el dominio en `dominio/antes-de-pagar.ts`, con pruebas, y `positivosPorBanda` en
      `dominio/panorama.ts`;
    - salen `hallazgos.ts`, `como-lo-sabemos.ts` y `dominio/hallazgos-inicio.ts`.
  - **Pestañas** (bajo · medio · alto):
    - Señal: 4.2×, con 1.02 % · 1.31 % · 4.29 %;
    - Precio: 3×, con $179 · $359 · $580;
    - Reseñas positivas: 53 %, con 93 % · 97 % · 53 %.
  - **Histograma** (Gratis, <200, 200–400, 400–600, 600–900, 900+):
    - todos: 7 · 31 · 36 · 12 · 17 · 18;
    - riesgo alto: 3 · 4 · 14 · 2 · 7 · 12.
  - **Lo dinámico:**
    - las barras y las columnas crecen al entrar en pantalla;
    - al cambiar de pestaña o de nivel se animan;
    - cada columna da su detalle con el cursor o el foco;
    - con «reducir movimiento», todo es instantáneo.
  - El recorrido (`_angular_5_vistas`) compara cada pestaña, el histograma y el filtro
    «Alto» con la API.
- ALTO hasta el visto bueno.

### «Fuentes» del panel de metodología (pedido del dueño, 2026-09-26)

«Rediseña esta parte, es mucho texto y se ve encimado» (las cuatro tarjetas de Fuentes y
la línea del entrenamiento, en el panel «Ver metodología» del pie).

- **Una fila por fuente:** quién y de qué (Steam · reseñas, Steam · datos del juego,
  Metacritic · crítica), qué da en una línea, cuánto (184,367 reseñas · 123 juegos · 90
  de 123 juegos), la fecha de descarga y su enlace. Las columnas van alineadas, sin
  tarjetas dentro del panel. En el teléfono, cada fuente en bloque.
- **Servicios**, en una línea cada uno. OpenAI: «redacta las respuestas de Nia con tu
  pregunta y los datos del juego; tus respuestas del perfil no salen del navegador y el
  riesgo no pasa por ella». Las tipografías, con su licencia SIL OFL.
- **El entrenamiento**, en una línea: data-v1, 83 juegos y 123,972 reseñas, y los otros
  40 son la prueba.
- **El título**, con el mismo estilo que «Metodología».
- **Medido:** de 221 a 133 palabras y de 673 a 402 px de alto a 1440, sin desborde.
- **Recorrido:** `_angular_5_vistas`, `_angular_como_funciona` y
  `_angular_letra_y_vocabulario` corridas solas, 0 problemas.
- ALTO hasta el visto bueno, junto con las gráficas.

### La ficha, con aire (pedido del dueño, 2026-09-26)

«Mejora el diseño, que no se vea muy apretado» (la ficha de Terraria).

- **Entre bloques:** 28 px en lugar de 20, 32 px entre columnas y más relleno en el
  veredicto.
- **Dentro de los bloques:** 28/32 px de relleno y 20 px entre partes. `.bloque` (base.css)
  toma el relleno y el hueco de variables CSS, que la ficha sube. Comparar, que también
  usa `.bloque`, queda igual.
- **Qué mueve esta estimación:** más espacio entre factores.
- **Ficha técnica:** un dato por renglón, con una línea fina entre ellos.
- **El chat de Nia en la ficha:** un poco más de relleno.

### El pie, solo en el Inicio (pedido del dueño, 2026-09-26)

«Quita la metodología y el mensaje "Fuentes: Steam (appreviews y appdetails) y
Metacritic, descargadas…" de todos lados, excepto el Inicio.»

- El armazón muestra el pie solo en la vista del Inicio (`conPie` en `app.ts`); el pie
  vuelve a no tener excepciones.
- «Cómo calculamos esta estimación», de la ficha, lleva a `/#metodologia`: el Inicio con
  el panel abierto, como ya hacían `/panorama` y `/como-funciona`.
- **Recorrido:**
  - el pie está en el Inicio y en ninguna otra vista ni en la ficha;
  - el enlace de la ficha abre el panel en el Inicio;
  - «Tu actividad» cuenta como a la vista si queda entera en pantalla, porque sin pie
    Perfil ya no da para subirla hasta arriba.
- **Lo que destapó quitar el pie:** en la ficha, a 674 px de alto, la columna derecha
  mide 642 px. Con una ficha técnica larga (WILD HEARTS, con su resumen de Steam), al
  chat de Nia le quedaban 24 px, y el campo y el botón se salían por abajo.
  - Antes pasaba por suerte: el pie empujaba la columna hacia arriba al final del scroll.
  - Ahora el chat tiene prioridad y no baja de 340 px. La ficha técnica cede y, en
    pantallas bajas, se desplaza dentro de su recuadro.
  - Medido a 1280×674: el botón queda en y=585 en WILD HEARTS y en Terraria.
