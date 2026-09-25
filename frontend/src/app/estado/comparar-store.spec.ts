import { TestBed } from '@angular/core/testing';

import { CompararStore, MAXIMO_COMPARAR } from './comparar-store';

describe('CompararStore', () => {
  let store: CompararStore;

  beforeEach(() => {
    store = TestBed.inject(CompararStore);
  });

  it('agrega y quita con el mismo gesto', () => {
    expect(store.alternar(1)).toBe('agregado');
    expect(store.contiene(1)).toBe(true);
    expect(store.alternar(1)).toBe('quitado');
    expect(store.cantidad()).toBe(0);
  });

  it(`no pasa de ${MAXIMO_COMPARAR} y avisa`, () => {
    [1, 2, 3, 4].forEach((appid) => store.alternar(appid));
    expect(store.alternar(5)).toBe('lleno');
    expect(store.appids()).toEqual([1, 2, 3, 4]);
    expect(store.aviso()).toContain('Quita uno');
    store.quitar(2);
    expect(store.aviso()).toBe('');
    expect(store.alternar(5)).toBe('agregado');
  });

  it('reemplazar quita repetidos y recorta al máximo', () => {
    store.reemplazar([7, 7, 8, 9, 10, 11]);
    expect(store.appids()).toEqual([7, 8, 9, 10]);
  });
});
