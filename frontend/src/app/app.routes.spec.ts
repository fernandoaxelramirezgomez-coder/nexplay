import { TestBed } from '@angular/core/testing';
import { Router, UrlTree, provideRouter } from '@angular/router';

import { routes } from './app.routes';

describe('rutas', () => {
  it('solo quedan las cinco vistas, la ficha y Administración, que va fuera del menú', () => {
    const conVista = routes.filter((ruta) => ruta.loadComponent).map((ruta) => ruta.path);
    expect(conVista).toEqual(['', 'explorar', 'juego/:appid', 'comparar', 'nia', 'perfil', 'admin']);
  });

  it('las tres vistas que salieron del menú llevan a su ancla, sin romper enlaces viejos', () => {
    TestBed.configureTestingModule({ providers: [provideRouter([])] });
    const router = TestBed.inject(Router);
    const destino = (camino: string) => {
      const redirigir = routes.find((ruta) => ruta.path === camino)?.redirectTo as () => UrlTree;
      return router.serializeUrl(TestBed.runInInjectionContext(() => redirigir()));
    };
    expect(destino('panorama')).toBe('/#metodologia');
    expect(destino('como-funciona')).toBe('/#metodologia');
    expect(destino('historial')).toBe('/perfil#actividad');
  });
});
