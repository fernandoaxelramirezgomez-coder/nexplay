# Reorganización: de 9 vistas a 5

> Rama: `reorganizacion-5-vistas`, creada desde `barra-lateral-y-tema` en `6144ce7`.
> Estado: paso 0 hecho (`fa448e3`). Mockup aprobado. Etapa B hecha; ALTO sin push.

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
