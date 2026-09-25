# Referencia visual: entorno índigo con acentos neón

Segunda referencia de estilo del frontend, posterior a [referencia-estilo.md](referencia-estilo.md).
Aquella daba el sistema (plano, sin sombras, tipografía y ritmo); esta cambia el **ambiente**: de
un gris pizarra neutro a un índigo profundo con acentos neón, para que la app se lea como algo de
videojuegos y no como un panel de administración.

El punto de partida es la guía de estilo de Discord, con dos desvíos deliberados:

- **El color de marca no es el blurple**: el acento es un cian neón, y las bandas de riesgo
  aportan el verde, el ámbar y el magenta. Eso da la lectura "neón" sin importar una identidad
  ajena.
- **Se mantiene el plano**: sin gradientes de sección y sin sombras de elevación. La única
  excepción es un resplandor corto (`--resplandor`) en foco y en estado activo, que no simula
  altura sino energía.

## Lo que se tomó de la referencia

- Un solo ambiente oscuro de punta a punta, sin franjas claras alternadas.
- Titulares en mayúsculas, peso 800 y tracking negativo, leídos como bloques macizos.
- El color de marca reservado a la acción, nunca como fondo de un área grande.
- Fog (`#babcd9`) como color del texto secundario sobre oscuro, en vez de un gris neutro.
- Radios generosos y una escala de espacio de 4px, que ya coincidían con el sistema anterior.

## Lo que no se tomó

| De la referencia | Por qué no |
|---|---|
| Ilustración 3D y mascotas flotando entre secciones | No hay ese material y no se va a producir; las portadas de Steam ya son la imagen. |
| Tarjetas de sección con gradiente propio | Rompe la regla de "sin gradientes" y aquí las secciones no compiten por identidad. |
| Titulares de 56–61px en todas las secciones | Solo el titular del hero usa el tamaño display; el resto bajaría la densidad de una app que se lee, no que se navega. |
| Interlineado de 0.86 en titulares | En español, los acentos de una MAYÚSCULA en la segunda línea chocan con la primera. El sistema usa 1.05. |
| Blurple `#5865f2` como acento único | Es la marca de otro producto. El cian neón cumple el mismo papel. |

## Contraste medido (WCAG)

Página `#0e0f2d`, tarjeta `#181a3a`, tarjeta en hover `#22254c`.

| Par | Razón | Mínimo |
|---|---|---|
| texto `#f2f3ff` sobre página | 16.9:1 | 4.5 |
| texto `#f2f3ff` sobre tarjeta | 15.3:1 | 4.5 |
| meta `#babcd9` sobre tarjeta | 9.0:1 | 4.5 |
| meta `#babcd9` sobre tarjeta en hover | 7.9:1 | 4.5 |
| borde de control `#6d72a8` sobre página | 4.1:1 | 3.0 |
| borde de control `#6d72a8` sobre tarjeta en hover | 3.2:1 | 3.0 |
| neón `#22e0ff` sobre tarjeta | 10.6:1 | 4.5 |
| texto oscuro sobre el CTA neón | 11.7:1 | 4.5 |
| texto oscuro sobre banda baja `#3df2a7` | 12.9:1 | 4.5 |
| texto oscuro sobre banda media `#ffc53d` | 11.8:1 | 4.5 |
| texto oscuro sobre banda alta `#ff4d97` | 6.0:1 | 4.5 |
| banda alta como texto sobre tarjeta | 5.4:1 | 4.5 |

El único par que no llega es el relleno del estado activo (`#242a63`) contra la tarjeta: 1.3:1.
Por eso nunca va solo — siempre lo acompaña el borde neón, que sí da 10.6:1, además de una marca
de verificación en las opciones del perfil. Es la misma regla que ya existía con el índigo
anterior, con un borde que ahora contrasta mucho más.

## Sin cajas: el lienzo es la superficie

Segunda pasada del rediseño. Se quitaron los 14 paneles con fondo y el recuadro de cada chip,
porque el texto quedaba encerrado en recuadros dentro de recuadros. La regla que los reemplaza:

> **Una superficie con fondo solo existe cuando encierra una portada o flota sobre el contenido.**

Se quedan con fondo la tarjeta del catálogo, la columna de `/comparar` y el panel flotante de Nia.
Todo lo demás es lienzo, y la jerarquía la dan tres señales: un filete de 1px, el aire entre
secciones y un rótulo en mayúsculas pequeñas con tracking positivo.

**Dónde vive el filete.** No en cada sección, sino en el contenedor (`.pila-separada > * + *`).
Varias secciones viven dentro de un componente y, con la encapsulación de Angular, el padre no
puede alcanzarlas: lo que sí puede tocar son sus hijos directos, que son los elementos del
componente. Con `:first-child` la línea aparecía y desaparecía según si la sección estaba escrita
en la plantilla o venía de otro componente.

**Chips y opciones sin recuadro.** El área clicable se conserva con padding y lo elegido se marca
con una barra de 2px en `::after` —para que el texto no se mueva al aparecer— más la palomita en
las opciones del perfil. Contraste medido:

| Par | Razón | Mínimo |
|---|---|---|
| chip en reposo (`#babcd9`) sobre la página | 10.0:1 | 4.5 |
| chip en reposo sobre tarjeta | 9.0:1 | 4.5 |
| chip al pasar el cursor (`#f2f3ff`) | 16.9:1 | 4.5 |
| chip activo (`#22e0ff`) | 11.7:1 | 4.5 |
| barra del chip activo | 11.7:1 | 3.0 |
| barra del hover (`#6d72a8`) | 4.1:1 | 3.0 |
| opción del perfil elegida | 11.7:1 | 4.5 |
| rótulo de sección y botón terciario | 10.0:1 | 4.5 |

**Botones: tres variantes y nada más.** Primario de relleno neón con texto índigo, secundario con
borde, terciario solo texto. Misma forma de píldora y el mismo movimiento; al presionar bajan 1px
y encienden el resplandor.

**Titulares en caja normal.** Las mayúsculas se mudaron al rótulo de sección. El del inicio es el
único que usa el tamaño display, con un subtítulo al peso 300 debajo.

**El logo respira**: flota 3px y su halo cian late en un ciclo de 6s. Con
`prefers-reduced-motion: reduce` queda quieto (la regla global lo deja en 0.01 ms), y eso se
verifica en el script de capturas con un contexto aparte.

## Iconos

El pulgar del voto y de las reacciones es un trazo propio
(`src/app/compartido/icono-pulgar.ts`), no un emoji: el emoji depende de una fuente que no todos
los sistemas traen y en Linux sin fuente de emoji salía un cuadro. El pulgar hacia abajo es el
mismo dibujo girado media vuelta.

## Tema claro y barra lateral

La navegación vive en una **barra lateral** de 240 px con dos grupos —`PRINCIPAL` y
`TRANSPARENCIA`—, el ítem abierto con fondo propio (`--acento-sistema` más filo neón) y, al
pie, el interruptor de tema. En escritorio se encoge a 64 px, que es la columna de íconos con
su área de toque de 44; el nombre no se borra del DOM, se esconde con la técnica de
`.solo-lector` y vuelve como `title`. Por debajo de 900 px la barra es un cajón que entra desde
la izquierda con velo, se cierra al navegar, con `Escape`, con el velo o con su X, y mientras
está abierto la página queda `inert` para que el tabulador no se escape detrás del velo.

Los cortes de dos y tres columnas del catálogo, la ficha y comparar pasaron de `@media` a
`@container`: con la barra abierta la ventana sigue siendo ancha aunque al contenido le queden
736 px, y con un `@media` el hero se rompía y comparar sacaba una barra de scroll horizontal.

**El tema claro no es el oscuro invertido.** Cada valor se midió contra los tres fondos claros
(lienzo `#f6f7fb`, tarjeta `#ffffff`, hover `#eceff8`) y se eligió el primer tono que pasa:

| Token | Claro | lienzo | tarjeta | hover | Mínimo |
|---|---|---|---|---|---|
| `--texto` | `#14173d` | 16.1:1 | 17.2:1 | 15.0:1 | 4.5 |
| `--texto-meta` | `#4d5178` | 7.1:1 | 7.6:1 | 6.6:1 | 4.5 |
| `--borde-control` | `#7f83aa` | 3.4:1 | 3.7:1 | 3.2:1 | 3.0 |
| `--neon` | `#0b6f8c` | 5.4:1 | 5.7:1 | 5.0:1 | 4.5 |
| `--banda-bajo-texto` | `#0d7a52` | 5.0:1 | 5.4:1 | 4.7:1 | 4.5 |
| `--banda-medio-texto` | `#8a5a00` | 5.5:1 | 5.9:1 | 5.2:1 | 4.5 |
| `--banda-alto-texto` | `#c0136a` | 5.5:1 | 5.9:1 | 5.2:1 | 4.5 |

Se descartaron por medición `#8b8fb4` para el borde de control (2.9:1 contra el lienzo) y
`#0e7f9e` para el acento (4.3:1 sobre el hover de tarjeta).

**Los rellenos cromáticos no cambian de color**: el cian del botón primario y las tres bandas
son el mismo hex en los dos temas, con texto tinta encima (11.7, 12.9, 11.8 y 6.0:1). Lo que
cambia es que en claro llevan un filo de 1 px de su tinta, porque el borde del relleno contra el
papel da 1.4, 1.5 y 2.9:1 y un control pide 3:1. En oscuro ese filo vale el color del propio
relleno, así que no se ve y la caja mide lo mismo (el relleno baja 1 px de padding).

**El resplandor cambia de luz emitida a contorno.** El cian tiene menos luminancia que el papel,
así que sobre blanco un halo aditivo *baja* el brillo y se lee como suciedad. En claro
`--resplandor` pasa a un anillo sólido más una sombra suave, y los halos de sprite se escalan con
`--halo-radio` (a la mitad) y `--halo-alfa` (0.62) en vez de reescribirse uno por uno.

El tema se guarda en `localStorage` y la primera vez toma `prefers-color-scheme`; sin preferencia
declarada se queda en oscuro. Un script de cinco líneas en `index.html` pone el atributo
`data-tema` antes de que Angular pinte, para que no haya destello. Los 22 pares de contraste se
vuelven a medir en cada corrida de `herramientas/capturar_ui.py`, sobre los tokens que el
navegador resolvió, en los dos temas.
