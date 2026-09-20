# NexPlay · frontend Angular

Frontend en Angular 22 (componentes standalone, signals, zoneless) que consume la API
FastAPI de la raíz del repo sin modificarla. Gradio (`ui/app.py`) sigue funcionando como
plan B hasta que este frontend lo iguale.

## Correr en local

Requisitos: Node `^22.22.3 || ^24.15.0 || >=26` y la API corriendo en `http://localhost:8000`
(`uvicorn api.main:app` desde la raíz; su CORS ya permite `http://localhost:4200`).

```bash
cd frontend
npm ci
npx ng serve        # http://localhost:4200 (abrir como localhost, no 127.0.0.1: CORS)
```

- `npx ng test --watch=false`: tests unitarios (Vitest).
- `npx ng build`: build de producción en `dist/frontend/browser`.
- `python scripts/capturar_ui.py --frontend angular` (desde la raíz): capturas en
  `docs/capturas/angular/` para revisar los cambios visuales.

Si alguna vez hay que regenerar el lockfile, npm 10.9 falla con
`Cannot read properties of null (reading 'edgesOut')` al resolver las dependencias de
Vitest; `npx npm@11.19.1 install` lo resuelve. `npm ci` con npm 10 funciona bien.

## Qué hay en la ficha

Además del riesgo, los motivos y los factores, cada ficha tiene:

- **Valoración de la segunda opinión**: 👍 / 👎 (uno por persona y juego, se puede cambiar
  o quitar) con el conteo público.
- **Hilo de comentarios**, público y anónimo. Cada quien edita y elimina los suyos
  —con "(editado)" a la vista y una confirmación antes de borrar—, y cualquiera puede
  darle 👍 a un comentario, uno por persona. Para moderar el de alguien más está
  `moderar_comentarios.py`, desde la terminal.
- **Nia**, el chat del juego. Sin clave de OpenAI configurada responde en modo
  demostración, con reglas sobre los mismos datos, y lo dice en pantalla.

La identidad es un id anónimo en `localStorage` (`UsuarioStore`): identifica, no autentica.

## Deuda conocida

- **La cabecera de la ficha arma una URL de Steam en el frontend**
  (`capsule_616x353.jpg`, en `src/app/compartido/portada-ancha.ts`), con respaldo automático
  a `portada_url` si esa imagen no existe. Lo limpio sería que la API la entregue como un
  campo más del catálogo, junto a `portada_url` y `tienda_url`, que ya se derivan del appid
  en `api/catalogo.py`.

## Decisiones

- **Un solo servicio HTTP**: `src/app/api/nexplay-api.ts`, con la URL base en `src/environments/`.
  El contrato está en `src/app/api/contrato.ts`, escrito a partir de las respuestas reales.
- **Diseño**: `docs/diseno/referencia-estilo.md` con las adaptaciones del proyecto, como tokens
  en `src/styles/tokens.css`. Sin Tailwind ni librería de componentes, sin sombras ni gradientes.
- **Vocabulario**: "arrepentimiento temprano", nunca "abandono". El score numérico de riesgo
  nunca se muestra: solo la banda (bajo, medio, alto).
