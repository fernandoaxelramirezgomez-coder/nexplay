import { Injectable, computed, inject, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';

import { FormularioAlta, PerfilJugador } from '../api/contrato';
import { NexplayApi } from '../api/nexplay-api';
import { HistorialStore } from './historial-store';
import { ValoresPerfil } from '../dominio/opciones-perfil';

// v4 (6C): varias plataformas y la pregunta del gasto. Los v3 sí se migran —son
// respuestas de verdad—: su plataforma pasa a la lista y el gasto queda sin responder, con
// el perfil activo. v3 fue el formulario que arranca vacío: hasta v2 venía con respuestas
// puestas, así que esos no se migraron, como tampoco el cambio de "tamaño de la
// biblioteca" a "compras al año" de v2.
const CLAVE = 'nexplay.perfil.v4';
const CLAVE_V3 = 'nexplay.perfil.v3';

/** El perfil neutro lo deriva la API: se manda a /perfil para no duplicar aquí
 * las heurísticas de segmento y disponibilidad. */
const FORMULARIO_NEUTRO: FormularioAlta = {
  compras_al_anio: 5,
  horas_por_semana: 8,
  tolerancia_friccion: 3,
  tags_preferidos: [],
  tags_rechazados: [],
  plataforma: 'pc',
};

interface Guardado {
  /** Lo que el jugador eligió en el formulario, para volver a marcarlo. */
  valores: ValoresPerfil;
  /** Lo que devolvió /perfil, que es lo que consume /prediccion. */
  perfil: PerfilJugador;
}

function valido(guardado: Guardado | null): guardado is Guardado {
  return typeof guardado?.perfil?.compras_al_anio === 'number' && Array.isArray(guardado?.valores?.plataformas);
}

/** Un perfil v3: sus valores tenían una sola plataforma y no tenían gasto. */
interface GuardadoV3 {
  valores: Omit<ValoresPerfil, 'plataformas' | 'gasto'> & { plataforma: ValoresPerfil['plataformas'][number] | null };
  perfil: PerfilJugador;
}

export function migrarV3(viejo: GuardadoV3): Guardado {
  const { plataforma, ...resto } = viejo.valores;
  return {
    valores: { ...resto, gasto: null, plataformas: plataforma ? [plataforma] : [viejo.perfil.plataforma] },
    perfil: viejo.perfil,
  };
}

function leerGuardado(): Guardado | null {
  try {
    const crudo = localStorage.getItem(CLAVE);
    if (crudo) {
      const guardado = JSON.parse(crudo) as Guardado;
      return valido(guardado) ? guardado : null;
    }
    const viejo = localStorage.getItem(CLAVE_V3);
    if (!viejo) {
      return null;
    }
    const v3 = JSON.parse(viejo) as GuardadoV3;
    if (typeof v3?.perfil?.compras_al_anio !== 'number' || !v3?.valores) {
      return null;
    }
    const migrado = migrarV3(v3);
    localStorage.setItem(CLAVE, JSON.stringify(migrado));
    localStorage.removeItem(CLAVE_V3);
    return migrado;
  } catch {
    // Modo privado, almacenamiento bloqueado o dato corrupto: se sigue sin perfil.
    return null;
  }
}

@Injectable({ providedIn: 'root' })
export class PerfilStore {
  private readonly api = inject(NexplayApi);
  private readonly historial = inject(HistorialStore);
  private readonly guardado = signal<Guardado | null>(leerGuardado());

  readonly perfil = computed(() => this.guardado()?.perfil ?? null);
  readonly valores = computed(() => this.guardado()?.valores ?? null);
  readonly hayPerfil = computed(() => this.guardado() !== null);
  /** Un perfil de antes de la 6C: activo, pero sin la pregunta del gasto. */
  readonly faltaGasto = computed(() => this.guardado() !== null && this.guardado()!.valores.gasto === null);

  private readonly neutro = rxResource({
    // Solo se pide si hace falta: con perfil declarado no se usa.
    params: () => (this.guardado() ? undefined : true),
    stream: () => this.api.crearPerfil(FORMULARIO_NEUTRO),
  });

  /** El perfil con el que se puntúa: el declarado o, si no hay, el neutro. */
  readonly efectivo = computed(() => this.perfil() ?? this.neutro.value() ?? null);
  readonly cargandoNeutro = computed(() => !this.guardado() && this.neutro.isLoading());

  guardar(valores: ValoresPerfil, perfil: PerfilJugador): void {
    this.guardado.set({ valores, perfil });
    this.historial.registrar({
      tipo: 'perfil',
      titulo: `${perfil.compras_al_anio} compras al año · ${perfil.horas_por_semana} h por semana · fricción ${perfil.tolerancia_friccion}`,
    });
    try {
      localStorage.setItem(CLAVE, JSON.stringify({ valores, perfil }));
    } catch {
      // Sin almacenamiento, el perfil vive solo en esta pestaña.
    }
  }

  borrar(): void {
    this.guardado.set(null);
    try {
      localStorage.removeItem(CLAVE);
    } catch {
      // Nada que limpiar si el almacenamiento no está disponible.
    }
  }
}
