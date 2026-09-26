import { JuegoCatalogo, JuegoPanorama } from '../api/contrato';

/** Los resúmenes de Steam, con las palabras que usa Steam en español. */
const RESUMEN_STEAM: Record<string, string> = {
  'Overwhelmingly Positive': 'Extremadamente positivas',
  'Very Positive': 'Muy positivas',
  Positive: 'Positivas',
  'Mostly Positive': 'Mayormente positivas',
  Mixed: 'Variadas',
  'Mostly Negative': 'Mayormente negativas',
  Negative: 'Negativas',
  'Very Negative': 'Muy negativas',
  'Overwhelmingly Negative': 'Extremadamente negativas',
};

export interface SentimientoSteam {
  /** 0 a 100, redondeado. */
  porcentaje: number;
  total: number;
  /** El resumen de Steam en español, o null si Steam no lo da. */
  etiqueta: string | null;
}

const ENTEROS = new Intl.NumberFormat('es-MX', { maximumFractionDigits: 0 });

/** Qué dicen los jugadores en Steam: el porcentaje de reseñas positivas sobre el total que
 * Steam reporta. No es crítica especializada y no entra al modelo. */
export function sentimientoSteam(
  fila: Pick<JuegoPanorama, 'resenas_en_steam' | 'positivas_en_steam' | 'consenso'> | undefined,
): SentimientoSteam | null {
  if (!fila?.resenas_en_steam || fila.positivas_en_steam == null) {
    return null;
  }
  return {
    porcentaje: Math.round((fila.positivas_en_steam / fila.resenas_en_steam) * 100),
    total: fila.resenas_en_steam,
    etiqueta: fila.consenso ? (RESUMEN_STEAM[fila.consenso] ?? null) : null,
  };
}

/** "Steam 94 % positivas (87,051 reseñas)". */
export function textoSteam(sentimiento: SentimientoSteam): string {
  return `Steam ${sentimiento.porcentaje} % positivas (${ENTEROS.format(sentimiento.total)} reseñas)`;
}

/** La línea de crítica de un juego: Metacritic y Steam si están los dos; sin Metacritic,
 * lo dice y da Steam. */
export function lineaCritica(juego: Pick<JuegoCatalogo, 'metacritic'>, sentimiento: SentimientoSteam | null): string {
  const critica = juego.metacritic === null ? 'Sin crítica especializada' : `Metacritic ${juego.metacritic}`;
  return sentimiento ? `${critica} · ${textoSteam(sentimiento)}` : critica;
}

/** La advertencia que acompaña al sentimiento de Steam cuando no hay crítica especializada. */
export function advertenciaSinCritica(total: number): string {
  return `Sin crítica especializada; esto viene de ${ENTEROS.format(total)} ${total === 1 ? 'reseña' : 'reseñas'} de jugadores.`;
}

/** La misma advertencia para lo que se dice en NexPlay. Valoraciones y comentarios se
 * cuentan aparte: los comentarios son anónimos y no se pueden sumar como personas. */
export function advertenciaNexplay(valoraciones: number, comentarios: number): string {
  const partes = [
    valoraciones ? `${valoraciones} ${valoraciones === 1 ? 'valoración' : 'valoraciones'}` : '',
    comentarios ? `${comentarios} ${comentarios === 1 ? 'comentario' : 'comentarios'}` : '',
  ].filter(Boolean);
  return `Sin crítica especializada; esto viene de ${partes.join(' y ')} en NexPlay.`;
}
