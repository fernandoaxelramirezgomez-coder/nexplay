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
