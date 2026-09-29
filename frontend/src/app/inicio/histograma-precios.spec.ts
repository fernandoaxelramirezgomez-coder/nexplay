import { TestBed } from '@angular/core/testing';

import { RangoDePrecio } from '../dominio/antes-de-pagar';
import { HistogramaPrecios } from './histograma-precios';

const RANGOS: RangoDePrecio[] = [
  { etiqueta: '<200', detalle: 'cuestan menos de $200', porNivel: { bajo: 20, medio: 7, alto: 4 } },
  { etiqueta: '900+', detalle: 'cuestan $900 o más', porNivel: { bajo: 3, medio: 3, alto: 12 } },
];

function montar() {
  TestBed.configureTestingModule({ imports: [HistogramaPrecios] });
  const fixture = TestBed.createComponent(HistogramaPrecios);
  fixture.componentRef.setInput('rangos', RANGOS);
  fixture.detectChanges();
  return fixture;
}

function columnas(fixture: ReturnType<typeof montar>): HTMLElement[] {
  return [...fixture.nativeElement.querySelectorAll('[data-testid="histograma-columna"]')];
}

describe('HistogramaPrecios', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('con «Todos», cada columna suma los tres niveles y lo dice en su detalle', () => {
    const fixture = montar();
    expect(columnas(fixture).map((c) => c.dataset['cuantos'])).toEqual(['31', '18']);
    expect(columnas(fixture)[1].getAttribute('aria-label')).toBe(
      '18 juegos cuestan $900 o más: 3 de riesgo bajo, 3 medio y 12 alto',
    );
  });

  it('elegir un nivel deja solo sus conteos y apaga los tramos de los otros', () => {
    const fixture = montar();
    fixture.nativeElement.querySelector('[data-testid="histograma-nivel"][data-nivel="alto"]').click();
    fixture.detectChanges();
    expect(columnas(fixture).map((c) => c.dataset['cuantos'])).toEqual(['4', '12']);
    expect(columnas(fixture)[1].getAttribute('aria-label')).toBe('12 juegos de riesgo alto cuestan $900 o más');
    const tramoBajo = columnas(fixture)[1].querySelector<HTMLElement>('.tramo[data-banda="bajo"]')!;
    expect(tramoBajo.style.blockSize).toBe('0px');
  });

  it('la nota dice cuántos juegos tienen precio conocido, sumando las columnas', () => {
    const fixture = montar();
    const nota = fixture.nativeElement.querySelector('[data-testid="histograma-nota"]').textContent.replace(/\s+/g, ' ');
    expect(nota).toContain('49 juegos con precio conocido');
  });

  it('antes de verse, las columnas quedan en cero para crecer al entrar', () => {
    const fixture = montar();
    fixture.componentRef.setInput('visible', false);
    fixture.detectChanges();
    const tramos = [...fixture.nativeElement.querySelectorAll('.tramo')] as HTMLElement[];
    expect(tramos.every((t) => t.style.blockSize === '0px')).toBe(true);
  });
});
