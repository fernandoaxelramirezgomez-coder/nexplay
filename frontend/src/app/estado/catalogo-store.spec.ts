import { HttpErrorResponse } from '@angular/common/http';
import { ApplicationRef } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { NEVER, Observable, throwError } from 'rxjs';

import { JuegoCatalogo } from '../api/contrato';
import { NexplayApi } from '../api/nexplay-api';
import { BarraLateral } from '../barra-lateral/barra-lateral';
import { CatalogoStore } from './catalogo-store';

/** La API caída: el navegador no llega al servidor (status 0). */
const caida = () => throwError(() => new HttpErrorResponse({ status: 0, url: 'http://localhost:8000/catalogo' }));

/** La API que se simula. Con la API caída tampoco llega el perfil neutro, que la barra
 * lateral pide al montarse; con Render dormido, nada responde. */
function configurar(catalogo: () => Observable<JuegoCatalogo[]>, crearPerfil: () => Observable<never> = () => NEVER) {
  localStorage.clear();
  TestBed.configureTestingModule({
    imports: [BarraLateral],
    providers: [provideRouter([]), { provide: NexplayApi, useValue: { catalogo, crearPerfil } }],
  });
}

async function estable() {
  await TestBed.inject(ApplicationRef).whenStable();
}

describe('CatalogoStore con la API caída o dormida', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('si la API falla, juegos() queda vacío en vez de lanzar, y el error queda a la vista', async () => {
    configurar(caida);
    const store = TestBed.inject(CatalogoStore);
    await estable();

    expect(() => store.juegos()).not.toThrow();
    expect(store.juegos()).toEqual([]);
    expect(store.porAppid().size).toBe(0);
    expect(store.generos()).toEqual([]);
    expect(store.error()).toBeTruthy();
  });

  it('mientras Render despierta, juegos() está vacío y el catálogo sigue cargando', async () => {
    configurar(() => NEVER);
    const store = TestBed.inject(CatalogoStore);
    TestBed.tick();

    expect(store.juegos()).toEqual([]);
    expect(store.cargando()).toBe(true);
  });

  it('con la API caída, la barra lateral se pinta y dice «El catálogo»', async () => {
    vi.stubGlobal('matchMedia', (consulta: string) => ({ matches: false, media: consulta }));
    configurar(caida, caida);
    const fixture = TestBed.createComponent(BarraLateral);
    await fixture.whenStable();

    const html = fixture.nativeElement as HTMLElement;
    expect(html.querySelector('[data-testid="nav-explorar"] .sub')?.textContent?.trim()).toBe('El catálogo');
  });
});
