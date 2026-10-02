import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { of } from 'rxjs';

import { PanoramaCatalogo, PerfilJugador } from './api/contrato';
import { NexplayApi } from './api/nexplay-api';
import { App } from './app';
import { CORTES_DE_NIVEL } from './dominio/etiqueta-riesgo';
import { juegoDePrueba } from './dominio/juego-prueba';
import { BarraStore } from './estado/barra-store';
import { PanoramaStore } from './estado/panorama-store';

/** Solo lo que lee el pie: las fechas de descarga. */
const panorama = signal<Pick<PanoramaCatalogo, 'descargas'> | undefined>(undefined);

/** La barra lateral y la burbuja de Nia piden el catálogo y el perfil neutro: aquí no salen
 * a la red, y cualquier otra llamada a la API falla en la prueba en vez de salir. */
const PERFIL_NEUTRO: PerfilJugador = {
  compras_al_anio: 4,
  horas_por_semana: 6,
  tolerancia_friccion: 'media',
  tags_preferidos: [],
  tags_rechazados: [],
  plataforma: 'pc',
  segmento: 'novato',
  disponibilidad: 'media',
};
const API = {
  catalogo: () => of([juegoDePrueba(), juegoDePrueba({ appid: 2, nombre: 'Portal 2', banda_riesgo: 'bajo' })]),
  crearPerfil: () => of(PERFIL_NEUTRO),
} satisfies Partial<NexplayApi>;

describe('App (shell)', () => {
  beforeEach(async () => {
    localStorage.clear();
    document.documentElement.removeAttribute('data-tema');
    vi.stubGlobal('matchMedia', (consulta: string) => ({ matches: false, media: consulta }));
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [
        provideRouter([]),
        { provide: PanoramaStore, useValue: { datos: panorama } },
        { provide: NexplayApi, useValue: API },
      ],
    }).compileComponents();
    panorama.set(undefined);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('la navegación vive en la barra lateral, con las cinco vistas de la exposición', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const html = fixture.nativeElement as HTMLElement;
    const enlaces = [...html.querySelectorAll('app-barra-lateral nav a.item .nombre')].map((a) => a.textContent?.trim());
    expect(enlaces).toEqual(['Inicio', 'Explorar', 'Nia', 'Comparar', 'Tu perfil']);
  });

  it('el pie despliega la metodología y las fuentes ahí mismo, sin cambiar de vista', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const html = fixture.nativeElement as HTMLElement;
    const boton = html.querySelector<HTMLButtonElement>('footer [data-testid="pie-ver-metodologia"]')!;
    expect(boton.getAttribute('aria-controls')).toBe('metodologia');
    expect(boton.getAttribute('aria-expanded')).toBe('false');
    expect(html.querySelector('footer [data-testid="metodologia"]')).toBeNull();
    expect(html.querySelector('footer a[href*="como-funciona"]')).toBeNull();

    boton.click();
    await fixture.whenStable();
    expect(boton.getAttribute('aria-expanded')).toBe('true');
    expect(html.querySelector('footer #metodologia [data-testid="metodologia"]')).not.toBeNull();
    expect(html.querySelector('footer #metodologia [data-testid="fuentes"]')).not.toBeNull();
    // La única definición de los niveles, con los dos juegos del catálogo de prueba (uno alto y uno bajo).
    expect(html.querySelector('footer [data-testid="metodologia-niveles"]')?.textContent?.trim()).toBe(
      `${CORTES_DE_NIVEL}; en el catálogo quedan 1, 0 y 1.`,
    );
  });

  it('llegar con #metodologia abre el panel del pie', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    await TestBed.inject(Router).navigateByUrl('/#metodologia');
    await fixture.whenStable();
    const boton = (fixture.nativeElement as HTMLElement).querySelector('footer [data-testid="pie-ver-metodologia"]');
    expect(boton?.getAttribute('aria-expanded')).toBe('true');
  });

  it('el pie dice de dónde salen los datos y cuándo se bajaron', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const html = fixture.nativeElement as HTMLElement;
    const linea = () => html.querySelector('footer [data-testid="pie-linea"]')?.textContent?.trim();
    expect(linea()).toBe('Fuentes: Steam (appreviews y appdetails) y Metacritic.');

    panorama.set({
      descargas: {
        appdetails: { desde: '2026-09-14', hasta: '2026-09-21' },
        appreviews: { desde: '2026-09-13', hasta: '2026-09-20' },
      },
    });
    await fixture.whenStable();
    expect(linea()).toBe('Fuentes: Steam (appreviews y appdetails) y Metacritic, descargadas del 13 al 21 sep 2026.');
  });

  it('con el cajón abierto la página queda inerte y el velo la cierra', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const html = fixture.nativeElement as HTMLElement;
    const barra = TestBed.inject(BarraStore);
    const pagina = html.querySelector('[data-testid="shell"]')!;
    const hamburguesa = html.querySelector<HTMLButtonElement>('[data-testid="abrir-menu"]')!;

    expect(pagina.hasAttribute('inert')).toBe(false);
    expect(hamburguesa.getAttribute('aria-controls')).toBe('riel');

    hamburguesa.click();
    await fixture.whenStable();
    expect(barra.cajonAbierto()).toBe(true);
    expect(pagina.hasAttribute('inert')).toBe(true);
    expect(hamburguesa.getAttribute('aria-expanded')).toBe('true');

    html.querySelector<HTMLButtonElement>('[data-testid="velo-menu"]')!.click();
    await fixture.whenStable();
    expect(barra.cajonAbierto()).toBe(false);
    expect(pagina.hasAttribute('inert')).toBe(false);
    // El foco vuelve a donde estaba: al botón que abrió el cajón.
    expect(document.activeElement).toBe(hamburguesa);
  });
});
