import { colorDominante } from './color-portada';

/** Una miniatura hecha de bloques de color: [r, g, b, cuántos píxeles]. */
function pixeles(...bloques: [number, number, number, number][]): number[] {
  return bloques.flatMap(([r, g, b, n]) => Array.from({ length: n }, () => [r, g, b, 255]).flat());
}

describe('colorDominante', () => {
  it('gana el tono con más peso, no el promedio', () => {
    const azul = pixeles([20, 60, 220, 60], [220, 30, 30, 20]);
    expect(colorDominante(azul)).toBe('#143cdc');
  });

  it('el fondo negro y los grises no votan', () => {
    const portada = pixeles([5, 5, 8, 300], [128, 128, 130, 200], [230, 120, 20, 10]);
    expect(colorDominante(portada)).toBe('#e67814');
  });

  it('sin ningún color que destaque, no inventa uno', () => {
    expect(colorDominante(pixeles([0, 0, 0, 50], [255, 255, 255, 50], [120, 120, 120, 50]))).toBeNull();
  });
});
