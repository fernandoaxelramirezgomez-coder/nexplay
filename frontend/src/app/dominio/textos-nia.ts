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
