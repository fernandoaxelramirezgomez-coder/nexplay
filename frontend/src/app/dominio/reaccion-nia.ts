import { NivelRiesgo } from '../api/contrato';

/** Cómo reacciona Nia en la ficha. `emocion` nombra el estado visual (y la animación
 * que le toca); no es el nombre del sprite de la hoja, que a veces no coincide. */
export interface ReaccionNia {
  emocion: 'tranquila' | 'pensativa' | 'cautelosa';
  imagen: string;
  texto: string;
  /** Para el texto alternativo: qué se ve y a qué banda responde. */
  descripcion: string;
}

/** La banda es la única entrada. No se mira el score, ni los motivos, ni el perfil:
 * si la reacción dependiera de otra cosa podría contradecir a la ficha, que muestra la
 * banda. Nia reacciona al riesgo relativo estimado, no a una supuesta confianza del
 * modelo en su estimación.
 *
 * La reacción a la banda está en el gesto, no en el texto. Justo arriba, el veredicto ya
 * nombra la banda y la segunda opinión el motivo principal: si el globo repitiera
 * cualquiera de los dos, sería la misma frase dos veces. Lo que ninguno de esos párrafos
 * ofrece es la conversación, así que el globo invita al chat. Tampoco aconseja qué
 * hacer: decidir le toca a quien lee. */
const REACCIONES: Record<NivelRiesgo, ReaccionNia> = {
  bajo: {
    emocion: 'tranquila',
    imagen: 'nia/ficha-bajo.png',
    texto: '¿Quieres saber qué la separa del resto del catálogo? Pregúntame y te lo explico con los datos de este juego.',
    descripcion: 'Nia sonríe con los brazos arriba: riesgo relativo bajo.',
  },
  medio: {
    emocion: 'pensativa',
    imagen: 'nia/ficha-medio.png',
    texto: '¿Quieres saber por qué quedó a la mitad? Pregúntame y te lo explico con los datos de este juego.',
    descripcion: 'Nia piensa con la mano en la barbilla: riesgo relativo medio.',
  },
  alto: {
    emocion: 'cautelosa',
    imagen: 'nia/ficha-alto.png',
    texto: '¿Quieres saber de dónde sale esta banda? Pregúntame y te lo explico con los datos de este juego.',
    descripcion: 'Nia concentrada frente a su laptop, con gesto serio: riesgo relativo alto.',
  },
};

export function reaccionPara(nivel: NivelRiesgo): ReaccionNia {
  return REACCIONES[nivel];
}
