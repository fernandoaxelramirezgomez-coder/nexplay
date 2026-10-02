import { HttpErrorResponse } from '@angular/common/http';
import { ApplicationRef, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { NEVER, Observable, throwError } from 'rxjs';

import { NexplayApi } from '../api/nexplay-api';
import { ColumnaComparar } from '../comparar/columna-comparar';
import { juegoDePrueba } from '../dominio/juego-prueba';
import { Ficha } from '../ficha/ficha';
import { CatalogoStore } from './catalogo-store';
import { PanoramaStore } from './panorama-store';
import { PerfilStore } from './perfil-store';

/** El perfil neutro no llega: la API está caída (status 0) o Render sigue dormido. */
const caida = () => throwError(() => new HttpErrorResponse({ status: 0, url: 'http://localhost:8000/perfil' }));

const JUEGO = juegoDePrueba();

/** Todo lo demás de la API no responde: aquí solo importa el perfil. */
function api(crearPerfil: () => Observable<never>): Partial<NexplayApi> {
  return new Proxy({} as Partial<NexplayApi>, {
    get: (_, metodo) => (metodo === 'crearPerfil' ? crearPerfil : () => NEVER),
  });
}

function configurar(crearPerfil: () => Observable<never>) {
  localStorage.clear();
  TestBed.configureTestingModule({
    providers: [
      provideRouter([]),
      { provide: NexplayApi, useValue: api(crearPerfil) },
      {
        provide: CatalogoStore,
        useValue: {
          juegos: signal([JUEGO]),
          porAppid: signal(new Map([[JUEGO.appid, JUEGO]])),
          cargando: signal(false),
          error: signal(undefined),
          promedioMetacritic: signal(85.5),
        },
      },
      { provide: PanoramaStore, useValue: { datos: signal(undefined), porAppid: signal(new Map()) } },
    ],
  });
}

async function estable() {
  await TestBed.inject(ApplicationRef).whenStable();
}

describe('PerfilStore sin perfil guardado y sin /perfil', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('si /perfil falla, efectivo() queda en null en vez de lanzar', async () => {
    configurar(caida);
    const perfil = TestBed.inject(PerfilStore);
    await estable();

    expect(() => perfil.efectivo()).not.toThrow();
    expect(perfil.efectivo()).toBeNull();
    expect(perfil.cargandoNeutro()).toBe(false);
  });

  it('mientras /perfil tarda, efectivo() es null y se sabe que está cargando', () => {
    configurar(() => NEVER);
    const perfil = TestBed.inject(PerfilStore);
    TestBed.tick();

    expect(perfil.efectivo()).toBeNull();
    expect(perfil.cargandoNeutro()).toBe(true);
  });

  it('con /perfil caído, la ficha se pinta y dice que no pudo calcular el riesgo', () => {
    vi.stubGlobal('matchMedia', (consulta: string) => ({ matches: false, media: consulta }));
    configurar(caida);
    const fixture = TestBed.createComponent(Ficha);
    fixture.componentRef.setInput('appid', String(JUEGO.appid));
    // tick y no whenStable: lo demás de la API nunca responde, así que nunca queda estable.
    TestBed.tick();

    const html = fixture.nativeElement as HTMLElement;
    expect(html.textContent).toContain(JUEGO.nombre);
    expect(html.querySelector('[data-testid="ficha-riesgo-error"]')).not.toBeNull();
  });

  it('con /perfil caído, la columna de Comparar se pinta', () => {
    configurar(caida);
    const fixture = TestBed.createComponent(ColumnaComparar);
    fixture.componentRef.setInput('juego', JUEGO);
    TestBed.tick();

    expect((fixture.nativeElement as HTMLElement).textContent).toContain(JUEGO.nombre);
  });
});
