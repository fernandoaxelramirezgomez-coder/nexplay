import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { juegoDePrueba } from '../dominio/juego-prueba';
import { VALORES_VACIOS, ValoresPerfil } from '../dominio/opciones-perfil';
import { CatalogoStore } from '../estado/catalogo-store';
import { PanoramaStore } from '../estado/panorama-store';
import { SugerenciasPerfil } from './sugerencias-perfil';

const JUEGOS = [juegoDePrueba({ generos: ['Rol'] }), juegoDePrueba({ appid: 2, nombre: 'Portal 2', generos: ['Rol', 'Indie'] })];

function montar(valores: ValoresPerfil): HTMLElement {
  TestBed.configureTestingModule({
    providers: [
      provideRouter([]),
      { provide: CatalogoStore, useValue: { juegos: signal(JUEGOS), porAppid: signal(new Map(JUEGOS.map((j) => [j.appid, j]))) } },
      { provide: PanoramaStore, useValue: { porAppid: signal(new Map()) } },
    ],
  });
  const fixture = TestBed.createComponent(SugerenciasPerfil);
  fixture.componentRef.setInput('valores', valores);
  fixture.detectChanges();
  return fixture.nativeElement as HTMLElement;
}

/** El globito de Nia dice «Ver coincidencias»: la página dice lo mismo, coinciden, y no que
 * los juegos encajan con quien los declaró. */
describe('Sugerencias de Tu perfil: coincidencias', () => {
  it('con géneros declarados, dice que los juegos coinciden con lo que declaraste', () => {
    const texto = montar({ ...VALORES_VACIOS, generos: ['Rol'] }).textContent ?? '';

    expect(texto).toContain('Juegos del catálogo que coinciden con lo que declaraste.');
    expect(texto).toMatch(/En el catálogo, \d+ juegos? coincidee?n? con lo que declaraste/);
    expect(texto).not.toMatch(/encaja/);
  });

  it('sin respuestas, el aviso tampoco dice que encajan', () => {
    const texto = montar(VALORES_VACIOS).textContent ?? '';

    expect(texto).toContain('aquí aparecen juegos que coinciden.');
    expect(texto).not.toMatch(/encaja/);
  });
});
