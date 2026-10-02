import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';

import { RespuestaNia, SolicitudNia } from '../api/contrato';
import { NexplayApi } from '../api/nexplay-api';
import { juegoDePrueba } from '../dominio/juego-prueba';
import { ValoresPerfil } from '../dominio/opciones-perfil';
import { CatalogoStore } from '../estado/catalogo-store';
import { PanoramaStore } from '../estado/panorama-store';
import { PerfilStore } from '../estado/perfil-store';
import { UsuarioStore } from '../estado/usuario-store';
import { Nia } from './nia';

const JUEGOS = [juegoDePrueba(), juegoDePrueba({ appid: 2, nombre: 'Portal 2', generos: ['Rol', 'Indie'] })];
const RESPUESTA: RespuestaNia = {
  respuesta: 'En parte 🎮 ¿Te cuento por qué tiene ese riesgo?',
  modo: 'demostracion',
  modelo: null,
  aviso: null,
  id: 'respuesta-de-prueba',
  pasos: [],
  juegos: [],
  version_prompt: 'reglas',
};

const valores = signal<ValoresPerfil | null>(null);

function montar() {
  const enviadas: SolicitudNia[] = [];
  TestBed.configureTestingModule({
    imports: [Nia],
    providers: [
      provideRouter([]),
      {
        provide: NexplayApi,
        useValue: {
          preguntarANia: (solicitud: SolicitudNia) => {
            enviadas.push(solicitud);
            return of(RESPUESTA);
          },
        },
      },
      { provide: CatalogoStore, useValue: { juegos: signal(JUEGOS), porAppid: signal(new Map(JUEGOS.map((j) => [j.appid, j]))) } },
      { provide: PanoramaStore, useValue: { porAppid: signal(new Map()) } },
      { provide: PerfilStore, useValue: { valores, perfil: signal(null), hayPerfil: signal(false) } },
      { provide: UsuarioStore, useValue: { id: 'usuario-de-prueba' } },
    ],
  });
  const fixture = TestBed.createComponent(Nia);
  fixture.componentRef.setInput('appid', 2);
  return { fixture, enviadas };
}

describe('Nia: lo que viaja del perfil', () => {
  beforeEach(() => {
    localStorage.clear();
    valores.set(null);
  });

  it('con perfil, de las respuestas del formulario solo viajan los géneros', async () => {
    valores.set({ compras: 4, horas: 6, friccion: 3, gasto: 2, plataformas: ['pc'], generos: ['Rol', 'Estrategia'] });
    const { fixture, enviadas } = montar();
    await fixture.whenStable();
    fixture.componentInstance.preguntar('¿Encaja conmigo?');
    await fixture.whenStable();

    expect(enviadas).toHaveLength(1);
    expect(enviadas[0].generos).toEqual(['Rol', 'Estrategia']);
    // Ni horas, ni compras, ni gasto, ni plataformas: nada más del formulario.
    const claves = Object.keys(enviadas[0]).sort();
    expect(claves.every((clave) => ['appid', 'generos', 'mensajes', 'sugerencias', 'usuario'].includes(clave))).toBe(true);
  });

  it('sin perfil no viaja ningún género', async () => {
    const { fixture, enviadas } = montar();
    await fixture.whenStable();
    fixture.componentInstance.preguntar('¿Encaja conmigo?');
    await fixture.whenStable();

    expect(enviadas).toHaveLength(1);
    expect('generos' in enviadas[0]).toBe(false);
  });
});
