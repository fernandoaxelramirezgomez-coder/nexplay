/** Los géneros del catálogo como filtro de Explorar: cada uno con su emoji y cuántos juegos
 * tiene. Los géneros vienen de Steam, así que uno nuevo recibe el de mando. */

export interface OpcionGenero {
  /** Vacío es «Todos». */
  genero: string;
  nombre: string;
  juegos: number;
  emoji: string;
}

/** Con el selector de variación (U+FE0F) donde hace falta, para que se vea como emoji a
 * color y no como símbolo de texto. */
const EMOJIS: Record<string, string> = {
  'acceso anticipado': '⏳',
  acción: '💥',
  aventura: '🗺\uFE0F',
  carreras: '🏎\uFE0F',
  casual: '🎲',
  deportes: '⚽',
  estrategia: '♟\uFE0F',
  'free to play': '🆓',
  indie: '🎨',
  'multijugador masivo': '🌐',
  rol: '🧙',
  simuladores: '✈\uFE0F',
};

export const EMOJI_TODOS = '🎮';
export const EMOJI_OTRO = '🕹\uFE0F';

export function emojiDeGenero(genero: string): string {
  return EMOJIS[genero.toLowerCase()] ?? EMOJI_OTRO;
}

/** «Todos» primero y después los géneros en el orden en que llegan (alfabético, del
 * catálogo), cada uno con cuántos juegos del catálogo lo tienen. */
export function opcionesDeGenero(
  generos: readonly string[],
  juegos: readonly { generos: readonly string[] }[],
): OpcionGenero[] {
  const cuantos = new Map<string, number>();
  for (const juego of juegos) {
    for (const genero of juego.generos) {
      cuantos.set(genero, (cuantos.get(genero) ?? 0) + 1);
    }
  }
  return [
    { genero: '', nombre: 'Todos', juegos: juegos.length, emoji: EMOJI_TODOS },
    ...generos.map((genero) => ({ genero, nombre: genero, juegos: cuantos.get(genero) ?? 0, emoji: emojiDeGenero(genero) })),
  ];
}
