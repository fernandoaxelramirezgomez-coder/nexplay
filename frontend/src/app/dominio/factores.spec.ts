import { FactorPrediccion } from '../api/contrato';
import {
  TEXTO_EVIDENCIA_DEBIL,
  TEXTO_PRECIO_IMPUTADO,
  TEXTO_TIPICO,
  factoresVisibles,
  fraseFactor,
  lecturaDeJugador,
  textoEvidencia,
} from './factores';

const factor = (etiqueta: string, cambios: Partial<FactorPrediccion> = {}): FactorPrediccion => ({
  etiqueta,
  valor_relativo: 'bajo',
  contribucion: 1,
  direccion: 'aumenta',
  evidencia: 'solida',
  cerca_de_lo_tipico: false,
  valor: null,
  referencia: null,
  imputado: false,
  ...cambios,
});

describe('factoresVisibles', () => {
  const cobertura = factor('cobertura de crítica especializada');
  const precioImputado = factor('precio del juego', { imputado: true, evidencia: 'debil' });
  const nota = factor('nota de Metacritic', { valor: 96, referencia: 85.5, direccion: 'reduce' });

  it('ya no oculta el precio que falta (GTA V Legacy): sale en su lugar, marcado como imputado', () => {
    const visibles = factoresVisibles([precioImputado, nota, cobertura], { metacritic: 96 });
    expect(visibles.map((f) => f.etiqueta)).toEqual(['precio del juego', 'nota de Metacritic', 'cobertura de crítica especializada']);
  });

  it('omite la nota de Metacritic cuando no hay nota, pero conserva la cobertura (Wild Hearts)', () => {
    const visibles = factoresVisibles([cobertura, precioImputado, nota], { metacritic: null });
    expect(visibles.map((f) => f.etiqueta)).toEqual(['cobertura de crítica especializada', 'precio del juego']);
  });
});

describe('lecturaDeJugador', () => {
  it('la nota se lee con su cifra y el promedio del catálogo, sin «por encima» ni «por debajo»', () => {
    const lectura = lecturaDeJugador(factor('nota de Metacritic', { valor: 86, referencia: 85.5, valor_relativo: 'alto' }));
    expect(lectura).toBe('Nota de Metacritic: 86 · promedio del catálogo 85.5');
    expect(lectura).not.toMatch(/por encima|por debajo/);
  });

  it('el precio se lee con su cifra y el precio mediano del catálogo', () => {
    expect(lecturaDeJugador(factor('precio del juego', { valor: 999, referencia: 349.88 }))).toBe(
      'Precio: $999.00 MXN · precio mediano del catálogo $349.88 MXN',
    );
    expect(lecturaDeJugador(factor('precio del juego', { valor: 0, referencia: 349.88 }))).toBe(
      'Precio: gratis · precio mediano del catálogo $349.88 MXN',
    );
  });

  it('el precio imputado dice que falta y que el modelo lo toma como 0', () => {
    expect(lecturaDeJugador(factor('precio del juego', { imputado: true, referencia: 349.88 }))).toBe(TEXTO_PRECIO_IMPUTADO);
  });

  it('la gratuidad, el descuento y la cobertura se leen como lo que son', () => {
    expect(lecturaDeJugador(factor('gratuidad del juego', { valor_relativo: 'alto' }))).toBe('Es gratis');
    expect(lecturaDeJugador(factor('descuento actual del juego', { valor_relativo: 'bajo' }))).toBe('No está con descuento');
    expect(lecturaDeJugador(factor('cobertura de crítica especializada'))).toBe('No tiene nota de la crítica');
  });

  it('una etiqueta que no conoce no se queda sin frase', () => {
    expect(lecturaDeJugador(factor('variable nueva'))).toBe('variable nueva, por debajo del promedio del catálogo');
  });
});

describe('fraseFactor y evidencia', () => {
  it('fuera de la banda dice qué hace con la estimación', () => {
    expect(fraseFactor(factor('cobertura de crítica especializada'))).toBe(
      'No tiene nota de la crítica · en este catálogo eso sube el riesgo estimado.',
    );
  });

  it('dentro de la banda no dice que suba ni baje', () => {
    const frase = fraseFactor(factor('nota de Metacritic', { valor: 86, referencia: 85.5, cerca_de_lo_tipico: true }));
    expect(frase).toBe(`Nota de Metacritic: 86 · promedio del catálogo 85.5 · ${TEXTO_TIPICO}.`);
    expect(frase).not.toMatch(/sube|baja/);
  });

  it('precio, descuento y gratuidad dicen que su evidencia es débil', () => {
    expect(textoEvidencia(factor('precio del juego', { evidencia: 'debil' }))).toBe(TEXTO_EVIDENCIA_DEBIL);
    expect(textoEvidencia(factor('nota de Metacritic'))).toBe('evidencia sólida');
  });
});
