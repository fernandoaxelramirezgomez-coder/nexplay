/** Cómo se llama el nivel de riesgo en todo el sitio. "Banda" y "Riesgo general" no los
 * entendía quien llegaba sin contexto; el nombre lo eligió el dueño tras la revisión del
 * usuario final. El riesgo es del título, igual para cualquier persona: no hay una versión
 * "para tu perfil", así que el rótulo es uno solo. */
export const ROTULO_RIESGO = 'Riesgo de arrepentimiento';

/** La explicación corta que acompaña al rótulo al pasar el cursor, con lo mismo que dice
 * Nia: compara con el catálogo, no es una probabilidad y sale de datos del juego, no de sus
 * reseñas. Antes decía «qué tan seguido deja reseñas negativas» y chocaba con Nia. "Es del
 * juego, no de ti" responde lo que el nombre podría hacer creer. */
export const EXPLICACION_RIESGO =
  'Compara el juego con el resto del catálogo; no es una probabilidad. Lo estima un modelo con datos del juego, no con sus reseñas. Es del juego, no de ti.';

/** La versión larga, en la ⓘ del veredicto de la ficha, con las palabras del dueño. Dice
 * «el resto del catálogo» y no un número: los niveles se fijaron con los 83 juegos de
 * entrenamiento, así que «los otros 122» confundía. */
export const EXPLICACION_VEREDICTO =
  'Se estima con datos del juego: precio, descuento, gratuidad y nota de la crítica. Las reseñas de Steam ' +
  'sirvieron para entrenar el modelo y para los motivos, pero no cambian la estimación de un juego. Lo compara ' +
  'con el resto del catálogo y no es una probabilidad.';
