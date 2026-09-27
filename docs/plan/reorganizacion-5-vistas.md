# Reorganización: de 9 vistas a 5

> Rama: `reorganizacion-5-vistas`, creada desde `barra-lateral-y-tema` en `6144ce7`.
> Estado: paso 0 hecho; mockup del Inicio esperando visto bueno.

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

- [ ] Cinco entradas, en ese orden, con el color de cada vista que ya existe.
- [ ] Quita del menú Panorama, Cómo funciona e Historial.
- [ ] Las rutas /panorama, /como-funciona y /historial redirigen: /panorama y
  /como-funciona a /#metodologia (el panel del pie del Inicio), /historial a
  /perfil#actividad. Así no se rompe ningún enlace viejo.

## R2 — Inicio nuevo, de arriba abajo

- [ ] 1. Título + una línea ("Descubre qué podría frustrarte en las primeras 2 horas") y el
   buscador como acción principal. Igual que hoy.
- [ ] 2. "Qué encontramos": tres tarjetas grandes, cada una con una cifra y una frase,
   calculadas desde /panorama (no escritas a mano):
   - "43 de 123": juegos con riesgo alto de arrepentimiento.
   - Mediana de precio alto vs bajo ("$580 vs $179"): los de riesgo alto cuestan
     el triple que los de riesgo bajo.
   - "23 de 43": juegos de riesgo alto con reseñas muy o extremadamente positivas en
     Steam. Frase: "La crítica general no ve lo que pasa en las primeras dos horas."
     Esta va al final del trío.
- [ ] 3. "Cómo lo sabemos": una franja de cuatro cifras en una línea: 123 juegos ·
   184,367 reseñas · 4,126 con señal de arrepentimiento · probado con 40 juegos que
   el modelo no vio. También desde la API.
- [ ] 4. Pie: la línea de fuentes con fecha y un botón "Ver metodología" que abre un panel
   desplegable (ancla #metodologia) con las tres tarjetas de metodología y las
   tarjetas de fuentes y servicios que ya existen en Cómo funciona. Reutiliza esos
   componentes, no los reescribas.
- [ ] Se quitan del Inicio: las cuatro tarjetas de "Qué puedes hacer aquí" y el bloque
  largo de "De dónde salen los datos".
- [ ] La invitación a crear perfil (6C) se queda.

## R3 — Perfil absorbe Historial

- [ ] Al final de Perfil, una sección "Tu actividad" (ancla #actividad) con lo que hoy
  muestra Historial y su botón de borrar. Plegada por defecto.

## R4 — Lo que no cambia

- [ ] Explorar, la ficha, Nia y Comparar quedan como están.
- [ ] Las gráficas de Panorama que no pasan al Inicio no se borran del repo: sus
  componentes se quedan sin ruta. Anota en el plan que su lugar es el reporte escrito
  y docs/evidencia/.

## VERIFICACIÓN

- [ ] npx ng test --watch=false y build sin advertencias.
- [ ] capturar_ui.py adaptado a 5 vistas + ficha, en 1440, 1024 y 390, dos temas:
  contraste, nebulosa, letra mínima 16 px, barra a 674 px sin scroll.
- [ ] Comprueba las tres redirecciones y que las cifras del Inicio coincidan con curl a
  /panorama.
- [ ] Mide el alto del Inicio antes y después, y cuántas palabras tiene.

- [ ] Muéstrame primero un mockup del Inicio nuevo (como en la fase 6) y espera mi visto
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
