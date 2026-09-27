import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { Observable, of, throwError } from 'rxjs';

import { JuegoCatalogo, OpinionNia } from '../api/contrato';
import { NexplayApi } from '../api/nexplay-api';
import { CatalogoStore } from '../estado/catalogo-store';
import { CarruselEjemplo, EJEMPLOS_PORTADA } from './carrusel-ejemplo';

const NIVELES = ['bajo', 'medio', 'alto', 'medio'] as const;

const JUEGOS = EJEMPLOS_PORTADA.map(
  (appid, i) =>
    ({
      appid,
      nombre: `Juego ${i + 1}`,
      banda_riesgo: NIVELES[i],
      portada_url: `https://example.test/${appid}.jpg`,
    }) as JuegoCatalogo,
);

const OPINIONES: OpinionNia[] = JUEGOS.map((juego) => ({
  appid: juego.appid,
  nombre: juego.nombre,
  nivel: juego.banda_riesgo,
  pregunta: `¿Qué opinas de ${juego.nombre}?`,
  respuesta: `${juego.nombre} tiene riesgo ${juego.banda_riesgo} 🙂 ¿Te cuento más?`,
}));

function montar(opiniones: Observable<OpinionNia[]>) {
  const opinionesDeNia = vi.fn().mockReturnValue(opiniones);
  TestBed.configureTestingModule({
    imports: [CarruselEjemplo],
    providers: [
      provideRouter([]),
      { provide: NexplayApi, useValue: { opinionesDeNia } },
      { provide: CatalogoStore, useValue: { porAppid: signal(new Map(JUEGOS.map((j) => [j.appid, j]))) } },
    ],
  });
  const fixture = TestBed.createComponent(CarruselEjemplo);
  fixture.detectChanges();
  return { fixture, opinionesDeNia };
}

function en(fixture: ReturnType<typeof montar>['fixture'], id: string): HTMLElement | null {
  return fixture.nativeElement.querySelector(`[data-testid="${id}"]`);
}

/** Las cuatro diapositivas están en la página (apiladas); lo que cuenta es la visible. */
function enActiva(fixture: ReturnType<typeof montar>['fixture'], id: string): HTMLElement | null {
  return fixture.nativeElement.querySelector(`[data-testid="hero-ejemplo"] [data-testid="${id}"]`);
}

describe('CarruselEjemplo («Análisis crítico con nuestra asistente Nia»)', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('pide las opiniones una sola vez y muestra la de cada juego con su mascota', async () => {
    const { fixture, opinionesDeNia } = montar(of(OPINIONES));
    await fixture.whenStable();
    fixture.detectChanges();

    expect(opinionesDeNia).toHaveBeenCalledTimes(1);
    expect(opinionesDeNia).toHaveBeenCalledWith(EJEMPLOS_PORTADA);
    expect(en(fixture, 'hero-etiqueta')!.textContent).toContain('Análisis crítico con nuestra asistente Nia');
    expect(fixture.nativeElement.querySelectorAll('[data-testid="hero-ejemplo"]').length).toBe(1);

    NIVELES.forEach((nivel, i) => {
      expect(enActiva(fixture, 'hero-mascota')!.getAttribute('src')).toBe(`nia/ficha-${nivel}.png`);
      expect(enActiva(fixture, 'hero-pregunta')!.textContent).toContain(`¿Qué opinas de Juego ${i + 1}?`);
      expect(enActiva(fixture, 'hero-respuesta')!.textContent).toContain(`riesgo ${nivel}`);
      en(fixture, 'hero-siguiente')!.click();
      fixture.detectChanges();
    });
    expect(opinionesDeNia).toHaveBeenCalledTimes(1);
  });

  it('lleva a la ficha y al chat con el juego elegido', async () => {
    const { fixture } = montar(of(OPINIONES));
    await fixture.whenStable();
    fixture.detectChanges();

    const [appid] = EJEMPLOS_PORTADA;
    expect(enActiva(fixture, 'hero-ficha')!.getAttribute('href')).toBe(`/juego/${appid}`);
    expect(enActiva(fixture, 'hero-seguir-nia')!.getAttribute('href')).toBe(`/nia?appid=${appid}`);
    expect(enActiva(fixture, 'hero-seguir-nia')!.textContent).toContain('Seguir con Nia');
  });

  it('sin opiniones deja la pregunta y la invitación a preguntarle a Nia', async () => {
    const { fixture } = montar(throwError(() => new Error('sin red')));
    await fixture.whenStable();
    fixture.detectChanges();

    expect(enActiva(fixture, 'hero-mascota')).not.toBeNull();
    expect(enActiva(fixture, 'hero-pregunta')!.textContent).toContain('¿Qué opinas de Juego 1?');
    expect(enActiva(fixture, 'hero-respuesta')).toBeNull();
    expect(enActiva(fixture, 'hero-seguir-nia')!.textContent).toContain('Pregúntale a Nia');
  });
});
