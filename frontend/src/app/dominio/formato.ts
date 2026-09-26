import { JuegoCatalogo } from '../api/contrato';

const PESOS = new Intl.NumberFormat('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export function textoPrecio(juego: Pick<JuegoCatalogo, 'es_gratis' | 'precio_final' | 'moneda'>): string {
  if (juego.es_gratis) {
    return 'Gratis';
  }
  if (juego.precio_final === null) {
    return 'Precio no disponible';
  }
  return `$${PESOS.format(juego.precio_final)} ${juego.moneda ?? ''}`.trim();
}

export function textoMetacritic(metacritic: number | null): string {
  return metacritic === null ? 'Sin nota de Metacritic' : `Metacritic ${metacritic}`;
}

const ENTEROS = new Intl.NumberFormat('es-MX', { maximumFractionDigits: 0 });

/** 184367 → "184,367". Para conteos grandes: sin separador no se leen. */
export function numero(valor: number): string {
  return ENTEROS.format(valor);
}

/** 0.0224 → "2.24%". Un decimal no alcanza cuando la cifra es de dos dígitos por mil. */
export function porcentajeFino(fraccion: number): string {
  return `${(fraccion * 100).toFixed(2)}%`;
}

/** 0.86 → "86%". Solo para frecuencias y coberturas, nunca para el score de riesgo. */
export function porcentaje(fraccion: number): string {
  return `${Math.round(fraccion * 100)}%`;
}

const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

/** "2026-09-14" → { dia: 14, mes: 'sep', anio: 2026 }. Se leen las cifras tal cual: con
 * new Date() la zona horaria del navegador podía mover el día. */
function partesDeFecha(iso: string): { dia: number; mes: string; anio: number } | null {
  const encontrado = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!encontrado) {
    return null;
  }
  return { anio: Number(encontrado[1]), mes: MESES[Number(encontrado[2]) - 1], dia: Number(encontrado[3]) };
}

/** "2023-04-08" → "abr 2023". */
export function mesAnio(iso: string): string {
  const fecha = partesDeFecha(iso);
  return fecha ? `${fecha.mes} ${fecha.anio}` : '';
}

/** Un rango de descarga sin repetir lo que comparten los extremos: "del 14 al 21 sep 2026",
 * "del 30 ago al 2 sep 2026", "del 20 dic 2025 al 3 ene 2026" o "el 14 sep 2026". */
export function rangoDeFechas(desde: string, hasta: string): string {
  const a = partesDeFecha(desde);
  const b = partesDeFecha(hasta);
  if (!a || !b) {
    return '';
  }
  if (a.anio !== b.anio) {
    return `del ${a.dia} ${a.mes} ${a.anio} al ${b.dia} ${b.mes} ${b.anio}`;
  }
  if (a.mes !== b.mes) {
    return `del ${a.dia} ${a.mes} al ${b.dia} ${b.mes} ${b.anio}`;
  }
  return a.dia === b.dia ? `el ${a.dia} ${a.mes} ${a.anio}` : `del ${a.dia} al ${b.dia} ${b.mes} ${b.anio}`;
}
