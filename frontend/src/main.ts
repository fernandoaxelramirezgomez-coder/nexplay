import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';
import { protegerTransicionesDeVista } from './app/nucleo/transiciones-seguras';

// Antes de arrancar: con la pestaña oculta, las transiciones de vista del router
// abortan y dejan la navegación a medias (ver nucleo/transiciones-seguras.ts).
protegerTransicionesDeVista();

bootstrapApplication(App, appConfig)
  .catch((err) => console.error(err));
