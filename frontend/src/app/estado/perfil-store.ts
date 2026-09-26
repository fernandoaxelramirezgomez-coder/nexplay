import { Injectable, computed, inject, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';

import { FormularioAlta, PerfilJugador } from '../api/contrato';
import { NexplayApi } from '../api/nexplay-api';
import { HistorialStore } from './historial-store';
import { ValoresPerfil } from '../dominio/opciones-perfil';

// v3: hasta v2 el formulario venía con respuestas puestas (compras 4, horas 6, fricción
// media), así que un perfil guardado podía tener valores que nadie declaró. No se migran:
// el formulario arranca vacío y lo declarado tiene que ser de quien lo declara.
// v2 fue el cambio de "tamaño de la biblioteca" a "compras al año", que tampoco se migró.
const CLAVE = 'nexplay.perfil.v3';

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

function leerGuardado(): Guardado | null {
  try {
    const crudo = localStorage.getItem(CLAVE);
    if (!crudo) {
      return null;
    }
    const guardado = JSON.parse(crudo) as Guardado;
    return typeof guardado?.perfil?.compras_al_anio === 'number' && guardado?.valores ? guardado : null;
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
