import { MensajeChat, SugerenciaNia } from '../api/contrato';
import { Sugerencia } from './sugerencias';

/** Lo mismo que MAXIMO_MENSAJES_NIA en api/schemas.py y MAXIMO_CARACTERES_DE_HISTORIAL en
 * api/nia/agente.py: el hilo entero para poder resumirlo, con tope para que no pese más que la
 * pregunta. */
export const MAXIMO_MENSAJES_NIA = 40;
export const MAXIMO_CARACTERES_NIA = 8000;

/** Los mensajes más recientes que caben en los dos topes; la pregunta nueva siempre va. */
export function recortarHistorial(
  mensajes: readonly MensajeChat[],
  maximoMensajes = MAXIMO_MENSAJES_NIA,
  maximoCaracteres = MAXIMO_CARACTERES_NIA,
): MensajeChat[] {
  const elegidos: MensajeChat[] = [];
  let usados = 0;
  for (let i = mensajes.length - 1; i >= 0 && elegidos.length < maximoMensajes; i--) {
    const mensaje = mensajes[i];
    if (elegidos.length && usados + mensaje.contenido.length > maximoCaracteres) {
      break;
    }
    elegidos.unshift(mensaje);
    usados += mensaje.contenido.length;
  }
  return elegidos;
}

/** Lo único del perfil que viaja a Nia: los juegos sugeridos y su porqué, ya escritos. Las
 * respuestas del formulario se quedan en el navegador. */
export function sugerenciasParaNia(sugerencias: readonly Sugerencia[], cuantas = 6): SugerenciaNia[] {
  return sugerencias.slice(0, cuantas).map((sugerencia) => ({
    appid: sugerencia.juego.appid,
    razones: sugerencia.razones
      .filter((razon) => razon.cumple)
      .map((razon) => razon.texto)
      .slice(0, 3),
  }));
}
