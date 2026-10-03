# api/

La API en FastAPI: contrato estable, lógica delgada. Se levanta con `make api` desde la raíz, o desde
`backend/` con `uvicorn api.main:app --reload`, y responde en http://localhost:8000.

- `main.py`: los endpoints. `schemas.py`: entradas y salidas en Pydantic; todo lo que entra se valida ahí.
- `scoring.py`: carga `modelo/nexplay.pkl` y calcula el riesgo, los factores y los motivos.
- `catalogo.py` y `panorama.py`: el catálogo y su panorama, cargados una vez al arrancar desde
  `datos/nexplay.db`.
- `valoraciones.py`: calificaciones, comentarios y votos a Nia, en su propia base (`datos/valoraciones.db`).
- `config.py` (las variables del `.env` de la raíz) y `limites.py` (topes por minuto, en memoria).
- `nia/`: el chat de Nia. `agente.py` arma el contexto y habla con el modelo de lenguaje, `reglas.py`
  responde por reglas (con o sin modelo) y `herramientas.py` es lo que el modelo puede consultar del
  catálogo.

No va aquí: el entrenamiento (`modelado/`), el análisis (`analisis/`) ni los scripts de revisión
(`calidad/`).

## Contrato

El esquema completo lo sirve la propia API en `/docs` (Swagger) y `/openapi.json`. Aquí va lo que el
esquema no dice: qué significa cada campo y por qué está así.

### `GET /catalogo?q=`

Busca juegos por nombre. Sin `q`, devuelve el catálogo completo.

### `POST /perfil`

Recibe el formulario de alta declarado por el jugador y devuelve el perfil derivado.

**Request** (`FormularioAlta`):

```json
{
  "compras_al_anio": 3,
  "horas_por_semana": 6,
  "tolerancia_friccion": 3,
  "tags_preferidos": ["roguelike", "singleplayer"],
  "tags_rechazados": ["pvp", "pay to win"],
  "plataforma": "pc"
}
```

`tolerancia_friccion` es una escala 1 (nula tolerancia) a 5 (muy alta).

**Response** (`PerfilJugador`): `tolerancia_friccion` normalizada a `baja`/`media`/`alta`,
más `segmento` (`novato`/`veterano`) y `disponibilidad` (`baja`/`media`/`alta`),
todas derivadas por heurística.

### `POST /prediccion`

Recibe el perfil derivado (el que devolvió `/perfil`) más un `appid`, y devuelve el
riesgo con los tres factores que más lo movieron. El riesgo es del título (modelo
`conjunto='juego'`): el perfil se acepta por compatibilidad y solo aporta la nota de
plataforma; ningún dato suyo mueve el score.

**Request** (`SolicitudPrediccion`): `{ "perfil": {...}, "appid": 1245620 }`

**Response** (`PrediccionRiesgo`):

```json
{
  "appid": 1245620,
  "riesgo": 0.42,
  "nivel": "medio",
  "modelo_version": "logreg-compra-2026-09-16",
  "nota_plataforma": null,
  "factores": [
    {
      "etiqueta": "cobertura de crítica especializada",
      "valor_relativo": "bajo",
      "contribucion": 1.33,
      "direccion": "aumenta"
    },
    {
      "etiqueta": "precio del juego",
      "valor_relativo": "alto",
      "contribucion": 0.2,
      "direccion": "aumenta"
    },
    {
      "etiqueta": "compras declaradas por año",
      "valor_relativo": "bajo",
      "contribucion": -0.07,
      "direccion": "reduce"
    }
  ]
}
```

`nivel` (`bajo`/`medio`/`alto`): los cortes entre bajo, medio y alto están en los percentiles 33.3 y
66.7 de las estimaciones fuera de pliegue del entrenamiento; en el catálogo quedan 43, 37 y 43. No es
un umbral de probabilidad fijo: `class_weight="balanced"` hace que `riesgo` ordene, no que sea una
probabilidad calibrada.

`factores`: las tres variables del modelo con mayor contribución absoluta al score
(coeficiente × valor estandarizado), en lenguaje claro. `contribucion` está en unidades
de log-odds: no se traduce a probabilidad ni tiene una escala intuitiva; sirve para
comparar factores entre sí, no como número a mostrar suelto. En los juegos gratis, la
gratuidad y el precio (0) dicen lo mismo y tiran en sentidos opuestos, así que salen como un
solo factor, «gratuidad del juego», con los dos aportes sumados y evidencia débil. Que el
modelo extrapola en los gratis (en el entrenamiento había solo 2) lo dice `avisos`.

`nota_plataforma` viene poblada cuando el perfil declara una plataforma distinta de
`pc`, aclarando que no existe fuente de entrenamiento propia para PlayStation/Xbox/
Nintendo (el lado del juego transfiere, pero la señal viene de reseñas de Steam).

### `GET /estado`

El sistema de un vistazo, para la vista de Administración (`/admin`):

```json
{
  "nia_con_openai": true,
  "modelo_nia": "gpt-4.1-mini",
  "datos_release": "data-v3",
  "juegos_catalogo": 123,
  "modelo_version": "logreg-juego-2026-10-01",
  "modelo_datos": "data-v1",
  "modelo_juegos_entrenamiento": 83
}
```

Solo booleanos, versiones y conteos, y sin consultas a la base: todo está en memoria, y el release se lee una
vez al arrancar de la marca que deja `preparar_entorno.py` (`datos/nexplay.db.origen.json`; sin ella,
`datos_release` es `null`). De OpenAI solo dice si hay clave y qué modelo usa Nia (el valor de
`NEXPLAY_MODELO_NIA`): la clave nunca sale ni se escribe en los logs. Como es barato, también sirve para saber si Render ya despertó.

### `GET /panorama`

Cuántas reseñas hay detrás del catálogo, de cuándo son y cuántas traen la señal, más los motivos agregados
y una fila por juego. Es descriptivo: sale de contar la base, no de predecir, así que ninguna cifra de aquí
es un score. Se calcula una vez al arrancar (`panorama.py`) y necesita la tabla `resumen_resenas`, que
trae data-v3.

### `GET /explicacion/{appid}`

Motivos de insatisfacción más frecuentes en las reseñas de arrepentimiento temprano
(`Y=1`) de ese juego, por conteo de palabras clave por categoría (rendimiento, bugs,
dificultad, controles, contenido, precio), sin modelo de lenguaje.

**Response** (`ExplicacionJuego`):

```json
{
  "appid": 1938010,
  "nombre": "WILD HEARTS™",
  "n_casos": 325,
  "pct_clasificados": 0.6554,
  "motivos": [
    { "motivo": "rendimiento", "frecuencia": 0.86 },
    { "motivo": "bugs", "frecuencia": 0.25 },
    { "motivo": "dificultad", "frecuencia": 0.09 }
  ]
}
```

`n_casos` es cuántas reseñas `Y=1` se analizaron; `pct_clasificados`, qué proporción de
esas menciona al menos una de las seis categorías. `frecuencia` se calcula sobre las
reseñas clasificadas, no sobre `n_casos`: con cobertura parcial, dividir sobre el total
se ve engañosamente bajo. Con menos de 5 casos `Y=1`, `motivos` viene vacío: no hay
muestra para decir algo confiable.

### Valoraciones y comentarios de la segunda opinión

Viven en `datos/valoraciones.db`, aparte de `nexplay.db`. La identidad es un id anónimo
que genera el navegador y guarda en `localStorage`: **identifica, no autentica**.

- `GET /valoraciones/{appid}?usuario=` → `{ appid, promedio, total, mia }`. El promedio
  y el total son públicos (`promedio` es `null` si nadie ha calificado); `mia` es la
  calificación de quien pregunta, de 1 a 5, o `null`.
- `PUT /valoraciones/{appid}` con `{ usuario, calificacion }` → crea o cambia la
  calificación (uno por persona y juego). `calificacion` es un entero de 1 a 5: `0`, `6`,
  `3.5` o `"3"` devuelven 422. `DELETE` con `?usuario=` la quita.
- `GET /comentarios/{appid}?usuario=` → hilo público, del más viejo al más nuevo. Cada
  entrada trae `id`, `texto`, `creado`, `actualizado`, `editado`, `reacciones`,
  `reaccione_mia` y `es_mio`. **Nunca devuelve el id de quien escribió**: de esa identidad
  solo sale `es_mio`, que es la comparación contra quien pregunta. Sin `usuario` el hilo
  se lee igual, pero nada viene marcado como propio. Máximo 100.
- `POST /comentarios/{appid}` con `{ usuario, texto }` (hasta 500 caracteres) → agrega uno
  al final. Pasado el tope por minuto responde 429 con `Retry-After`.
- `PUT /comentarios/{appid}/{id}` con `{ usuario, texto }` → cambia el texto, marca
  `editado` y guarda la fecha del cambio en `actualizado`; `creado` no se toca, porque es
  cuándo apareció en el hilo. **403** si el comentario es de otra persona, 404 si no
  existe en ese juego.
- `DELETE /comentarios/{appid}/{id}?usuario=` → lo borra con todo y sus reacciones.
  **403** si es de otra persona.
- `PUT /comentarios/{appid}/{id}/reaccion` con `{ usuario }` → pulgar arriba en toggle:
  una fila por persona y comentario, y si ya estaba se quita. Devuelve
  `{ comentario_id, reacciones, reaccione_mia }`. Tiene su propio tope por minuto
  (`NEXPLAY_REACCIONES_POR_MINUTO`, 30), más alto que el de publicar porque es un clic.

Los tres últimos se apoyan en el mismo id anónimo, así que **no son control de acceso**:
impiden el accidente, no a quien mande el id de otra persona a propósito.

### `POST /nia`

El chat de Nia, con un juego (`appid`) o sobre el catálogo entero. Recibe
`{ usuario, appid?, mensajes, sugerencias?, generos? }`: hasta 40 mensajes, los tuyos de 500
caracteres como máximo y los de Nia de 1,500. Al modelo solo llegan los últimos 10 turnos.
Devuelve `{ respuesta, modo, modelo, aviso, juegos, oferta, pide_juego, fuera_de_tema, … }`.

`oferta` es la pregunta con que cierra la respuesta, como dato: `{ intencion, juegos, criterio?,
pregunta? }`, con la intención de una lista cerrada (`riesgo`, `resenas`, `ordenar`, `buscar`…).
El chat la devuelve dentro del mensaje de Nia en el historial, junto con `juegos` (los de sus
tarjetas, hasta 8); los mensajes de la persona no pueden llevar ninguno de los dos. Con eso,
«sí», «cuéntame» o «dale» cumplen lo ofrecido, y «esos dos» sabe cuáles eran; los dos casos se
contestan con reglas aunque haya modelo. Si responde el modelo, su pregunta final se cambia por
una de esas ofertas.

`generos` son los géneros que la persona declaró en su perfil (hasta 12). Sirven para decir
cuáles coinciden con un juego («¿encaja conmigo?»). No mueven el riesgo ni se guardan aparte,
y ningún log los escribe. Si Nia responde con IA, viajan a OpenAI junto con la pregunta.
Del resto del perfil no viaja nada: solo las sugerencias que el navegador ya calculó.

`modo` dice de dónde salió la respuesta: `openai` (el modelo), `demostracion` (sin clave,
por reglas) o `reglas`. Este último es cuando hay clave pero la respuesta no pasa por el
modelo porque tiene que ser siempre la misma: pedir el juego, resumir la conversación, no
coronar «el mejor», no contestar preguntas que no son de juegos y explicar por qué un juego
abierto tiene su riesgo («¿por qué tiene ese riesgo?»), con el factor que más aporta, su
evidencia y los avisos.

**Limitación conocida.** Un seguimiento sin palabras de juegos, como «¿Y eso es mucho?», se
trata como fuera de tema y se contesta con reglas: el detector de temas ajenos mira solo la
pregunta, no la conversación. Se deja así a propósito: si mirara la conversación, la trivia a
mitad de un hilo («¿cuál es la capital de Francia?») llegaría al modelo.

El backend arma el contexto con los datos reales de ese juego, ya como hechos en palabras:
- los factores del modelo como ideas («cuesta casi el triple de lo normal del catálogo»),
  con qué tan firme es cada uno;
- las quejas en conteos, no en porcentaje;
- Metacritic, el precio y los géneros;
- si llegan los géneros declarados, cuáles coinciden y cuáles no.

El prompt de sistema fija el vocabulario del proyecto ("arrepentimiento temprano" y nunca
"abandono", señal proxy, bandas en vez de probabilidades, nada de recomendar comprar o no
comprar) y la regla de redacción: primero la respuesta, sin etiquetas ni jerga, y el emoji
acorde al nivel de riesgo.

Sin `OPENAI_API_KEY` o sin `NEXPLAY_MODELO_NIA`, y también si la llamada falla, responde
en **modo demostración**: la misma información armada con reglas, marcada como tal en la
respuesta y en pantalla.

**Para probar el modo con OpenAI real:** pon la clave y el modelo en el `.env` de la raíz, reinicia la
API y hazle a Nia una pregunta *fuera de las reglas*, por ejemplo "¿me lo recomiendas?" o
"¿lo compro?". La respuesta debe describir los datos y devolver la decisión a quien
pregunta, sin recomendar la compra. Es la forma de confirmar que el prompt de sistema
también frena al modelo real, no solo al modo demostración.

### `GET /nia/opiniones?appids=`

La opinión corta de Nia sobre hasta 6 juegos (`appids` separados por coma), para el carrusel del Inicio.
Sale de las reglas del chat con los datos del catálogo: sin modelo de lenguaje y sin guardar nada. Un
appid que no está en el catálogo se omite.

### `PUT` y `DELETE /nia/valoracion/{id_respuesta}`

El 👍 o 👎 a una respuesta de Nia. El 👎 puede llevar uno de los motivos de una lista fija; con 👍 el motivo
se ignora. Se guarda en `datos/valoraciones.db` con el mismo id anónimo y tiene su propio tope por minuto
(`NEXPLAY_VOTOS_NIA_POR_MINUTO`, 30). Qué se guarda y cuánto tiempo, en `docs/evidencia/valoraciones-nia.md`.

Con el motivo «otro motivo», el 👎 puede llevar además una `sugerencia`: qué mejorar, hasta 280 caracteres.
Antes de guardarla se le quitan correos y teléfonos, y se borra con el voto a los 180 días, igual que la
pregunta.

### `GET /nia/sugerencias`

El buzón de sugerencias de `/admin`: cuántos 👍 y 👎 recibió Nia, los 👎 por motivo (con «sin motivo» al
final) y las 10 sugerencias de texto más recientes, con su fecha. No trae el usuario ni la pregunta: `/admin`
no tiene contraseña, así que todo lo que sale aquí lo puede ver cualquiera.

**Para verificar a Nia**, desde `backend/`:

```bash
python calidad/verificar_nia.py              # contexto, reglas, votos y los casos de producción; sale 1 si algo falla
python calidad/preguntas_nia.py --api http://localhost:8000 --etiqueta prueba   # las 25 preguntas contra una API levantada
```

`verificar_nia.py` no gasta llamadas. `preguntas_nia.py` responde con el modelo si la API
que le das tiene clave; si no, con reglas.
