/** Textos cortos de Nia fuera del chat. Viven juntos para que una sola prueba vigile
 * el mismo criterio en todos: Nia describe la estimación, nunca aconseja qué hacer. */

/** La bienvenida del catálogo. Describe qué muestra NexPlay; no pide ni sugiere nada. */
export const SALUDO_CATALOGO =
  '¡Hola! Soy Nia. Aquí ves qué tan seguido un juego deja señales de arrepentimiento temprano' +
  ' en sus primeras dos horas, según las reseñas que la gente publicó en Steam.';

/** El modelo de lenguaje a veces responde con markdown aunque el prompt le pida texto
 * plano: `**así**`, `*así*` o viñetas con guion. Una regla del prompt es una petición, no
 * una garantía, así que el cliente la limpia antes de pintar. No se renderiza markdown:
 * la respuesta de Nia es prosa, y un renderizador solo abriría la puerta a más formato. */
export function sinMarkdown(texto: string): string {
  return texto
    .replace(/\*\*(.+?)\*\*/gs, '$1')
    .replace(/(^|[\s(¡¿"'])\*(\S(?:.*?\S)?)\*(?=[\s).,;:!?"']|$)/gs, '$1$2')
    .replace(/(^|\n)\s*[-*•]\s+/g, '$1')
    .replace(/(^|\n)#{1,6}\s+/g, '$1')
    .replace(/`([^`]+)`/g, '$1')
    .trim();
}

/** Qué es la señal, para alguien que llega nuevo. Va fija arriba del chat, en /nia, en la
 * ficha y en la burbuja, y es lo mismo que Nia contesta si preguntan qué significa: es la
 * misma frase que EXPLICACION_SENAL en backend/api/nia/agente.py (verificar_nia lo revisa). */
export const EXPLICACION_SENAL =
  'El riesgo se basa en reseñas de gente que no recomendó el juego tras jugar menos de 2 horas. Es una señal, no prueba que se arrepintiera.';

/** El saludo del chat sin juego: el de la página de Nia. Corto: el dueño pidió menos texto. */
export const SALUDO_CHAT_CATALOGO = '¡Hola! Soy Nia 👋 ¿Buscas algo en particular o ya tienes un juego en mente?';

/** Lo primero que dice la burbuja al abrirse. */
export const SALUDO_BURBUJA = '¡Hola! ¿Qué juego estás viendo? 👀';

/** En la ficha, el primer mensaje del chat es de ese juego: invita a la pregunta que más
 * se hace, la del riesgo. */
/** La cara según el nivel, la misma que usa Nia en el backend (EMOJI_DEL_NIVEL): ninguna
 * sonrisa junto a un riesgo alto. */
const EMOJI_DEL_NIVEL: Record<string, string> = { bajo: '🙂', medio: '🤔', alto: '😬' };

export function saludoDeJuego(nombre: string, nivel: string): string {
  return `¿Te explico por qué ${nombre} tiene riesgo ${nivel}? ${EMOJI_DEL_NIVEL[nivel] ?? '🤔'}`;
}

/** Fichas de arranque. «Sí, explícamelo» responde al saludo de la ficha. */
export const FICHAS_JUEGO = ['Sí, explícamelo', '¿Qué dicen las reseñas?', '¿Cuánto cuesta?'];
export const FICHAS_CATALOGO = [
  '¿Qué juegos de acción tienen riesgo bajo?',
  '¿Hay algo gratis?',
  '¿De dónde salen los datos?',
];

/** Las dos fichas de la burbuja que no son preguntas: abren el buscador o piden filtros. */
export const HABLAR_DE_UN_JUEGO = 'Hablar de un juego';
export const FILTRAR_EL_CATALOGO = 'Filtrar el catálogo';
export const FICHAS_BURBUJA = [FILTRAR_EL_CATALOGO, HABLAR_DE_UN_JUEGO, '¿Hay algo gratis?'];

/** Lo que Nia contesta sin ir a la API cuando se toca «Filtrar el catálogo». */
export const COMO_FILTRAR =
  'Dime un género, un precio o un riesgo 🔎 Por ejemplo: «juegos de rol de menos de 300 pesos». ¿Por cuál empezamos?';

/** Cuando falta el juego y cuando se suelta el que había. */
export const PIDE_JUEGO = '¿De qué juego hablamos? 👀 Búscalo aquí y te lo explico.';

export type VistaConGlobito = 'explorar' | 'perfil' | 'comparar';

/** El globito de la burbuja, uno por vista: qué ofrece y qué hace su botón. En Comparar
 * nombra cuántos juegos hay, porque lo que ofrece es resumir esos. */
export function textoGlobito(vista: VistaConGlobito, enComparacion = 0): { texto: string; accion: string } {
  switch (vista) {
    case 'explorar':
      return { texto: '¿Te ayudo a filtrar? 🔎 Dime un género, un precio o un riesgo.', accion: 'Filtrar con Nia' };
    case 'perfil':
      return { texto: 'Con tu perfil te sugiero juegos que encajan contigo ✨', accion: 'Ver sugerencias' };
    case 'comparar':
      return { texto: `¿Te resumo en qué se diferencian estos ${enComparacion}? 📊`, accion: 'Resumir la comparación' };
  }
}

const EMOJI = /\p{Extended_Pictographic}/gu;

/** Cuántos emojis lleva un texto: la voz de Nia usa de 1 a 3. */
export function cuantosEmojis(texto: string): number {
  return texto.match(EMOJI)?.length ?? 0;
}
