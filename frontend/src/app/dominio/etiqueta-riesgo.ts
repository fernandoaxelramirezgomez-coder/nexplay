import { JuegoCatalogo, NivelRiesgo } from '../api/contrato';

/** Cómo se llama el nivel de riesgo en todo el sitio. "Banda" y "Riesgo general" no los
 * entendía quien llegaba sin contexto; el nombre lo eligió el dueño tras la revisión del
 * usuario final. El riesgo es del título, igual para cualquier persona: no hay una versión
 * "para tu perfil", así que el rótulo es uno solo. */
export const ROTULO_RIESGO = 'Riesgo de arrepentimiento';

/** Cómo se cortan los niveles, la única definición del sitio: la misma que CORTES_DE_NIVEL en
 * api/nia/agente.py. Los cortes salen del entrenamiento, no del catálogo, así que el catálogo
 * no queda en tercios; calidad/verificar_niveles.py revisa que ningún texto diga otra cosa. */
export const CORTES_DE_NIVEL =
  'Los cortes entre bajo, medio y alto están en los percentiles 33.3 y 66.7 de las estimaciones fuera de pliegue del entrenamiento';

/** La definición con cuántos juegos del catálogo quedan en cada nivel; sin catálogo, solo los cortes. */
export function definicionDeNiveles(juegos: readonly Pick<JuegoCatalogo, 'banda_riesgo'>[]): string {
  if (!juegos.length) {
    return `${CORTES_DE_NIVEL}.`;
  }
  const cuantos = (nivel: NivelRiesgo) => juegos.filter((juego) => juego.banda_riesgo === nivel).length;
  return `${CORTES_DE_NIVEL}; en el catálogo quedan ${cuantos('bajo')}, ${cuantos('medio')} y ${cuantos('alto')}.`;
}

/** La explicación corta que acompaña al rótulo al pasar el cursor: compara con el catálogo, no
 * es una probabilidad y sale de un modelo entrenado con reseñas a partir de datos del juego.
 * Antes negaba que las reseñas intervinieran, y el modelo sí se entrenó con ellas. "Es del juego, no de
 * ti" responde lo que el nombre podría hacer creer. El detalle de la evidencia va solo en la ⓘ. */
export const EXPLICACION_RIESGO =
  'Compara este juego con el resto del catálogo; no es una probabilidad. Lo estima un modelo entrenado con reseñas de Steam, a partir de datos del juego: es del juego, no de ti.';

/** La versión larga, en la ⓘ del veredicto de la ficha, con las palabras del dueño. Dice
 * «el resto del catálogo» y no un número: los niveles se fijaron con los 83 juegos de
 * entrenamiento, así que «los otros 122» confundía. */
export const EXPLICACION_VEREDICTO =
  'Se estima con datos del juego: precio, descuento, gratuidad y nota de la crítica. Las reseñas de Steam ' +
  'sirvieron para entrenar el modelo y para los motivos, pero no cambian la estimación de un juego. Lo compara ' +
  'con el resto del catálogo y no es una probabilidad. La crítica es evidencia sólida; precio, descuento y ' +
  'gratuidad, débil: con 83 juegos su efecto no se distingue de cero.';
