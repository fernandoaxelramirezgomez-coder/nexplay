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
 * Los tres textos describen la banda con la misma frase y cambian una palabra. Ninguno
 * aconseja qué hacer: el veredicto de arriba ya dice que es comparado con el catálogo, y
 * decidir le toca a quien lee. */
const REACCIONES: Record<NivelRiesgo, ReaccionNia> = {
  bajo: {
    emocion: 'tranquila',
    imagen: 'nia/ficha-bajo.png',
    texto: 'La estimación muestra una señal baja de arrepentimiento temprano.',
    descripcion: 'Nia sonríe con los brazos arriba: riesgo relativo bajo.',
  },
  medio: {
    emocion: 'pensativa',
    imagen: 'nia/ficha-medio.png',
    texto: 'La estimación muestra una señal mixta de arrepentimiento temprano.',
    descripcion: 'Nia piensa con la mano en la barbilla: riesgo relativo medio.',
  },
  alto: {
    emocion: 'cautelosa',
    imagen: 'nia/ficha-alto.png',
    texto: 'La estimación muestra una señal alta de arrepentimiento temprano.',
    descripcion: 'Nia concentrada frente a su laptop, con gesto serio: riesgo relativo alto.',
  },
};

export function reaccionPara(nivel: NivelRiesgo): ReaccionNia {
  return REACCIONES[nivel];
}
