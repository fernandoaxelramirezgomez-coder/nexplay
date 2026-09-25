import { Injectable, computed, signal } from '@angular/core';

export type Tema = 'claro' | 'oscuro';

const CLAVE = 'nexplay.tema.v1';

function esTema(valor: unknown): valor is Tema {
  return valor === 'claro' || valor === 'oscuro';
}

/** Lo elegido antes, y solo la primera vez lo que pide el sistema. Se pregunta por
 * `light` y no por `dark`: sin preferencia declarada, NexPlay se queda en oscuro. */
export function temaInicial(): Tema {
  try {
    const guardado = localStorage.getItem(CLAVE);
    if (esTema(guardado)) {
      return guardado;
    }
  } catch {
    // Modo privado o almacenamiento bloqueado: se sigue con la preferencia del sistema.
  }
  try {
    return matchMedia('(prefers-color-scheme: light)').matches ? 'claro' : 'oscuro';
  } catch {
    return 'oscuro';
  }
}

/** El tema vive en un atributo de <html>, que es lo que leen los tokens
 * (`:root[data-tema='claro']`). El mismo atributo lo pone el script de index.html antes
 * de que Angular pinte, para que no se vea un destello del tema que no se eligió. */
@Injectable({ providedIn: 'root' })
export class TemaStore {
  private readonly _tema = signal<Tema>(temaInicial());
  readonly tema = this._tema.asReadonly();
  readonly esClaro = computed(() => this._tema() === 'claro');

  constructor() {
    this.aplicar(this._tema());
  }

  alternar(): void {
    this.poner(this._tema() === 'oscuro' ? 'claro' : 'oscuro');
  }

  poner(tema: Tema): void {
    this._tema.set(tema);
    this.aplicar(tema);
  }

  private aplicar(tema: Tema): void {
    document.documentElement.setAttribute('data-tema', tema);
    try {
      localStorage.setItem(CLAVE, tema);
    } catch {
      // Sin almacenamiento el tema vale solo para esta pestaña.
    }
  }
}
