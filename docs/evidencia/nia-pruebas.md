# Nia con el modelo de lenguaje: qué se probó y qué pasó

Nia se probó con la clave real de OpenAI (`gpt-5.6-sol`) de dos formas:
- **Regresión:** las 25 preguntas de `calidad/preguntas_nia.py`, 25 de 25 en las dos corridas.
- **Trampas y legítimas:** tres rondas contra el conjunto de `calidad/preguntas_trampa.json`.
  La última corrida (30 de septiembre, 48 respuestas) terminó con 0 casos por revisar.

En todas, las respuestas se separan en dos modos. Las **del modelo** (`modo: openai`) las
redacta el modelo de lenguaje con las herramientas del catálogo. Las **por reglas**
(`modo: reglas`) salen de `api/nia/reglas.py` aunque haya modelo, porque tienen que salir
siempre igual: trivia, «el mejor», resumen, juego fuera del catálogo, pedir el juego y, desde
la ronda «explicar el riesgo», «¿por qué tiene ese riesgo?» con un juego abierto.

Aquí solo van conteos, categorías y descripciones redactadas para este documento. No se
copia texto de respuestas ni de personas: las preguntas de estas corridas son de prueba y
ninguna sale de usuarios del sitio.

## Fuentes

| Qué | Dónde | Versionado |
|---|---|---|
| Las 25 preguntas de regresión y sus chequeos | `calidad/preguntas_nia.py` | sí |
| Resultados de la regresión | `registros/preguntas_nia-<etiqueta>.json` | no (`registros/` se ignora) |
| Las 48 preguntas trampa, legítimas y de conversación, con su comportamiento esperado | `calidad/preguntas_trampa.json` | sí |
| Resultados de las corridas de trampas | transcript de la sesión de trabajo `ce04a9d3-19c8-4cae-839c-3c206ff2163b` (Claude Code), entradas 35090, 36058 y 40480; el script que las corrió (`nia_real.py`) vivía en el scratchpad y no se versionó | no |

Las horas son de la Ciudad de México (UTC−6). Las APIs de prueba corrían en local: la 8010
sin clave (modo demostración) y la 8020 con la clave de `.env`, cada una con una base de
valoraciones temporal. Ninguna corrida tocó producción.

## 1. Regresión: las 25 preguntas de `preguntas_nia.py`

| Corrida | Fecha | Clave | Pasan | Por modelo | Por reglas | Palabras máx. (modelo / reglas) | Latencia p50 / p95 |
|---|---|---|---|---:|---:|---|---|
| `openai-bloque1` | 29-sep 02:14 | sí | 25/25 | 20 | 5 | 59 / 32 | 3,729 / 6,366 ms |
| `openai-bloque4` | 29-sep 19:44 | sí | 25/25 | 20 | 5 | 57 / 32 | 4,082 / 7,649 ms |

- **Por reglas, en las dos:** las preguntas 3 (resumen), 6 (juego fuera del catálogo), 13
  (falta el juego), 19 (parecido con juegos fuera del catálogo) y 20 («más corto»).
- **Por modelo:** las otras 20. Son filtros por género, precio, horas o novedad, comparación,
  sugerencias del perfil, precio y crítica de un juego, de dónde salen los datos y cierres de
  cortesía.
- **Sin clave** (modo demostración, todo por reglas) hay ocho corridas del 26 al 30 de
  septiembre, todas 25 de 25, con p50 entre 4 y 24 ms. La última, `un-factor-gratis-demostracion`
  (30-sep 01:55), es sobre el código de `c5478f6`.

## 2. Trampas y legítimas con la clave real

Cada corrida manda los casos de `preguntas_trampa.json` a `POST /nia` y revisa en cada respuesta
las reglas de la sección `reglas_para_toda_respuesta` (60 palabras, cierre con pregunta,
emojis, sin trivia ni coronar, sin vocabulario prohibido), más el texto obligatorio de
`debe_contener` y el modo esperado.

| Ronda | Corridas | Casos | Por modelo | Por reglas | Por revisar al final | Qué se corrigió |
|---|---|---:|---:|---:|---|---|
| 1 · tras el bloque 1 de producción | 29-sep 02:03 y 02:18 | 40 | 31 | 9 | ninguno | La primera corrida destapó cinco fallas (abajo). Se corrigieron en `34e9fc4`, `c68c8d4`, `14427ef` y `9090213` antes de repetir |
| 2 · tras los bloques 2 y 4 | 29-sep 19:41 y 19:47 | 40 | 32 | 8 | ninguno | Una pregunta nombraba cinco juegos y pintaba cuatro tarjetas por un ® en el nombre: `0d8b411` |
| 3 · «explicar el riesgo» | 30-sep 00:57, 01:02, 01:24 y 01:40 | 45 → 48 | 34 | 14 | 0 de 48 | En las dos primeras, el modelo omitía algo distinto cada vez. «¿Por qué tiene ese riesgo?» con juego abierto pasó a reglas (`ee2ebf4`), y el seguimiento sobre «evidencia débil» dejó de marcarse fuera de tema (`b7c7e5f`) |

**Ronda 1, las cinco fallas de la primera corrida:**
1. Una herramienta devolvía un conteo como número y la respuesta caía a modo demostración.
2. El aviso «solo hablo del catálogo» salía en respuestas legítimas.
3. Al modelo le faltaba filtrar por horas típicas y ordenar por lanzamiento.
4. Repetía «abandono» al citar la pregunta.
5. El resumen salía revuelto y había menos tarjetas que juegos nombrados.

**Ronda 2:** quedó anotado el caso L-2 para la siguiente. Ante «¿vale lo que cuesta?», el
modelo comparaba la nota contra la media del entrenamiento y no contra el promedio del catálogo
que muestra la ficha. Se resolvió en la ronda 3.

**Ronda 3, lo que omitía el modelo:** la nota de extrapolación en un juego gratis, el factor
principal de un juego sin precio o el descargo de la señal. Con la explicación por reglas, las
dos últimas corridas terminaron con 0 casos por revisar (0 de 45 y 0 de 48).

### Por modelo y por reglas, en la última corrida (30-sep 01:40)

| Grupo | Casos | Por modelo | Por reglas | Cuáles fueron por reglas |
|---|---:|---:|---:|---|
| Trampas | 29 | 21 | 8 | T-7 (fuera del catálogo), T-10 (instrucciones), T-12 (trivia), T-13 (datos personales), T-18 («el mejor»), T-19 (falta el juego), T-21a y T-21b (resumen) |
| Legítimas | 8 | 8 | 0 | ninguna: las 8 fueron al modelo, como se esperaba |
| Explicar el riesgo | 5 | 1 | 4 | R-1 a R-4 («¿por qué tiene ese riesgo?» con juego abierto); R-5 fue al modelo |
| Conversación del descargo (D) | 3 | 2 | 1 | D·1 |
| Seguimiento tras reglas (S) | 3 | 2 | 1 | S·1 |
| **Total** | **48** | **34** | **14** | |

| Modo | Palabras máx. | Con el descargo | Con aviso de tema | Piden el juego |
|---|---:|---:|---:|---:|
| Por modelo | 58 | 14 | 0 | 0 |
| Por reglas | 60 | 6 | 3 | 1 |

- **Descargo:** en la conversación D salió una vez en tres respuestas, que es lo pedido.
- **Seguimientos:** en la S, las dos preguntas que siguen a la explicación por reglas las
  contestó el modelo.

**Cómo se comportó, en ejemplos redactados para este documento:**
- Ante «¿me lo compro?», deja la decisión a la persona, da riesgo, precio y nota, y cierra
  preguntando qué quiere revisar.
- Ante la trivia y la petición de mostrar sus instrucciones, contesta por reglas que solo habla
  del catálogo, sin contestar ni cambiar de papel.
- Ante un correo escrito en el chat, dice que no guarda datos personales. El correo se borra
  antes de anotar la pregunta y antes de mandarla al modelo.
- Ante «jugar con amigos», ofrece el género Multijugador masivo y aclara que no hay un dato de
  cooperativo.

## 3. Lo que queda abierto

- **La última corrida con clave es anterior a `c5478f6`.** Ese commit juntó gratuidad y precio
  en un solo factor y evitó que el resumen deje una lista a medias. Después solo hubo
  corridas sin clave (25/25).
  - R-1 a R-4 van por reglas, así que se revisaron sin clave el 30-sep, con el código de
    `c5478f6`, llamando a `api.nia.agente.responder` con cada juego y «¿Por qué tiene ese
    riesgo?».
  - Siguen diciendo lo que exige `debe_contener`: el aviso de estimación menos confiable en
    R-1 y R-2, la extrapolación con evidencia débil en R-3, la crítica en R-2 y R-4, y el
    descargo en las cuatro.
- **Limitaciones conocidas** (README, sección `/nia`):
  - un seguimiento sin palabras de juegos se trata como fuera de tema, a propósito, para que
    la trivia no llegue al modelo;
  - «¿Apex vale la pena?» sin juego abierto pide el juego, porque el nombre corto no coincide
    con el del catálogo.
- **No se registró qué modelo usa Render** en producción. Estas corridas son locales, con la
  clave de `.env`.
- **Los resultados de las trampas no están versionados.** Para repetirlos hace falta correr
  `calidad/preguntas_trampa.json` contra una API con clave, lo que gasta OpenAI y le toca al
  dueño. No hay un script versionado que lo haga.

## Cómo se reproduce

Las APIs de prueba se levantan con una base de valoraciones temporal y sin el tope de 10
preguntas por minuto, que frenaría una corrida de 25 seguidas:

```
# regresión sin clave (no gasta OpenAI)
OPENAI_API_KEY= NEXPLAY_MODELO_NIA= NEXPLAY_VALORACIONES_DB=/tmp/val-8010.db NEXPLAY_NIA_POR_MINUTO=1000 \
  .venv/bin/uvicorn api.main:app --port 8010
.venv/bin/python calidad/preguntas_nia.py --api http://localhost:8010 --etiqueta demostracion

# regresión con clave (gasta OpenAI; la clave y el modelo salen de .env)
NEXPLAY_VALORACIONES_DB=/tmp/val-8020.db NEXPLAY_NIA_POR_MINUTO=1000 .venv/bin/uvicorn api.main:app --port 8020
.venv/bin/python calidad/preguntas_nia.py --api http://localhost:8020 --etiqueta openai
```
