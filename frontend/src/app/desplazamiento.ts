import { ViewportScroller } from '@angular/common';
import { EnvironmentProviders, inject, provideEnvironmentInitializer } from '@angular/core';
import { Router, Scroll } from '@angular/router';
import { filter } from 'rxjs';

/** A dónde va la página al navegar. Sube al principio solo al cambiar de pantalla: los
 * filtros del catálogo (?q=, ?genero=) cambian la URL con cada género y cada tecla, y con
 * la restauración del router la página saltaba arriba y sacaba de vista lo que se estaba
 * eligiendo. Atrás y adelante devuelven la posición guardada; las anclas (#metodologia)
 * las sigue bajando el router con anchorScrolling. */
export function provideDesplazamiento(): EnvironmentProviders {
  return provideEnvironmentInitializer(() => {
    const router = inject(Router);
    const scroller = inject(ViewportScroller);
    scroller.setHistoryScrollRestoration('manual');
    let pantallaAnterior: string | null = null;
    router.events.pipe(filter((evento): evento is Scroll => evento instanceof Scroll)).subscribe((evento) => {
      const url = 'urlAfterRedirects' in evento.routerEvent ? evento.routerEvent.urlAfterRedirects : evento.routerEvent.url;
      const pantalla = url.split(/[?#]/)[0];
      const otraPantalla = pantalla !== pantallaAnterior;
      pantallaAnterior = pantalla;
      if (evento.position) {
        scroller.scrollToPosition(evento.position);
      } else if (!evento.anchor && otraPantalla) {
        scroller.scrollToPosition([0, 0]);
      }
    });
  });
}
