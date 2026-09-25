import { redondearPromedio, textoCalificacion } from './calificacion';

describe('redondearPromedio', () => {
  it('deja un decimal', () => {
    expect(redondearPromedio(4.2)).toBe(4.2);
    expect(redondearPromedio(3.5)).toBe(3.5);
    expect(redondearPromedio(4.1666)).toBe(4.2);
  });

  it('redondea la mitad hacia arriba, sin que lo tuerza la coma flotante', () => {
    expect(redondearPromedio(4.25)).toBe(4.3);
    expect(redondearPromedio(4.35)).toBe(4.4);
    expect(redondearPromedio(2.05)).toBe(2.1);
  });

  it('no se sale de 1 a 5 con promedios en los extremos', () => {
    expect(redondearPromedio(5)).toBe(5);
    expect(redondearPromedio(1)).toBe(1);
  });
});

describe('textoCalificacion', () => {
  it('sin calificaciones lo dice, en vez de mostrar un cero', () => {
    expect(textoCalificacion(null, 0)).toBe('Nadie la ha calificado todavía.');
  });

  it('muestra el promedio con un decimal, la estrella y el total', () => {
    expect(textoCalificacion(4.2, 15)).toBe('4.2 ★ · 15 valoraciones');
    expect(textoCalificacion(3, 2)).toBe('3.0 ★ · 2 valoraciones');
  });

  it('usa el singular con una sola valoración', () => {
    expect(textoCalificacion(5, 1)).toBe('5.0 ★ · 1 valoración');
  });
});
