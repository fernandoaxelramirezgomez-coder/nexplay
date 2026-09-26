import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { NexplayApi } from '../api/nexplay-api';
import { PerfilStore } from './perfil-store';

const PERFIL_API = {
  compras_al_anio: 4,
  horas_por_semana: 6,
  tolerancia_friccion: 'media',
  tags_preferidos: ['acción'],
  tags_rechazados: [],
  plataforma: 'xbox',
  segmento: 'novato',
  disponibilidad: 'media',
};

function crear(): PerfilStore {
  // Sin perfil guardado, el almacén pide el perfil neutro: aquí no sale a la red.
  TestBed.configureTestingModule({ providers: [{ provide: NexplayApi, useValue: { crearPerfil: () => of(PERFIL_API) } }] });
  return TestBed.inject(PerfilStore);
}

describe('PerfilStore', () => {
  beforeEach(() => localStorage.clear());

  it('un perfil v3 se migra a v4: sigue activo, su plataforma pasa a la lista y falta el gasto', () => {
    localStorage.setItem(
      'nexplay.perfil.v3',
      JSON.stringify({
        valores: { compras: 4, horas: 6, friccion: 3, plataforma: 'xbox', generos: ['Acción'] },
        perfil: PERFIL_API,
      }),
    );
    const perfil = crear();

    expect(perfil.hayPerfil()).toBe(true);
    expect(perfil.faltaGasto()).toBe(true);
    expect(perfil.valores()).toEqual({
      compras: 4,
      horas: 6,
      friccion: 3,
      gasto: null,
      plataformas: ['xbox'],
      generos: ['Acción'],
    });
    expect(localStorage.getItem('nexplay.perfil.v3')).toBeNull();
    expect(JSON.parse(localStorage.getItem('nexplay.perfil.v4') ?? '{}').valores.plataformas).toEqual(['xbox']);
  });

  it('un v4 completo no pide nada', () => {
    localStorage.setItem(
      'nexplay.perfil.v4',
      JSON.stringify({
        valores: { compras: 4, horas: 6, friccion: 3, gasto: 2, plataformas: ['pc'], generos: [] },
        perfil: PERFIL_API,
      }),
    );
    const perfil = crear();
    expect(perfil.hayPerfil()).toBe(true);
    expect(perfil.faltaGasto()).toBe(false);
  });

  it('sin nada guardado no hay perfil', () => {
    expect(crear().hayPerfil()).toBe(false);
  });
});
