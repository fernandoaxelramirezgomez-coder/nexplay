import { TestBed } from '@angular/core/testing';

import { CLAVE_GLOBITOS, hoyLocal } from '../dominio/globito-nia';
import { NiaBurbujaStore } from '../estado/nia-burbuja-store';
import { FranjaNia } from './franja-nia';

function montar(entradas: Record<string, unknown>) {
  TestBed.configureTestingModule({ imports: [FranjaNia] });
  const fixture = TestBed.createComponent(FranjaNia);
  for (const [nombre, valor] of Object.entries(entradas)) {
    fixture.componentRef.setInput(nombre, valor);
  }
  fixture.detectChanges();
  return fixture;
}

function franja(fixture: ReturnType<typeof montar>): HTMLElement | null {
  return fixture.nativeElement.querySelector('[data-testid="franja-nia"]');
}

describe('FranjaNia', () => {
  beforeEach(() => localStorage.removeItem(CLAVE_GLOBITOS));
  afterEach(() => TestBed.resetTestingModule());

  it('sale la primera vez del día, se queda en la visita y queda marcada como vista', () => {
    const fixture = montar({ vista: 'explorar' });
    expect(franja(fixture)?.textContent).toContain('¿Te ayudo a filtrar?');
    expect(JSON.parse(localStorage.getItem(CLAVE_GLOBITOS)!).explorar).toBe(hoyLocal());
    fixture.detectChanges();
    expect(franja(fixture)).not.toBeNull();
  });

  it('no vuelve el mismo día', () => {
    localStorage.setItem(CLAVE_GLOBITOS, JSON.stringify({ explorar: hoyLocal() }));
    expect(franja(montar({ vista: 'explorar' }))).toBeNull();
  });

  it('en Perfil solo sale con perfil creado', () => {
    expect(franja(montar({ vista: 'perfil', disponible: false }))).toBeNull();
    // Sin perfil no se gasta la vez del día.
    expect(localStorage.getItem(CLAVE_GLOBITOS)).toBeNull();
    TestBed.resetTestingModule();
    expect(franja(montar({ vista: 'perfil', disponible: true }))?.textContent).toContain('Ver sugerencias');
  });

  it('su botón le pide a la burbuja lo que ofrecía y la franja se cierra', () => {
    const fixture = montar({ vista: 'comparar', cuantos: 3 });
    expect(franja(fixture)?.textContent).toContain('estos 3');
    fixture.nativeElement.querySelector('[data-testid="franja-nia-accion"]').click();
    fixture.detectChanges();
    expect(TestBed.inject(NiaBurbujaStore).pedido()).toBe('comparar');
    expect(franja(fixture)).toBeNull();
  });

  it('la × la cierra', () => {
    const fixture = montar({ vista: 'explorar' });
    fixture.nativeElement.querySelector('[data-testid="franja-nia-cerrar"]').click();
    fixture.detectChanges();
    expect(franja(fixture)).toBeNull();
  });
});
