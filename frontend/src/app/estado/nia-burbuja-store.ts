import { Injectable, signal } from '@angular/core';

import { VistaConGlobito } from '../dominio/textos-nia';

/** Lo que la franja de Nia de una vista le pide a la burbuja: abrirse y hacer lo que
 * ofrecía su botón. La burbuja vive en el armazón y las franjas en cada vista; este es el
 * único puente entre las dos. */
@Injectable({ providedIn: 'root' })
export class NiaBurbujaStore {
  private readonly _pedido = signal<VistaConGlobito | null>(null);
  readonly pedido = this._pedido.asReadonly();

  pedir(vista: VistaConGlobito): void {
    this._pedido.set(vista);
  }

  atendido(): void {
    this._pedido.set(null);
  }
}
