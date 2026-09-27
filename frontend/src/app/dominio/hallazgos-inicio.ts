import { JuegoCatalogo, JuegoPanorama, PanoramaCatalogo } from '../api/contrato';
import { cuantasVeces } from './conclusiones-panorama';
import { numero, textoPrecio } from './formato';
import { positivosEnBandaAlta, precioPorBanda, senalPorBanda } from './panorama';

/** Una tarjeta de «Qué encontramos»: la cifra grande (a veces dos, «$580 vs $179»), la
 * frase que la explica, un dato de apoyo y de dónde sale. Todo se calcula con el catálogo y
 * el panorama de la API: nada va escrito a mano. */
export interface Hallazgo {
  id: 'senal' | 'precio' | 'steam';
  cifra: string;
  /** "vs", "de": la palabra chica entre dos cifras. */
  union?: string;
  otra?: string;
  frase: string;
  dato: string;
  fuente: string;
}

type PorAppid = ReadonlyMap<number, JuegoPanorama>;

const DURO = ' ';

function pctFino(fraccion: number): string {
  return `${(fraccion * 100).toFixed(2)}${DURO}%`;
}

function precio(valor: number): string {
  return textoPrecio({ es_gratis: false, precio_final: valor, moneda: null });
}

/** Cuántas veces más señal hay en riesgo alto que en bajo. La frase dice que el modelo no
 * lee las reseñas: en los 40 juegos que nunca vio la diferencia es menor (1.93×, ver
 * docs/evidencia/senal-por-nivel.md), así que no se presume que "no las vio". */
export function hallazgoSenal(juegos: readonly JuegoCatalogo[], porAppid: PorAppid): Hallazgo | null {
  const filas = senalPorBanda(juegos, porAppid);
  const alto = filas.find((f) => f.banda === 'alto');
  const bajo = filas.find((f) => f.banda === 'bajo');
  if (!alto?.prevalencia || !bajo?.prevalencia) {
    return null;
  }
  const razon = alto.prevalencia / bajo.prevalencia;
  const veces = Math.round(razon) >= 2 ? `${Math.round(razon)} veces` : `${razon.toFixed(1)} veces`;
  const resenas = filas.reduce((suma, f) => suma + f.resenas, 0);
  return {
    id: 'senal',
    cifra: `${razon.toFixed(1)}×`,
    frase:
      `Los juegos de riesgo alto tienen ${veces} más reseñas de arrepentimiento temprano que los de riesgo bajo ` +
      `(${pctFino(alto.prevalencia)} vs ${pctFino(bajo.prevalencia)}).`,
    dato: 'El modelo asigna el riesgo con datos del juego, sin leer las reseñas.',
    fuente: `${numero(resenas)} reseñas de Steam`,
  };
}

export function hallazgoPrecio(juegos: readonly JuegoCatalogo[]): Hallazgo | null {
  const filas = precioPorBanda(juegos);
  const alto = filas.find((f) => f.banda === 'alto')?.mediana;
  const bajo = filas.find((f) => f.banda === 'bajo')?.mediana;
  if (!alto || !bajo) {
    return null;
  }
  const veces = cuantasVeces(alto / bajo);
  const cuanto = veces.endsWith('veces') ? `${veces} lo que` : `${veces} que`;
  return {
    id: 'precio',
    cifra: `$${numero(Math.round(alto))}`,
    union: 'vs',
    otra: `$${numero(Math.round(bajo))}`,
    frase: `Los de riesgo alto cuestan ${cuanto} los de riesgo bajo.`,
    dato: `Mediana de precio de los juegos de pago: ${precio(alto)} contra ${precio(bajo)}.`,
    fuente: 'Precios de Steam México',
  };
}

export function hallazgoSteam(juegos: readonly JuegoCatalogo[], porAppid: PorAppid): Hallazgo | null {
  const altos = juegos.filter((juego) => juego.banda_riesgo === 'alto').length;
  if (!altos) {
    return null;
  }
  const positivos = positivosEnBandaAlta(juegos, porAppid).length;
  return {
    id: 'steam',
    cifra: String(positivos),
    union: 'de',
    otra: String(altos),
    frase: 'juegos de riesgo alto tienen reseñas muy o extremadamente positivas en Steam.',
    dato: 'La crítica general no ve lo que pasa en las primeras dos horas.',
    fuente: 'Resumen de reseñas de Steam',
  };
}

/** El trío, en el orden acordado: la señal, el precio y lo que Steam no ve. */
export function hallazgosDelInicio(juegos: readonly JuegoCatalogo[], porAppid: PorAppid): Hallazgo[] {
  return [hallazgoSenal(juegos, porAppid), hallazgoPrecio(juegos), hallazgoSteam(juegos, porAppid)].filter(
    (hallazgo): hallazgo is Hallazgo => hallazgo !== null,
  );
}

export interface CifraMuestra {
  id: 'juegos' | 'resenas' | 'senal' | 'no-vistos';
  cifra: string;
  texto: string;
}

/** «Cómo lo sabemos»: de qué tamaño es la muestra y con cuántos juegos que no vio se probó
 * el modelo (los del catálogo menos los de entrenamiento, que dice el propio modelo). */
export function cifrasDeLaMuestra(juegos: readonly JuegoCatalogo[], panorama: PanoramaCatalogo): CifraMuestra[] {
  const cifras: CifraMuestra[] = [
    { id: 'juegos', cifra: numero(juegos.length), texto: 'juegos de Steam' },
    { id: 'resenas', cifra: numero(panorama.resenas_descargadas), texto: 'reseñas' },
    { id: 'senal', cifra: numero(panorama.casos_senal), texto: 'con señal de arrepentimiento' },
  ];
  const entrenamiento = panorama.modelo?.juegos_entrenamiento;
  if (entrenamiento != null && juegos.length > entrenamiento) {
    cifras.push({
      id: 'no-vistos',
      cifra: numero(juegos.length - entrenamiento),
      texto: 'juegos que el modelo no vio, para probarlo',
    });
  }
  return cifras;
}
