import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';

import { TarjetaGrafica } from './tarjeta-grafica';

@Component({
  imports: [TarjetaGrafica],
  template: `
    <app-tarjeta-grafica idPrueba="prueba" titulo="Cómo se reparte" conclusion="Tres tercios." fuente="Steam">
      <p ayuda>El texto largo.</p>
      <span class="grafica">barras</span>
    </app-tarjeta-grafica>
  `,
})
class Anfitrion {}

describe('TarjetaGrafica', () => {
  it('muestra título, conclusión y fuente; la ayuda empieza cerrada y la ⓘ la abre dentro de la tarjeta', async () => {
    const fixture = TestBed.createComponent(Anfitrion);
    await fixture.whenStable();
    const html = fixture.nativeElement as HTMLElement;
    const tarjeta = html.querySelector('[data-testid="prueba"]')!;
    expect(tarjeta.querySelector('h3')?.textContent?.trim()).toBe('Cómo se reparte');
    expect(tarjeta.querySelector('[data-testid="tarjeta-conclusion"]')?.textContent?.trim()).toBe('Tres tercios.');
    expect(tarjeta.querySelector('[data-testid="tarjeta-fuente"]')?.textContent?.trim()).toBe('Fuente: Steam');
    expect(tarjeta.querySelector('[data-testid="tarjeta-cuerpo"] .grafica')).not.toBeNull();

    const boton = tarjeta.querySelector<HTMLButtonElement>('[data-testid="tarjeta-info"]')!;
    const ayuda = tarjeta.querySelector<HTMLElement>('[data-testid="tarjeta-ayuda"]')!;
    expect(boton.getAttribute('aria-expanded')).toBe('false');
    expect(ayuda.hidden).toBe(true);
    expect(boton.getAttribute('aria-controls')).toBe(ayuda.id);

    boton.click();
    await fixture.whenStable();
    expect(boton.getAttribute('aria-expanded')).toBe('true');
    expect(ayuda.hidden).toBe(false);
    expect(ayuda.textContent?.trim()).toBe('El texto largo.');
  });
});
