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
import { provideDesplazamiento } from './desplazamiento';

function hoja(ruta: ActivatedRouteSnapshot): ActivatedRouteSnapshot {
  return ruta.firstChild ? hoja(ruta.firstChild) : ruta;
}

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(
      routes,
      withComponentInputBinding(),
      // anchorScrolling: los enlaces con ancla (#metodologia, #actividad) bajan a su sección.
      // Subir al principio o volver a la posición guardada lo decide provideDesplazamiento,
      // para que cambiar un filtro del catálogo no suba la página.
      withInMemoryScrolling({ scrollPositionRestoration: 'disabled', anchorScrolling: 'enabled' }),
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
    provideDesplazamiento(),
    provideHttpClient(withFetch()),
  ],
};
