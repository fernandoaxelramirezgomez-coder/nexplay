# ¿Dejan más señal los veteranos que los novatos?

El encuadre de NexPlay dice que los jugadores con biblioteca grande se arrepienten más que los
novatos: **1.34 % contra 0.45 %**. De ahí sale que el riesgo está en el título y no en la
inexperiencia de quien compra. La cifra no tenía fuente en el repo. Esta ficha fija cómo se
reproduce **antes de correr nada**, y después anota el resultado.

## Prerregistro (commiteado antes de la primera corrida)

**Definición original, que se reproduce primero:**
- **Datos:** reseñas de data-v1 (83 juegos, sha256 `2ef8ef40…9ee7`) con perfil público,
  `num_games_owned > 0`. El 0 es bandera de privacidad, no una biblioteca vacía, así que esas
  reseñas se excluyen.
- **Novatos:** de 1 a 19 juegos. **Veteranos:** 20 o más.
- **Señal:** `playtime_at_review < 120` y `voted_up = 0`, la misma Y del modelo.
- **Dos medidas por grupo:**
  - por reseña: señales entre reseñas del grupo;
  - promedio por juego: la tasa del grupo dentro de cada juego, promediada con cada juego
    pesando igual.
- **Incertidumbre:** IC 95 % de la diferencia (veteranos − novatos, en puntos porcentuales)
  por bootstrap sobre juegos: 2,000 réplicas con reemplazo y semilla 42.

**Regla de reproducción:** la cifra se da por reproducida si las tasas **por reseña**, en
porcentaje y redondeadas a dos decimales, son 0.45 (novatos) y 1.34 (veteranos). Si no, se
reporta al dueño **antes de cambiar nada**: ni la definición, ni la frase del documento.

**Regla para citarla en el documento:**
- Se cita si la diferencia por reseña es positiva y su IC 95 % no cruza el cero.
- Si el promedio por juego cuenta otra historia (otro signo, o un IC que cruza el cero), el
  documento lo dice junto a la cifra.
- El texto aclara siempre cuál de las dos medidas usa.

**Robustez, después y separada del resultado principal:**
- Los cuartiles de `num_games_owned` en las reseñas con perfil público. Q1 es hasta el
  percentil 25 y Q4 queda por encima del 75.
- Q4 contra Q1, con las mismas dos medidas y el mismo bootstrap.
- No reemplaza a la definición original: solo dice si la dirección se sostiene con otro corte.

**Límite que ya se sabe:** `num_games_owned` describe al autor cuando se descargó la reseña,
no cuando compró el juego. Es contexto del encuadre y no entra al modelo de título, que es del
juego y vale igual para cualquier persona.

## Resultado

Pendiente: se llena después de correr `calidad/senal_por_biblioteca.py`.

## Cómo se reproduce

```
python calidad/senal_por_biblioteca.py [--cache DIR]
```

Baja data-v1 con su sha256 (`despliegue/utilidades.py::descargar_verificado`), lee las reseñas
con `modelado/entrenar_baseline.py::cargar_datos` y escribe
`docs/evidencia/senal-por-biblioteca.json`. No toca `datos/` ni `modelo/`.
