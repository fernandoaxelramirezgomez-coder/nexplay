import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { JuegoCatalogo, PanoramaCatalogo } from '../api/contrato';
import { juegoDePrueba } from '../dominio/juego-prueba';
import { CatalogoStore } from '../estado/catalogo-store';
import { PanoramaStore } from '../estado/panorama-store';
import { ComoFunciona, PASOS } from './como-funciona';

const panorama = signal<Partial<PanoramaCatalogo> | undefined>(undefined);
const juegos = signal<JuegoCatalogo[]>([]);

/** Mismo criterio que reaccion-nia.spec.ts: describir, nunca prometer ni aconsejar la compra. */
const PROHIBIDO = ['confiable', 'fiable', 'confianza', 'seguro', 'buena compra', 'mala compra', 'abandono'];

describe('ComoFunciona', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ComoFunciona],
      providers: [
        provideRouter([]),
        { provide: PanoramaStore, useValue: { datos: panorama } },
        { provide: CatalogoStore, useValue: { juegos } },
      ],
    }).compileComponents();
    panorama.set(undefined);
    juegos.set([]);
  });

  it('muestra los cuatro pasos, en orden', async () => {
    const fixture = TestBed.createComponent(ComoFunciona);
    await fixture.whenStable();
    const html = fixture.nativeElement as HTMLElement;
    const titulos = [...html.querySelectorAll('[data-testid="paso"] h2')].map((h) => h.textContent?.trim());
    expect(titulos).toEqual(['Busca un juego', 'Mira su riesgo', 'Cuéntanos cómo juegas', 'Pregúntale a Nia']);
  });

  it('cada paso se lee en una frase y el texto largo queda cerrado', async () => {
    const fixture = TestBed.createComponent(ComoFunciona);
    await fixture.whenStable();
    const html = fixture.nativeElement as HTMLElement;
    for (const paso of PASOS) {
      expect(paso.linea.split('. ').length, paso.titulo).toBe(1);
    }
    const detalles = [...html.querySelectorAll<HTMLDetailsElement>('[data-testid="paso-mas"]')];
    expect(detalles).toHaveLength(4);
    expect(detalles.every((d) => !d.open)).toBe(true);
    expect(html.querySelector<HTMLDetailsElement>('[data-testid="metodologia-completa"]')?.open).toBe(false);
  });

  it('Fuentes: tres fuentes de datos y los servicios, con fechas y cifras de la API', async () => {
    const fixture = TestBed.createComponent(ComoFunciona);
    await fixture.whenStable();
    const html = fixture.nativeElement as HTMLElement;
    expect(html.querySelectorAll('[data-testid="fuente"]')).toHaveLength(3);
    expect(html.querySelector('#titulo-fuentes')?.textContent).toContain('Fuentes');
    expect(html.querySelector('[data-testid="fuente-descarga"]')).toBeNull();

    panorama.set({
      resenas_descargadas: 184367,
      muestra: { resenas_en_ingles: 184366 } as PanoramaCatalogo['muestra'],
      descargas: {
        appdetails: { desde: '2026-09-14', hasta: '2026-09-21' },
        appreviews: { desde: '2026-09-14', hasta: '2026-09-21' },
      },
    });
    juegos.set([juegoDePrueba({ appid: 1, metacritic: 80 }), juegoDePrueba({ appid: 2, metacritic: null })]);
    await fixture.whenStable();
    const fechas = [...html.querySelectorAll('[data-testid="fuente-descarga"]')].map((d) => d.textContent?.trim());
    expect(fechas).toEqual(['del 14 al 21 sep 2026', 'del 14 al 21 sep 2026', 'con appdetails, del 14 al 21 sep 2026']);
    const texto = html.querySelector('[data-testid="fuentes"]')?.textContent ?? '';
    expect(texto).toContain('184,367 reseñas');
    expect(texto).toContain('1 de los 2 juegos tienen nota');
    const servicios = html.querySelector('[data-testid="fuente-servicios"]')?.textContent ?? '';
    expect(servicios).toContain('OpenAI');
    expect(servicios).toContain('Open Font License');
  });

  it('la metodología vive aquí, con el vocabulario del proyecto', async () => {
    const fixture = TestBed.createComponent(ComoFunciona);
    await fixture.whenStable();
    const texto = (fixture.nativeElement as HTMLElement).querySelector('[data-testid="metodologia"]')?.textContent;
    expect(texto).toContain('arrepentimiento temprano');
    expect(texto).toContain('120 minutos');
    expect(texto).toContain('GroupKFold');
    expect(texto).toContain('PR-AUC');
  });

  it('los pasos no usan fórmulas prohibidas', () => {
    for (const paso of PASOS) {
      const todo = `${paso.titulo} ${paso.linea} ${paso.texto}`.toLowerCase();
      for (const frase of PROHIBIDO) {
        expect(todo, `"${paso.titulo}" dice "${frase}"`).not.toContain(frase);
      }
    }
  });
});
