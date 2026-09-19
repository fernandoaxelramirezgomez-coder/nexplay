import { Injectable, computed, signal } from '@angular/core';

export const MAXIMO_COMPARAR = 4;

export type ResultadoComparar = 'agregado' | 'quitado' | 'lleno';

/** Juegos elegidos para comparar: hasta 4 y sin repetidos, como _agregar_a_comparar en
 * ui/app.py. La vista /comparar la lleva también en la URL (?appids=). */
@Injectable({ providedIn: 'root' })
export class CompararStore {
  private readonly elegidos = signal<number[]>([]);

  readonly appids = this.elegidos.asReadonly();
  readonly cantidad = computed(() => this.elegidos().length);
  readonly lleno = computed(() => this.elegidos().length >= MAXIMO_COMPARAR);
  /** Último intento rechazado por estar lleno; lo muestra la región de avisos. */
  readonly aviso = signal('');

  contiene(appid: number): boolean {
    return this.elegidos().includes(appid);
  }

  alternar(appid: number): ResultadoComparar {
    if (this.contiene(appid)) {
      this.quitar(appid);
      return 'quitado';
    }
    if (this.lleno()) {
      this.aviso.set(`Ya hay ${MAXIMO_COMPARAR} juegos en comparación. Quita uno antes de agregar otro.`);
      return 'lleno';
    }
    this.elegidos.update((actuales) => [...actuales, appid]);
    this.aviso.set('');
    return 'agregado';
  }

  quitar(appid: number): void {
    this.elegidos.update((actuales) => actuales.filter((a) => a !== appid));
    this.aviso.set('');
  }

  /** Reemplaza la selección (p. ej. desde la URL): sin repetidos y hasta el máximo. */
  reemplazar(appids: readonly number[]): void {
    this.elegidos.set([...new Set(appids)].slice(0, MAXIMO_COMPARAR));
    this.aviso.set('');
  }
}
