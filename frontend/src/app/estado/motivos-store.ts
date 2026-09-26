import { Injectable, inject, signal } from '@angular/core';

import { NexplayApi } from '../api/nexplay-api';

/** Motivo principal por juego, pedido solo cuando una tarjeta lo necesita (al pasar el
 * cursor o al enfocarla) y guardado para no repetir la llamada. Pedirlos todos al cargar
 * el catálogo serían más de cien peticiones que casi nadie mira. */
/** El motivo más mencionado. Si varios empatan en frecuencia se nombran todos: decir solo
 * el primero por orden alfabético sería elegir por azar. */
function principalDe(motivos: readonly { motivo: string; frecuencia: number }[]): string | null {
  if (!motivos.length) {
    return null;
  }
  const mayor = Math.max(...motivos.map((m) => m.frecuencia));
  const empatados = motivos.filter((m) => m.frecuencia === mayor).map((m) => m.motivo);
  return empatados.length > 1
    ? `${empatados.slice(0, -1).join(', ')} y ${empatados[empatados.length - 1]}`
    : empatados[0];
}

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
      next: (explicacion) => this.guardar(appid, principalDe(explicacion.motivos)),
      error: () => this.guardar(appid, null),
    });
  }

  private guardar(appid: number, motivo: string | null): void {
    this.cache.update((actual) => new Map(actual).set(appid, motivo));
  }
}
