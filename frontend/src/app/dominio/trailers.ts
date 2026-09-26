import { JuegoCatalogo, JuegoPanorama } from '../api/contrato';
import { ORDEN_BANDAS } from './estantes';

/** Cuántos tráileres por nivel de riesgo lleva el escenario de Explorar. */
export const TRAILERS_POR_NIVEL = 2;

/** Los tráileres del escenario de Explorar: por cada nivel, en orden bajo, medio, alto,
 * los juegos con tráiler que más reseñas tienen en Steam, que son los que más gente
 * reconoce. Sin cifra de reseñas un juego queda al final de su nivel. */
export function elegirTrailers(
  juegos: readonly JuegoCatalogo[],
  porAppid: ReadonlyMap<number, Pick<JuegoPanorama, 'resenas_en_steam'>>,
  porNivel = TRAILERS_POR_NIVEL,
): JuegoCatalogo[] {
  const resenas = (juego: JuegoCatalogo) => porAppid.get(juego.appid)?.resenas_en_steam ?? -1;
  return ORDEN_BANDAS.flatMap((banda) =>
    juegos
      .filter((juego) => juego.banda_riesgo === banda && juego.video_url)
      .sort((a, b) => resenas(b) - resenas(a))
      .slice(0, porNivel),
  );
}
