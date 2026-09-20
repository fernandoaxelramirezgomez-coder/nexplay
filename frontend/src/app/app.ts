import { Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter, map, startWith } from 'rxjs';

import { NiaFlotante } from './chat/nia-flotante';
import { Metodologia } from './compartido/metodologia';
import { CompararStore } from './estado/comparar-store';
import { PerfilStore } from './estado/perfil-store';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, Metodologia, NiaFlotante],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  protected readonly comparar = inject(CompararStore);
  protected readonly perfil = inject(PerfilStore);
  private readonly router = inject(Router);

  protected readonly parametrosComparar = computed(() =>
    this.comparar.cantidad() ? { appids: this.comparar.appids().join(',') } : {},
  );

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
}
