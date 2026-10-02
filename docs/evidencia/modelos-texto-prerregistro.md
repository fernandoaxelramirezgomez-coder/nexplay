# Modelos de texto · Parte A: ¿el texto distingue las negativas tempranas de las tardías?

Prerregistro. Se escribió y se commiteó antes de escribir el código que lo corre. El hash de ese commit queda
en `backend/analisis/texto.py` y en `docs/evidencia/modelos-texto.json`. Nada de lo que sigue se ajusta después
de ver resultados.

Fecha: 2026-10-01. Código de partida: `4d47c3e`, rama `modelos-texto`.

## 1. Pregunta

Entre las reseñas negativas, ¿el texto distingue las tempranas (`playtime_at_review < 120`, es decir `Y = 1`)
de las tardías (`voted_up = 0` y 120 minutos o más)?

- **Si sí:** las quejas del arrepentimiento temprano tienen lenguaje propio, y los motivos de la ficha son
  específicos de ese momento.
- **Si no:** la ficha los presenta como quejas generales de las reseñas negativas.

Una reseña temprana es una **señal de arrepentimiento temprano**, no la confirmación de que alguien se
arrepintió.

**En ningún caso entra al score de riesgo**, porque `Y` sale de esas mismas reseñas. Ningún modelo de esta
parte llega a la API ni a Render.

## 2. Datos

- **Release:** data-v1, con sus 83 juegos. Asset `nexplay_reproducible.db.xz`, sha256
  `2ef8ef40330385af4c03cd072dccb20fc9a4b635e3929e513235c191d14e9ee7`. Los 40 externos no se usan.
- **Conjunto limpio del 00:** `limpieza.limpiar`, sin duplicados de 8 palabras o más y sin reseñas vacías.
  Su firma es `FIRMA_LIMPIO_DATA_V1` (`cb1e4b06fdf5a0264471f722446ac73bd06e28db30653819b8f1773c58e3f41e`). Si
  no coincide, no se corre.
- **Qué reseñas:** solo las negativas (`voted_up = 0`) en inglés, es decir, sin la marca `no_ingles`. Es la
  definición del 00: «en inglés o sin idioma determinado». Las cortas y las plantillas entran: se marcan, no
  se quitan.
- **Clase positiva:** temprana.

Conteos, medidos el 2026-10-01 sin ningún modelo:

| | Reseñas |
|---|---|
| Negativas en inglés | 16,836 |
| Tempranas (`Y = 1`) | 2,670 (15.86 %) |
| Tardías | 14,166 |
| Juegos | 83, todos con al menos 2 tempranas |
| Quedan fuera por otro idioma | 223 negativas (36 tempranas) |
| Entran sin idioma determinado | 4,221, casi todas cortas |

Por fold de la partición congelada, en la validación:

| Fold | Juegos | Negativas | Tempranas | Prevalencia (= PR-AUC del trivial) |
|---|---|---|---|---|
| 0 | 16 | 3,186 | 606 | 0.1902 |
| 1 | 16 | 2,690 | 447 | 0.1662 |
| 2 | 17 | 3,374 | 624 | 0.1849 |
| 3 | 17 | 4,505 | 590 | 0.1310 |
| 4 | 17 | 3,081 | 403 | 0.1308 |

## 3. Las duraciones se enmascaran

La clase se define por los minutos jugados. Una reseña que dice cuánto jugó («refunded after 20 minutes»,
«300 hours in») repite la etiqueta: el modelo que la lee no encuentra lenguaje de la queja, lee la
definición de la clase. Por eso **el análisis principal y la regla de decisión usan el texto con las
duraciones enmascaradas**, en los cinco modelos.

La máscara se aplica sobre `texto_norm` del 00, que está en minúsculas y sin puntuación («2.5h» queda «2 5h»).
Cada coincidencia se reemplaza por la palabra `duracion`:

```python
CANTIDAD = (r"(?:\d+(?: \d+)?|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
            r"fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|hundreds of|thousands of|"
            r"hundred|thousand|a|an|half|few|couple of|couple|several|many|some)")
PATRON_DURACION = re.compile(
    rf"\b(?:{CANTIDAD} )?(?:seconds|minutes?|hours?|hrs?)\b"            # la unidad siempre, con su cantidad si la hay
    r"|\b\d+(?: \d+)? (?:secs?|second|mins?|h)\b"                       # abreviatura después de una cifra
    r"|\b\d+(?: \d+)?(?:hours?|hrs?|h|minutes?|mins?|seconds?|secs?)\b"  # cifra pegada a su unidad
)
```

**Qué no se enmascara:**
- `days` y `weeks`, que son tiempo de calendario;
- una `m` pegada a una cifra («162m budget», «15m away»);
- «second» sin cifra («a second chance»).

La marca dice que hubo una duración, no cuál. Lo que queda de esa señal es un límite (§8).

**Sensibilidad, fuera de la regla.** NB y TF-IDF + LR se corren también con el texto sin enmascarar, sobre las
mismas filas y los mismos folds. Se reporta cuánto ganaban por leer la duración: la diferencia pareada «sin
máscara − con máscara», con su intervalo. No cambia la decisión.

## 4. Modelos

Los cinco reciben el mismo texto enmascarado y la misma partición. Todo ajuste se hace solo con el fold de
entrenamiento, dentro de un `Pipeline`: vocabulario, idf, escalado y coeficientes. No hay búsqueda de
hiperparámetros: los valores son estos y no se mueven.

1. **Trivial.** Un puntaje constante. Su PR-AUC en cada fold es la prevalencia de ese fold.
2. **Regla de una palabra.** Vale 1 si la reseña contiene «refund» y 0 si no. El patrón es `\brefund`, sin
   distinguir mayúsculas (refund, refunded, refunding…).
   - **Esa palabra salió de §7.3 del documento (§3.7 del 00) sobre estos mismos datos, así que esta
     referencia es optimista.**
   - Con un puntaje binario, la curva tiene dos puntos:
     PR-AUC = recall · precisión + (1 − recall) · prevalencia.
3. **TF-IDF + Naive Bayes.** `TfidfVectorizer(ngram_range=(1, 2), min_df=5, sublinear_tf=True)` y
   `MultinomialNB(alpha=1.0)`.
   - Sin stopwords, porque la negación importa (§3.7 del 00).
   - En dos clases, el prior de NB solo suma una constante y no cambia el orden, que es lo único que mide
     el PR-AUC.
4. **TF-IDF + regresión logística.** El mismo `TfidfVectorizer` y
   `LogisticRegression(class_weight="balanced", max_iter=2000, random_state=42)`.
5. **all-MiniLM-L6-v2 + regresión logística, fuera de línea.**
   - Modelo `sentence-transformers/all-MiniLM-L6-v2`, revisión `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`,
     en CPU, con `batch_size=64` y un máximo de 256 tokens (lo demás se trunca).
   - El encoder está preentrenado y congelado, y no se ajusta con estos datos. Por eso los vectores se
     calculan una sola vez para todas las reseñas.
   - Después van un `StandardScaler` y la misma `LogisticRegression`, ajustados en cada fold.
   - No se sirve en ningún lado.

**Orden de complejidad, para la parsimonia:** NB < TF-IDF + LR < MiniLM + LR.

## 5. Muestra

**Sin muestra:** los cinco modelos usan las 16,836 reseñas. Codificar 1,000 negativas con MiniLM tomó 30 s en
CPU (medido el 2026-10-01, sin etiquetas), así que todas tardan unos 8.5 min. En Colab se estiman de 12 a
20 min.

## 6. Métrica e intervalos

- **PR-AUC de la clase temprana** (`average_precision_score`), calculado por fold con las predicciones fuera de
  fold. Los folds son los de la partición congelada (`splits_congelados`), nunca un `GroupKFold` recalculado.
  La cifra de cada modelo es la **media de los 5 folds**.
- **Cociente contra el trivial:** la media de los PR-AUC del modelo entre la media de las prevalencias de los
  folds.
- **Intervalos:** bootstrap sobre juegos, con 2,000 réplicas y `numpy.random.default_rng(42)`.
  - En cada réplica y en cada fold se sacan, con reemplazo, tantos juegos como tiene ese fold. Cada reseña pesa
    las veces que salió su juego.
  - Las predicciones fuera de fold son fijas: no se reentrena en cada réplica. El intervalo mide cuánto cambia
    la cifra según qué juegos se evalúan.
  - IC del 95 % por percentiles (2.5 y 97.5).
- **Comparaciones pareadas:** todas las cifras de una réplica salen de los mismos juegos sorteados, y la
  diferencia A − B se calcula réplica por réplica.

## 7. Regla de decisión

**Definiciones**
- **Mejor modelo (M):** el de mayor PR-AUC medio entre NB, TF-IDF + LR y MiniLM + LR. La regla «refund» es una
  referencia, no una candidata.
- **Supera al trivial:** el límite inferior del IC del cociente es mayor que 1.
- **Supera a «refund»:** el límite inferior del IC de la diferencia pareada «M − regla» es mayor que 0.

**Reglas, en orden**
1. **M no supera al trivial** (el intervalo del cociente incluye 1): es una moneda.
   - Se descarta.
   - Conclusión: las quejas tempranas no tienen lenguaje propio.
   - La ficha presenta los motivos como quejas generales.
2. **M supera al trivial pero no a «refund»** (la diferencia pareada incluye 0 o queda por debajo): un modelo no
   aporta más que una palabra.
   - Se descarta el modelo y se documenta la regla.
   - Lo que distingue a las tempranas es mencionar el reembolso, que es una acción y no un motivo.
   - La ficha presenta los motivos como quejas generales.
3. **M supera a los dos.**
   - Se guarda el modelo más simple que cumpla tres condiciones: su diferencia pareada contra M incluye 0, y él
     mismo supera al trivial y a «refund». M siempre las cumple.
   - Conclusión: las quejas tempranas tienen lenguaje propio, más allá de «refund».
   - Los motivos de la ficha se pueden presentar como propios de ese momento.
   - «Se guarda» significa que es el modelo que se documenta. No se publica ni se sirve.

**En ningún caso entra al score de riesgo**, porque `Y` sale de esas mismas reseñas. La regla se aplica sobre el
texto enmascarado; la corrida sin máscara (§3) no la cambia.

## 8. Qué no dice y límites

- Es una señal de arrepentimiento temprano, no un arrepentimiento confirmado.
- «refund» se eligió mirando estos datos: la regla es una referencia optimista.
- La máscara es una lista fija:
  - lo que se le escape queda en el texto («a while», «days», «playtime»);
  - la sola presencia de `duracion` puede ser distinta entre las clases.
- MiniLM lee hasta 256 tokens. Cerca del 6.7 % de las negativas es más largo (medido sin máscara) y se trunca.
- Que el modelo distinga a las tempranas no dice qué motivos lo hacen. Las categorías de palabras clave de la
  ficha no se prueban aquí: eso es la Parte B.
- Solo inglés y solo data-v1: quedan fuera las 223 negativas en otro idioma y los 40 externos.
- El intervalo no incluye la variación que daría reentrenar.

## 9. Dónde queda el resultado

- **Código:** `backend/analisis/texto.py`, que se corre desde `backend/` con `python analisis/texto.py`.
- **Resultado:** `docs/evidencia/modelos-texto.json`, con el commit de este prerregistro y el del código que lo
  produjo.
- **Notebook:** `notebooks/02_modelos_texto.ipynb`. Reproduce las cifras y falla si dejan de coincidir.
