import { TestBed } from '@angular/core/testing';

import { CompararStore, MAXIMO_COMPARAR } from './comparar-store';

describe('CompararStore', () => {
  let store: CompararStore;

  beforeEach(() => {
    localStorage.clear();
    TestBed.resetTestingModule();
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

  it('la selección sobrevive a recargar', () => {
    store.alternar(10);
    store.alternar(20);
    expect(localStorage.getItem('nexplay.comparar.v1')).toBe('[10,20]');

    TestBed.resetTestingModule();
    expect(TestBed.inject(CompararStore).appids()).toEqual([10, 20]);
  });

  it('quitar y reemplazar también se guardan', () => {
    store.reemplazar([1, 2, 3]);
    store.quitar(2);
    TestBed.resetTestingModule();
    expect(TestBed.inject(CompararStore).appids()).toEqual([1, 3]);
  });

  it('un dato corrupto o con basura no rompe la bandeja', () => {
    localStorage.setItem('nexplay.comparar.v1', '{"no":"es una lista"}');
    TestBed.resetTestingModule();
    expect(TestBed.inject(CompararStore).appids()).toEqual([]);

    localStorage.setItem('nexplay.comparar.v1', '[1,"dos",null,1,2,3,4,5,6]');
    TestBed.resetTestingModule();
    expect(TestBed.inject(CompararStore).appids()).toEqual([1, 2, 3, 4]);
  });
});
