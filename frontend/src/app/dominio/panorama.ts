import { JuegoCatalogo, JuegoPanorama, NivelRiesgo } from '../api/contrato';
import { ORDEN_BANDAS } from './estantes';

export interface TajadaBanda {
  banda: NivelRiesgo;
  cuantos: number;
  /** 0–1 sobre el total del corte, no sobre el catálogo entero. */
  fraccion: number;
}

/** Cuántos juegos hay en cada banda. El orden es siempre bajo, medio, alto: el mismo de
 * los estantes, para que la gráfica se lea igual que el catálogo. */
export function repartoDeBandas(juegos: readonly JuegoCatalogo[]): TajadaBanda[] {
  const total = juegos.length;
  return ORDEN_BANDAS.map((banda) => {
    const cuantos = juegos.filter((juego) => juego.banda_riesgo === banda).length;
    return { banda, cuantos, fraccion: total ? cuantos / total : 0 };
  });
}

export interface RiesgoDeGenero {
  genero: string;
  /** Cuántos juegos del catálogo tienen ese género: sin esto el porcentaje engaña. */
  total: number;
  altos: number;
  fraccion: number;
}

/** Qué proporción de cada género cae en banda alta. Los géneros con menos juegos que
 * `minimo` se dejan fuera: con los 4 juegos de Carreras, un 25% no dice nada. */
export function riesgoPorGenero(juegos: readonly JuegoCatalogo[], minimo = 5): RiesgoDeGenero[] {
  const cuenta = new Map<string, { total: number; altos: number }>();
  for (const juego of juegos) {
    for (const genero of juego.generos) {
      const fila = cuenta.get(genero) ?? { total: 0, altos: 0 };
      fila.total += 1;
      fila.altos += juego.banda_riesgo === 'alto' ? 1 : 0;
      cuenta.set(genero, fila);
    }
  }
  return [...cuenta.entries()]
    .filter(([, fila]) => fila.total >= minimo)
    .map(([genero, fila]) => ({ genero, ...fila, fraccion: fila.altos / fila.total }))
    .sort((a, b) => b.fraccion - a.fraccion || b.total - a.total || a.genero.localeCompare(b.genero, 'es'));
}

export function mediana(valores: readonly number[]): number | null {
  if (!valores.length) {
    return null;
  }
  const orden = [...valores].sort((a, b) => a - b);
  const medio = Math.floor(orden.length / 2);
  return orden.length % 2 ? orden[medio] : (orden[medio - 1] + orden[medio]) / 2;
}

export interface PrecioDeBanda {
  banda: NivelRiesgo;
  /** null cuando ningún juego de pago de esa banda tiene precio conocido. */
  mediana: number | null;
  cuantos: number;
}

/** Precio mediano por banda, solo de los juegos de pago con precio conocido: meter los
 * gratuitos como cero arrastraría la mediana de las bandas donde hay más. */
export function precioPorBanda(juegos: readonly JuegoCatalogo[]): PrecioDeBanda[] {
  return ORDEN_BANDAS.map((banda) => {
    const precios = juegos
      .filter((juego) => juego.banda_riesgo === banda && !juego.es_gratis && juego.precio_final !== null)
      .map((juego) => juego.precio_final as number);
    return { banda, mediana: mediana(precios), cuantos: precios.length };
  });
}

export interface RepartoDeBanda {
  banda: NivelRiesgo;
  total: number;
  /** Los que cumplen la condición: con nota de crítica, o gratuitos. */
  cuantos: number;
  fraccion: number;
}

function repartoPorBanda(
  juegos: readonly JuegoCatalogo[],
  cumple: (juego: JuegoCatalogo) => boolean,
): RepartoDeBanda[] {
  return ORDEN_BANDAS.map((banda) => {
    const delBanda = juegos.filter((juego) => juego.banda_riesgo === banda);
    const cuantos = delBanda.filter(cumple).length;
    return { banda, total: delBanda.length, cuantos, fraccion: delBanda.length ? cuantos / delBanda.length : 0 };
  });
}

/** Cuántos juegos de cada banda NO tienen nota de Metacritic. La cobertura de crítica es
 * una de las variables del modelo, así que esta gráfica muestra una de sus entradas. */
export function sinCriticaPorBanda(juegos: readonly JuegoCatalogo[]): RepartoDeBanda[] {
  return repartoPorBanda(juegos, (juego) => juego.metacritic === null);
}

/** Cuántos juegos de cada banda son gratuitos: la otra variable del modelo. */
export function gratuitosPorBanda(juegos: readonly JuegoCatalogo[]): RepartoDeBanda[] {
  return repartoPorBanda(juegos, (juego) => juego.es_gratis);
}

export interface LanzamientosDeAnio {
  anio: number;
  cuantos: number;
}

/** Steam publica la fecha como texto ("16 FEB 2023"), no como ISO: se toma el número de
 * cuatro cifras que aparezca. Los juegos sin fecha reconocible no se cuentan. */
export function lanzamientosPorAnio(juegos: readonly JuegoCatalogo[]): LanzamientosDeAnio[] {
  const cuenta = new Map<number, number>();
  for (const juego of juegos) {
    const encontrado = /\b(19|20)\d{2}\b/.exec(juego.fecha_lanzamiento ?? '');
    if (encontrado) {
      const anio = Number(encontrado[0]);
      cuenta.set(anio, (cuenta.get(anio) ?? 0) + 1);
    }
  }
  return [...cuenta.entries()].map(([anio, cuantos]) => ({ anio, cuantos })).sort((a, b) => a.anio - b.anio);
}

export interface SenalDeBanda {
  banda: NivelRiesgo;
  resenas: number;
  casos: number;
  /** 0–1: casos sobre reseñas de esa banda. */
  prevalencia: number;
  juegos: number;
}

/** Cuántas reseñas con señal de arrepentimiento temprano hay en cada banda. Cruza el
 * catálogo (que tiene la banda) con el panorama (que tiene las reseñas): es la
 * comprobación de que la banda ordena algo que se puede contar. */
export function senalPorBanda(
  juegos: readonly JuegoCatalogo[],
  porAppid: ReadonlyMap<number, JuegoPanorama>,
): SenalDeBanda[] {
  return ORDEN_BANDAS.map((banda) => {
    let resenas = 0;
    let casos = 0;
    let conDatos = 0;
    for (const juego of juegos) {
      const fila = juego.banda_riesgo === banda ? porAppid.get(juego.appid) : undefined;
      if (fila) {
        resenas += fila.resenas;
        casos += fila.casos_senal;
        conDatos += 1;
      }
    }
    return { banda, resenas, casos, prevalencia: resenas ? casos / resenas : 0, juegos: conDatos };
  });
}

/** Las etiquetas de Steam, en el orden en que Steam las ordena y con su nombre en
 * español. El tono es la posición en esa escala; 5 es "sin dato". */
export const CONSENSO_STEAM: readonly { clave: string; etiqueta: string; tono: number }[] = [
  { clave: 'Overwhelmingly Positive', etiqueta: 'Extremadamente positivas', tono: 0 },
  { clave: 'Very Positive', etiqueta: 'Muy positivas', tono: 1 },
  { clave: 'Mostly Positive', etiqueta: 'Mayormente positivas', tono: 2 },
  { clave: 'Mixed', etiqueta: 'Variadas', tono: 3 },
  { clave: 'Mostly Negative', etiqueta: 'Mayormente negativas', tono: 4 },
  { clave: 'Overwhelmingly Negative', etiqueta: 'Extremadamente negativas', tono: 4 },
  { clave: 'Very Negative', etiqueta: 'Muy negativas', tono: 4 },
  { clave: 'Negative', etiqueta: 'Negativas', tono: 4 },
  { clave: 'Positive', etiqueta: 'Positivas', tono: 1 },
];

export interface ConsensoDeBanda {
  banda: NivelRiesgo;
  total: number;
  /** Una entrada por etiqueta presente, en el orden de CONSENSO_STEAM. */
  tajadas: { etiqueta: string; valor: number; tono: number }[];
}

/** Qué dice el resumen de Steam de los juegos de cada banda. Es una fuente externa: no
 * entra al modelo, así que coincidir con ella no es circular. */
export function consensoPorBanda(
  juegos: readonly JuegoCatalogo[],
  porAppid: ReadonlyMap<number, JuegoPanorama>,
): ConsensoDeBanda[] {
  const orden = [...CONSENSO_STEAM, { clave: '', etiqueta: 'Sin dato', tono: 5 }];
  return ORDEN_BANDAS.map((banda) => {
    const cuenta = new Map<string, number>();
    let total = 0;
    for (const juego of juegos) {
      if (juego.banda_riesgo !== banda) {
        continue;
      }
      const fila = porAppid.get(juego.appid);
      if (!fila) {
        continue;
      }
      const clave = fila.consenso ?? '';
      cuenta.set(clave, (cuenta.get(clave) ?? 0) + 1);
      total += 1;
    }
    const tajadas = orden
      .filter((entrada) => cuenta.has(entrada.clave))
      .map((entrada) => ({ etiqueta: entrada.etiqueta, valor: cuenta.get(entrada.clave) as number, tono: entrada.tono }));
    return { banda, total, tajadas };
  });
}

/** Juegos de banda alta cuyo consenso en Steam es de los dos escalones más positivos: el
 * caso que justifica mirar las primeras dos horas aparte de la nota general. */
export function positivosEnBandaAlta(
  juegos: readonly JuegoCatalogo[],
  porAppid: ReadonlyMap<number, JuegoPanorama>,
): JuegoCatalogo[] {
  return juegos.filter(
    (juego) =>
      juego.banda_riesgo === 'alto' &&
      ['Overwhelmingly Positive', 'Very Positive'].includes(porAppid.get(juego.appid)?.consenso ?? ''),
  );
}

export interface MotivoDeBanda {
  banda: NivelRiesgo;
  /** Cuántos juegos de esa banda tienen cada motivo como el más mencionado. */
  motivos: { motivo: string; juegos: number }[];
  conMotivo: number;
}

/** Cuál es el motivo más mencionado en cada banda, contando juegos y no reseñas: así un
 * juego con miles de reseñas no decide por los demás. */
export function motivoPrincipalPorBanda(
  juegos: readonly JuegoCatalogo[],
  porAppid: ReadonlyMap<number, JuegoPanorama>,
): MotivoDeBanda[] {
  return ORDEN_BANDAS.map((banda) => {
    const cuenta = new Map<string, number>();
    let conMotivo = 0;
    for (const juego of juegos) {
      const motivo = juego.banda_riesgo === banda ? porAppid.get(juego.appid)?.motivo_principal : null;
      if (motivo) {
        cuenta.set(motivo, (cuenta.get(motivo) ?? 0) + 1);
        conMotivo += 1;
      }
    }
    const motivos = [...cuenta.entries()]
      .map(([motivo, juegos]) => ({ motivo, juegos }))
      .sort((a, b) => b.juegos - a.juegos || a.motivo.localeCompare(b.motivo, 'es'));
    return { banda, motivos, conMotivo };
  });
}
