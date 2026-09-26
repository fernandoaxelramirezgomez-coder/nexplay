import { FactorPrediccion } from '../api/contrato';
import { factoresVisibles, fraseFactor } from './factores';

const factor = (etiqueta: string, cambios: Partial<FactorPrediccion> = {}): FactorPrediccion => ({
  etiqueta,
  valor_relativo: 'bajo',
  contribucion: 1,
  direccion: 'aumenta',
  ...cambios,
});

describe('factoresVisibles', () => {
  const cobertura = factor('cobertura de crítica especializada');
  const precio = factor('precio del juego', { valor_relativo: 'alto' });
  const nota = factor('nota de Metacritic', { valor_relativo: 'alto', direccion: 'reduce' });

  it('omite el precio cuando es desconocido y el juego no es gratis (GTA V Legacy)', () => {
    const visibles = factoresVisibles([precio, nota, cobertura], {
      precio_final: null,
      es_gratis: false,
      metacritic: 96,
    });
    expect(visibles.map((f) => f.etiqueta)).toEqual(['nota de Metacritic', 'cobertura de crítica especializada']);
  });

  it('conserva el precio en juegos gratuitos: ahí el 0 es cierto', () => {
    const visibles = factoresVisibles([precio], { precio_final: null, es_gratis: true, metacritic: null });
    expect(visibles).toHaveLength(1);
  });

  it('omite la nota de Metacritic cuando no hay nota, pero conserva la cobertura (Wild Hearts)', () => {
    const visibles = factoresVisibles([cobertura, precio, nota], {
      precio_final: 1599,
      es_gratis: false,
      metacritic: null,
    });
    expect(visibles.map((f) => f.etiqueta)).toEqual(['cobertura de crítica especializada', 'precio del juego']);
  });

  it('con precio y nota conocidos no quita nada', () => {
    expect(factoresVisibles([cobertura, precio, nota], { precio_final: 599, es_gratis: false, metacritic: 80 })).toHaveLength(3);
  });
});

describe('fraseFactor', () => {
  it('dice qué se ve del juego y después qué hace con la estimación', () => {
    expect(fraseFactor(factor('cobertura de crítica especializada'))).toBe(
      'No tiene nota de la crítica · en este catálogo eso sube el riesgo estimado.',
    );
    expect(fraseFactor(factor('nota de Metacritic', { valor_relativo: 'alto', direccion: 'reduce' }))).toBe(
      'Su nota de Metacritic está por encima del promedio del catálogo · en este catálogo eso baja el riesgo estimado.',
    );
  });

  it('la gratuidad y el descuento se leen como lo que son, no como un promedio', () => {
    expect(fraseFactor(factor('gratuidad del juego', { valor_relativo: 'alto', direccion: 'aumenta' }))).toBe(
      'Es gratis · en este catálogo eso sube el riesgo estimado.',
    );
    expect(fraseFactor(factor('descuento actual del juego', { valor_relativo: 'bajo', direccion: 'reduce' }))).toBe(
      'No está con descuento · en este catálogo eso baja el riesgo estimado.',
    );
  });

  it('una etiqueta que no conoce no se queda sin frase', () => {
    expect(fraseFactor(factor('variable nueva'))).toBe(
      'variable nueva, por debajo del promedio del catálogo · en este catálogo eso sube el riesgo estimado.',
    );
  });
});
