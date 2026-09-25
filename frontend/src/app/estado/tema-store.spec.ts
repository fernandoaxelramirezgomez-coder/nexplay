import { TestBed } from '@angular/core/testing';

import { TemaStore, temaInicial } from './tema-store';

const CLAVE = 'nexplay.tema.v1';

/** matchMedia no existe en jsdom: se sustituye por uno que responde lo que pida la prueba. */
function sistemaPrefiere(claro: boolean): void {
  vi.stubGlobal('matchMedia', (consulta: string) => ({
    matches: consulta.includes('prefers-color-scheme: light') ? claro : !claro,
    media: consulta,
  }));
}

describe('TemaStore', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.removeAttribute('data-tema');
    sistemaPrefiere(false);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('la primera vez toma lo que pide el sistema', () => {
    sistemaPrefiere(true);
    expect(temaInicial()).toBe('claro');
    sistemaPrefiere(false);
    expect(temaInicial()).toBe('oscuro');
  });

  it('lo guardado gana sobre la preferencia del sistema', () => {
    localStorage.setItem(CLAVE, 'oscuro');
    sistemaPrefiere(true);
    expect(temaInicial()).toBe('oscuro');
  });

  it('un valor corrupto en localStorage no rompe nada', () => {
    localStorage.setItem(CLAVE, 'neón');
    sistemaPrefiere(true);
    expect(temaInicial()).toBe('claro');
  });

  it('sin preferencia declarada se queda en oscuro', () => {
    vi.stubGlobal('matchMedia', (consulta: string) => ({ matches: false, media: consulta }));
    expect(temaInicial()).toBe('oscuro');
  });

  it('al alternar escribe el atributo de <html> y lo guarda', () => {
    const store = TestBed.inject(TemaStore);
    expect(store.tema()).toBe('oscuro');
    expect(document.documentElement.getAttribute('data-tema')).toBe('oscuro');

    store.alternar();
    expect(store.tema()).toBe('claro');
    expect(store.esClaro()).toBe(true);
    expect(document.documentElement.getAttribute('data-tema')).toBe('claro');
    expect(localStorage.getItem(CLAVE)).toBe('claro');

    store.alternar();
    expect(store.tema()).toBe('oscuro');
    expect(localStorage.getItem(CLAVE)).toBe('oscuro');
  });
});
