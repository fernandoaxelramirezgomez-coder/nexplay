import { TestBed } from '@angular/core/testing';

import { ActividadStore, CLAVE_ACTIVIDAD } from './actividad-store';

function nuevoStore(): ActividadStore {
  TestBed.resetTestingModule();
  return TestBed.inject(ActividadStore);
}

describe('ActividadStore: lo que cuenta la vista de Administración', () => {
  beforeEach(() => localStorage.clear());

  it('sin nada registrado es null, para mostrar «—» y no un 0 que no se midió', () => {
    expect(nuevoStore().actividad()).toBeNull();
  });

  it('la primera pregunta de un hilo vacío abre una conversación; las siguientes solo suman mensajes', () => {
    const store = nuevoStore();
    store.preguntaANia(true);
    store.preguntaANia(false);
    store.preguntaANia(true);

    expect(store.actividad()).toMatchObject({ conversacionesNia: 2, mensajesNia: 3 });
    // Se guarda: otra pestaña o una recarga lo leen igual.
    expect(nuevoStore().actividad()).toMatchObject({ conversacionesNia: 2, mensajesNia: 3 });
  });

  it('valorar y votar cuentan lo que está puesto ahora: quitarlo lo saca y repetirlo no suma', () => {
    const store = nuevoStore();
    store.juegoValorado(10, true);
    store.juegoValorado(10, true);
    store.juegoValorado(20, true);
    store.juegoValorado(10, false);
    store.respuestaVotada('a', true);
    store.respuestaVotada('a', true);
    store.respuestaVotada('b', true);
    store.respuestaVotada('b', false);
    store.comentarioPublicado();

    expect(store.actividad()).toMatchObject({ juegosValorados: [20], respuestasVotadas: ['a'], comentarios: 1 });
  });

  it('un dato corrupto se lee como sin registro, sin tronar', () => {
    localStorage.setItem(CLAVE_ACTIVIDAD, '{no es json');
    expect(nuevoStore().actividad()).toBeNull();
  });
});
