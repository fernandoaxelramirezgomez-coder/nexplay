import { Component, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { JuegoCatalogo } from '../api/contrato';
import { juegoDePrueba } from '../dominio/juego-prueba';
import { Buscador } from './buscador';

@Component({
  imports: [Buscador],
  template: `<app-buscador
    [juegos]="juegos()"
    [texto]="texto()"
    [sugerir]="sugerir()"
    (textoCambio)="texto.set($event)"
  />`,
})
class Anfitrion {
  readonly sugerir = signal(true);
  readonly juegos = signal<JuegoCatalogo[]>([
    juegoDePrueba({ appid: 1, nombre: 'Hollow Knight' }),
    juegoDePrueba({ appid: 2, nombre: 'Portal 2' }),
  ]);
  readonly texto = signal('');
}

async function montar() {
  TestBed.configureTestingModule({ imports: [Anfitrion], providers: [provideRouter([])] });
  const fixture = TestBed.createComponent(Anfitrion);
  await fixture.whenStable();
  const html = fixture.nativeElement as HTMLElement;
  const campo = html.querySelector<HTMLInputElement>('[data-testid="filtro-texto"]')!;
  const escribir = async (valor: string) => {
    campo.value = valor;
    campo.dispatchEvent(new Event('input'));
    await fixture.whenStable();
  };
  return { fixture, html, campo, escribir };
}

describe('Buscador', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('sugiere los juegos que coinciden, con lo tecleado en negrita', async () => {
    const { html, escribir } = await montar();
    await escribir('hollow');
    const nombres = [...html.querySelectorAll('[data-testid="sugerencias"] .nombre')].map((n) =>
      n.textContent?.replace(/\s+/g, ' ').trim(),
    );
    expect(nombres).toEqual(['Hollow Knight']);
    // Se resalta el trozo del nombre, con su acentuación y sus mayúsculas, no lo tecleado.
    expect(html.querySelector('[data-testid="sugerencias"] .nombre strong')?.textContent).toBe('Hollow');
    expect(html.querySelector('[data-testid="buscador-vacio"]')).toBeNull();
  });

  it('cada fila lleva la banda con texto, el precio y la crítica', async () => {
    const { html, escribir } = await montar();
    await escribir('hollow');
    const fila = html.querySelector('[data-testid="sugerencias"] li')?.textContent ?? '';
    // En el panel la banda va en corto: "Alto", no "Riesgo general · alto".
    expect(fila).toContain('Alto');
    expect(fila).toContain('MXN');
    expect(fila).toContain('Metacritic');
  });

  it('el pie dice cuántos resultados hay en total, no cuántos se ven', async () => {
    const { fixture, html, escribir } = await montar();
    fixture.componentInstance.juegos.set(
      Array.from({ length: 9 }, (_, i) => juegoDePrueba({ appid: i + 1, nombre: `Portal ${i + 1}` })),
    );
    await escribir('portal');
    expect(html.querySelectorAll('[data-testid="sugerencias"] li').length).toBe(6);
    expect(html.querySelector('[data-testid="buscador-ver-todos"]')?.textContent).toContain('9 resultados');
  });

  it('con un solo resultado lo dice en singular', async () => {
    const { html, escribir } = await montar();
    await escribir('hollow');
    expect(html.querySelector('[data-testid="buscador-ver-todos"]')?.textContent?.trim()).toBe(
      'Ver el resultado en Explorar →',
    );
  });

  it('sin panel no sugiere nada, aunque haya coincidencias', async () => {
    const { fixture, html, escribir } = await montar();
    fixture.componentInstance.sugerir.set(false);
    await escribir('hollow');
    expect(html.querySelector('[data-testid="buscador-panel"]')).toBeNull();
  });

  it('dice que no está en el catálogo cuando no hay ninguno, con el número real', async () => {
    const { html, escribir } = await montar();
    await escribir('zelda');
    expect(html.querySelector('[data-testid="sugerencias"]')).toBeNull();
    const aviso = html.querySelector('[data-testid="buscador-vacio"]')?.textContent ?? '';
    expect(aviso).toContain('«zelda»');
    expect(aviso).toContain('2 juegos');
  });

  it('con el campo vacío no avisa nada', async () => {
    const { html, escribir } = await montar();
    await escribir('   ');
    expect(html.querySelector('[data-testid="buscador-vacio"]')).toBeNull();
    expect(html.querySelector('[data-testid="sugerencias"]')).toBeNull();
  });
});
