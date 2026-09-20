import { textoUtilidad } from './utilidad';

describe('textoUtilidad', () => {
  it('sin valoraciones lo dice', () => {
    expect(textoUtilidad(0, 0)).toBe('Nadie la ha valorado todavía.');
  });

  it('con una sola valoración usa el singular', () => {
    expect(textoUtilidad(1, 1)).toBe('1 persona la encontró útil.');
    expect(textoUtilidad(0, 1)).toBe('1 persona no la encontró útil.');
  });

  it('con varias muestra la proporción', () => {
    expect(textoUtilidad(12, 15)).toBe('12 de 15 personas la encontraron útil.');
    expect(textoUtilidad(0, 3)).toBe('0 de 3 personas la encontraron útil.');
  });
});
