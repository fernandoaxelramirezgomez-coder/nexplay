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

/** El titular del veredicto. Al lado del título de la ficha ya hay una píldora que dice
 * "Riesgo medio", así que el titular no repite la etiqueta: dice lo único que la etiqueta
 * no dice, que es qué significa. Son las mismas frases que `_FRASES_BANDA` en api/nia.py. */
const TITULARES_BANDA: Record<NivelRiesgo, Segmento[]> = {
  bajo: [
    { texto: 'Tiende a generar ' },
    { texto: 'menos', clave: true },
    { texto: ' arrepentimiento temprano que el resto del catálogo' },
  ],
  medio: [
    { texto: 'No se distingue', clave: true },
    { texto: ' del resto del catálogo en arrepentimiento temprano' },
  ],
  alto: [
    { texto: 'Tiende a generar ' },
    { texto: 'más', clave: true },
    { texto: ' arrepentimiento temprano que el resto del catálogo' },
  ],
};

export function titularBanda(nivel: NivelRiesgo): Segmento[] {
  return TITULARES_BANDA[nivel];
}

/** Síntesis por reglas (banda + motivo dominante + Metacritic), igual que
 * describe los datos, no recomienda comprar. */
/** La crítica se menciona aquí solo cuando no aparece como factor debajo: con
 * `metacriticEsFactor`, decir "la calificó bien (82)" arriba y "su nota está por debajo
 * del promedio · eso sube el riesgo" abajo son dos lecturas del mismo 82, y la de arriba
 * suena a contradicción. */
export function segundaOpinion(
  nivel: NivelRiesgo,
  motivos: readonly MotivoInsatisfaccion[],
  metacritic: number | null,
  metacriticEsFactor = false,
  clasificadas = 0,
): Segmento[] {
  const segmentos = [...fraseBanda(nivel)];

  if (motivos.length) {
    const principal = motivos[0];
    // El porcentaje sin su n engaña: "contenido 100%" sale de tres reseñas.
    const cuantas = !clasificadas
      ? ' de las reseñas clasificadas'
      : clasificadas === 1
        ? ' de 1 reseña clasificada'
        : ` de las ${clasificadas} reseñas clasificadas`;
    segmentos.push({
      texto:
        ` Entre las reseñas con señal de arrepentimiento temprano, el motivo más mencionado es ${principal.motivo}` +
        ` (${porcentaje(principal.frecuencia)}${cuantas}).`,
    });
  } else {
    segmentos.push({
      texto:
        ' No hay suficientes reseñas de arrepentimiento temprano de este juego para identificar un motivo dominante.',
    });
  }

  if (metacritic === null) {
    segmentos.push({ texto: ' No tiene cobertura de crítica especializada (sin nota de Metacritic).' });
  } else if (!metacriticEsFactor) {
    const juicio = metacritic >= 75 ? 'bien' : metacritic >= 50 ? 'de forma mixta' : 'mal';
    segmentos.push({ texto: ` La crítica especializada lo calificó ${juicio} (Metacritic ${metacritic}).` });
  }

  return segmentos;
}
