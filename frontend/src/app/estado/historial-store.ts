import { Injectable, computed, signal } from '@angular/core';

import { NivelRiesgo } from '../api/contrato';

const CLAVE = 'nexplay.historial.v1';
/** Tope de entradas guardadas: lo viejo se cae por el fondo. */
export const MAXIMO_HISTORIAL = 100;

export type TipoEntrada = 'visto' | 'comparado' | 'nia' | 'perfil';

export interface EntradaHistorial {
  tipo: TipoEntrada;
  /** ISO. Se guarda al escribir, no se recalcula al leer. */
  cuando: string;
  appid?: number;
  /** Nombre del juego, o el resumen de la acción cuando no hay uno solo. */
  titulo: string;
  banda?: NivelRiesgo;
  /** Los juegos de una comparación. */
  appids?: number[];
}

function esEntrada(valor: unknown): valor is EntradaHistorial {
  const entrada = valor as EntradaHistorial;
  return (
    !!entrada &&
    typeof entrada.titulo === 'string' &&
    typeof entrada.cuando === 'string' &&
    ['visto', 'comparado', 'nia', 'perfil'].includes(entrada.tipo)
  );
}

function leerGuardado(): EntradaHistorial[] {
  try {
    const crudo = localStorage.getItem(CLAVE);
    const lista: unknown = crudo ? JSON.parse(crudo) : [];
    return Array.isArray(lista) ? lista.filter(esEntrada).slice(0, MAXIMO_HISTORIAL) : [];
  } catch {
    // Modo privado, almacenamiento bloqueado o dato corrupto: se empieza vacío.
    return [];
  }
}

/** Dos entradas son la misma cosa cuando hablan del mismo juego (o de la misma
 * comparación) y son del mismo tipo. El texto no entra a la comparación: una pregunta a
 * Nia sobre el mismo juego sustituye a la anterior. */
function esLaMisma(una: EntradaHistorial, otra: EntradaHistorial): boolean {
  return (
    una.tipo === otra.tipo &&
    una.appid === otra.appid &&
    (una.appids ?? []).join(',') === (otra.appids ?? []).join(',') &&
    (una.appid !== undefined || una.appids !== undefined || una.titulo === otra.titulo)
  );
}

/** Lo que hiciste en NexPlay, **solo en este navegador**: ni la API ni la base de datos
 * guardan actividad por persona. El id anónimo de UsuarioStore identifica valoraciones y
 * comentarios por juego, pero no se puede pedir "lo mío"; esto es local a propósito. */
@Injectable({ providedIn: 'root' })
export class HistorialStore {
  private readonly _entradas = signal<EntradaHistorial[]>(leerGuardado());
  readonly entradas = this._entradas.asReadonly();
  readonly hayHistorial = computed(() => this._entradas().length > 0);

  /** Las entradas más recientes primero, una sola por cosa: volver a abrir la ficha de un
   * juego la sube al principio con su hora nueva en vez de dejar el mismo nombre repetido
   * tres veces en la lista. */
  registrar(entrada: Omit<EntradaHistorial, 'cuando'> & { cuando?: string }): void {
    const nueva: EntradaHistorial = { ...entrada, cuando: entrada.cuando ?? new Date().toISOString() };
    this._entradas.update((actuales) => [nueva, ...actuales.filter((vieja) => !esLaMisma(vieja, nueva))]
      .slice(0, MAXIMO_HISTORIAL));
    this.guardar();
  }

  borrar(): void {
    this._entradas.set([]);
    this.guardar();
  }

  private guardar(): void {
    try {
      localStorage.setItem(CLAVE, JSON.stringify(this._entradas()));
    } catch {
      // Sin almacenamiento el historial dura lo que dure la pestaña.
    }
  }
}
