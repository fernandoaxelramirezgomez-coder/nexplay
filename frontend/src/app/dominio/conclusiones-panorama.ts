import { JuegoCatalogo, JuegoPanorama, MotivoInsatisfaccion, TramoPlaytime } from '../api/contrato';
import { textoPrecio } from './formato';
import {
  MotivoDeBanda,
  gratuitosPorBanda,
  lanzamientosPorAnio,
  positivosEnBandaAlta,
  precioPorBanda,
  repartoDeBandas,
  riesgoPorGenero,
  senalPorBanda,
  sinCriticaPorBanda,
} from './panorama';

/** La conclusión de cada gráfica de Panorama, en una frase, con el corte que se esté
 * mirando. Solo cuenta lo que la gráfica muestra: si el corte cambia y la frase ya no es
 * cierta (un "sigue subiendo" que deja de subir), la frase cambia con él. */

type PorAppid = ReadonlyMap<number, JuegoPanorama>;

/** En prosa el porcentaje lleva espacio, como en la crítica: "60 %". El espacio es duro,
 * para que el signo no quede solo al principio de la línea siguiente. */
const DURO = '\u00a0';

function pct(fraccion: number): string {
  return `${Math.round(fraccion * 100)}${DURO}%`;
}

function pctFino(fraccion: number): string {
  return `${(fraccion * 100).toFixed(2)}${DURO}%`;
}

function lista(partes: readonly string[]): string {
  return partes.length < 2 ? (partes[0] ?? '') : `${partes.slice(0, -1).join(', ')} y ${partes[partes.length - 1]}`;
}

function mayuscula(texto: string): string {
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

function precio(valor: number): string {
  return textoPrecio({ es_gratis: false, precio_final: valor, moneda: null });
}

export function conclusionReparto(juegos: readonly JuegoCatalogo[]): string {
  const tajadas = repartoDeBandas(juegos);
  const con = tajadas.filter((t) => t.cuantos > 0);
  if (!con.length) {
    return 'Ningún juego en este corte.';
  }
  if (con.length === 1) {
    const [unica] = con;
    return unica.cuantos === 1
      ? `El único juego del corte está en riesgo ${unica.banda}.`
      : `Los ${unica.cuantos} juegos del corte están en riesgo ${unica.banda}.`;
  }
  const cuentas = lista(tajadas.map((t) => `${t.cuantos || 'ninguno'} en ${t.banda}`));
  const fracciones = tajadas.map((t) => t.fraccion);
  if (con.length === 3 && Math.max(...fracciones) - Math.min(...fracciones) <= 0.1) {
    return `Tres tercios: ${cuentas}.`;
  }
  const mayor = Math.max(...tajadas.map((t) => t.cuantos));
  const primeras = tajadas.filter((t) => t.cuantos === mayor);
  return primeras.length === 1 ? `Pesa más el riesgo ${primeras[0].banda}: ${cuentas}.` : `${mayuscula(cuentas)}.`;
}

export function conclusionGeneros(juegos: readonly JuegoCatalogo[], minimo: number): string {
  const filas = riesgoPorGenero(juegos, minimo);
  if (!filas.length) {
    return `Ningún género llega a ${minimo} juegos en este corte.`;
  }
  if (filas.length === 1) {
    return `Solo ${filas[0].genero} llega a ${minimo} juegos en este corte: ${pct(filas[0].fraccion)} en riesgo alto.`;
  }
  // Se agrupa por el porcentaje que se lee, no por la fracción exacta: 6/10 y 3/5 empatan.
  const redondo = (fraccion: number) => Math.round(fraccion * 100);
  const alto = redondo(filas[0].fraccion);
  const bajo = redondo(filas[filas.length - 1].fraccion);
  if (alto === bajo) {
    return `Todos los géneros con ${minimo} juegos o más tienen la misma parte en riesgo alto (${alto}${DURO}%).`;
  }
  const arriba = filas.filter((f) => redondo(f.fraccion) === alto).map((f) => f.genero);
  const abajo = filas.filter((f) => redondo(f.fraccion) === bajo).map((f) => f.genero);
  const verbo = arriba.length > 1 ? 'tienen' : 'tiene';
  return `${lista(arriba)} ${verbo} más juegos en riesgo alto (${alto}${DURO}%); ${lista(abajo)}, menos (${bajo}${DURO}%).`;
}

/** Cómo se compara la mediana de riesgo alto con la de bajo, en palabras y sin redondear
 * hacia arriba: 3.2 veces es "más del triple", no "el triple". */
function comparacion(razon: number): string {
  const tramos: [boolean, string][] = [
    [Math.abs(razon - 2) < 0.05, 'el doble de'],
    [Math.abs(razon - 3) < 0.05, 'el triple de'],
    [razon > 2 && razon < 3, 'más del doble de'],
    [razon > 3 && razon < 4, 'más del triple de'],
    [razon >= 0.95 && razon <= 1.05, 'casi igual a'],
    [razon < 0.95, 'menor que'],
  ];
  return tramos.find(([cumple]) => cumple)?.[1] ?? `${razon.toFixed(1)} veces`;
}

export function conclusionPrecio(juegos: readonly JuegoCatalogo[]): string {
  const filas = precioPorBanda(juegos).filter((f) => f.mediana !== null);
  const alto = filas.find((f) => f.banda === 'alto');
  const bajo = filas.find((f) => f.banda === 'bajo');
  if (alto?.mediana && bajo?.mediana) {
    return `En riesgo alto la mediana es ${precio(alto.mediana)}, ${comparacion(alto.mediana / bajo.mediana)} la de bajo (${precio(bajo.mediana)}).`;
  }
  if (!filas.length) {
    return 'Ningún juego de pago con precio conocido en este corte.';
  }
  return `La mediana es ${lista(filas.map((f) => `${precio(f.mediana as number)} en riesgo ${f.banda}`))}.`;
}

/** Los juegos sin Metacritic y, aparte, la señal entre los que sí tienen nota: la duda
 * legítima es si el riesgo alto es solo "no tiene crítica" (docs/evidencia). */
export function conclusionSinCritica(juegos: readonly JuegoCatalogo[], porAppid: PorAppid): string {
  const sin = sinCriticaPorBanda(juegos).filter((f) => f.cuantos > 0);
  const totalSin = sin.reduce((suma, f) => suma + f.cuantos, 0);
  let primera: string;
  if (!totalSin) {
    primera = 'todos tienen nota de Metacritic';
  } else if (sin.length === 1) {
    primera =
      totalSin === 1 ? `el único sin nota está en riesgo ${sin[0].banda}` : `los ${totalSin} sin nota están en riesgo ${sin[0].banda}`;
  } else {
    primera = `los ${totalSin} sin nota se reparten: ${lista(sin.map((f) => `${f.cuantos} en ${f.banda}`))}`;
  }

  const conNota = juegos.filter((juego) => juego.metacritic !== null);
  const senal = senalPorBanda(conNota, porAppid).filter((f) => f.resenas > 0);
  if (!conNota.length || !senal.length) {
    return `${mayuscula(primera)}.`;
  }
  let segunda: string;
  if (senal.length === 3) {
    const sube = senal.every((f, i) => i === 0 || f.prevalencia > senal[i - 1].prevalencia);
    const cifras = `${senal.map((f) => (f.prevalencia * 100).toFixed(2)).join(' → ')}${DURO}%`;
    segunda = `entre los ${conNota.length} con nota, la señal ${sube ? 'sigue subiendo por nivel' : 'por nivel es'}: ${cifras}`;
  } else {
    const partes = senal.map((f) => `${pctFino(f.prevalencia)} en ${f.banda}`);
    segunda = `entre los ${conNota.length} con nota, la señal es de ${lista(partes)}`;
  }
  return totalSin ? `${mayuscula(primera)}; ${segunda}.` : `${mayuscula(segunda)}.`;
}

export function conclusionGratuitos(juegos: readonly JuegoCatalogo[]): string {
  const filas = gratuitosPorBanda(juegos).filter((f) => f.total > 0);
  const total = filas.reduce((suma, f) => suma + f.cuantos, 0);
  if (!total) {
    return 'Ningún juego gratuito en este corte.';
  }
  const cabeza = total === 1 ? 'Hay 1 gratuito' : `Hay ${total} gratuitos`;
  if (filas.length === 1) {
    return `${cabeza}, en riesgo ${filas[0].banda}.`;
  }
  return `${cabeza}: ${lista(filas.map((f) => `${f.cuantos || 'ninguno'} en ${f.banda}`))}.`;
}

/** Los últimos diez años cuentan desde el lanzamiento más reciente del corte, no desde hoy:
 * así la frase no cambia sola cuando cambia el año. */
export function conclusionAnios(juegos: readonly JuegoCatalogo[]): string {
  const anios = lanzamientosPorAnio(juegos);
  if (!anios.length) {
    return 'Ningún juego del corte tiene una fecha de lanzamiento que se pueda leer.';
  }
  if (anios.length === 1) {
    return `Todos salieron en ${anios[0].anio}.`;
  }
  const total = anios.reduce((suma, a) => suma + a.cuantos, 0);
  const desde = anios[anios.length - 1].anio - 10;
  const recientes = anios.filter((a) => a.anio >= desde).reduce((suma, a) => suma + a.cuantos, 0);
  const mayor = Math.max(...anios.map((a) => a.cuantos));
  const pico = anios.filter((a) => a.cuantos === mayor).map((a) => String(a.anio));
  const cola = pico.length === 1 ? `${pico[0]} es el año con más (${mayor})` : `${lista(pico)} son los años con más (${mayor} cada uno)`;
  return `${recientes} de los ${total} salieron de ${desde} en adelante; ${cola}.`;
}

/** Es de toda la muestra: la API no la parte por juego. */
export function conclusionPlaytime(tramos: readonly TramoPlaytime[]): string {
  if (tramos.length < 2) {
    return '';
  }
  const primero = tramos[0];
  const ultimo = tramos[tramos.length - 1];
  const inicio = primero.fraccion < 0.1 ? 'Solo el' : 'El';
  return `${inicio} ${pct(primero.fraccion)} se escribió con ${primero.tramo.toLowerCase()} jugadas; el ${pct(ultimo.fraccion)}, con ${ultimo.tramo.toLowerCase()}.`;
}

export function conclusionSenal(juegos: readonly JuegoCatalogo[], porAppid: PorAppid): string {
  const filas = senalPorBanda(juegos, porAppid).filter((f) => f.resenas > 0);
  const alto = filas.find((f) => f.banda === 'alto');
  const bajo = filas.find((f) => f.banda === 'bajo');
  if (alto && bajo) {
    return `En riesgo alto, el ${pctFino(alto.prevalencia)} de las reseñas trae señal; en bajo, el ${pctFino(bajo.prevalencia)}.`;
  }
  if (!filas.length) {
    return 'Ningún juego de este corte tiene reseñas en la muestra.';
  }
  return `Con señal: ${lista(filas.map((f) => `el ${pctFino(f.prevalencia)} de las reseñas en riesgo ${f.banda}`))}.`;
}

export function conclusionConsenso(juegos: readonly JuegoCatalogo[], porAppid: PorAppid): string {
  const altos = juegos.filter((juego) => juego.banda_riesgo === 'alto').length;
  if (!altos) {
    return 'No hay juegos en riesgo alto en este corte; la barra dice qué opina Steam de los demás.';
  }
  const positivos = positivosEnBandaAlta(juegos, porAppid).length;
  if (altos === 1) {
    return positivos
      ? 'El único juego en riesgo alto tiene reseñas muy o extremadamente positivas en Steam.'
      : 'El único juego en riesgo alto no tiene reseñas muy positivas en Steam.';
  }
  return `${positivos} de los ${altos} juegos en riesgo alto tienen reseñas muy o extremadamente positivas en Steam.`;
}

/** Es de toda la muestra, como las barras que acompaña. */
export function conclusionMotivos(motivos: readonly MotivoInsatisfaccion[]): string {
  if (!motivos.length) {
    return 'Ninguna reseña con señal nombra una de las seis categorías.';
  }
  const [primero, segundo] = motivos;
  const cabeza = `${mayuscula(primero.motivo)} es lo más mencionado (${pct(primero.frecuencia)})`;
  return segundo ? `${cabeza}, seguido de ${segundo.motivo} (${pct(segundo.frecuencia)}).` : `${cabeza}.`;
}

export function conclusionMotivoPorJuego(filas: readonly MotivoDeBanda[]): string {
  const conDatos = filas
    .filter((fila) => fila.conMotivo > 0)
    .map((fila) => {
      const mayor = Math.max(...fila.motivos.map((m) => m.juegos));
      return { banda: fila.banda, primeros: fila.motivos.filter((m) => m.juegos === mayor).map((m) => m.motivo) };
    });
  if (!conDatos.length) {
    return 'Ningún juego del corte llega a cinco reseñas con señal para nombrar un motivo.';
  }
  const comun = conDatos[0].primeros.find((motivo) => conDatos.every((fila) => fila.primeros.includes(motivo)));
  if (!comun) {
    return `El motivo que más juegos encabeza: ${lista(conDatos.map((f) => `${lista(f.primeros)} en ${f.banda}`))}.`;
  }
  const donde: Record<number, string> = { 1: `el riesgo ${conDatos[0].banda}`, 2: `los niveles ${lista(conDatos.map((f) => f.banda))}`, 3: 'los tres niveles' };
  const empates = conDatos
    .filter((fila) => fila.primeros.length > 1)
    .map((fila, i) => `en ${fila.banda} ${i === 0 ? 'empata con ' : 'con '}${lista(fila.primeros.filter((m) => m !== comun))}`);
  const cabeza = `${mayuscula(comun)} encabeza ${donde[conDatos.length]}`;
  return empates.length ? `${cabeza}; ${lista(empates)}.` : `${cabeza}.`;
}
