import { provideHttpClient, withFetch } from '@angular/common/http';
import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import {
  ActivatedRouteSnapshot,
  provideRouter,
  withComponentInputBinding,
  withInMemoryScrolling,
  withViewTransitions,
} from '@angular/router';

import { routes } from './app.routes';

function hoja(ruta: ActivatedRouteSnapshot): ActivatedRouteSnapshot {
  return ruta.firstChild ? hoja(ruta.firstChild) : ruta;
}

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(
      routes,
      withComponentInputBinding(),
      withInMemoryScrolling({ scrollPositionRestoration: 'enabled' }),
      withViewTransitions({
        // Solo al cambiar de pantalla: los filtros del catálogo cambian la URL en cada
        // tecla y un fundido ahí se sentiría como parpadeo.
        onViewTransitionCreated: ({ transition, from, to }) => {
          const [desde, hacia] = [hoja(from), hoja(to)];
          const mismosParametros = JSON.stringify(desde.params) === JSON.stringify(hacia.params);
          if (desde.routeConfig === hacia.routeConfig && mismosParametros) {
            // Saltarla rechaza sus promesas: se atienden para no ensuciar la consola.
            transition.ready.catch(() => undefined);
            transition.finished.catch(() => undefined);
            transition.skipTransition();
          }
        },
      }),
    ),
    provideHttpClient(withFetch()),
  ],
};
