import { Injectable } from '@angular/core';

const CLAVE = 'nexplay.usuario.v1';

/** Identidad anónima para las valoraciones: un id que genera el navegador y vive en
 * localStorage. Identifica de qué navegador vino una valoración; no autentica a nadie. */
function leerOCrear(): string {
  try {
    const guardado = localStorage.getItem(CLAVE);
    if (guardado) {
      return guardado;
    }
    const nuevo = crypto.randomUUID();
    localStorage.setItem(CLAVE, nuevo);
    return nuevo;
  } catch {
    // Sin almacenamiento (modo privado, permisos): el id vive solo en esta pestaña.
    return crypto.randomUUID();
  }
}

@Injectable({ providedIn: 'root' })
export class UsuarioStore {
  readonly id = leerOCrear();
}
