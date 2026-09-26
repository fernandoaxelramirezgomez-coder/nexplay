import { Injectable, computed, inject } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';

import { JuegoPanorama } from '../api/contrato';
import { NexplayApi } from '../api/nexplay-api';

/** La muestra de reseñas detrás del catálogo, pedida una sola vez por sesión. La usan el
 * inicio, Panorama, Cómo funciona y el pie de todas las vistas (las fechas de descarga). */
@Injectable({ providedIn: 'root' })
export class PanoramaStore {
  private readonly api = inject(NexplayApi);

  private readonly recurso = rxResource({
    stream: () => this.api.panorama(),
  });

  /** value() lanza si la petición falló; el pie lee esto en todas las vistas, así que sin
   * /panorama tiene que quedar en undefined y no tumbar la página. */
  readonly datos = computed(() => (this.recurso.hasValue() ? this.recurso.value() : undefined));
  readonly cargando = this.recurso.isLoading;
  readonly error = this.recurso.error;

  readonly porAppid = computed(
    () => new Map<number, JuegoPanorama>((this.datos()?.por_juego ?? []).map((fila) => [fila.appid, fila])),
  );

  reintentar(): void {
    this.recurso.reload();
  }
}
