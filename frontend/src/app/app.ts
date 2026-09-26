import { Component, ElementRef, computed, effect, inject, viewChild } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink, RouterOutlet } from '@angular/router';
import { filter, map, startWith } from 'rxjs';

import { BarraLateral } from './barra-lateral/barra-lateral';
import { NiaFlotante } from './chat/nia-flotante';
import { Pie } from './compartido/pie';
import { BarraStore } from './estado/barra-store';
import { CompararStore } from './estado/comparar-store';
import { TemaStore } from './estado/tema-store';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, BarraLateral, Pie, NiaFlotante],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  protected readonly comparar = inject(CompararStore);
  protected readonly barra = inject(BarraStore);
  private readonly router = inject(Router);
  /** Se inyecta para que el tema quede aplicado desde el arranque. */
  protected readonly tema = inject(TemaStore);

  private readonly hamburguesa = viewChild<ElementRef<HTMLButtonElement>>('hamburguesa');
  private cajonEstaba = false;

  constructor() {
    effect(() => {
      // Al navegar, el cajón se cierra: la página nueva no debe aparecer detrás del velo.
      this.ruta();
      this.barra.cerrarCajon();
    });
    effect(() => {
      // Al cerrarse, el foco vuelve al botón que lo abrió, no al principio de la página.
      const abierto = this.barra.cajonAbierto();
      if (!abierto && this.cajonEstaba) {
        this.hamburguesa()?.nativeElement.focus();
      }
      this.cajonEstaba = abierto;
    });
  }

  private readonly ruta = toSignal(
    this.router.events.pipe(
      filter((evento): evento is NavigationEnd => evento instanceof NavigationEnd),
      map((evento) => evento.urlAfterRedirects),
      startWith(this.router.url),
    ),
    { initialValue: this.router.url },
  );

  /** Ni en la ficha ni en la página de Nia: en las dos ya hay una conversación abierta y
   * la burbuja sería la misma, ofrecida dos veces. En el resto del sitio acompaña. */
  protected readonly muestraNiaFlotante = computed(() => {
    const ruta = this.ruta().split(/[?#]/)[0];
    return !ruta.startsWith('/juego/') && ruta !== '/nia';
  });

  /** La vista abierta, para que el color de acción (fondo, menú y botón principal) sea uno
   * por vista, como pide la paleta. La ficha es de Explorar: el menú ya la marca ahí y los
   * tres tienen que coincidir. Historial y Cómo funciona comparten el gris-azul. */
  protected readonly vista = computed(() => vistaDe(this.ruta()));

}

const VISTAS: Record<string, string> = {
  explorar: 'explorar',
  juego: 'explorar',
  comparar: 'comparar',
  nia: 'nia',
  perfil: 'perfil',
  panorama: 'panorama',
  historial: 'neutro',
  'como-funciona': 'neutro',
};

/** La primera parte de la ruta decide la vista; la raíz y cualquier otra, el inicio. */
export function vistaDe(url: string): string {
  const primera = url.split(/[?#]/)[0].split('/').filter(Boolean)[0] ?? '';
  return VISTAS[primera] ?? 'inicio';
}
