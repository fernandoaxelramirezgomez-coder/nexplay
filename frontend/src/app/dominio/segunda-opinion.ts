import { MotivoInsatisfaccion, NivelRiesgo } from '../api/contrato';
import { porcentaje } from './formato';

/** Trozo de frase; `clave` es la única palabra que va en negrita (adaptación 2). */
export interface Segmento {
  texto: string;
  clave?: boolean;
}

// Mismas frases que _FRASES_BANDA en api/nia.py, para que Nia y la ficha digan lo mismo.
const FRASES_BANDA: Record<NivelRiesgo, Segmento[]> = {
  bajo: [
    { texto: 'Comparado con el resto del catálogo, este juego tiende a generar ' },
    { texto: 'menos', clave: true },
    { texto: ' arrepentimiento temprano.' },
  ],
  medio: [
    { texto: 'Comparado con el resto del catálogo, este juego ' },
    { texto: 'no se distingue', clave: true },
    { texto: ' particularmente en arrepentimiento temprano.' },
  ],
  alto: [
    { texto: 'Comparado con el resto del catálogo, este juego tiende a generar ' },
    { texto: 'más', clave: true },
    { texto: ' arrepentimiento temprano.' },
  ],
};

export function fraseBanda(nivel: NivelRiesgo): Segmento[] {
  return FRASES_BANDA[nivel];
}

/** Síntesis por reglas (banda + motivo dominante + Metacritic), igual que
 * describe los datos, no recomienda comprar. */
export function segundaOpinion(
  nivel: NivelRiesgo,
  motivos: readonly MotivoInsatisfaccion[],
  metacritic: number | null,
): Segmento[] {
  const segmentos = [...fraseBanda(nivel)];

  if (motivos.length) {
    const principal = motivos[0];
    segmentos.push({
      texto:
        ` Entre las reseñas con señal de arrepentimiento temprano, el motivo más mencionado es ${principal.motivo}` +
        ` (${porcentaje(principal.frecuencia)} de las reseñas clasificadas).`,
    });
  } else {
    segmentos.push({
      texto:
        ' No hay suficientes reseñas de arrepentimiento temprano de este juego para identificar un motivo dominante.',
    });
  }

  if (metacritic === null) {
    segmentos.push({ texto: ' No tiene cobertura de crítica especializada (sin nota de Metacritic).' });
  } else {
    const juicio = metacritic >= 75 ? 'bien' : metacritic >= 50 ? 'de forma mixta' : 'mal';
    segmentos.push({ texto: ` La crítica especializada lo calificó ${juicio} (Metacritic ${metacritic}).` });
  }

  return segmentos;
}
