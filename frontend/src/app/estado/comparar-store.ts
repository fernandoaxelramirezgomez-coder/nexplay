import { Injectable, computed, signal } from '@angular/core';

export const MAXIMO_COMPARAR = 4;

const CLAVE = 'nexplay.comparar.v1';

export type ResultadoComparar = 'agregado' | 'quitado' | 'lleno';

function guardados(): number[] {
  try {
    const crudo = localStorage.getItem(CLAVE);
    const lista: unknown = crudo ? JSON.parse(crudo) : [];
    return Array.isArray(lista)
      ? [...new Set(lista.filter((appid): appid is number => Number.isInteger(appid) && appid > 0))].slice(
          0,
          MAXIMO_COMPARAR,
        )
      : [];
  } catch {
    // Modo privado, almacenamiento bloqueado o dato corrupto: se empieza sin nada.
    return [];
  }
}

/** Juegos elegidos para comparar: hasta 4 y sin repetidos. La selección se guarda en el
 * navegador —recargar dejaba la bandeja vacía— y la vista /comparar la lleva además en la
 * URL (?appids=), que es lo que se puede compartir. */
@Injectable({ providedIn: 'root' })
export class CompararStore {
  private readonly elegidos = signal<number[]>(guardados());

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
    this.guardar();
    return 'agregado';
  }

  quitar(appid: number): void {
    this.elegidos.update((actuales) => actuales.filter((a) => a !== appid));
    this.aviso.set('');
    this.guardar();
  }

  /** Reemplaza la selección (p. ej. desde la URL): sin repetidos y hasta el máximo. */
  reemplazar(appids: readonly number[]): void {
    this.elegidos.set([...new Set(appids)].slice(0, MAXIMO_COMPARAR));
    this.aviso.set('');
    this.guardar();
  }

  private guardar(): void {
    try {
      localStorage.setItem(CLAVE, JSON.stringify(this.elegidos()));
    } catch {
      // Sin almacenamiento la selección dura lo que dure la pestaña.
    }
  }
}
