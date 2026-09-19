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
  it('arma la frase con la posición y la dirección', () => {
    expect(fraseFactor(factor('cobertura de crítica especializada'))).toBe(
      'cobertura de crítica especializada, por debajo del promedio del catálogo — aumenta el riesgo estimado.',
    );
    expect(fraseFactor(factor('nota de Metacritic', { valor_relativo: 'alto', direccion: 'reduce' }))).toBe(
      'nota de Metacritic, por encima del promedio del catálogo — reduce el riesgo estimado.',
    );
  });
});
