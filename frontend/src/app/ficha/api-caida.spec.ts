import { HttpErrorResponse } from '@angular/common/http';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { throwError } from 'rxjs';

import { NexplayApi } from '../api/nexplay-api';
import { ColumnaComparar } from '../comparar/columna-comparar';
import { juegoDePrueba } from '../dominio/juego-prueba';
import { CatalogoStore } from '../estado/catalogo-store';
import { PanoramaStore } from '../estado/panorama-store';
import { UsuarioStore } from '../estado/usuario-store';
import { Ficha } from './ficha';
import { HiloComentarios } from './hilo-comentarios';
import { ValoracionOpinion } from './valoracion-opinion';

const JUEGO = juegoDePrueba();

/** Toda la API caída: cada llamada falla como cuando el navegador no llega al servidor. */
const API_CAIDA = new Proxy({} as Partial<NexplayApi>, {
  get: (_, metodo) => () =>
    throwError(() => new HttpErrorResponse({ status: 0, url: `http://localhost:8000/${String(metodo)}` })),
});

function configurar() {
  localStorage.clear();
  TestBed.configureTestingModule({
    providers: [
      provideRouter([]),
      { provide: NexplayApi, useValue: API_CAIDA },
      { provide: UsuarioStore, useValue: { id: 'usuario-de-prueba' } },
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

function texto(nativo: unknown): string {
  return (nativo as HTMLElement).textContent?.replace(/\s+/g, ' ') ?? '';
}

describe('Con la API caída nada truena', () => {
  beforeEach(() => configurar());
  afterEach(() => vi.unstubAllGlobals());

  it('los comentarios dicen que no se pudieron cargar', async () => {
    const fixture = TestBed.createComponent(HiloComentarios);
    fixture.componentRef.setInput('appid', JUEGO.appid);
    await fixture.whenStable();

    expect(texto(fixture.nativeElement)).toContain('No se pudieron cargar los comentarios.');
  });

  it('el hilo avisa que se reinicia cuando el servidor se duerme, aun sin API', async () => {
    const fixture = TestBed.createComponent(HiloComentarios);
    fixture.componentRef.setInput('appid', JUEGO.appid);
    await fixture.whenStable();

    const aviso = fixture.nativeElement.querySelector('[data-testid="aviso-reinicio"]');
    expect(texto(aviso)).toContain('se reinician cuando el servidor se duerme (plan gratuito)');
  });

  it('la valoración se pinta sin conteo', async () => {
    const fixture = TestBed.createComponent(ValoracionOpinion);
    fixture.componentRef.setInput('appid', JUEGO.appid);
    await fixture.whenStable();

    const html = fixture.nativeElement as HTMLElement;
    expect(texto(html)).toContain('Tu opinión');
    expect(html.querySelector('[data-testid="valoracion-conteo"]')?.textContent?.trim()).toBe('');
  });

  it('la columna de Comparar dice que no pudo calcular el riesgo, en vez de quedarse en el esqueleto', async () => {
    const fixture = TestBed.createComponent(ColumnaComparar);
    fixture.componentRef.setInput('juego', JUEGO);
    await fixture.whenStable();

    const html = fixture.nativeElement as HTMLElement;
    expect(texto(html)).toContain(JUEGO.nombre);
    expect(html.querySelector('[data-testid="columna-riesgo-error"]')?.textContent).toContain(
      'No se pudo calcular el riesgo',
    );
    const opinion = html.querySelector('[data-testid="columna-riesgo-error"]')!.closest('section')!;
    expect(opinion.querySelector('app-skeleton')).toBeNull();
  });

  it('la ficha completa se pinta y dice que no pudo calcular el riesgo', async () => {
    vi.stubGlobal('matchMedia', (consulta: string) => ({ matches: false, media: consulta }));
    const fixture = TestBed.createComponent(Ficha);
    fixture.componentRef.setInput('appid', String(JUEGO.appid));
    await fixture.whenStable();

    const html = fixture.nativeElement as HTMLElement;
    expect(texto(html)).toContain(JUEGO.nombre);
    expect(html.querySelector('[data-testid="ficha-riesgo-error"]')).not.toBeNull();
    expect(texto(html)).toContain('No se pudieron cargar los comentarios.');
  });
});
