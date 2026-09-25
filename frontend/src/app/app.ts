import { Component, ElementRef, computed, effect, inject, viewChild } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink, RouterOutlet } from '@angular/router';
import { filter, map, startWith } from 'rxjs';

import { BarraLateral } from './barra-lateral/barra-lateral';
import { NiaFlotante } from './chat/nia-flotante';
import { Metodologia } from './compartido/metodologia';
import { NiaMascota } from './compartido/nia-mascota';
import { BarraStore } from './estado/barra-store';
import { CompararStore } from './estado/comparar-store';
import { TemaStore } from './estado/tema-store';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, BarraLateral, Metodologia, NiaFlotante, NiaMascota],
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

  /** En la ficha, Nia ya vive en la columna lateral con el juego abierto: la burbuja
   * ahí sería la misma conversación dos veces. */
  protected readonly muestraNiaFlotante = computed(() => !this.ruta().startsWith('/juego/'));

  /** El saludo de Nia va al pie y solo en la portada: arriba competía con el buscador,
   * que en móvil es lo primero que hay que ver. Los filtros del catálogo viajan en la URL
   * (?q=, ?genero=), así que se compara solo la ruta. */
  protected readonly enPortada = computed(() => this.ruta().split(/[?#]/)[0] === '/');
}
