import { JuegoCatalogo, JuegoPanorama, NivelRiesgo, PanoramaCatalogo, SenalPorNivel } from '../api/contrato';
import { Segmento } from '../compartido/graficas/segmento';
import { ORDEN_BANDAS } from './estantes';
import { numero, porcentaje, porcentajeFino } from './formato';
import { positivosPorBanda } from './panorama';

/** «Antes de pagar, esto importa», en el Inicio: lo que le sirve a quien va a comprar,
 * en dos gráficas con los datos de la API. Nada va escrito a mano: las cifras salen del
 * catálogo y del panorama. */

export type MetricaAntesDePagar = 'senal' | 'positivas';

export const PESTANAS_ANTES_DE_PAGAR: readonly { id: MetricaAntesDePagar; nombre: string }[] = [
  { id: 'senal', nombre: 'Señal' },
  { id: 'positivas', nombre: 'Reseñas positivas' },
];

/** Una pestaña: la cifra grande, su línea, una barra por nivel y, debajo, lo que hay que saber
 * para leerla. */
export interface BarrasAntesDePagar {
  cifra: string;
  linea: string;
  segmentos: Segmento[];
  notas: string[];
}

export const NOMBRE_NIVEL: Record<NivelRiesgo, string> = {
  bajo: 'Riesgo bajo',
  medio: 'Riesgo medio',
  alto: 'Riesgo alto',
};

type PorAppid = ReadonlyMap<number, JuegoPanorama>;

const veces = (cociente: number, decimales: number) => `${cociente.toFixed(decimales)}×`;

/** «13 o 14»: cuántos juegos tiene cada nivel, sin repetir. */
function juegosPorNivel(corte: SenalPorNivel): string {
  const distintos = [...new Set(corte.niveles.map((n) => n.juegos))].sort((a, b) => a - b);
  return distintos.length > 1 ? `${distintos.slice(0, -1).join(', ')} o ${distintos.at(-1)}` : `${distintos[0]}`;
}

/** La señal en los juegos que el modelo no vio: el número honesto, como el PR-AUC externo. En los
 * 123 el cociente es mayor porque ahí cuentan los 83 de entrenamiento, donde la señal fue su
 * etiqueta; se menciona en una nota, con lo que lo distingue. */
function barrasSenal(cortes: readonly SenalPorNivel[]): BarrasAntesDePagar | null {
  const externos = cortes.find((c) => c.corte === 'externos');
  const catalogo = cortes.find((c) => c.corte === 'catalogo');
  if (!externos?.cociente_alto_bajo) {
    return null;
  }
  const nivel = (n: NivelRiesgo) => externos.niveles.find((f) => f.nivel === n);
  const notas: string[] = [];
  if (externos.ic_inferior !== null && externos.ic_superior !== null) {
    notas.push(
      `Intervalo de 95 %: de ${veces(externos.ic_inferior, 2)} a ${veces(externos.ic_superior, 2)}. ` +
        `Con ${externos.juegos} juegos es una tendencia, no una conclusión firme.`,
    );
  }
  const bajo = nivel('bajo');
  const medio = nivel('medio');
  if (bajo && medio && medio.tasa < bajo.tasa) {
    notas.push(
      'El riesgo medio sale un poco abajo del bajo: en juegos que el modelo no vio, el medio no se separa ' +
        `del bajo, y con ${juegosPorNivel(externos)} juegos por nivel esa diferencia es ruido. ` +
        'Lo que se sostiene es el riesgo alto.',
    );
  }
  if (catalogo?.cociente_alto_bajo) {
    notas.push(
      `En los ${catalogo.juegos} juegos son ${veces(catalogo.cociente_alto_bajo, 1)}, pero ahí cuentan los ` +
        `${catalogo.juegos - externos.juegos} con que se entrenó el modelo.`,
    );
  }
  return {
    // Con un decimal, como en el resto del sitio: 1.9× y no 2×.
    cifra: veces(externos.cociente_alto_bajo, 1),
    linea: `más señal de arrepentimiento temprano en riesgo alto que en bajo, en los ${externos.juegos} juegos que el modelo no vio`,
    segmentos: ORDEN_BANDAS.flatMap((banda) => {
      const fila = nivel(banda);
      return fila
        ? [{
            etiqueta: NOMBRE_NIVEL[banda],
            valor: fila.tasa,
            cifra: porcentajeFino(fila.tasa),
            banda,
            detalle: `${NOMBRE_NIVEL[banda]}: ${porcentajeFino(fila.tasa)} de sus reseñas con señal de arrepentimiento temprano, en ${fila.juegos} juegos que el modelo no vio`,
          }]
        : [];
    }),
    notas,
  };
}

function barrasPositivas(juegos: readonly JuegoCatalogo[], porAppid: PorAppid): BarrasAntesDePagar | null {
  const filas = positivosPorBanda(juegos, porAppid);
  const alto = filas.find((f) => f.banda === 'alto');
  if (!alto?.total) {
    return null;
  }
  return {
    cifra: porcentaje(alto.fraccion),
    linea: 'de los de riesgo alto se ven muy bien en Steam: la nota no basta',
    segmentos: filas.map((f) => ({
      etiqueta: NOMBRE_NIVEL[f.banda],
      valor: f.fraccion,
      cifra: porcentaje(f.fraccion),
      banda: f.banda,
      detalle: `${NOMBRE_NIVEL[f.banda]}: ${f.positivas} de ${f.total} juegos con reseñas muy o extremadamente positivas en Steam`,
    })),
    notas: [],
  };
}

export function barrasAntesDePagar(
  metrica: MetricaAntesDePagar,
  juegos: readonly JuegoCatalogo[],
  porAppid: PorAppid,
  senalPorNivel: readonly SenalPorNivel[] = [],
): BarrasAntesDePagar | null {
  switch (metrica) {
    case 'senal':
      return barrasSenal(senalPorNivel);
    case 'positivas':
      return barrasPositivas(juegos, porAppid);
  }
}

/** Un rango del histograma de precios, con cuántos juegos de cada nivel caen en él. */
export interface RangoDePrecio {
  /** Corta, para debajo de la columna y sin «$»: el pie de la gráfica dice que son pesos,
   * y «<$200» se partía en el teléfono. En dos renglones, se parte en el guion. */
  etiqueta: string;
  /** Para la frase del detalle: «… cuestan de $200 a menos de $400». */
  detalle: string;
  porNivel: Record<NivelRiesgo, number>;
}

/** En pesos (MXN), de lo gratis a lo más caro; cada rango incluye su piso y no su techo. */
const RANGOS: readonly { etiqueta: string; detalle: string; cabe: (juego: JuegoCatalogo) => boolean }[] = [
  { etiqueta: 'Gratis', detalle: 'son gratis', cabe: (j) => j.es_gratis },
  { etiqueta: '<200', detalle: 'cuestan menos de $200', cabe: enRango(0, 200) },
  { etiqueta: '200–400', detalle: 'cuestan de $200 a menos de $400', cabe: enRango(200, 400) },
  { etiqueta: '400–600', detalle: 'cuestan de $400 a menos de $600', cabe: enRango(400, 600) },
  { etiqueta: '600–900', detalle: 'cuestan de $600 a menos de $900', cabe: enRango(600, 900) },
  { etiqueta: '900+', detalle: 'cuestan $900 o más', cabe: enRango(900, Infinity) },
];

function enRango(piso: number, techo: number): (juego: JuegoCatalogo) => boolean {
  return (juego) => !juego.es_gratis && juego.precio_final !== null && juego.precio_final >= piso && juego.precio_final < techo;
}

/** Los juegos del catálogo por rango de precio y nivel. Los que no tienen precio conocido
 * no entran: no hay rango honesto donde ponerlos. */
export function histogramaDePrecios(juegos: readonly JuegoCatalogo[]): RangoDePrecio[] {
  return RANGOS.map((rango) => {
    const porNivel = Object.fromEntries(ORDEN_BANDAS.map((banda) => [banda, 0])) as Record<NivelRiesgo, number>;
    for (const juego of juegos) {
      if (rango.cabe(juego)) {
        porNivel[juego.banda_riesgo] += 1;
      }
    }
    return { etiqueta: rango.etiqueta, detalle: rango.detalle, porNivel };
  });
}

/** Lo que más mencionan las negativas tempranas de todo el catálogo. No es de un juego:
 * la mejora 01 comprobó que el motivo por juego no anticipa mejor que el del catálogo. */
export interface MotivosDelCatalogo {
  segmentos: Segmento[];
  /** Cuántas negativas tempranas mencionan un motivo: de ellas salen los %. */
  conMotivo: string;
  /** Qué parte de todas las negativas tempranas son esas. */
  cobertura: string;
  total: string;
}

export const MOTIVOS_EN_EL_INICIO = 3;

export function motivosDelCatalogo(
  panorama: Pick<PanoramaCatalogo, 'motivos' | 'resenas_clasificadas' | 'casos_senal'> | undefined,
): MotivosDelCatalogo | null {
  if (!panorama?.motivos.length || !panorama.resenas_clasificadas || !panorama.casos_senal) {
    return null;
  }
  return {
    segmentos: panorama.motivos.slice(0, MOTIVOS_EN_EL_INICIO).map((motivo) => ({
      etiqueta: motivo.motivo.charAt(0).toUpperCase() + motivo.motivo.slice(1),
      valor: motivo.frecuencia,
      cifra: porcentaje(motivo.frecuencia),
      detalle: `${motivo.motivo}: ${porcentaje(motivo.frecuencia)} de las negativas tempranas que mencionan un motivo`,
    })),
    conMotivo: numero(panorama.resenas_clasificadas),
    cobertura: porcentaje(panorama.resenas_clasificadas / panorama.casos_senal),
    total: numero(panorama.casos_senal),
  };
}
