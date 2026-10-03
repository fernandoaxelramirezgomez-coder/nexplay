import { TestBed } from '@angular/core/testing';
import { NEVER, of, throwError } from 'rxjs';

import { NexplayApi } from '../api/nexplay-api';
import { UsuarioStore } from '../estado/usuario-store';
import { GRACIAS_POR_EL_MOTIVO, VotoNia } from './voto-nia';

function montar(api: Partial<NexplayApi>) {
  TestBed.configureTestingModule({
    imports: [VotoNia],
    providers: [
      { provide: NexplayApi, useValue: api },
      { provide: UsuarioStore, useValue: { id: 'usuario-de-prueba' } },
    ],
  });
  const fixture = TestBed.createComponent(VotoNia);
  fixture.componentRef.setInput('idRespuesta', 'r1');
  fixture.detectChanges();
  return fixture;
}

function boton(fixture: ReturnType<typeof montar>, id: string): HTMLButtonElement | null {
  return fixture.nativeElement.querySelector(`[data-testid="${id}"]`);
}

function motivos(fixture: ReturnType<typeof montar>): HTMLButtonElement[] {
  return [...fixture.nativeElement.querySelectorAll('[data-testid="voto-nia-motivo"]')];
}

/** El componente agrupa los cambios de motivo con una espera, así que las pruebas
 * adelantan el reloj en vez de esperarlo. */
const ESPERA = 800;

function chip(fixture: ReturnType<typeof montar>, texto: string): HTMLButtonElement {
  return motivos(fixture).find((c) => c.textContent?.trim() === texto)!;
}

const panel = (fixture: ReturnType<typeof montar>) =>
  (fixture.nativeElement as HTMLElement).querySelector('[data-testid="voto-nia-motivos"]');
const aviso = (fixture: ReturnType<typeof montar>) =>
  (fixture.nativeElement as HTMLElement).querySelector('.aviso')?.textContent?.trim();
const campo = (fixture: ReturnType<typeof montar>) =>
  (fixture.nativeElement as HTMLElement).querySelector<HTMLTextAreaElement>('[data-testid="voto-nia-sugerencia-texto"]');

function abajoYEsperar(fixture: ReturnType<typeof montar>): void {
  boton(fixture, 'voto-nia-abajo')!.click();
  vi.advanceTimersByTime(ESPERA);
  fixture.detectChanges();
}

function elegirYEsperar(fixture: ReturnType<typeof montar>, texto: string): void {
  chip(fixture, texto).click();
  vi.advanceTimersByTime(ESPERA);
  fixture.detectChanges();
}

function escribirSugerencia(fixture: ReturnType<typeof montar>, texto: string): void {
  campo(fixture)!.value = texto;
  campo(fixture)!.dispatchEvent(new Event('input'));
  fixture.detectChanges();
}

describe('VotoNia', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => {
    vi.useRealTimers();
    TestBed.resetTestingModule();
  });

  it('vota 👍 y lo marca como propio', () => {
    const votar = vi.fn().mockReturnValue(of({ id_respuesta: 'r1', voto: 1, motivo: null }));
    const fixture = montar({ votarRespuestaDeNia: votar } as Partial<NexplayApi>);

    boton(fixture, 'voto-nia-arriba')!.click();
    vi.advanceTimersByTime(ESPERA);
    fixture.detectChanges();

    expect(votar).toHaveBeenCalledWith('r1', { usuario: 'usuario-de-prueba', voto: 1 });
    expect(boton(fixture, 'voto-nia-arriba')!.getAttribute('aria-pressed')).toBe('true');
  });

  /** Los motivos solo tienen sentido con 👎: con 👍 no hay nada que explicar. */
  it('los chips de motivo aparecen solo con 👎', () => {
    const votar = vi.fn().mockReturnValue(of({ id_respuesta: 'r1', voto: -1, motivo: null }));
    const fixture = montar({ votarRespuestaDeNia: votar } as Partial<NexplayApi>);

    expect(motivos(fixture)).toHaveLength(0);
    boton(fixture, 'voto-nia-abajo')!.click();
    vi.advanceTimersByTime(ESPERA);
    fixture.detectChanges();
    expect(motivos(fixture).length).toBeGreaterThan(0);
  });

  it('elegir un motivo lo manda con el voto y pliega el panel a «¡Gracias por avisarnos! · Cambiar»', () => {
    const votar = vi
      .fn()
      .mockReturnValueOnce(of({ id_respuesta: 'r1', voto: -1, motivo: null }))
      .mockReturnValueOnce(of({ id_respuesta: 'r1', voto: -1, motivo: 'muy larga' }));
    const fixture = montar({ votarRespuestaDeNia: votar } as Partial<NexplayApi>);

    abajoYEsperar(fixture);
    expect(aviso(fixture)).toBe('Gracias.');
    chip(fixture, 'muy larga').click();
    vi.advanceTimersByTime(ESPERA);
    fixture.detectChanges();

    expect(votar).toHaveBeenLastCalledWith('r1', { usuario: 'usuario-de-prueba', voto: -1, motivo: 'muy larga' });
    expect(panel(fixture)).toBeNull();
    expect(aviso(fixture)).toBe(GRACIAS_POR_EL_MOTIVO);
    expect(GRACIAS_POR_EL_MOTIVO).toBe('¡Gracias por avisarnos!');
    expect(boton(fixture, 'voto-nia-cambiar')!.textContent?.trim()).toBe('Cambiar');
    expect(boton(fixture, 'voto-nia-cambiar')!.getAttribute('aria-label')).toBe('Cambiar el motivo: muy larga');
  });

  it('«Cambiar» vuelve a abrir los chips con el motivo actual marcado, y otro chip lo reemplaza', () => {
    const votar = vi
      .fn()
      .mockReturnValueOnce(of({ id_respuesta: 'r1', voto: -1, motivo: null }))
      .mockReturnValueOnce(of({ id_respuesta: 'r1', voto: -1, motivo: 'muy larga' }))
      .mockReturnValueOnce(of({ id_respuesta: 'r1', voto: -1, motivo: 'dato incorrecto' }));
    const fixture = montar({ votarRespuestaDeNia: votar } as Partial<NexplayApi>);

    abajoYEsperar(fixture);
    elegirYEsperar(fixture, 'muy larga');
    boton(fixture, 'voto-nia-cambiar')!.click();
    fixture.detectChanges();

    expect(panel(fixture)).not.toBeNull();
    expect(motivos(fixture).filter((c) => c.getAttribute('aria-pressed') === 'true').map((c) => c.textContent?.trim())).toEqual([
      'muy larga',
    ]);
    expect(boton(fixture, 'voto-nia-cambiar')).toBeNull();

    elegirYEsperar(fixture, 'dato incorrecto');
    expect(votar).toHaveBeenLastCalledWith('r1', { usuario: 'usuario-de-prueba', voto: -1, motivo: 'dato incorrecto' });
    expect(panel(fixture)).toBeNull();
    expect(boton(fixture, 'voto-nia-cambiar')!.getAttribute('aria-label')).toBe('Cambiar el motivo: dato incorrecto');
  });

  it('volver a pulsar el chip marcado quita el motivo, deja el 👎 y cierra el panel', () => {
    const votar = vi
      .fn()
      .mockReturnValueOnce(of({ id_respuesta: 'r1', voto: -1, motivo: null }))
      .mockReturnValueOnce(of({ id_respuesta: 'r1', voto: -1, motivo: 'muy larga' }))
      .mockReturnValueOnce(of({ id_respuesta: 'r1', voto: -1, motivo: null }));
    const fixture = montar({ votarRespuestaDeNia: votar } as Partial<NexplayApi>);

    abajoYEsperar(fixture);
    elegirYEsperar(fixture, 'muy larga');
    boton(fixture, 'voto-nia-cambiar')!.click();
    fixture.detectChanges();
    elegirYEsperar(fixture, 'muy larga');

    expect(votar).toHaveBeenLastCalledWith('r1', { usuario: 'usuario-de-prueba', voto: -1 });
    expect(panel(fixture)).toBeNull();
    expect(boton(fixture, 'voto-nia-cambiar')).toBeNull();
    expect(aviso(fixture)).toBe('Gracias.');
  });

  /** Elegir, «Cambiar» y elegir otro, rápido, son peticiones que se pisan; con el tope por
   * ventana del servidor, un 429. Solo viaja la última. */
  it('cambiar de motivo varias veces seguidas manda una sola petición, la última', () => {
    const votar = vi.fn().mockReturnValue(of({ id_respuesta: 'r1', voto: -1, motivo: 'dato incorrecto' }));
    const fixture = montar({ votarRespuestaDeNia: votar } as Partial<NexplayApi>);

    abajoYEsperar(fixture);
    votar.mockClear();

    for (const texto of ['muy larga', 'me recomendó algo', 'dato incorrecto']) {
      boton(fixture, 'voto-nia-cambiar')?.click();
      fixture.detectChanges();
      chip(fixture, texto).click();
      vi.advanceTimersByTime(200);
      fixture.detectChanges();
    }
    expect(votar).not.toHaveBeenCalled();

    vi.advanceTimersByTime(ESPERA);
    fixture.detectChanges();
    expect(votar).toHaveBeenCalledTimes(1);
    expect(votar).toHaveBeenCalledWith('r1', { usuario: 'usuario-de-prueba', voto: -1, motivo: 'dato incorrecto' });
  });

  it('«otro motivo» abre el campo sin registrar nada; al enviar el texto, lo manda y pliega igual', () => {
    const votar = vi
      .fn()
      .mockReturnValueOnce(of({ id_respuesta: 'r1', voto: -1, motivo: null }))
      .mockReturnValueOnce(
        of({ id_respuesta: 'r1', voto: -1, motivo: 'otro motivo', sugerencia: 'Que diga más del modo historia' }),
      );
    const fixture = montar({ votarRespuestaDeNia: votar } as Partial<NexplayApi>);
    const html = fixture.nativeElement as HTMLElement;

    abajoYEsperar(fixture);
    expect(html.querySelector('[data-testid="voto-nia-sugerencia"]')).toBeNull();
    chip(fixture, 'otro motivo').click();
    vi.advanceTimersByTime(ESPERA);
    fixture.detectChanges();

    expect(votar).toHaveBeenCalledTimes(1);
    expect(chip(fixture, 'otro motivo').getAttribute('aria-pressed')).toBe('true');
    escribirSugerencia(fixture, '  Que diga más del modo historia ');
    expect(campo(fixture)!.maxLength).toBe(280);
    boton(fixture, 'voto-nia-sugerencia-enviar')!.click();
    vi.advanceTimersByTime(0);
    fixture.detectChanges();

    expect(votar).toHaveBeenLastCalledWith('r1', {
      usuario: 'usuario-de-prueba',
      voto: -1,
      motivo: 'otro motivo',
      sugerencia: 'Que diga más del modo historia',
    });
    expect(panel(fixture)).toBeNull();
    expect(aviso(fixture)).toBe(GRACIAS_POR_EL_MOTIVO);

    // «Cambiar» la muestra otra vez, con su texto; reenviarla igual no hace otra petición.
    boton(fixture, 'voto-nia-cambiar')!.click();
    fixture.detectChanges();
    expect(campo(fixture)!.value).toBe('Que diga más del modo historia');
    boton(fixture, 'voto-nia-sugerencia-enviar')!.click();
    vi.advanceTimersByTime(ESPERA);
    fixture.detectChanges();
    expect(votar).toHaveBeenCalledTimes(2);
    expect(panel(fixture)).toBeNull();
  });

  it.each([
    ['Cancelar', (f: ReturnType<typeof montar>) => boton(f, 'voto-nia-sugerencia-cancelar')!.click()],
    ['Enviar vacío', (f: ReturnType<typeof montar>) => {
      escribirSugerencia(f, '   ');
      boton(f, 'voto-nia-sugerencia-enviar')!.click();
    }],
    ['Escape', (f: ReturnType<typeof montar>) =>
      campo(f)!.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))],
  ])('«otro motivo» con %s cierra el panel sin registrar nada', (_, cerrar) => {
    const votar = vi.fn().mockReturnValue(of({ id_respuesta: 'r1', voto: -1, motivo: null }));
    const fixture = montar({ votarRespuestaDeNia: votar } as Partial<NexplayApi>);

    abajoYEsperar(fixture);
    chip(fixture, 'otro motivo').click();
    fixture.detectChanges();
    escribirSugerencia(fixture, 'algo que al final no mando');
    cerrar(fixture);
    vi.advanceTimersByTime(ESPERA);
    fixture.detectChanges();

    expect(panel(fixture)).toBeNull();
    expect(votar).toHaveBeenCalledTimes(1);
    expect(boton(fixture, 'voto-nia-cambiar')).toBeNull();
    expect(boton(fixture, 'voto-nia-abajo')!.getAttribute('aria-pressed')).toBe('true');
  });

  it('plegar(): sin motivo elegido el panel se cierra; con texto en «otro motivo» se queda', () => {
    const votar = vi.fn().mockReturnValue(of({ id_respuesta: 'r1', voto: -1, motivo: null }));
    const fixture = montar({ votarRespuestaDeNia: votar } as Partial<NexplayApi>);

    abajoYEsperar(fixture);
    chip(fixture, 'otro motivo').click();
    fixture.detectChanges();
    escribirSugerencia(fixture, 'a medio escribir');
    fixture.componentInstance.plegar();
    fixture.detectChanges();
    expect(campo(fixture)!.value).toBe('a medio escribir');

    escribirSugerencia(fixture, '');
    fixture.componentInstance.plegar();
    fixture.detectChanges();
    expect(panel(fixture)).toBeNull();
    expect(votar).toHaveBeenCalledTimes(1);
  });

  it('el mismo pulgar dos veces quita el voto', () => {
    const votar = vi.fn().mockReturnValue(of({ id_respuesta: 'r1', voto: 1, motivo: null }));
    const quitar = vi.fn().mockReturnValue(of({ id_respuesta: 'r1', voto: null, motivo: null }));
    const fixture = montar({ votarRespuestaDeNia: votar, quitarVotoDeNia: quitar } as Partial<NexplayApi>);

    boton(fixture, 'voto-nia-arriba')!.click();
    vi.advanceTimersByTime(ESPERA);
    fixture.detectChanges();
    boton(fixture, 'voto-nia-arriba')!.click();
    vi.advanceTimersByTime(ESPERA);
    fixture.detectChanges();

    expect(quitar).toHaveBeenCalledWith('r1', 'usuario-de-prueba');
    expect(boton(fixture, 'voto-nia-arriba')!.getAttribute('aria-pressed')).toBe('false');
  });

  it('si la API falla lo dice y no deja el voto marcado', () => {
    const votar = vi.fn().mockReturnValue(throwError(() => new Error('sin API')));
    const fixture = montar({ votarRespuestaDeNia: votar } as Partial<NexplayApi>);

    boton(fixture, 'voto-nia-arriba')!.click();
    vi.advanceTimersByTime(ESPERA);
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('No se pudo guardar tu voto');
    expect(boton(fixture, 'voto-nia-arriba')!.getAttribute('aria-pressed')).toBe('false');
  });

  /** Un 429 en mitad de un cambio de motivo dejaba dos marcados: el que se guardó y el
   * que no. La interfaz vuelve a lo último que la API confirmó. */
  it('si un cambio de motivo falla, vuelve al último motivo guardado', () => {
    const votar = vi
      .fn()
      .mockReturnValueOnce(of({ id_respuesta: 'r1', voto: -1, motivo: null }))
      .mockReturnValueOnce(of({ id_respuesta: 'r1', voto: -1, motivo: 'muy larga' }))
      .mockReturnValueOnce(throwError(() => new Error('429')));
    const fixture = montar({ votarRespuestaDeNia: votar } as Partial<NexplayApi>);

    boton(fixture, 'voto-nia-abajo')!.click();
    vi.advanceTimersByTime(ESPERA);
    fixture.detectChanges();
    motivos(fixture).find((c) => c.textContent?.includes('muy larga'))!.click();
    vi.advanceTimersByTime(ESPERA);
    fixture.detectChanges();

    boton(fixture, 'voto-nia-cambiar')!.click();
    fixture.detectChanges();
    motivos(fixture).find((c) => c.textContent?.includes('dato incorrecto'))!.click();
    vi.advanceTimersByTime(ESPERA);
    fixture.detectChanges();

    // Los chips se abren otra vez para reintentar, con el motivo que sí se guardó.
    const marcados = motivos(fixture).filter((c) => c.getAttribute('aria-pressed') === 'true');
    expect(marcados).toHaveLength(1);
    expect(marcados[0].textContent).toContain('muy larga');
    expect(fixture.nativeElement.textContent).toContain('No se pudo guardar tu voto');
  });

  describe('el foco del teclado', () => {
    /** Vitest no espera el render que sigue al cambio: lo pide a la aplicación. */
    async function renderizar(fixture: ReturnType<typeof montar>): Promise<void> {
      fixture.detectChanges();
      await fixture.whenStable();
    }

    it('al plegar pasa a «Cambiar»; al reabrir, al chip marcado; al cancelar «otro motivo», vuelve a «Cambiar»', async () => {
      const votar = vi
        .fn()
        .mockReturnValueOnce(of({ id_respuesta: 'r1', voto: -1, motivo: null }))
        .mockReturnValue(of({ id_respuesta: 'r1', voto: -1, motivo: 'muy larga' }));
      const fixture = montar({ votarRespuestaDeNia: votar } as Partial<NexplayApi>);

      boton(fixture, 'voto-nia-abajo')!.focus();
      abajoYEsperar(fixture);
      expect(document.activeElement).toBe(boton(fixture, 'voto-nia-abajo'));

      chip(fixture, 'muy larga').focus();
      chip(fixture, 'muy larga').click();
      await renderizar(fixture);
      expect(document.activeElement).toBe(boton(fixture, 'voto-nia-cambiar'));

      boton(fixture, 'voto-nia-cambiar')!.click();
      await renderizar(fixture);
      expect(document.activeElement).toBe(chip(fixture, 'muy larga'));

      chip(fixture, 'otro motivo').click();
      await renderizar(fixture);
      expect(document.activeElement).toBe(campo(fixture));

      boton(fixture, 'voto-nia-sugerencia-cancelar')!.click();
      await renderizar(fixture);
      expect(document.activeElement).toBe(boton(fixture, 'voto-nia-cambiar'));
    });

    it('mientras guarda, los botones no se deshabilitan: quien vota con el teclado no pierde el foco', () => {
      const votar = vi.fn().mockReturnValue(NEVER);
      const fixture = montar({ votarRespuestaDeNia: votar } as Partial<NexplayApi>);

      boton(fixture, 'voto-nia-abajo')!.focus();
      abajoYEsperar(fixture);

      expect(boton(fixture, 'voto-nia-abajo')!.disabled).toBe(false);
      expect(boton(fixture, 'voto-nia-abajo')!.getAttribute('aria-disabled')).toBe('true');
      expect(document.activeElement).toBe(boton(fixture, 'voto-nia-abajo'));
      // Ocupado, un segundo clic no manda nada.
      chip(fixture, 'muy larga').click();
      vi.advanceTimersByTime(ESPERA);
      expect(votar).toHaveBeenCalledTimes(1);
    });

    it('si el foco ya está en otro lado (el campo del chat), plegar no se lo quita', async () => {
      const votar = vi.fn().mockReturnValue(of({ id_respuesta: 'r1', voto: -1, motivo: null }));
      const fixture = montar({ votarRespuestaDeNia: votar } as Partial<NexplayApi>);
      const fuera = document.createElement('textarea');
      document.body.append(fuera);

      abajoYEsperar(fixture);
      fuera.focus();
      fixture.componentInstance.plegar();
      await renderizar(fixture);

      expect(panel(fixture)).toBeNull();
      expect(document.activeElement).toBe(fuera);
      fuera.remove();
    });
  });
});
