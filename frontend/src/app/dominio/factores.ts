import { FactorPrediccion, JuegoCatalogo } from '../api/contrato';

const PRECIO = 'precio del juego';
const NOTA_METACRITIC = 'nota de Metacritic';

/** Frases que la ficha pinta y Nia dice igual (api/nia/agente.py las repite y
 * calidad/verificar_nia.py comprueba que sigan aquí). */
export const TEXTO_TIPICO = 'cerca de lo típico del catálogo; casi no mueve la estimación';
export const TEXTO_EVIDENCIA_SOLIDA = 'evidencia sólida';
export const TEXTO_EVIDENCIA_DEBIL = 'evidencia débil: con 83 juegos no se distingue de cero';
export const TEXTO_PRECIO_IMPUTADO = 'Precio no disponible: el modelo lo toma como 0';

const PESOS = new Intl.NumberFormat('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** Quita solo la nota de Metacritic de un juego sin nota: ahí el modelo usa la mediana del
 * catálogo y "cobertura de crítica especializada" ya dice lo que importa, que no hay nota.
 * El precio que falta ya no se esconde: se muestra marcado como imputado, en su lugar por
 * aporte, porque así lo calculó el modelo y junto al veredicto va el aviso. */
export function factoresVisibles(
  factores: readonly FactorPrediccion[],
  juego: Pick<JuegoCatalogo, 'metacritic'>,
): FactorPrediccion[] {
  return factores.filter((factor) => !(juego.metacritic === null && factor.etiqueta === NOTA_METACRITIC));
}

/** Cómo se lee cada variable de sí o no en palabras de jugador. La nota y el precio no están
 * aquí: se leen con su cifra y la referencia del catálogo (lecturaDeJugador), sin "por encima"
 * ni "por debajo", porque el modelo los compara contra su media de entrenamiento y la ficha
 * contra el catálogo.
 *
 * Las mismas frases están en `_LECTURA_FACTORES` (api/nia/agente.py): Nia explica la banda con
 * estas variables, así que las dos tablas cambian juntas o Nia contradice a la ficha. */
const COMO_SE_LEE: Record<string, { alto: string; bajo: string }> = {
  'gratuidad del juego': { alto: 'Es gratis', bajo: 'Es de pago' },
  'descuento actual del juego': { alto: 'Está con descuento', bajo: 'No está con descuento' },
  'cobertura de crítica especializada': {
    alto: 'Tiene nota de la crítica',
    bajo: 'No tiene nota de la crítica',
  },
  'compras declaradas por año': { alto: 'Compras más juegos que el promedio', bajo: 'Compras menos juegos que el promedio' },
};

function pesos(valor: number): string {
  return `$${PESOS.format(valor)} MXN`;
}

/** Qué se ve del juego, en una frase. Sin entrada en la tabla cae a la forma nominal de
 * la API, que siempre se puede leer aunque suene más técnica. */
export function lecturaDeJugador(factor: FactorPrediccion): string {
  if (factor.etiqueta === NOTA_METACRITIC && factor.valor !== null) {
    const referencia = factor.referencia === null ? '' : ` · promedio del catálogo ${factor.referencia.toFixed(1)}`;
    return `Nota de Metacritic: ${factor.valor}${referencia}`;
  }
  if (factor.etiqueta === PRECIO) {
    if (factor.imputado || factor.valor === null) {
      return TEXTO_PRECIO_IMPUTADO;
    }
    const precio = factor.valor === 0 ? 'gratis' : pesos(factor.valor);
    const referencia = factor.referencia === null ? '' : ` · precio mediano del catálogo ${pesos(factor.referencia)}`;
    return `Precio: ${precio}${referencia}`;
  }
  const lectura = COMO_SE_LEE[factor.etiqueta]?.[factor.valor_relativo];
  if (lectura) {
    return lectura;
  }
  const posicion = factor.valor_relativo === 'alto' ? 'por encima' : 'por debajo';
  return `${factor.etiqueta}, ${posicion} del promedio del catálogo`;
}

export function textoEvidencia(factor: FactorPrediccion): string {
  return factor.evidencia === 'solida' ? TEXTO_EVIDENCIA_SOLIDA : TEXTO_EVIDENCIA_DEBIL;
}

export function fraseFactor(factor: FactorPrediccion): string {
  if (factor.cerca_de_lo_tipico) {
    return `${lecturaDeJugador(factor)} · ${TEXTO_TIPICO}.`;
  }
  const efecto = factor.direccion === 'aumenta' ? 'sube' : 'baja';
  return `${lecturaDeJugador(factor)} · en este catálogo eso ${efecto} el riesgo estimado.`;
}
