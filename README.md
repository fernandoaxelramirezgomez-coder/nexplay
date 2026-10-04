# NexPlay

**Una segunda opinión antes de comprar tu próximo juego.** NexPlay estima qué tan seguido un juego deja la
señal de arrepentimiento temprano, las reseñas negativas de Steam escritas en las primeras dos horas, y te dice
por qué, con los motivos que aparecen en reseñas reales y no con una nota genérica. Es el proyecto del Módulo V
del Diplomado en Ciencia de Datos de la FES Acatlán (UNAM).

[![Open in Colab: 00_exploracion](https://img.shields.io/badge/Open_in_Colab-00__exploracion-F9AB00?logo=googlecolab&logoColor=white)](https://colab.research.google.com/github/fernandoaxelramirezgomez-coder/nexplay/blob/master/notebooks/00_exploracion.ipynb)
[![Open in Colab: 01_modelo_riesgo](https://img.shields.io/badge/Open_in_Colab-01__modelo__riesgo-F9AB00?logo=googlecolab&logoColor=white)](https://colab.research.google.com/github/fernandoaxelramirezgomez-coder/nexplay/blob/master/notebooks/01_modelo_riesgo.ipynb)
[![Open in Colab: 02_modelos_texto](https://img.shields.io/badge/Open_in_Colab-02__modelos__texto-F9AB00?logo=googlecolab&logoColor=white)](https://colab.research.google.com/github/fernandoaxelramirezgomez-coder/nexplay/blob/master/notebooks/02_modelos_texto.ipynb)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](#1-lo-que-necesitas)
[![Angular 22](https://img.shields.io/badge/Angular-22-DD0031?logo=angular&logoColor=white)](frontend/README.md)

**Pruébalo:** [la app en vivo](https://nexplay-six.vercel.app) · [la API y su contrato (/docs)](https://nexplay-api-345o.onrender.com/docs) · [📄 Documento final](https://github.com/fernandoaxelramirezgomez-coder/nexplay/blob/master/entregables/documento-entregafinal.pdf) · [🎤 Presentación](https://github.com/fernandoaxelramirezgomez-coder/nexplay/blob/master/entregables/presentacion-entregafinal.pdf).
La API está en el plan gratis de Render y se duerme cuando nadie la usa, así que la primera carga puede tardar
un poco.

## Entregables

| Entregable | Ver en línea | Descargar |
|---|---|---|
| 📄 Documento final | [Abrir PDF](https://github.com/fernandoaxelramirezgomez-coder/nexplay/blob/master/entregables/documento-entregafinal.pdf) | [Descargar](https://github.com/fernandoaxelramirezgomez-coder/nexplay/raw/master/entregables/documento-entregafinal.pdf) |
| 🎤 Presentación (PDF) | [Abrir PDF](https://github.com/fernandoaxelramirezgomez-coder/nexplay/blob/master/entregables/presentacion-entregafinal.pdf) | [Descargar](https://github.com/fernandoaxelramirezgomez-coder/nexplay/raw/master/entregables/presentacion-entregafinal.pdf) |
| 💡 El nicho en simples palabras | [nicho.md](entregables/nicho.md) | — |

> **Steam te dice si un juego es bueno. NexPlay te dice cuáles van contigo y cuáles suelen fallar en las primeras
> dos horas, antes de pagar.** [El nicho completo](entregables/nicho.md)

> **En 30 segundos**
>
> - **El problema:** comprar un juego en Steam que te decepciona en las primeras horas, cuando todavía lo puedes devolver.
> - **Qué estima:** para cada uno de los 123 juegos del catálogo, un riesgo de arrepentimiento (bajo, medio o
>   alto), según qué tan seguido deja la señal de arrepentimiento temprano, con los factores que lo mueven y los
>   motivos de queja de las reseñas.
> - **Qué tan bien:** PR-AUC de 0.0694 ± 0.0415 con GroupKFold por juego, 3.2 veces el clasificador trivial. En
>   40 juegos que el modelo no vio, 0.0356 contra 0.0234, 1.5 veces el trivial.
> - **Qué no hace:** no predice lo que vas a sentir tú (el riesgo es del juego), no es una probabilidad y no te
>   dice si comprar.

![Inicio de NexPlay en producción: qué podría frustrarte en las primeras dos horas y la opinión de Nia sobre Hades, con su riesgo de arrepentimiento](docs/capturas/captura-interfaz.png)

<table>
  <tr>
    <td width="50%"><img src="docs/capturas/captura-ficha-dead-space.png" alt="Ficha de Dead Space: riesgo de arrepentimiento bajo"></td>
    <td width="50%"><img src="docs/capturas/captura-comparar.png" alt="Comparar: PAYDAY 3, riesgo alto, contra Dead Space, riesgo bajo"></td>
  </tr>
  <tr>
    <td align="center">La ficha de Dead Space</td>
    <td align="center">PAYDAY 3 contra Dead Space, en Comparar</td>
  </tr>
</table>

## 📑 Índice

- [Qué es NexPlay](#-qué-es-nexplay)
- [Hazlo tú: la ruta completa](#-hazlo-tú-la-ruta-completa), del clon al sitio publicado
  1. [Lo que necesitas](#1-lo-que-necesitas)
  2. [Consigue el código](#2-consigue-el-código)
  3. [Instala](#3-instala)
  4. [Consigue los datos](#4-consigue-los-datos)
  5. [Explora los datos](#5-explora-los-datos)
  6. [Entrena y valida el modelo](#6-entrena-y-valida-el-modelo)
  7. [Levanta la API y la app](#7-levanta-la-api-y-la-app)
  8. [Dale un modelo de lenguaje a Nia (opcional)](#8-dale-un-modelo-de-lenguaje-a-nia-opcional)
  9. [Comprueba que todo está en orden](#9-comprueba-que-todo-está-en-orden)
  10. [Publícalo](#10-publícalo)
  11. [Cuéntalo: el documento](#11-cuéntalo-el-documento)
- Referencia: [Arquitectura](#%EF%B8%8F-arquitectura) · [Configuración (.env)](#%EF%B8%8F-configuración-env) ·
  [API](#-api) · [Calidad](#-calidad) · [Estructura del repositorio](#%EF%B8%8F-estructura-del-repositorio) ·
  [Datos y releases](#-datos-y-releases) · [Contenido de usuarios y moderación](#-contenido-de-usuarios-y-moderación) ·
  [Solución de problemas](#%EF%B8%8F-solución-de-problemas)
- [Autor y datos](#-autor-y-datos)

## 🎮 Qué es NexPlay

Steam te devuelve el dinero de un juego si lo pides dentro de los 14 días posteriores a la compra y con menos
de 2 horas jugadas. NexPlay se fija en ese límite de 2 horas: una reseña negativa escrita antes de los 120
minutos de juego es una **señal de arrepentimiento temprano** (`Y = 1` si `playtime_at_review < 120` y
`voted_up == 0`). Los 14 días no se pueden usar, porque las reseñas no dicen cuándo se compró el juego.

Es una señal proxy. Steam no le pregunta a nadie si se arrepintió, así que el proyecto nunca dice que alguien
lo hizo.

- **Los datos.** Salen de la API pública de Steam: las reseñas, de `appreviews`, y el precio, la gratuidad y
  la nota de Metacritic de cada juego, de `appdetails`. Todo está publicado en releases con tag fijo. El
  modelo se entrena siempre con data-v1 (83 juegos, 123,972 reseñas). La app sirve 123 juegos (data-v3), y
  los 40 que no están en data-v1 son la prueba externa: nunca entran al entrenamiento.
- **El modelo.** Es una regresión logística con variables del juego: gratuidad, precio, descuento y cobertura
  y nota de la crítica. El riesgo es del juego, el mismo para cualquier persona. Se valida con GroupKFold por
  `appid`, porque tiene que funcionar con juegos que no vio, y se mide con PR-AUC, porque la señal aparece en
  pocas reseñas: 0.0694 ± 0.0415 entre folds, 3.2 veces el clasificador trivial. En los 40 externos da 0.0356
  contra 0.0234 del trivial.
- **La app.** Te muestra la banda de riesgo (bajo, medio o alto, nunca un número), los factores que más la
  mueven, los motivos de queja más frecuentes y a Nia, un chat que te explica los datos del juego sin
  recomendarte que lo compres. El perfil que declares sirve para contarte qué tanto encaja un juego contigo;
  no cambia el riesgo. Fuera de sus cinco vistas, **Administración** (`/admin`, en el pie del menú) dice de un
  vistazo si la API, Nia, los datos y el modelo están en orden, cuenta lo que hiciste en ese navegador y junta
  el buzón de sugerencias a Nia.

La historia completa está en tres notebooks que corren en Colab: `00_exploracion` (los datos, antes del
modelo), `01_modelo_riesgo` (el modelo) y `02_modelos_texto` (si el texto distingue las negativas
tempranas). Los detalles, en [notebooks/README.md](notebooks/README.md).

## 🧭 Hazlo tú: la ruta completa

Estos son los pasos que seguí, en orden, para llegar del código al sitio publicado. Cada uno dice para qué
sirve, qué comando correr y cómo saber que salió bien. Si solo quieres ver el análisis, ve directo al
[paso 5](#5-explora-los-datos): los notebooks corren en Colab sin instalar nada. Los comandos con `make` corren
desde la raíz del repo; los de Python sueltos, desde `backend/`.

### 1. Lo que necesitas

| Herramienta | Versión | Para qué |
|---|---|---|
| Python | 3.12 o más nuevo (probado con 3.14, la del Dockerfile) | backend, modelo y notebooks |
| Node.js con npm | `^22.22.3`, `^24.15.0` o `>=26` | frontend |
| git | cualquiera reciente | clonar; `make notebooks` exporta el último commit |
| make | GNU make | los atajos de cada paso (Linux, macOS o WSL) |
| Chrome | opcional | las gráficas del 00 en PNG y las capturas de la UI |
| Clave de OpenAI | opcional | Nia con modelo de lenguaje; sin clave responde con reglas |
| LaTeX (latexmk, LuaLaTeX y biber) | opcional | compilar el documento con `make doc` |
| Cuentas de Render y Vercel | opcional, gratis | publicar la API y el sitio (paso 10) |

No necesitas cuenta ni credenciales de Steam ni de GitHub para correrlo: todo lo que se descarga es público. La
instalación base con los datos ocupa algo más de 1 GB (`.venv` 575 MB, `node_modules` 366 MB y los datos
102 MB). Si además corres los notebooks, sus paquetes (torch CPU, lingua y transformers, entre otros) suman
otros 1.6 GB.

### 2. Consigue el código

```bash
git clone https://github.com/fernandoaxelramirezgomez-coder/nexplay.git
cd nexplay
```

Si lo vas a publicar con tus cuentas (paso 10), primero haz un *fork* en GitHub y clona el tuyo: Render y
Vercel despliegan desde tu repositorio.

### 3. Instala

```bash
make setup
```

Crea `.venv` con lo que necesitan la API y el modelo (`backend/requirements.txt` y
`backend/requirements-modelo.txt`) e instala el frontend con `npm ci`.

**Salió bien si** termina con `Listo. Siguiente paso: make data`. Si te dice que hace falta Python 3.12, elige
otro intérprete: `make setup PYTHON=python3.14`.

<details>
<summary>Sin make</summary>

```bash
python3 -m venv .venv
source .venv/bin/activate            # en Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt -r backend/requirements-modelo.txt
cd frontend && npm ci
```

</details>

### 4. Consigue los datos

**La ruta corta, la del proyecto:** bajar los releases publicados.

```bash
make data
```

Baja dos bases de los releases de GitHub y verifica el sha256 de cada una antes de abrirla: data-v3, el
catálogo de 123 juegos que sirve la API, a `backend/datos/nexplay.db`, y data-v1, los 83 juegos con los que se
entrena, a `backend/datos/entrenamiento/`.

**Salió bien si** ves esto:

```
descarga verificada (data-v3): 15.9 MB, sha256 OK
descarga verificada (data-v1): 10.9 MB, sha256 OK
Datos listos: datos/nexplay.db (data-v3) y datos/entrenamiento/nexplay_data-v1.db (data-v1).
```

<details>
<summary>La ruta larga: recolectar tus propios datos de Steam</summary>

Solo hace falta si quieres otros juegos o reseñas más nuevas. Los juegos salen de
[`backend/ingesta/appids.txt`](backend/ingesta/appids.txt), un appid por línea; el criterio con el que elegí los
123 está en los comentarios de ese archivo. Desde `backend/`:

```bash
python ingesta/ingesta_steam.py --catalogo       # precio, gratuidad y nota de cada juego
python ingesta/ingesta_steam.py --resenas        # hasta 1,500 reseñas por juego; tarda horas y reanuda si se corta
python ingesta/ingesta_steam.py --estado         # cuánto llevas
```

La ingesta escribe en `backend/datos/nexplay.db`, el mismo archivo que llena `make data`. Esa base no se
recupera de ningún release, así que respáldala: por eso `preparar_entorno.py --force` se niega a pisarla.

Para que otros (y Render) usen tus datos, publícalos como un release nuevo:

```bash
python publicacion/extracto_datos.py             # extracto/nexplay_extracto.parquet, sin texto, para el 01
python publicacion/extracto_reproducible.py      # extracto/nexplay_reproducible.db.xz, sin steamid
```

Sube los dos archivos a un release de GitHub con un tag nuevo (`data-v4`, por ejemplo), desde la web o con
`gh release create`. Nunca reemplaces los assets de un release publicado. Después pon el tag y los sha256 que
imprime cada script en `backend/despliegue/preparar_entorno.py` (`SERVIDO_REF`, `SERVIDO_SHA256` y
`BASES_DE_RELEASE`, o los de `ENTRENAMIENTO_` si es la base de entrenamiento) y en los notebooks. Si no
coinciden, la descarga se rechaza a propósito.

Con otros juegos o datos, las bandas cambian y el paso 6 va a decir que no coinciden con la referencia. Revisa
el modelo en el 01 y, cuando estés conforme, reescribe la referencia con
`python modelado/verificar_bandas.py --generar` y versiona `backend/referencias/bandas_referencia.json`.

</details>

### 5. Explora los datos

Abre el notebook `00_exploracion` y ejecútalo completo: *Entorno de ejecución → Ejecutar todas*.

| Notebook | Qué hace | Abrir |
|---|---|---|
| `00_exploracion` | Valida, limpia y explora los datos; fija las decisiones que los otros dos dan por hechas | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/fernandoaxelramirezgomez-coder/nexplay/blob/master/notebooks/00_exploracion.ipynb) |
| `01_modelo_riesgo` | Construye y mide el modelo: GroupKFold por `appid`, prueba externa y señal por banda | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/fernandoaxelramirezgomez-coder/nexplay/blob/master/notebooks/01_modelo_riesgo.ipynb) |
| `02_modelos_texto` | Si el texto distingue las negativas tempranas, contra una regla prerregistrada | [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/fernandoaxelramirezgomez-coder/nexplay/blob/master/notebooks/02_modelos_texto.ipynb) |

Cada notebook clona el tag `codigo-v8` y baja los datos verificando su sha256, así que en Colab no necesitas
nada de los pasos anteriores ni te pide credenciales. Los tres corrieron en Colab el 2026-10-02 con `codigo-v8`,
el tag de entrega, sin errores ni avisos; la evidencia está en
[docs/evidencia/colab/](docs/evidencia/colab/README.md), junto con las corridas anteriores.

En tu máquina, después del paso 3, `make notebooks` ejecuta los tres en una carpeta temporal y compara cada
salida con la guardada, sin sobrescribirla. La primera vez instala sus paquetes (unos 1.6 GB).

### 6. Entrena y valida el modelo

```bash
make train
```

Entrena la regresión logística con data-v1 y la partición congelada
(`backend/referencias/particion_gkf_data-v1.csv`), deja el modelo en `backend/modelo/nexplay.pkl` y compara la
banda de cada uno de los 123 juegos contra la referencia validada. La partición está congelada porque cada
versión de scikit-learn desempata `GroupKFold` distinto, y las cifras tienen que salir iguales en cualquier
máquina.

**Salió bien si** termina con:

```
filas=123972  juegos=83  prevalencia=0.0219
bandas idénticas a la referencia: 123 juegos (modelo actual logreg-juego-AAAA-MM-DD)
```

La fecha es la del día en que entrenas. El porqué de cada decisión (las variables, la validación, la prueba
externa, por qué PR-AUC) está en el notebook `01_modelo_riesgo`, y lo que se midió para decidirlo, en
[docs/evidencia/](docs/evidencia/README.md).

### 7. Levanta la API y la app

En dos terminales:

```bash
make api         # terminal 1: la API en http://localhost:8000 (contrato en /docs)
make web         # terminal 2: el sitio en http://localhost:4200
```

Abre el sitio como `http://localhost:4200` y no como `127.0.0.1`: el CORS de la API solo permite el primero.

**Salió bien si** en Administración (el enlace «Administración» con el escudo, en el pie del menú) ves el
backend «Conectado», los datos `data-v3` con 123 juegos y el modelo `logreg-juego-…` «entrenado con 83 juegos
(data-v1)». Lo mismo, sin el navegador:

```bash
curl -s http://localhost:8000/estado
# {"nia_con_openai":false,"modelo_nia":null,"datos_release":"data-v3","juegos_catalogo":123,
#  "modelo_version":"logreg-juego-AAAA-MM-DD","modelo_datos":"data-v1","modelo_juegos_entrenamiento":83}
```

<details>
<summary>Sin make</summary>

```bash
cd backend && uvicorn api.main:app --reload       # terminal 1, con .venv activado
cd frontend && npx ng serve                       # terminal 2
```

</details>

### 8. Dale un modelo de lenguaje a Nia (opcional)

Sin clave, Nia contesta por reglas sobre los datos, sin costo. Con clave, usa un modelo de OpenAI para lo que
no tiene respuesta fija:

```bash
cp .env.example .env      # y llena OPENAI_API_KEY y NEXPLAY_MODELO_NIA
```

Reinicia `make api`. **Salió bien si** Administración dice OpenAI «Configurado» con el nombre del modelo y las
respuestas del chat llevan la etiqueta «Con IA». `.env` está en `.gitignore`: la clave nunca va en un archivo
del repo, y `/estado` dice si hay clave, nunca cuál es. Las demás variables están en
[Configuración](#%EF%B8%8F-configuración-env).

### 9. Comprueba que todo está en orden

```bash
make test
```

Revisa que las 123 bandas sigan idénticas, a Nia sin gastar llamadas (contexto, reglas, votos y buzón), los
factores de «Qué mueve esta estimación», que los niveles tengan una sola definición, que `/estado` no deje
salir la clave, que `preparar_entorno --force` no pise bases ajenas y todas las pruebas del frontend.

**Salió bien si** termina sin errores, con `bandas idénticas a la referencia: 123 juegos`, `sin problemas: 6
juegos × 3 preguntas` y las pruebas del frontend en verde (`Tests … passed`). Para el build de producción del
frontend: `cd frontend && npx ng build`. Qué revisa cada comando, en [Calidad](#-calidad).

### 10. Publícalo

**La API, en Render** (plan gratis, como servicio Docker):

1. *New → Web Service*, desde tu fork, con *Runtime* Docker.
2. *Root Directory* `backend`, *Dockerfile Path* `despliegue/Dockerfile` y *Docker Build Context Directory* `.`
   (un solo punto: la misma carpeta `backend/`).
3. En *Environment*, `NEXPLAY_CORS_ORIGENES` con la URL que te dará Vercel (por ejemplo,
   `https://tu-app.vercel.app`, sin `/` al final) y, si quieres a Nia con modelo, `OPENAI_API_KEY` y
   `NEXPLAY_MODELO_NIA`.
4. Opcional: en *Build Filters*, incluye solo lo que copia el Dockerfile, para que cambiar un README no
   dispare un deploy: `backend/api/**`, `backend/modelado/**`, `backend/analisis/motivos.py`,
   `backend/despliegue/**`, `backend/referencias/bandas_referencia.json`,
   `backend/referencias/particion_gkf_data-v1.csv`, `backend/requirements.txt` y
   `backend/requirements-modelo.txt`; ignora `**/README.md`.

El build hace lo mismo que los pasos 4 y 6: baja los datos con su sha256, entrena y corre
`verificar_bandas.py`. Si una banda cambia, o si llega torch a la imagen, el build falla.
**Salió bien si** `curl -s https://tu-api.onrender.com/estado` devuelve `"datos_release":"data-v3"` y
`"juegos_catalogo":123`.

**El sitio, en Vercel:**

1. En `frontend/src/environments/environment.ts`, cambia `apiUrl` por la URL de tu API en Render, sin `/` al
   final, y súbelo a tu fork.
2. *Add New → Project*, desde tu fork, con *Root Directory* `frontend`. `frontend/vercel.json` ya reescribe
   toda ruta a `index.html`.

**Salió bien si** `https://tu-app.vercel.app/admin` dice backend «Conectado». Si dice «Despertando…», Render
estaba dormido: el plan gratis duerme la API tras 15 minutos sin uso y tarda hasta un minuto en despertar. Si
dice «Sin conexión», revisa que `NEXPLAY_CORS_ORIGENES` tenga exactamente el origen de tu sitio. En ese plan el
disco es efímero: las calificaciones, los comentarios y los votos a Nia se borran cada vez que el servicio se
reinicia.

### 11. Cuéntalo: el documento

```bash
make doc
```

Genera las figuras y las cifras del documento desde el código y los datos, comprueba cada cifra contra su
fuente, lo compila con LaTeX y deja el PDF en `entregables/documento-entregafinal.pdf`. Ninguna cifra del texto
se escribe a mano: todas son macros de `documento/tables/cifras.tex`, y `documento/verificar_cifras.py` falla
si alguna no cuadra. Necesita LaTeX (paso 1); en Ubuntu, `make doc` te dice qué paquetes instalar si falta.
También usa los paquetes de los notebooks: si no corriste `make notebooks`, instálalos antes, con torch para CPU
primero para no bajar el de GPU:

```bash
.venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cpu
.venv/bin/pip install -r backend/requirements-notebooks.txt
```

## 🏗️ Arquitectura

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/diagramas/01-arquitectura.svg">
  <img alt="Arquitectura de NexPlay: la API pública de Steam alimenta los releases con tag fijo; de ahí salen backend/datos, el modelo, la API FastAPI (con OpenAI opcional para Nia) y el frontend en Angular; los notebooks clonan el tag codigo-v8 y leen los releases" src="docs/diagramas/01-arquitectura-claro.svg">
</picture>

<sub>Fuente: [docs/diagramas/01-arquitectura.mmd](docs/diagramas/01-arquitectura.mmd)</sub>

En producción, Render construye la API con `backend/despliegue/Dockerfile`: baja los datos, entrena el modelo
y, si alguna de las 123 bandas cambia, el build falla. Vercel publica el frontend.

Esto es lo que pasa cuando abres la ficha de un juego:

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/diagramas/02-ficha-de-un-juego.svg">
  <img alt="Al abrir la ficha de un juego, Angular pide el catálogo, la predicción (la API llama a scoring.py) y la explicación, y muestra banda, factores y motivos, nunca el score" src="docs/diagramas/02-ficha-de-un-juego-claro.svg">
</picture>

<sub>Fuente: [docs/diagramas/02-ficha-de-un-juego.mmd](docs/diagramas/02-ficha-de-un-juego.mmd)</sub>

## ⚙️ Configuración (.env)

`.env` va en la raíz (`cp .env.example .env`) y está en `.gitignore`; en Render, las variables se cargan en
*Environment*. La API lee el `.env` de la raíz aunque corra desde `backend/`, pero solo para las variables de
Nia. Las demás las toma del entorno del proceso: expórtalas en la terminal antes de `make api` o ponlas en el
panel de Render.

| Variable | Por omisión | Qué hace | Se lee de |
|---|---|---|---|
| `OPENAI_API_KEY` | vacía | La clave del chat de Nia. Vacía, Nia responde en modo demostración, con reglas. | `.env` o entorno |
| `NEXPLAY_MODELO_NIA` | vacío | El modelo de OpenAI de Nia. Vacío, también modo demostración. | `.env` o entorno |
| `NEXPLAY_NIA_MAX_TOKENS` | 400 | El largo máximo de la respuesta. | `.env` o entorno |
| `NEXPLAY_NIA_TIMEOUT` | 20 | Segundos de espera al modelo. | `.env` o entorno |
| `NEXPLAY_NIA_POR_MINUTO` | 10 | Mensajes a Nia por minuto, por usuario e IP. | `.env` o entorno |
| `NEXPLAY_NIA_RAZONAMIENTO` | false | En true, pide 1,200 tokens y esfuerzo bajo (para un modelo de razonamiento). | `.env` o entorno |
| `NEXPLAY_CORS_ORIGENES` | vacío | Orígenes extra separados por coma. `http://localhost:4200` siempre está permitido. | entorno |
| `NEXPLAY_VALORACIONES_DB` | `backend/datos/valoraciones.db` | Dónde guardar calificaciones, comentarios y votos. | entorno |
| `NEXPLAY_COMENTARIOS_POR_MINUTO` | 3 | Comentarios por minuto, por usuario e IP. | entorno |
| `NEXPLAY_REACCIONES_POR_MINUTO` | 30 | Reacciones por minuto. | entorno |
| `NEXPLAY_VOTOS_NIA_POR_MINUTO` | 30 | Votos a respuestas de Nia por minuto. | entorno |

## 🔌 API

Con la API levantada, tienes el contrato completo en http://localhost:8000/docs. Qué significa cada campo, con
ejemplos, lo explica [backend/api/README.md](backend/api/README.md).

| Método y ruta | Qué hace |
|---|---|
| `GET /catalogo?q=` | Busca juegos por nombre; sin `q`, el catálogo completo con la banda de cada uno. |
| `GET /estado` | El sistema de un vistazo: si Nia usa OpenAI, el release de datos, cuántos juegos y con qué modelo de riesgo. Sin la clave. |
| `GET /panorama` | Cuántas reseñas hay detrás del catálogo, de cuándo son y cuántas traen la señal. |
| `POST /perfil` | Recibe el formulario de alta y devuelve el perfil derivado. |
| `POST /prediccion` | Recibe perfil y `appid`; devuelve riesgo, nivel y los factores que más aportan. |
| `GET /explicacion/{appid}` | Los motivos de queja más frecuentes en las reseñas con señal de ese juego. |
| `GET`, `PUT` y `DELETE /valoraciones/{appid}` | La calificación de 1 a 5 de la segunda opinión: leerla, ponerla o quitarla. |
| `GET` y `POST /comentarios/{appid}` | El hilo público de comentarios del juego. |
| `PUT` y `DELETE /comentarios/{appid}/{id}` | Editar o borrar un comentario propio. |
| `PUT /comentarios/{appid}/{id}/reaccion` | Pulgar arriba a un comentario, en toggle. |
| `POST /nia` | El chat de Nia, sobre un juego o sobre el catálogo. |
| `GET /nia/opiniones?appids=` | La opinión corta de Nia sobre hasta 6 juegos, sin modelo de lenguaje. |
| `PUT` y `DELETE /nia/valoracion/{id}` | El 👍 o 👎 a una respuesta de Nia; el 👎 con «otro motivo» puede llevar una sugerencia. |
| `GET /nia/sugerencias` | El buzón de `/admin`: los 👍 y 👎 a Nia, los 👎 por motivo y las últimas sugerencias, sin usuario. |

Por ejemplo, así pides el riesgo de Hades:

```bash
PERFIL=$(curl -s -X POST http://localhost:8000/perfil -H 'Content-Type: application/json' \
  -d '{"compras_al_anio": 3, "horas_por_semana": 6, "tolerancia_friccion": 3,
       "tags_preferidos": ["Roguelike"], "tags_rechazados": [], "plataforma": "pc"}')
curl -s -X POST http://localhost:8000/prediccion -H 'Content-Type: application/json' \
  -d "{\"perfil\": $PERFIL, \"appid\": 1145360}"
```

`riesgo` ordena los juegos de más a menos riesgo, pero no es una probabilidad calibrada. Por eso la app solo
muestra `nivel`. Los cortes entre bajo, medio y alto están en los percentiles 33.3 y 66.7 de las estimaciones fuera
de pliegue del entrenamiento; en el catálogo quedan 43, 37 y 43.

## ✅ Calidad

| Comando | Qué revisa |
|---|---|
| `make test` | Que las 123 bandas sean las de `backend/referencias/bandas_referencia.json`. También revisa a Nia (contexto, reglas, votos y buzón, sin gastar llamadas), las nueve reglas de «Qué mueve esta estimación», que los niveles tengan una sola definición, que `/estado` no deje salir la clave, que `preparar_entorno --force` no pise bases ajenas y las pruebas del frontend. |
| `make notebooks` | Ejecuta el 00, el 01 y el 02 con el último commit y compara cada salida con la guardada, sin sobrescribirla. Falla si un notebook no termina; las celdas distintas las lista con su diff. |
| `cd frontend && npx ng build` | El build de producción del frontend. |
| `python calidad/capturar_ui.py`, desde `backend/` | Recorre la UI con Playwright (API y frontend corriendo), guarda capturas en `docs/capturas/angular/` y reporta problemas de texto y contraste. |
| `python calidad/preguntas_nia.py --api http://localhost:8000 --etiqueta prueba`, desde `backend/` | Las 25 preguntas a Nia contra una API levantada. |
| El build de Render | Corre `preparar_entorno.py` y `verificar_bandas.py`; falla si una banda cambia o si llega torch a la imagen. |

Cada decisión que se midió (por qué no se entrena con los 123, qué pasa con otra partición, la señal por
banda) está en [docs/evidencia/](docs/evidencia/README.md), con el script que la reproduce en
`backend/calidad/`.

## 🗂️ Estructura del repositorio

```
nexplay/
├── README.md            este archivo
├── Makefile             make help lista los objetivos
├── .env.example         plantilla de variables; el .env real no se versiona
├── CLAUDE.md · AGENTS.md  decisiones y convenciones del proyecto
├── entregables/         lo que se califica: el nicho, la presentación y el documento final
├── notebooks/           00_exploracion, 01_modelo_riesgo y 02_modelos_texto, con su ruta de ejecución
├── backend/             todo el Python; los comandos corren desde aquí
│   ├── api/               FastAPI: endpoints, esquemas, scoring y el chat de Nia (nia/)
│   ├── modelado/          entrenamiento y comparación de bandas
│   ├── analisis/          cuentas del EDA y del texto; motivos.py lo usa la API
│   ├── referencias/       bandas validadas y partición congelada
│   ├── despliegue/        preparar_entorno.py, utilidades.py y el Dockerfile de Render
│   ├── calidad/           verificadores y scripts de evidencia
│   ├── ingesta/           la ingesta original desde Steam
│   ├── publicacion/       lo que se sube a un release
│   ├── operacion/         exportar y moderar comentarios
│   └── requirements*.txt  uno por uso (ver backend/README.md)
├── frontend/            Angular: src/, public/, fuentes/ (la hoja de Nia) y scripts/
├── documento/           solo la fuente LaTeX del documento final (make doc)
└── docs/                evidencia, capturas, diseño e historial
```

Cada carpeta tiene un `README.md` corto que dice qué va ahí y qué no. Cuando corres el proyecto aparecen, sin
versionarse, `backend/datos/`, `backend/modelo/`, `backend/extracto/` y `backend/registros/`.

## 💾 Datos y releases

| Release | Qué trae | Para qué |
|---|---|---|
| `data-v1` | 83 juegos y 123,972 reseñas | Entrenar y medir el modelo; todas las decisiones. |
| `data-v2` | 123 juegos | Los 40 títulos que no están en data-v1 son la prueba externa del 01. |
| `data-v3` | Los juegos y reseñas de data-v2, más los totales públicos de Steam (`resumen_resenas`) | Lo que sirve la API. |

Cada release trae `nexplay_reproducible.db.xz`, una copia sanitizada de la base sin la columna `steamid`, y
`nexplay_extracto.parquet`, un extracto sin texto para el 01. Antes de abrirlos se verifica su sha256
(`descargar_verificado`, en `backend/despliegue/utilidades.py`). Cada extracto nuevo va con un tag nuevo; nunca
se reemplazan los assets de uno publicado. Cómo se arma uno, en la ruta larga del
[paso 4](#4-consigue-los-datos).

## 💬 Contenido de usuarios y moderación

Las calificaciones, los comentarios y los votos a Nia viven en `backend/datos/valoraciones.db`, aparte del
catálogo. No salen de ningún release: `make data` no los toca, y respaldarlos es copiar el archivo. La
identidad es un id anónimo que genera el navegador. Identifica, pero no autentica, así que no sirve como
control de acceso. Por eso `/admin` no tiene contraseña y no muestra nada que no pueda ver cualquiera: el
buzón junta los votos a Nia por motivo y las sugerencias de «otro motivo», sin usuario ni pregunta, y a esas
sugerencias la API les quita correos y teléfonos antes de guardarlas.

Desde `backend/`:

- `python operacion/exportar_valoraciones.py` deja dos CSV en `extracto/`, uno de calificaciones y otro de
  comentarios.
- `python operacion/moderar_comentarios.py [appid]` lista los comentarios, y `--borrar ID` elimina uno con sus
  reacciones. Es la única forma de borrar el comentario de otra persona.

## 🛠️ Solución de problemas

| Síntoma | Causa | Qué hacer |
|---|---|---|
| `make` dice «Falta el entorno .venv», «Faltan las bases» o «Falta el modelo» | Un paso anterior no se corrió. | Corre lo que indica, en orden: `make setup`, `make data`, `make train`. |
| `make setup` dice que hace falta Python 3.12 | `python3` es más viejo (numpy 2.5 pide 3.12). | `make setup PYTHON=python3.14`, o el Python 3.12+ que tengas. |
| El frontend carga pero no trae juegos | Lo abriste como `127.0.0.1`, o la API no está corriendo. | Ábrelo como `http://localhost:4200` y revisa que `make api` siga arriba. |
| `/admin` dice «Despertando…» o «Sin conexión» | La API de Render estaba dormida, o el CORS no deja pasar tu sitio. | Espera hasta un minuto y usa «Reintentar». Si sigue, revisa `NEXPLAY_CORS_ORIGENES` (paso 10). |
| `make api` dice que el puerto 8000 está en uso | Ya hay otra API corriendo. | Apágala, o usa `make api PUERTO=8001` (el frontend en desarrollo espera el 8000). |
| `preparar_entorno.py --force` dice «No piso …» | Esa base no salió de un release (por ejemplo, la base original de la ingesta). | Respáldala o muévela y vuelve a correr. Es a propósito: esa base no se recupera de un release. |
| «sha256 … no coincide» al bajar datos | El asset cambió o la descarga se cortó. | Vuelve a intentar. Si persiste, no sigas: el release no es el esperado. |
| `npm install` falla con `Cannot read properties of null (reading 'edgesOut')` | Un bug de npm 10.9 con las dependencias de Vitest. | Usa `npm ci` (es lo que hace `make setup`). Para regenerar el lockfile, `npx npm@11.19.1 install`. |
| El 00 avisa «Exportación estática apagada» | En Colab, o kaleido no encuentra un Chrome. | Nada que arreglar: las gráficas se ven interactivas. Para tener PNG en local, `.venv/bin/plotly_get_chrome` o `BROWSER_PATH`. |
| `make notebooks` lista celdas distintas | Las salidas guardadas salieron de otro entorno (Colab, otra versión de pandas). | Revisa el diff que imprime: si solo cambia cómo se escribe un tipo o el orden de un empate, no es una cifra distinta. No hace fallar el comando. |
| El build de Render falla con «torch o sentence-transformers en la imagen» | Algo agregó un paquete de notebooks a los requirements de la API. | Esos paquetes van solo en `backend/requirements-notebooks.txt`. |
| Vienes de la estructura anterior y la API no encuentra los datos | `datos/`, `modelo/`, `extracto/` y `registros/` ahora viven en `backend/`. | Muévelas: `mv datos modelo extracto registros backend/`. |

## 👤 Autor y datos

Fernando Axel Ramírez Gómez, Diplomado en Ciencia de Datos, FES Acatlán (UNAM).

Los datos vienen de la API pública de Steam: las reseñas, de `appreviews`, y el precio, la gratuidad y la
nota de Metacritic de cada juego, de `appdetails`. La nota de Metacritic es la que muestra Steam.
