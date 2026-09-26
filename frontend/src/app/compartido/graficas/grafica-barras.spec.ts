import { Component, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { GraficaBarras } from './grafica-barras';
import { Segmento } from './segmento';

@Component({
  imports: [GraficaBarras],
  template: `<app-grafica-barras [segmentos]="segmentos()" [maximo]="maximo()" />`,
})
class Anfitrion {
  readonly segmentos = signal<Segmento[]>([]);
  readonly maximo = signal<number | undefined>(undefined);
}

async function montar(segmentos: Segmento[], maximo?: number) {
  TestBed.configureTestingModule({ imports: [Anfitrion] });
  const fixture = TestBed.createComponent(Anfitrion);
  fixture.componentInstance.segmentos.set(segmentos);
  fixture.componentInstance.maximo.set(maximo);
  await fixture.whenStable();
  return fixture.nativeElement as HTMLElement;
}

describe('GraficaBarras', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('la cifra va en texto, no solo en el largo de la barra', async () => {
    const html = await montar([{ etiqueta: 'rendimiento', valor: 0.41, cifra: '41%' }]);
    expect(html.querySelector('.valor')?.textContent?.trim()).toBe('41%');
    expect(html.querySelector('.nombre')?.textContent?.trim()).toBe('rendimiento');
  });

  it('sin máximo declarado, el mayor llena la pista y el resto va en proporción', async () => {
    const html = await montar([
      { etiqueta: 'a', valor: 10, cifra: '10' },
      { etiqueta: 'b', valor: 5, cifra: '5' },
    ]);
    const anchos = [...html.querySelectorAll<HTMLElement>('.barra')].map((b) => b.style.inlineSize);
    expect(anchos[0]).toBe('100%');
    expect(anchos[1]).toBe('50%');
  });

  it('con máximo declarado, las barras se miden contra él', async () => {
    const html = await montar([{ etiqueta: 'a', valor: 0.25, cifra: '25%' }], 1);
    expect(html.querySelector<HTMLElement>('.barra')?.style.inlineSize).toBe('25%');
  });

  /** Antes había un mínimo de 6 px para que un segmento chico no desapareciera, pero
   * pintaba igual un cero que un uno y desalineaba el borde derecho de las barras cortas
   * con su porcentaje. La cifra de al lado ya dice lo que la barra no alcanza a mostrar. */
  it('un segmento en cero no pinta barra, y su detalle sigue siendo accesible', async () => {
    const html = await montar([
      { etiqueta: 'a', valor: 0, cifra: '0', detalle: 'ningún juego' },
      { etiqueta: 'b', valor: 3, cifra: '3' },
    ]);
    expect(html.querySelector<HTMLElement>('.barra')?.style.inlineSize).toBe('0px');
    expect(html.querySelector('.barra .solo-lector')?.textContent).toBe('ningún juego');
  });

  it('pinta cada barra con el color de su banda', async () => {
    const html = await montar([{ etiqueta: 'alto', valor: 1, cifra: '1', banda: 'alto' }]);
    expect(html.querySelector('.fila')?.getAttribute('data-banda')).toBe('alto');
  });
});
