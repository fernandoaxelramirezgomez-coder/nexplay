import { Injectable, signal } from '@angular/core';

const CLAVE = 'nexplay.barra.v1';

function expandidaGuardada(): boolean {
  try {
    return localStorage.getItem(CLAVE) !== 'corta';
  } catch {
    return true;
  }
}

/** Los dos estados de la barra lateral. En escritorio se expande o se encoge a la
 * columna de íconos, y eso se recuerda; en pantallas angostas la barra es un cajón que
 * se abre encima y nunca se recuerda abierto. */
@Injectable({ providedIn: 'root' })
export class BarraStore {
  private readonly _expandida = signal(expandidaGuardada());
  readonly expandida = this._expandida.asReadonly();

  private readonly _cajonAbierto = signal(false);
  readonly cajonAbierto = this._cajonAbierto.asReadonly();

  alternarExpandida(): void {
    const valor = !this._expandida();
    this._expandida.set(valor);
    try {
      localStorage.setItem(CLAVE, valor ? 'ancha' : 'corta');
    } catch {
      // Sin almacenamiento la elección dura lo que dure la pestaña.
    }
  }

  abrirCajon(): void {
    this._cajonAbierto.set(true);
  }

  cerrarCajon(): void {
    this._cajonAbierto.set(false);
  }

  alternarCajon(): void {
    this._cajonAbierto.update((abierto) => !abierto);
  }
}
