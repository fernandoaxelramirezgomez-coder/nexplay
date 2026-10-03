import { CLAVE_ACTIVIDAD } from '../estado/actividad-store';
import { CLAVE_COLOR_PORTADA } from '../estado/color-portada-store';
import { CLAVE_COMPARAR } from '../estado/comparar-store';
import { CLAVE_HISTORIAL } from '../estado/historial-store';
import { CLAVE_PERFIL, CLAVE_PERFIL_V3 } from '../estado/perfil-store';
import { CLAVE_GLOBITOS } from './globito-nia';

/** Lo que borra «Restablecer datos de esta sesión» en /admin: los datos de NexPlay en este
 * navegador. Se queda el id anónimo (nexplay.usuario.v1): con él se editan o borran los
 * comentarios y votos propios, que viven en el servidor. Se quedan las preferencias de tema,
 * menú y volumen, y nunca se toca una clave que no sea de NexPlay. */
export const CLAVES_DE_DATOS = [
  CLAVE_PERFIL,
  CLAVE_PERFIL_V3,
  CLAVE_HISTORIAL,
  CLAVE_COMPARAR,
  CLAVE_ACTIVIDAD,
  CLAVE_GLOBITOS,
  CLAVE_COLOR_PORTADA,
] as const;

/** Borra solo esas claves y devuelve cuáles tenían algo. */
export function restablecerDatos(almacen: Storage = localStorage): string[] {
  const borradas: string[] = [];
  for (const clave of CLAVES_DE_DATOS) {
    try {
      if (almacen.getItem(clave) !== null) {
        borradas.push(clave);
      }
      almacen.removeItem(clave);
    } catch {
      // Almacenamiento bloqueado: no hay nada que borrar.
    }
  }
  return borradas;
}
