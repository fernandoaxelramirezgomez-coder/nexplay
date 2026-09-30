import { TestBed } from '@angular/core/testing';

import { FactorPrediccion } from '../api/contrato';
import { FactoresModelo } from './factores-modelo';

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

function montar(factores: FactorPrediccion[]) {
  const fixture = TestBed.createComponent(FactoresModelo);
  fixture.componentRef.setInput('factores', factores);
  fixture.detectChanges();
  return [...fixture.nativeElement.querySelectorAll('[data-testid="factor"]')] as HTMLElement[];
}

const limpio = (elemento: Element | null) => elemento?.textContent?.replace(/\s+/g, ' ').trim();

describe('FactoresModelo', () => {
  it('respeta el orden de la API y dice la evidencia de cada factor', () => {
    const [precio, cobertura] = montar([
      factor('precio del juego', { imputado: true, evidencia: 'debil', direccion: 'reduce', contribucion: -1.5 }),
      factor('cobertura de crítica especializada'),
    ]);
    expect(limpio(precio.querySelector('.etiqueta'))).toBe('Precio no disponible: el modelo lo toma como 0');
    expect(limpio(precio.querySelector('[data-testid="factor-evidencia"]'))).toBe(
      'Evidencia débil: con 83 juegos no se distingue de cero',
    );
    expect(precio.dataset['direccion']).toBe('reduce');
    expect(limpio(cobertura.querySelector('[data-testid="factor-evidencia"]'))).toBe('Evidencia sólida');
  });

  it('en un juego gratis, «Es gratis» es un solo factor con su evidencia débil; la extrapolación va en el veredicto', () => {
    const [gratis] = montar([
      factor('gratuidad del juego', { valor_relativo: 'alto', direccion: 'reduce', contribucion: -0.58, evidencia: 'debil' }),
    ]);
    expect(limpio(gratis.querySelector('.etiqueta'))).toBe('Es gratis');
    expect(gratis.dataset['direccion']).toBe('reduce');
    expect(limpio(gratis.querySelector('[data-testid="factor-evidencia"]'))).toBe(
      'Evidencia débil: con 83 juegos no se distingue de cero',
    );
    expect(gratis.textContent).not.toContain('extrapola');
  });

  it('un factor cerca de lo típico va sin flecha de subir ni bajar (Cyberpunk: 86 contra 85.5)', () => {
    const [nota] = montar([
      factor('nota de Metacritic', { valor: 86, referencia: 85.5, cerca_de_lo_tipico: true, contribucion: 0.055 }),
    ]);
    expect(nota.dataset['direccion']).toBe('neutra');
    expect(limpio(nota.querySelector('.etiqueta'))).toBe('Nota de Metacritic: 86 · promedio del catálogo 85.5');
    expect(limpio(nota.querySelector('[data-testid="factor-tipico"]'))).toBe(
      'Cerca de lo típico del catálogo; casi no mueve la estimación.',
    );
  });
});
