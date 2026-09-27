import { EMOJI_OTRO, EMOJI_TODOS, emojiDeGenero, opcionesDeGenero } from './generos';

const JUEGOS = [{ generos: ['Acción', 'Indie'] }, { generos: ['Acción'] }, { generos: ['Rol'] }];

describe('géneros de Explorar', () => {
  it('«Todos» primero, con el total, y cada género con cuántos juegos tiene', () => {
    const opciones = opcionesDeGenero(['Acción', 'Indie', 'Rol'], JUEGOS);
    expect(opciones.map((o) => [o.nombre, o.juegos])).toEqual([
      ['Todos', 3],
      ['Acción', 2],
      ['Indie', 1],
      ['Rol', 1],
    ]);
    expect(opciones[0].genero).toBe('');
  });

  it('cada género conocido tiene su emoji y uno nuevo recibe el de mando', () => {
    expect(emojiDeGenero('Acción')).toBe('💥');
    expect(emojiDeGenero('Free to Play')).toBe('🆓');
    expect(emojiDeGenero('Género nuevo de Steam')).toBe(EMOJI_OTRO);
    expect(opcionesDeGenero([], [])[0].emoji).toBe(EMOJI_TODOS);
  });
});
