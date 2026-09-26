import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { PanoramaCatalogo } from '../api/contrato';
import { PanoramaStore } from '../estado/panorama-store';
import { FuentesDatos } from './fuentes-datos';

const PANORAMA: PanoramaCatalogo = {
  juegos: 123,
  resenas_descargadas: 184367,
  resenas_en_steam: 18313851,
  cobertura: 0.0101,
  ventana: { desde: '2023-04-08', hasta: '2026-09-21' },
  casos_senal: 4126,
  prevalencia: 0.0224,
  playtime_al_resenar: [{ tramo: 'Menos de 2 h', cuantas: 7874, fraccion: 0.0427 }],
  muestra: {
    compradas_en_steam: 0.8324,
    recibidas_gratis: 0.0164,
    acceso_anticipado: 0.0325,
    con_voto_util: 0.2219,
    perfiles_privados: 0.5982,
    en_ingles: 1,
    resenas_en_ingles: 184366,
  },
  motivos: [],
  resenas_clasificadas: 1344,
  por_juego: [],
};

function montar(datos: PanoramaCatalogo | undefined, cargando = false) {
  TestBed.configureTestingModule({
    imports: [FuentesDatos],
    providers: [
      provideRouter([]),
      {
        provide: PanoramaStore,
        useValue: { datos: signal(datos), cargando: signal(cargando), error: signal(undefined) },
      },
    ],
  });
  const fixture = TestBed.createComponent(FuentesDatos);
  return { fixture, html: fixture.nativeElement as HTMLElement };
}

describe('FuentesDatos', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('pinta las cifras que devuelve la API, no constantes escritas a mano', async () => {
    const { fixture, html } = montar(PANORAMA);
    await fixture.whenStable();
    const texto = html.textContent ?? '';

    expect(texto).toContain('18,313,851');
    expect(texto).toContain('184,367');
    expect(texto).toContain('4,126');
    expect(texto).toContain('2.24%');
    expect(texto).toContain('2023-04-08');
    // El corte de entrenamiento no está en la API: viene de docs/evidencia.
    expect(texto).toContain('123,972');
  });

  it('dice cuántas reseñas hay en inglés con el conteo de la API, no redondeando', async () => {
    const { fixture, html } = montar(PANORAMA);
    await fixture.whenStable();
    // La proporción redondeada es 1.0 y diría "todas": el conteo dice 184,366 de 184,367.
    expect(html.textContent).toContain('184,366');
  });

  it('sin datos avisa en vez de pintar ceros', async () => {
    const { fixture, html } = montar(undefined);
    await fixture.whenStable();
    expect(html.querySelector('[data-testid="cadena-datos"]')).toBeNull();
    expect(html.querySelector('[data-testid="inicio-fuentes-error"]')?.textContent).toContain('API');
  });

  it('mientras carga no dice que falló', async () => {
    const { fixture, html } = montar(undefined, true);
    await fixture.whenStable();
    expect(html.querySelector('[data-testid="inicio-fuentes-error"]')).toBeNull();
    expect(html.textContent).toContain('Contando las reseñas');
  });
});
