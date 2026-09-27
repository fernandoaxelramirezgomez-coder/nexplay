import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { JuegoPanorama } from '../api/contrato';
import { juegoDePrueba } from '../dominio/juego-prueba';
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

function montar() {
  TestBed.configureTestingModule({
    imports: [AntesDePagar],
    providers: [
      provideRouter([]),
      { provide: CatalogoStore, useValue: { juegos: signal(JUEGOS) } },
      {
        provide: PanoramaStore,
        useValue: {
          porAppid: signal(new Map([[1, fila(1, 1, 'Very Positive')], [2, fila(2, 2, 'Very Positive')], [3, fila(3, 4, 'Mixed')]])),
          datos: signal({ resenas_descargadas: 184367 }),
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
    expect(texto(fixture, 'antes-cifra')).toBe('4.0×');
    fixture.nativeElement.querySelector('[data-testid="antes-pestana"][data-metrica="precio"]').click();
    fixture.detectChanges();
    expect(texto(fixture, 'antes-cifra')).toBe('4×');
    expect(texto(fixture, 'antes-linea')).toContain('pagar más no te protege');
    const cifras = [...fixture.nativeElement.querySelectorAll('[data-testid="antes-barras"] .valor')].map(
      (v: Element) => v.textContent?.trim(),
    );
    expect(cifras).toEqual(['$100', '$200', '$400']);
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
  });
});
