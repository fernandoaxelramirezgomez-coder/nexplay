import { JuegoCatalogo } from '../api/contrato';

/** Promedio de las notas de Metacritic del catálogo, para dar contexto al factor
 * "nota de Metacritic". La API no lo expone, así que se calcula aquí sobre /catalogo.
 *
 * El modelo compara contra la media de sus filas de entrenamiento (86.97), no contra
 * este promedio (86.6), pero ambos coinciden en el lado que indican: en los 54 factores
 * de Metacritic del catálogo, ninguno queda "por encima" de uno y "por debajo" del otro. */
export function promedioMetacritic(juegos: readonly JuegoCatalogo[]): number | null {
  const notas = juegos.map((juego) => juego.metacritic).filter((nota) => nota !== null);
  if (!notas.length) {
    return null;
  }
  return notas.reduce((suma, nota) => suma + nota, 0) / notas.length;
}
