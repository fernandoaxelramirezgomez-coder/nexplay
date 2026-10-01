# NexPlay

Estima el riesgo de arrepentimiento temprano al comprar un videojuego, antes de la compra.
Proyecto del Módulo V del Diplomado en Ciencia de Datos, FES Acatlán (UNAM). Cómo correrlo, la API y
la estructura están en el README; aquí van las decisiones y las convenciones.

## Decisiones que no se reinventan

**Variable objetivo.** `Y = 1` si `playtime_at_review < 120` minutos **y** `voted_up == 0`. Se llama
*arrepentimiento temprano*. Los 120 minutos son la ventana de reembolso de Steam. Nunca «abandono» ni
«insatisfacción».

**Es una proxy.** Steam no observa arrepentimiento. En textos, gráficas o respuestas de la API: «señal de
arrepentimiento temprano», nunca «el usuario se arrepintió».

**Validación.** `GroupKFold` por `appid`: el modelo debe generalizar a juegos que no vio. Nunca un
`train_test_split` simple. La partición está congelada en `backend/referencias/particion_gkf_data-v1.csv`:
toda evaluación y los umbrales usan `splits_congelados` (`backend/modelado/entrenar_baseline.py`), nunca
un `GroupKFold` recalculado, porque cada versión de scikit-learn desempata distinto.

**Métrica principal.** PR-AUC. La clase está desbalanceada; accuracy no sirve.

**Datos.** Reseñas de la API `appreviews` de Steam, publicadas en releases con tag fijo. **Entrenamiento:
83 títulos** (data-v1, 123,972 reseñas), siempre ese corte. **Catálogo servido: 123 títulos** (data-v3:
los juegos y reseñas de data-v2 más los totales públicos de Steam). Los 40 que no están en data-v1 son
prueba externa: nunca entran al entrenamiento, a la elección de variables ni a los umbrales.

**Modelo de título.** `conjunto='juego'` (`logreg-juego-`): gratuidad, precio, descuento y
cobertura/nota de crítica. El riesgo es del juego, igual para cualquier persona.

**Perfil del jugador.** No hay API de consola con historial, así que el perfil se **declara** en un
formulario (compras al año, horas por semana, tolerancia a la fricción, etiquetas con el vocabulario de
tags de Steam y plataforma). No entra al modelo ni mueve el riesgo: sirve para la afinidad. `/prediccion`
lo sigue recibiendo por compatibilidad.

**Perfiles privados.** `author.num_games_owned == 0` es bandera de privacidad, no biblioteca vacía. No
imputar como cero.

**Notebooks.** Clonan un tag fijo de código (`codigo-v3`) y bajan los datos por sha256. El 01 guarda
las salidas de Colab; el 00, las de una corrida local con PNG, para que sus gráficas se vean en GitHub (su
corrida de Colab está en `docs/evidencia/colab/`). `make notebooks` solo compara, nunca las sobrescribe.

## Arquitectura

```
backend/     todo el Python; los comandos corren desde aquí (rutas de docstrings relativas a backend/)
  api/         FastAPI, contrato estable y lógica delgada; nia/ es el chat
  modelado/    entrenar_baseline, entrenar_modelo y verificar_bandas
  analisis/    cuentas del EDA; motivos.py también lo usa la API
  referencias/ bandas y partición congelada: contra qué se compara
  despliegue/  preparar_entorno.py y el Dockerfile de Render (contexto backend/)
  calidad/     verificadores y scripts de evidencia · ingesta/ · publicacion/ · operacion/
frontend/    Angular, el único frontend (Vercel, Root Directory frontend)
notebooks/   00_exploracion y 01_modelo_riesgo · docs/ evidencia, capturas, diseño e historial
```

Una regla por carpeta, con un README corto que dice qué va ahí y qué no. `backend/api/scoring.py` expone
funciones con firma estable: si cambia el modelo, nada fuera de ese archivo debe cambiar.

## Convenciones

- Python 3.12 o más nuevo, FastAPI y pydantic v2. Nombres de variables y funciones en español.
- Comentarios solo donde la intención no sea obvia; ninguno que repita el código.
- Sin `print` en la API: `logging`. Todo lo que entra por la API se valida con Pydantic.
- Para correr algo: `make` desde la raíz (`make help`), o `cd backend` y el script.

## No hacer

- No mezclar el corpus de Metacritic con los datos de entrenamiento: es fuente secundaria, solo para
  comparar motivos entre plataformas.
- No usar Kaggle como fuente: la rúbrica lo prohíbe.
- No prometer un score entrenado con datos de PlayStation o Xbox: esa fuente no existe. El lado del juego
  transfiere; el lado del jugador viene del formulario.
- No tocar `backend/datos/` ni `backend/modelo/` sin avisar. `preparar_entorno.py --force` no va sobre la
  base original de la ingesta.
