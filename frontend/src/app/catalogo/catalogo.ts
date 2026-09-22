import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  inject,
  input,
  linkedSignal,
  signal,
} from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { PildoraBanda } from '../compartido/pildora-banda';
import { Portada } from '../compartido/portada';
import { Skeleton } from '../compartido/skeleton';
import { agruparEnEstantes, ORDEN_BANDAS } from '../dominio/estantes';
import { filtrarJuegos } from '../dominio/filtros';
import { CatalogoStore } from '../estado/catalogo-store';
import { CompararStore } from '../estado/comparar-store';
import { Buscador } from './buscador';
import { Estante } from './estante';
import { FiltrosCatalogo } from './filtros-catalogo';

/** Juegos curados a mano para el ejemplo del inicio: uno de cada banda de riesgo con el
 * perfil neutro de hoy (Hades bajo, Cyberpunk 2077 medio, WILD HEARTS alto) y Outer Wilds
 * de contraste. La banda que se muestra es la que dé el modelo, no la de esta lista. */
const EJEMPLOS_PORTADA = [1145360, 1091500, 1938010, 753640];
/** Lento a propósito: da tiempo a leer el nombre y la banda antes de que cambie. */
const MS_ROTACION = 7000;

@Component({
  selector: 'app-catalogo',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, Buscador, Estante, FiltrosCatalogo, PildoraBanda, Portada, Skeleton],
  templateUrl: './catalogo.html',
  styleUrl: './catalogo.css',
})
export class Catalogo {
  /** Query params (?q=&genero=): el botón de atrás devuelve el catálogo tal como estaba. */
  readonly q = input<string>();
  readonly genero = input<string>();

  protected readonly catalogo = inject(CatalogoStore);
  protected readonly comparar = inject(CompararStore);
  private readonly router = inject(Router);

  protected readonly bandas = ORDEN_BANDAS;
  protected readonly texto = linkedSignal(() => this.q() ?? '');
  protected readonly generoActivo = computed(() => this.genero() ?? '');

  protected readonly filtrados = computed(() =>
    filtrarJuegos(this.catalogo.juegos(), { texto: this.texto(), genero: this.generoActivo() }),
  );
  protected readonly estantes = computed(() => agruparEnEstantes(this.filtrados()));
  protected readonly hayFiltro = computed(() => !!this.texto().trim() || !!this.generoActivo());
  /** Los curados que existan en el catálogo; si faltara alguno, el carrusel sigue. */
  protected readonly ejemplos = computed(() =>
    EJEMPLOS_PORTADA.map((appid) => this.catalogo.porAppid().get(appid)).filter((juego) => !!juego),
  );
  protected readonly indiceEjemplo = signal(0);
  protected readonly destacado = computed(() => {
    const ejemplos = this.ejemplos();
    return ejemplos.length ? ejemplos[this.indiceEjemplo() % ejemplos.length] : undefined;
  });
  /** Quieto mientras el ratón está encima o el foco está dentro: nadie lee un ejemplo
   * que se le escapa. */
  protected readonly ejemploPausado = signal(false);
  /** Con prefers-reduced-motion no rota solo; las flechas siguen funcionando. */
  protected readonly rotaSolo = !this.prefiereMenosMovimiento();

  constructor() {
    if (this.rotaSolo) {
      const reloj = setInterval(() => {
        if (!this.ejemploPausado() && this.ejemplos().length > 1) {
          this.moverEjemplo(1);
        }
      }, MS_ROTACION);
      inject(DestroyRef).onDestroy(() => clearInterval(reloj));
    }
  }

  protected moverEjemplo(paso: 1 | -1): void {
    const total = this.ejemplos().length;
    if (total) {
      this.indiceEjemplo.update((i) => (i + paso + total) % total);
    }
  }

  protected alSalirDelEjemplo(evento: FocusEvent): void {
    const adonde = evento.relatedTarget as Node | null;
    if (!adonde || !(evento.currentTarget as HTMLElement).contains(adonde)) {
      this.ejemploPausado.set(false);
    }
  }

  private prefiereMenosMovimiento(): boolean {
    return typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
  }

  protected cambiarTexto(texto: string): void {
    this.texto.set(texto);
    this.actualizarUrl({ q: texto.trim() || null });
  }

  protected cambiarGenero(genero: string): void {
    this.actualizarUrl({ genero: genero || null });
  }

  private actualizarUrl(queryParams: Record<string, string | null>): void {
    this.router.navigate([], { queryParams, queryParamsHandling: 'merge', replaceUrl: true });
  }
}
