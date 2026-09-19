import { Injectable, computed, inject, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';

import { FormularioAlta, PerfilJugador } from '../api/contrato';
import { NexplayApi } from '../api/nexplay-api';

const CLAVE = 'nexplay.perfil.v1';

/** Mismo _FORMULARIO_NEUTRO de ui/app.py: se manda a /perfil para no duplicar aquí
 * las heurísticas de segmento y disponibilidad. */
const FORMULARIO_NEUTRO: FormularioAlta = {
  compras_al_anio: 5,
  horas_por_semana: 8,
  tolerancia_friccion: 3,
  tags_preferidos: [],
  tags_rechazados: [],
  plataforma: 'pc',
};

function leerGuardado(): PerfilJugador | null {
  try {
    const crudo = localStorage.getItem(CLAVE);
    if (!crudo) {
      return null;
    }
    const perfil = JSON.parse(crudo) as PerfilJugador;
    return typeof perfil?.compras_al_anio === 'number' && typeof perfil?.plataforma === 'string' ? perfil : null;
  } catch {
    // Modo privado, almacenamiento bloqueado o dato corrupto: se sigue sin perfil.
    return null;
  }
}

@Injectable({ providedIn: 'root' })
export class PerfilStore {
  private readonly api = inject(NexplayApi);
  private readonly declarado = signal<PerfilJugador | null>(leerGuardado());

  readonly perfil = this.declarado.asReadonly();
  readonly hayPerfil = computed(() => this.declarado() !== null);

  private readonly neutro = rxResource({
    // Solo se pide si hace falta: con perfil declarado no se usa.
    params: () => (this.declarado() ? undefined : true),
    stream: () => this.api.crearPerfil(FORMULARIO_NEUTRO),
  });

  /** El perfil con el que se puntúa: el declarado o, si no hay, el neutro. */
  readonly efectivo = computed(() => this.declarado() ?? this.neutro.value() ?? null);
  readonly cargandoNeutro = computed(() => !this.declarado() && this.neutro.isLoading());

  guardar(perfil: PerfilJugador): void {
    this.declarado.set(perfil);
    try {
      localStorage.setItem(CLAVE, JSON.stringify(perfil));
    } catch {
      // Sin almacenamiento el perfil vive solo en esta pestaña.
    }
  }

  borrar(): void {
    this.declarado.set(null);
    try {
      localStorage.removeItem(CLAVE);
    } catch {
      // Nada que limpiar si el almacenamiento no está disponible.
    }
  }
}
