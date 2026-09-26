/** El color dominante de una portada, a partir de sus píxeles RGBA (una miniatura basta).
 *
 * No es el promedio, que en casi todas las portadas da un gris pardo: se reparten los
 * píxeles en doce tonos del círculo cromático, cada uno pesa por su saturación y su brillo,
 * y gana el tono con más peso. Los píxeles casi negros o casi grises no votan, porque el
 * fondo oscuro de media portada ahogaría el color que la distingue. Devuelve '#rrggbb', o
 * null si la portada no tiene ningún color que destaque (blanco y negro, por ejemplo). */
export function colorDominante(pixeles: ArrayLike<number>): string | null {
  const cubos = Array.from({ length: 12 }, () => ({ peso: 0, r: 0, g: 0, b: 0 }));
  for (let i = 0; i + 3 < pixeles.length; i += 4) {
    const [r, g, b, alfa] = [pixeles[i], pixeles[i + 1], pixeles[i + 2], pixeles[i + 3]];
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    const saturacion = max ? (max - min) / max : 0;
    const brillo = max / 255;
    if (alfa < 128 || brillo < 0.2 || saturacion < 0.25) {
      continue;
    }
    const tono = tonoEnGrados(r, g, b, max, min);
    const cubo = cubos[Math.floor(tono / 30) % 12];
    const peso = saturacion * brillo;
    cubo.peso += peso;
    cubo.r += r * peso;
    cubo.g += g * peso;
    cubo.b += b * peso;
  }
  const mejor = cubos.reduce((a, b) => (b.peso > a.peso ? b : a));
  if (!mejor.peso) {
    return null;
  }
  return '#' + [mejor.r, mejor.g, mejor.b].map((c) => Math.round(c / mejor.peso).toString(16).padStart(2, '0')).join('');
}

function tonoEnGrados(r: number, g: number, b: number, max: number, min: number): number {
  const d = max - min;
  let h: number;
  if (max === r) {
    h = ((g - b) / d) % 6;
  } else if (max === g) {
    h = (b - r) / d + 2;
  } else {
    h = (r - g) / d + 4;
  }
  return (h * 60 + 360) % 360;
}
