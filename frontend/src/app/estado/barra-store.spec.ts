import { TestBed } from '@angular/core/testing';

import { BarraStore } from './barra-store';

describe('BarraStore', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('empieza expandida y con el cajón cerrado', () => {
    const store = TestBed.inject(BarraStore);
    expect(store.expandida()).toBe(true);
    expect(store.cajonAbierto()).toBe(false);
  });

  it('recuerda que se encogió, pero nunca que el cajón quedó abierto', () => {
    const store = TestBed.inject(BarraStore);
    store.alternarExpandida();
    store.abrirCajon();
    expect(localStorage.getItem('nexplay.barra.v1')).toBe('corta');

    TestBed.resetTestingModule();
    const otra = TestBed.inject(BarraStore);
    expect(otra.expandida()).toBe(false);
    expect(otra.cajonAbierto()).toBe(false);
  });

  it('el cajón se abre, se alterna y se cierra', () => {
    const store = TestBed.inject(BarraStore);
    store.abrirCajon();
    expect(store.cajonAbierto()).toBe(true);
    store.alternarCajon();
    expect(store.cajonAbierto()).toBe(false);
    store.alternarCajon();
    store.cerrarCajon();
    expect(store.cajonAbierto()).toBe(false);
  });
});
