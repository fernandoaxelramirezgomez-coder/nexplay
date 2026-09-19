import { Injectable, computed, inject } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';

import { NexplayApi } from '../api/nexplay-api';
import { JuegoCatalogo } from '../api/contrato';

/** Catálogo completo, pedido una sola vez por sesión. Filtros, estantes y fichas
 * trabajan sobre esta copia en memoria (83 juegos). */
@Injectable({ providedIn: 'root' })
export class CatalogoStore {
  private readonly api = inject(NexplayApi);

  private readonly recurso = rxResource({
    stream: () => this.api.catalogo(),
    defaultValue: [] as JuegoCatalogo[],
  });

  readonly juegos = this.recurso.value;
  readonly cargando = this.recurso.isLoading;
  readonly error = this.recurso.error;

  readonly porAppid = computed(() => new Map(this.juegos().map((juego) => [juego.appid, juego])));

  readonly generos = computed(() =>
    [...new Set(this.juegos().flatMap((juego) => juego.generos))].sort((a, b) => a.localeCompare(b, 'es')),
  );

  reintentar(): void {
    this.recurso.reload();
  }
}
