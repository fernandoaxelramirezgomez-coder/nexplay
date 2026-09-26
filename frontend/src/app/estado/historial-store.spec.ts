import { TestBed } from '@angular/core/testing';

import { HistorialStore, MAXIMO_HISTORIAL } from './historial-store';

describe('HistorialStore', () => {
  beforeEach(() => {
    localStorage.clear();
    TestBed.resetTestingModule();
  });

  it('empieza vacío y lo dice', () => {
    const historial = TestBed.inject(HistorialStore);
    expect(historial.entradas()).toEqual([]);
    expect(historial.hayHistorial()).toBe(false);
  });

  it('pone lo último arriba', () => {
    const historial = TestBed.inject(HistorialStore);
    historial.registrar({ tipo: 'visto', appid: 1, titulo: 'Uno' });
    historial.registrar({ tipo: 'visto', appid: 2, titulo: 'Dos' });
    expect(historial.entradas().map((e) => e.titulo)).toEqual(['Dos', 'Uno']);
  });

  it('volver a un juego lo sube en vez de repetirlo', () => {
    const historial = TestBed.inject(HistorialStore);
    historial.registrar({ tipo: 'visto', appid: 1, titulo: 'Uno' });
    historial.registrar({ tipo: 'visto', appid: 2, titulo: 'Dos' });
    historial.registrar({ tipo: 'visto', appid: 1, titulo: 'Uno' });
    expect(historial.entradas().map((e) => e.titulo)).toEqual(['Uno', 'Dos']);
  });

  it('el mismo juego en tipos distintos son dos cosas', () => {
    const historial = TestBed.inject(HistorialStore);
    historial.registrar({ tipo: 'visto', appid: 1, titulo: 'Uno' });
    historial.registrar({ tipo: 'nia', appid: 1, titulo: 'Uno' });
    expect(historial.entradas().length).toBe(2);
  });

  it(`no guarda más de ${MAXIMO_HISTORIAL} y tira las viejas`, () => {
    const historial = TestBed.inject(HistorialStore);
    for (let appid = 1; appid <= MAXIMO_HISTORIAL + 5; appid++) {
      historial.registrar({ tipo: 'visto', appid, titulo: `Juego ${appid}` });
    }
    expect(historial.entradas().length).toBe(MAXIMO_HISTORIAL);
    expect(historial.entradas()[0].titulo).toBe(`Juego ${MAXIMO_HISTORIAL + 5}`);
  });

  it('sobrevive a recargar y se puede borrar', () => {
    TestBed.inject(HistorialStore).registrar({ tipo: 'visto', appid: 7, titulo: 'Siete' });
    TestBed.resetTestingModule();
    const otra = TestBed.inject(HistorialStore);
    expect(otra.entradas().map((e) => e.appid)).toEqual([7]);
    otra.borrar();
    expect(otra.entradas()).toEqual([]);
    expect(localStorage.getItem('nexplay.historial.v1')).toBe('[]');
  });

  it('un dato corrupto no rompe la lista', () => {
    localStorage.setItem('nexplay.historial.v1', '{"no":"es una lista"}');
    expect(TestBed.inject(HistorialStore).entradas()).toEqual([]);
  });

  it('descarta entradas con forma inesperada', () => {
    localStorage.setItem(
      'nexplay.historial.v1',
      JSON.stringify([{ tipo: 'visto', titulo: 'Bien', cuando: '2026-09-25T00:00:00.000Z' }, { tipo: 'raro' }, 7]),
    );
    expect(TestBed.inject(HistorialStore).entradas().map((e) => e.titulo)).toEqual(['Bien']);
  });
});
