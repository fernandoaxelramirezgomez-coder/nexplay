import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { CatalogoStore } from '../estado/catalogo-store';
import { PorQueElegir } from './por-que-elegir';

function montar(totalJuegos: number) {
  TestBed.configureTestingModule({
    imports: [PorQueElegir],
    providers: [
      provideRouter([]),
      { provide: CatalogoStore, useValue: { juegos: signal(Array.from({ length: totalJuegos }, (_, i) => ({ appid: i }))) } },
    ],
  });
  const fixture = TestBed.createComponent(PorQueElegir);
  fixture.detectChanges();
  return fixture;
}

function en(fixture: ReturnType<typeof montar>, id: string): HTMLElement {
  return fixture.nativeElement.querySelector(`[data-testid="${id}"]`);
}

describe('PorQueElegir', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('lleva a /explorar con el número del catálogo, como acción secundaria', () => {
    const fixture = montar(123);
    // La principal del Inicio es el buscador del encabezado: aquí no compite otra.
    expect(fixture.nativeElement.querySelectorAll('.boton-cta').length).toBe(0);
    expect(en(fixture, 'por-que-explorar').textContent).toContain('Explorar los 123 juegos');
    expect(en(fixture, 'por-que-explorar').getAttribute('href')).toBe('/explorar');
  });

  it('las cuatro herramientas llevan a su vista', () => {
    const fixture = montar(123);
    const enlaces = [...fixture.nativeElement.querySelectorAll('[data-testid="herramienta-inicio"]')].map(
      (a: Element) => a.getAttribute('href'),
    );
    expect(enlaces).toEqual(['/juego/1938010', '/nia', '/comparar', '/perfil']);
  });

  it('la nave baja a la sección y le pasa el foco al título', () => {
    const fixture = montar(123);
    const seccion = en(fixture, 'inicio-por-que');
    seccion.scrollIntoView = vi.fn();
    en(fixture, 'por-que-nave').click();
    expect(seccion.scrollIntoView).toHaveBeenCalledWith(expect.objectContaining({ block: 'start' }));
    expect(document.activeElement?.id).toBe('titulo-por-que');
  });
});
