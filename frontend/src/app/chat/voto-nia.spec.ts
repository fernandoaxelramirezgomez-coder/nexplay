import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';

import { NexplayApi } from '../api/nexplay-api';
import { UsuarioStore } from '../estado/usuario-store';
import { VotoNia } from './voto-nia';

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

describe('VotoNia', () => {
  afterEach(() => TestBed.resetTestingModule());

  it('vota 👍 y lo marca como propio', () => {
    const votar = vi.fn().mockReturnValue(of({ id_respuesta: 'r1', voto: 1, motivo: null }));
    const fixture = montar({ votarRespuestaDeNia: votar } as Partial<NexplayApi>);

    boton(fixture, 'voto-nia-arriba')!.click();
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
    fixture.detectChanges();
    expect(motivos(fixture).length).toBeGreaterThan(0);
  });

  it('elegir un motivo lo manda con el voto, y volver a pulsarlo lo quita', () => {
    const votar = vi
      .fn()
      .mockReturnValueOnce(of({ id_respuesta: 'r1', voto: -1, motivo: null }))
      .mockReturnValueOnce(of({ id_respuesta: 'r1', voto: -1, motivo: 'muy larga' }))
      .mockReturnValueOnce(of({ id_respuesta: 'r1', voto: -1, motivo: null }));
    const fixture = montar({ votarRespuestaDeNia: votar } as Partial<NexplayApi>);

    boton(fixture, 'voto-nia-abajo')!.click();
    fixture.detectChanges();
    const muyLarga = motivos(fixture).find((chip) => chip.textContent?.includes('muy larga'))!;
    muyLarga.click();
    fixture.detectChanges();

    expect(votar).toHaveBeenLastCalledWith('r1', { usuario: 'usuario-de-prueba', voto: -1, motivo: 'muy larga' });
    expect(motivos(fixture).find((c) => c.textContent?.includes('muy larga'))!.getAttribute('aria-pressed')).toBe('true');

    motivos(fixture).find((c) => c.textContent?.includes('muy larga'))!.click();
    fixture.detectChanges();
    expect(votar).toHaveBeenLastCalledWith('r1', { usuario: 'usuario-de-prueba', voto: -1 });
  });

  it('el mismo pulgar dos veces quita el voto', () => {
    const votar = vi.fn().mockReturnValue(of({ id_respuesta: 'r1', voto: 1, motivo: null }));
    const quitar = vi.fn().mockReturnValue(of({ id_respuesta: 'r1', voto: null, motivo: null }));
    const fixture = montar({ votarRespuestaDeNia: votar, quitarVotoDeNia: quitar } as Partial<NexplayApi>);

    boton(fixture, 'voto-nia-arriba')!.click();
    fixture.detectChanges();
    boton(fixture, 'voto-nia-arriba')!.click();
    fixture.detectChanges();

    expect(quitar).toHaveBeenCalledWith('r1', 'usuario-de-prueba');
    expect(boton(fixture, 'voto-nia-arriba')!.getAttribute('aria-pressed')).toBe('false');
  });

  it('si la API falla lo dice y no deja el voto marcado', () => {
    const votar = vi.fn().mockReturnValue(throwError(() => new Error('sin API')));
    const fixture = montar({ votarRespuestaDeNia: votar } as Partial<NexplayApi>);

    boton(fixture, 'voto-nia-arriba')!.click();
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('No se pudo guardar tu voto');
    expect(boton(fixture, 'voto-nia-arriba')!.getAttribute('aria-pressed')).toBe('false');
  });
});
