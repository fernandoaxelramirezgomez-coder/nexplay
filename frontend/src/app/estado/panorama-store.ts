import { Injectable, computed, inject } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';

import { JuegoPanorama } from '../api/contrato';
import { NexplayApi } from '../api/nexplay-api';

/** La muestra de reseñas detrás del catálogo, pedida una sola vez por sesión. La usan el
 * inicio (tres gráficas) y Panorama (todas). */
@Injectable({ providedIn: 'root' })
export class PanoramaStore {
  private readonly api = inject(NexplayApi);

  private readonly recurso = rxResource({
    stream: () => this.api.panorama(),
  });

  readonly datos = this.recurso.value;
  readonly cargando = this.recurso.isLoading;
  readonly error = this.recurso.error;

  readonly porAppid = computed(
    () => new Map<number, JuegoPanorama>((this.datos()?.por_juego ?? []).map((fila) => [fila.appid, fila])),
  );

  reintentar(): void {
    this.recurso.reload();
  }
}
