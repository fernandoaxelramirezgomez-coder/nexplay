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

/** Cómo se lee cada variable del modelo en palabras de jugador. La API manda etiquetas
 * nominales ("gratuidad del juego") pensadas para la frase vieja; aquí se convierten en
 * lo que la persona ve del juego, y después se dice qué hace con la estimación.
 *
 * `alto` y `bajo` son la posición frente al promedio del catálogo, no un juicio.
 *
 * Las mismas frases están en `_LECTURA_FACTORES` (api/nia.py): Nia explica la banda con
 * estas variables, así que las dos tablas cambian juntas o Nia contradice a la ficha. */
const COMO_SE_LEE: Record<string, { alto: string; bajo: string }> = {
  'gratuidad del juego': { alto: 'Es gratis', bajo: 'Es de pago' },
  'precio del juego': { alto: 'Cuesta más que el promedio del catálogo', bajo: 'Cuesta menos que el promedio' },
  'descuento actual del juego': { alto: 'Está con descuento', bajo: 'No está con descuento' },
  'cobertura de crítica especializada': {
    alto: 'Tiene nota de la crítica',
    bajo: 'No tiene nota de la crítica',
  },
  'nota de Metacritic': {
    alto: 'Su nota de Metacritic está por encima del promedio del catálogo',
    bajo: 'Su nota de Metacritic está por debajo del promedio',
  },
  'compras declaradas por año': { alto: 'Compras más juegos que el promedio', bajo: 'Compras menos juegos que el promedio' },
};

/** Qué se ve del juego, en una frase. Sin entrada en la tabla cae a la forma nominal de
 * la API, que siempre se puede leer aunque suene más técnica. */
export function lecturaDeJugador(factor: FactorPrediccion): string {
  const lectura = COMO_SE_LEE[factor.etiqueta]?.[factor.valor_relativo];
  if (lectura) {
    return lectura;
  }
  const posicion = factor.valor_relativo === 'alto' ? 'por encima' : 'por debajo';
  return `${factor.etiqueta}, ${posicion} del promedio del catálogo`;
}

export function fraseFactor(factor: FactorPrediccion): string {
  const efecto = factor.direccion === 'aumenta' ? 'sube' : 'baja';
  return `${lecturaDeJugador(factor)} · en este catálogo eso ${efecto} el riesgo estimado.`;
}
