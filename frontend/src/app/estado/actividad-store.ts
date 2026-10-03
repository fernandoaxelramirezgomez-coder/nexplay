import { Injectable, signal } from '@angular/core';

export const CLAVE_ACTIVIDAD = 'nexplay.actividad.v1';
/** Tope de ids de respuestas votadas que se recuerdan: lo viejo se cae por el fondo. */
const MAXIMO_RESPUESTAS = 200;

/** Lo que el historial no registra y la vista de Administración cuenta: las conversaciones y
 * los mensajes a Nia, y lo que esta persona valoró, votó y comentó. Vive en este navegador y
 * cuenta desde que existe (2026-10): antes no se registraba, así que no hay dato hacia atrás. */
export interface Actividad {
  conversacionesNia: number;
  mensajesNia: number;
  /** Juegos con estrellas puestas ahora; quitar la calificación lo saca. */
  juegosValorados: number[];
  /** Respuestas de Nia con 👍 o 👎 puesto ahora; quitar el voto la saca. */
  respuestasVotadas: string[];
  comentarios: number;
}

const VACIA: Actividad = { conversacionesNia: 0, mensajesNia: 0, juegosValorados: [], respuestasVotadas: [], comentarios: 0 };

function entero(valor: unknown): number {
  return Number.isInteger(valor) && (valor as number) > 0 ? (valor as number) : 0;
}

function leerGuardada(): Actividad | null {
  try {
    const crudo = localStorage.getItem(CLAVE_ACTIVIDAD);
    if (!crudo) {
      return null;
    }
    const guardada = JSON.parse(crudo) as Partial<Actividad>;
    return {
      conversacionesNia: entero(guardada.conversacionesNia),
      mensajesNia: entero(guardada.mensajesNia),
      juegosValorados: Array.isArray(guardada.juegosValorados)
        ? [...new Set(guardada.juegosValorados.filter((a): a is number => Number.isInteger(a) && a > 0))]
        : [],
      respuestasVotadas: Array.isArray(guardada.respuestasVotadas)
        ? [...new Set(guardada.respuestasVotadas.filter((id): id is string => typeof id === 'string'))].slice(
            0,
            MAXIMO_RESPUESTAS,
          )
        : [],
      comentarios: entero(guardada.comentarios),
    };
  } catch {
    // Modo privado, almacenamiento bloqueado o dato corrupto: como si no hubiera registro.
    return null;
  }
}

@Injectable({ providedIn: 'root' })
export class ActividadStore {
  private readonly _actividad = signal<Actividad | null>(leerGuardada());
  /** null mientras no se haya registrado nada: la vista muestra «—», no un 0 que no se midió. */
  readonly actividad = this._actividad.asReadonly();

  /** Una pregunta a Nia; si el hilo estaba vacío, también abre una conversación. */
  preguntaANia(abreConversacion: boolean): void {
    this.cambiar((a) => ({
      ...a,
      mensajesNia: a.mensajesNia + 1,
      conversacionesNia: a.conversacionesNia + (abreConversacion ? 1 : 0),
    }));
  }

  juegoValorado(appid: number, conCalificacion: boolean): void {
    this.cambiar((a) => ({
      ...a,
      juegosValorados: conCalificacion
        ? [...new Set([appid, ...a.juegosValorados])]
        : a.juegosValorados.filter((otro) => otro !== appid),
    }));
  }

  respuestaVotada(idRespuesta: string, conVoto: boolean): void {
    this.cambiar((a) => ({
      ...a,
      respuestasVotadas: conVoto
        ? [idRespuesta, ...a.respuestasVotadas.filter((otra) => otra !== idRespuesta)].slice(0, MAXIMO_RESPUESTAS)
        : a.respuestasVotadas.filter((otra) => otra !== idRespuesta),
    }));
  }

  comentarioPublicado(): void {
    this.cambiar((a) => ({ ...a, comentarios: a.comentarios + 1 }));
  }

  private cambiar(paso: (actual: Actividad) => Actividad): void {
    const nueva = paso(this._actividad() ?? VACIA);
    this._actividad.set(nueva);
    try {
      localStorage.setItem(CLAVE_ACTIVIDAD, JSON.stringify(nueva));
    } catch {
      // Sin almacenamiento, la cuenta vive solo en esta pestaña.
    }
  }
}
