import { VistaConGlobito } from './textos-nia';

/** Qué día vio cada vista su globito, por fecha local: "no vuelve hasta el día siguiente"
 * es el día de quien mira, no el de UTC. */
export type GlobitosVistos = Partial<Record<VistaConGlobito, string>>;

export const CLAVE_GLOBITOS = 'nexplay.globito-nia.v1';

/** 2026-09-26, en la zona del navegador. */
export function hoyLocal(fecha = new Date()): string {
  const dos = (n: number) => String(n).padStart(2, '0');
  return `${fecha.getFullYear()}-${dos(fecha.getMonth() + 1)}-${dos(fecha.getDate())}`;
}

export function debeMostrarGlobito(vista: VistaConGlobito, hoy: string, vistos: GlobitosVistos): boolean {
  return vistos[vista] !== hoy;
}

export function marcarGlobito(vista: VistaConGlobito, hoy: string, vistos: GlobitosVistos): GlobitosVistos {
  return { ...vistos, [vista]: hoy };
}

/** La vista de una ruta, si esa vista tiene globito. La ficha y /nia no: tienen su chat. */
export function vistaConGlobito(ruta: string): VistaConGlobito | null {
  const limpia = ruta.split(/[?#]/)[0];
  if (limpia === '/explorar') return 'explorar';
  if (limpia === '/perfil') return 'perfil';
  if (limpia === '/comparar') return 'comparar';
  return null;
}
