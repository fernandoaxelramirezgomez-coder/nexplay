import { JuegoCatalogo, JuegoPanorama, NivelRiesgo } from '../api/contrato';
import { Segmento } from '../compartido/graficas/segmento';
import { ORDEN_BANDAS } from './estantes';
import { numero, porcentaje, porcentajeFino } from './formato';
import { positivosPorBanda, precioPorBanda, senalPorBanda } from './panorama';

/** «Antes de pagar, esto importa», en el Inicio: lo que le sirve a quien va a comprar,
 * en dos gráficas con los datos de la API. Nada va escrito a mano: las cifras salen del
 * catálogo y del panorama. */

export type MetricaAntesDePagar = 'senal' | 'precio' | 'positivas';

export const PESTANAS_ANTES_DE_PAGAR: readonly { id: MetricaAntesDePagar; nombre: string }[] = [
  { id: 'senal', nombre: 'Señal' },
  { id: 'precio', nombre: 'Precio' },
  { id: 'positivas', nombre: 'Reseñas positivas' },
];

/** Una pestaña: la cifra grande, su línea y una barra por nivel. */
export interface BarrasAntesDePagar {
  cifra: string;
  linea: string;
  segmentos: Segmento[];
}

export const NOMBRE_NIVEL: Record<NivelRiesgo, string> = {
  bajo: 'Riesgo bajo',
  medio: 'Riesgo medio',
  alto: 'Riesgo alto',
};

type PorAppid = ReadonlyMap<number, JuegoPanorama>;

/** «3×» cuando alcanza para un entero (3.2 veces es más del triple); «1.4×» cuando no. */
function veces(razon: number): string {
  return razon >= 2 ? `${Math.floor(razon)}×` : `${razon.toFixed(1)}×`;
}

function barrasSenal(juegos: readonly JuegoCatalogo[], porAppid: PorAppid): BarrasAntesDePagar | null {
  const filas = senalPorBanda(juegos, porAppid);
  const alto = filas.find((f) => f.banda === 'alto')?.prevalencia;
  const bajo = filas.find((f) => f.banda === 'bajo')?.prevalencia;
  if (!alto || !bajo) {
    return null;
  }
  return {
    // Con un decimal, como en el resto del sitio: 4.2× y no 4×.
    cifra: `${(alto / bajo).toFixed(1)}×`,
    linea: 'más señal de arrepentimiento temprano en riesgo alto',
    segmentos: filas.map((f) => ({
      etiqueta: NOMBRE_NIVEL[f.banda],
      valor: f.prevalencia,
      cifra: porcentajeFino(f.prevalencia),
      banda: f.banda,
      detalle: `${NOMBRE_NIVEL[f.banda]}: ${porcentajeFino(f.prevalencia)} de sus reseñas con señal de arrepentimiento temprano`,
    })),
  };
}

function barrasPrecio(juegos: readonly JuegoCatalogo[]): BarrasAntesDePagar | null {
  const filas = precioPorBanda(juegos);
  const alto = filas.find((f) => f.banda === 'alto')?.mediana;
  const bajo = filas.find((f) => f.banda === 'bajo')?.mediana;
  if (!alto || !bajo) {
    return null;
  }
  return {
    cifra: veces(alto / bajo),
    linea: 'más caros son los de riesgo alto: pagar más no te protege',
    segmentos: filas.map((f) => ({
      etiqueta: NOMBRE_NIVEL[f.banda],
      valor: f.mediana ?? 0,
      cifra: f.mediana === null ? 'sin dato' : `$${numero(Math.round(f.mediana))}`,
      banda: f.banda,
      detalle: `${NOMBRE_NIVEL[f.banda]}: precio mediano de sus juegos de pago, $${numero(Math.round(f.mediana ?? 0))}`,
    })),
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
  };
}

export function barrasAntesDePagar(
  metrica: MetricaAntesDePagar,
  juegos: readonly JuegoCatalogo[],
  porAppid: PorAppid,
): BarrasAntesDePagar | null {
  switch (metrica) {
    case 'senal':
      return barrasSenal(juegos, porAppid);
    case 'precio':
      return barrasPrecio(juegos);
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
