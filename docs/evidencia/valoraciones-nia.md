# Los votos a las respuestas de Nia

Nia contesta con un modelo de lenguaje sobre datos reales, y hasta ahora no había forma de
saber si contestaba bien. La única señal habrían sido las quejas, y para cuando llegan ya
nadie recuerda a qué respuesta se referían ni con qué prompt salió.

Debajo de cada respuesta hay un 👍/👎 privado, con un motivo opcional cuando es 👎. Lo que
hace útil el voto no es el pulgar, sino lo que se guarda al lado: **el modo** (IA o
reglas), **el modelo** y **la versión del prompt**.

## Qué es `version_prompt`

Los primeros ocho hex del sha256 del texto del sistema (`_SISTEMA` en `api/nia.py`). No se
escribe a mano a propósito: una etiqueta manual se queda vieja en cuanto alguien toca el
prompt y no lo anota, y entonces los votos de dos versiones distintas se suman como si
fueran una sola, que es exactamente el error que esto existe para evitar.

Para saber qué cambió entre dos hashes:

```
git log -S'<un trozo del prompt>' -- api/nia.py
```

En modo demostración el valor es `reglas`: ahí el prompt no interviene y atribuirle el voto
sería falso.

## La consulta

```
python docs/evidencia/valoraciones_nia.py
```

Imprime tres cosas:

1. **Cobertura**: cuántas respuestas hubo y cuántas recibieron voto, por modo. Un 90 % de
   👍 sobre el 3 % de las respuestas dice mucho menos de lo que parece, y sin esta línea no
   se nota.
2. **% de 👍 por modo y por versión del prompt**, con el n de cada grupo y las fechas de la
   primera y la última respuesta de esa versión, que es lo que permite cruzarla con el
   historial de git.
3. **El reparto de motivos del 👎**, que es donde se ve si lo que falla es la exactitud, el
   largo o que se le escape una recomendación.

Con menos de 30 votos el propio script avisa de que eso es una pista y no una medida. No
hay forma de que unos pocos votos de la misma persona digan algo sobre el prompt.

## Qué se guarda y por cuánto

La pregunta y la respuesta completas, con el id anónimo del navegador que ya usan las
estrellas y los comentarios. Se guardan al producir la respuesta, no al votarla: así el
voto sigue teniendo a qué referirse aunque la API se haya reiniciado en medio, y se puede
medir la cobertura de arriba. El precio es que también se guarda lo que nadie votó.

**Retención: 180 días** (`DIAS_DE_RETENCION_NIA` en `api/valoraciones.py`). El barrido corre
en cada escritura, no en un documento ni en una tarea que alguien tenga que acordarse de
lanzar, y se lleva los votos de lo que borra. El chat lo dice antes de que se escriba nada:
«No escribas datos personales: se guardan tu pregunta y la respuesta durante 180 días, para
poder revisar los votos.»

Vive en `datos/valoraciones.db`, que es contenido de quien usa la app y no datos del
proyecto: `preparar_entorno.py` no la reconstruye ni la pisa, y no se versiona.
`herramientas/exportar_valoraciones.py` la saca a CSV para analizarla fuera.
