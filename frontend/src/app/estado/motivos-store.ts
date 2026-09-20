import { Injectable, inject, signal } from '@angular/core';

import { NexplayApi } from '../api/nexplay-api';

/** Motivo principal por juego, pedido solo cuando una tarjeta lo necesita (al pasar el
 * cursor o al enfocarla) y guardado para no repetir la llamada. Pedir los 83 al cargar
 * el catálogo serían 83 peticiones que casi nadie mira. */
@Injectable({ providedIn: 'root' })
export class MotivosStore {
  private readonly api = inject(NexplayApi);
  private readonly cache = signal<ReadonlyMap<number, string | null>>(new Map());
  private readonly pedidos = new Set<number>();

  /** undefined = todavía no llegó; null = el juego no tiene motivos suficientes. */
  principal(appid: number): string | null | undefined {
    return this.cache().get(appid);
  }

  pedir(appid: number): void {
    if (this.pedidos.has(appid)) {
      return;
    }
    this.pedidos.add(appid);
    this.api.explicacion(appid).subscribe({
      next: (explicacion) => this.guardar(appid, explicacion.motivos[0]?.motivo ?? null),
      error: () => this.guardar(appid, null),
    });
  }

  private guardar(appid: number, motivo: string | null): void {
    this.cache.update((actual) => new Map(actual).set(appid, motivo));
  }
}
