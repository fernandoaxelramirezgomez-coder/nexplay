import { JuegoCatalogo, NivelRiesgo } from '../api/contrato';

export const ORDEN_BANDAS: readonly NivelRiesgo[] = ['bajo', 'medio', 'alto'];

// Criterio de orden dentro de cada estante: en "bajo" los más seguros
// primero; en "medio" y "alto", los más riesgosos primero.
const DESCENDENTE: Record<NivelRiesgo, boolean> = { bajo: false, medio: true, alto: true };

export interface Estante {
  banda: NivelRiesgo;
  juegos: JuegoCatalogo[];
}

export function agruparEnEstantes(juegos: readonly JuegoCatalogo[]): Estante[] {
  return ORDEN_BANDAS.map((banda) => {
    const signo = DESCENDENTE[banda] ? -1 : 1;
    const delEstante = juegos
      .filter((juego) => juego.banda_riesgo === banda)
      .sort((a, b) => signo * (a.riesgo - b.riesgo));
    return { banda, juegos: delEstante };
  });
}
