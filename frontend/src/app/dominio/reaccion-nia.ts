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
 * modelo en su estimación. */
const REACCIONES: Record<NivelRiesgo, ReaccionNia> = {
  bajo: {
    emocion: 'tranquila',
    imagen: 'nia/ficha-bajo.png',
    texto: 'Las señales observadas son favorables respecto a otros juegos del catálogo de NexPlay.',
    descripcion: 'Nia sonríe con los brazos arriba: riesgo relativo bajo.',
  },
  medio: {
    emocion: 'pensativa',
    imagen: 'nia/ficha-medio.png',
    texto: 'Hay señales mixtas. Conviene revisar un poco más antes de decidir.',
    descripcion: 'Nia piensa con la mano en la barbilla: riesgo relativo medio.',
  },
  alto: {
    emocion: 'cautelosa',
    imagen: 'nia/ficha-alto.png',
    texto: 'Detecté señales de mayor riesgo relativo. Conviene revisar los motivos frecuentes antes de decidir.',
    descripcion: 'Nia revisa datos en su laptop con gesto serio: riesgo relativo alto.',
  },
};

export function reaccionPara(nivel: NivelRiesgo): ReaccionNia {
  return REACCIONES[nivel];
}
