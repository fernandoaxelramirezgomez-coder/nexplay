import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { JuegoPanorama } from '../api/contrato';
import { juegoDePrueba, senalDePrueba } from '../dominio/juego-prueba';
import { CatalogoStore } from '../estado/catalogo-store';
import { PanoramaStore } from '../estado/panorama-store';
import { AntesDePagar } from './antes-de-pagar';

const JUEGOS = [
  juegoDePrueba({ appid: 1, banda_riesgo: 'bajo', precio_final: 100 }),
  juegoDePrueba({ appid: 2, banda_riesgo: 'medio', precio_final: 200 }),
  juegoDePrueba({ appid: 3, banda_riesgo: 'alto', precio_final: 400 }),
];

function fila(appid: number, casos: number, consenso: string): JuegoPanorama {
  return {
    appid,
    resenas: 100,
    casos_senal: casos,
    prevalencia: casos / 100,
    resenas_en_steam: null,
    positivas_en_steam: null,
    consenso,
    motivo_principal: null,
    horas_al_recomendar: null,
  };
}

const MOTIVOS = [
  { motivo: 'rendimiento', frecuencia: 0.4085 },
  { motivo: 'bugs', frecuencia: 0.2716 },
  { motivo: 'contenido', frecuencia: 0.2284 },
  { motivo: 'dificultad', frecuencia: 0.1555 },
];

function montar(
  datos: object = {
    resenas_descargadas: 184367,
    motivos: MOTIVOS,
    resenas_clasificadas: 1344,
    casos_senal: 4126,
    senal_por_nivel: senalDePrueba(),
  },
) {
  TestBed.configureTestingModule({
    imports: [AntesDePagar],
    providers: [
      provideRouter([]),
      { provide: CatalogoStore, useValue: { juegos: signal(JUEGOS) } },
      {
        provide: PanoramaStore,
        useValue: {
          porAppid: signal(new Map([[1, fila(1, 1, 'Very Positive')], [2, fila(2, 2, 'Very Positive')], [3, fila(3, 4, 'Mixed')]])),
          datos: signal(datos),
        },
      },
    ],
  });
  const fixture = TestBed.createComponent(AntesDePagar);
  fixture.detectChanges();
  return fixture;
}

function texto(fixture: ReturnType<typeof montar>, id: string): string {
  return fixture.nativeElement.querySelector(`[data-testid="${id}"]`).textContent.replace(/\s+/g, ' ').trim();
}

describe('AntesDePagar', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('abre en la señal y cambia cifra y barras al cambiar de pestaña', () => {
    const fixture = montar();
    expect(texto(fixture, 'antes-cifra')).toBe('1.9×');
    fixture.nativeElement.querySelector('[data-testid="antes-pestana"][data-metrica="positivas"]').click();
    fixture.detectChanges();
    expect(texto(fixture, 'antes-cifra')).toBe('0%');
    expect(fixture.nativeElement.querySelector('[data-testid="antes-notas"]')).toBeNull();
    const cifras = [...fixture.nativeElement.querySelectorAll('[data-testid="antes-barras"] .valor')].map(
      (v: Element) => v.textContent?.trim(),
    );
    expect(cifras).toEqual(['100%', '100%', '0%']);
  });

  it('la señal es la de los 40 que el modelo no vio, con su intervalo y por qué el medio sale abajo', () => {
    const fixture = montar();
    expect(texto(fixture, 'antes-linea')).toContain('que en bajo, en los 40 juegos que el modelo no vio');
    const notas = texto(fixture, 'antes-notas');
    expect(notas).toContain('de 0.87× a 3.50×');
    expect(notas).toContain('es una tendencia, no una conclusión firme');
    expect(notas).toContain('El riesgo medio sale un poco abajo del bajo');
    expect(notas).toContain('En los 123 juegos son 4.2×, pero ahí cuentan los 83 con que se entrenó el modelo.');
  });

  it('solo dos pestañas: sin «Precio», que es una variable del modelo', () => {
    const fixture = montar();
    const pestanas = [...fixture.nativeElement.querySelectorAll('[data-testid="antes-pestana"]')].map(
      (p: Element) => p.textContent?.trim(),
    );
    expect(pestanas).toEqual(['Señal', 'Reseñas positivas']);
  });

  it('las flechas del teclado pasan de pestaña', () => {
    const fixture = montar();
    const senal = fixture.nativeElement.querySelector('[data-metrica="senal"]') as HTMLElement;
    senal.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true }));
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[aria-selected="true"]').dataset.metrica).toBe('positivas');
  });

  it('la confianza dice cuántas reseñas y que el riesgo no lee las reseñas', () => {
    const fixture = montar();
    const confianza = texto(fixture, 'antes-confianza');
    expect(confianza).toContain('184,367 reseñas de Steam');
    expect(confianza).toContain('sin leer las reseñas');
    // «Ver metodología» vive en el pie del Inicio; aquí era un duplicado.
    expect(fixture.nativeElement.querySelector('[data-testid="antes-metodologia"]')).toBeNull();
  });

  it('la tarjeta de motivos es de todo el catálogo, con los tres primeros y de cuántas negativas salen', () => {
    const fixture = montar();
    const barras = [...fixture.nativeElement.querySelectorAll('[data-testid="antes-motivos-barras"] li')].map((fila: Element) =>
      [fila.querySelector('.nombre')?.textContent?.trim(), fila.querySelector('.valor')?.textContent?.trim()],
    );
    expect(barras).toEqual([['Rendimiento', '41%'], ['Bugs', '27%'], ['Contenido', '23%']]);
    expect(texto(fixture, 'antes-motivos')).toContain('En todo el catálogo, no de un juego');
    expect(texto(fixture, 'antes-motivos-origen')).toBe(
      'Porcentaje de las 1,344 negativas tempranas que mencionan un motivo (el 33% de las 4,126). Una reseña puede mencionar más de uno.',
    );
  });

  it('da la regla de reembolso de Steam con su enlace, sin prometer nada', () => {
    const fixture = montar();
    const reembolso = texto(fixture, 'antes-reembolso');
    expect(reembolso).toContain(
      'Steam permite pedir reembolso dentro de los 14 días posteriores a la compra y con menos de 2 horas de juego.',
    );
    expect(reembolso).toContain('Steam decide cada solicitud: NexPlay no garantiza nada.');
    const enlace = fixture.nativeElement.querySelector('[data-testid="antes-enlace-steam"]') as HTMLAnchorElement;
    expect(enlace.href).toBe('https://store.steampowered.com/steam_refunds/');
    expect(enlace.rel).toBe('noopener');
  });

  it('sin motivos en el panorama no pinta la tarjeta', () => {
    const fixture = montar({ resenas_descargadas: 184367, motivos: [], resenas_clasificadas: 0, casos_senal: 0 });
    expect(fixture.nativeElement.querySelector('[data-testid="antes-motivos"]')).toBeNull();
  });
});
