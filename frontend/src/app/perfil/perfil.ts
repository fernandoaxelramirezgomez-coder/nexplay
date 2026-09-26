import { ChangeDetectionStrategy, Component, Injector, afterNextRender, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { NexplayApi } from '../api/nexplay-api';
import { Plataforma } from '../api/contrato';
import {
  COMPRAS,
  FRICCION,
  GASTO,
  HORAS,
  PLATAFORMAS,
  TOTAL_PREGUNTAS,
  ValoresPerfil,
  VALORES_VACIOS,
  estaCompleto,
  formularioDesde,
  juegosHastaTope,
  preguntasPendientes,
} from '../dominio/opciones-perfil';
import { CatalogoStore } from '../estado/catalogo-store';
import { PerfilStore } from '../estado/perfil-store';
import { SelectorGeneros } from './selector-generos';
import { SugerenciasPerfil } from './sugerencias-perfil';
import { TarjetasOpcion } from './tarjetas-opcion';

@Component({
  selector: 'app-perfil',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, TarjetasOpcion, SelectorGeneros, SugerenciasPerfil],
  templateUrl: './perfil.html',
  styleUrl: './perfil.css',
})
export class Perfil {
  private readonly api = inject(NexplayApi);
  private readonly inyector = inject(Injector);
  protected readonly perfil = inject(PerfilStore);
  protected readonly catalogo = inject(CatalogoStore);

  protected readonly compras = COMPRAS;
  protected readonly horas = HORAS;
  protected readonly friccion = FRICCION;
  protected readonly plataformas = PLATAFORMAS;
  protected readonly total = TOTAL_PREGUNTAS;

  /** El detalle de cada tramo del gasto: cuántos juegos del catálogo caben en su tope. */
  protected readonly opcionesGasto = computed(() =>
    GASTO.map((opcion) => ({
      ...opcion,
      detalle: this.catalogo.juegos().length
        ? `${juegosHastaTope(this.catalogo.juegos(), opcion.valor)} juegos del catálogo`
        : undefined,
    })),
  );

  protected readonly valores = signal<ValoresPerfil>(this.perfil.valores() ?? VALORES_VACIOS);
  /** Sin las cinco respuestas no hay perfil que guardar: el botón espera. */
  protected readonly completo = computed(() => estaCompleto(this.valores()));
  protected readonly pendientes = computed(() => preguntasPendientes(this.valores()));
  protected readonly respondidas = computed(() => TOTAL_PREGUNTAS - this.pendientes().length);
  protected readonly guardando = signal(false);
  protected readonly guardado = signal(false);
  protected readonly error = signal('');

  protected readonly textoEstado = computed(() => {
    const pendientes = this.pendientes();
    if (!pendientes.length) {
      return `${TOTAL_PREGUNTAS} de ${TOTAL_PREGUNTAS} · listo para guardar`;
    }
    // Un perfil de antes de la 6C: todo respondido menos la pregunta nueva.
    if (this.perfil.faltaGasto() && pendientes.length === 1 && pendientes[0] === 'cuánto pagas por juego') {
      return 'Falta 1 pregunta nueva: cuánto pagas por juego';
    }
    // Con una o dos se nombran; con más, la lista ocupaba media pantalla en el teléfono.
    const falta = pendientes.length <= 2 ? `falta: ${pendientes.join(' y ')}` : `faltan ${pendientes.length}`;
    return `${this.respondidas()} de ${TOTAL_PREGUNTAS} respondidas · ${falta}`;
  });

  protected estado(respondida: boolean): string {
    return respondida ? '✓ Respondida' : 'Falta responder';
  }

  protected elegidas(cuantas: number, una: string, varias: string): string {
    return cuantas ? `✓ ${cuantas} ${cuantas === 1 ? una : varias}` : 'Falta responder';
  }

  protected cambiar<K extends keyof ValoresPerfil>(clave: K, valor: ValoresPerfil[K]): void {
    this.valores.update((actuales) => ({ ...actuales, [clave]: valor }));
    this.guardado.set(false);
  }

  protected alternarPlataforma(plataforma: Plataforma): void {
    const actuales = this.valores().plataformas;
    this.cambiar(
      'plataformas',
      actuales.includes(plataforma) ? actuales.filter((p) => p !== plataforma) : [...actuales, plataforma],
    );
  }

  protected alternarGenero(genero: string): void {
    const actuales = this.valores().generos;
    this.cambiar('generos', actuales.includes(genero) ? actuales.filter((g) => g !== genero) : [...actuales, genero]);
  }

  protected crear(): void {
    this.guardando.set(true);
    this.error.set('');
    const valores = this.valores();
    this.api.crearPerfil(formularioDesde(valores)).subscribe({
      next: (perfil) => {
        this.perfil.guardar(valores, perfil);
        this.guardando.set(false);
        this.guardado.set(true);
        // Las sugerencias aparecen justo debajo al guardar: irse al catálogo dejaba sin
        // ver lo único que el perfil cambia.
        afterNextRender(
          () => document.querySelector('[data-testid="sugerencias"]')?.scrollIntoView({ block: 'start' }),
          { injector: this.inyector },
        );
      },
      error: () => {
        this.guardando.set(false);
        this.error.set('No se pudo guardar el perfil. Revisa que la API esté corriendo e inténtalo de nuevo.');
      },
    });
  }

  protected borrar(): void {
    this.perfil.borrar();
    this.valores.set(VALORES_VACIOS);
    this.guardado.set(false);
  }
}
