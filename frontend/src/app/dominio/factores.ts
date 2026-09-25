import { FactorPrediccion, JuegoCatalogo } from '../api/contrato';

const PRECIO = 'precio del juego';
const NOTA_METACRITIC = 'nota de Metacritic';

/** Quita los factores que describen un valor imputado, no el juego:
 * - sin precio conocido, el modelo lo lee como 0 (ver notebook, sección 4);
 * - sin nota de Metacritic, usa la mediana del catálogo.
 * "Cobertura de crítica especializada" se conserva: ahí la ausencia sí es el dato. */
export function factoresVisibles(
  factores: readonly FactorPrediccion[],
  juego: Pick<JuegoCatalogo, 'precio_final' | 'es_gratis' | 'metacritic'>,
): FactorPrediccion[] {
  const precioImputado = juego.precio_final === null && !juego.es_gratis;
  return factores.filter(
    (factor) =>
      !(precioImputado && factor.etiqueta === PRECIO) &&
      !(juego.metacritic === null && factor.etiqueta === NOTA_METACRITIC),
  );
}

export function fraseFactor(factor: FactorPrediccion): string {
  const posicion = factor.valor_relativo === 'alto' ? 'por encima' : 'por debajo';
  return `${factor.etiqueta}, ${posicion} del promedio del catálogo — ${factor.direccion} el riesgo estimado.`;
}
