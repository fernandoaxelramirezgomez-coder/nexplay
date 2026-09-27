import { ChangeDetectionStrategy, Component, computed, inject, input, linkedSignal } from '@angular/core';
import { Router } from '@angular/router';

import { SeparadorNave } from '../compartido/separador-nave';
import { Skeleton } from '../compartido/skeleton';
import { agruparEnEstantes, ORDEN_BANDAS } from '../dominio/estantes';
import { filtrarJuegos, generosDeUrl, generosParaUrl } from '../dominio/filtros';
import { CatalogoStore } from '../estado/catalogo-store';
import { CompararStore } from '../estado/comparar-store';
import { Buscador } from './buscador';
import { Estante } from './estante';
import { FiltrosCatalogo } from './filtros-catalogo';
import { Trailers } from './trailers';

@Component({
  selector: 'app-catalogo',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Buscador, Estante, FiltrosCatalogo, SeparadorNave, Skeleton, Trailers],
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
  /** ?genero=Acción,Rol: se puede elegir más de uno. */
  protected readonly generosActivos = computed(() => generosDeUrl(this.genero()));

  protected readonly filtrados = computed(() =>
    filtrarJuegos(this.catalogo.juegos(), { texto: this.texto(), generos: this.generosActivos() }),
  );
  protected readonly estantes = computed(() => agruparEnEstantes(this.filtrados()));
  /** Sin filtro se muestran las tres bandas, aunque alguna venga vacía: es el reparto del
   * catálogo. Con filtro, solo las que tienen algo. */
  protected readonly estantesVisibles = computed(() =>
    this.hayFiltro() ? this.estantes().filter((estante) => estante.juegos.length) : this.estantes(),
  );
  protected readonly hayFiltro = computed(() => !!this.texto().trim() || this.generosActivos().length > 0);
  protected cambiarTexto(texto: string): void {
    this.texto.set(texto);
    this.actualizarUrl({ q: texto.trim() || null });
  }

  protected cambiarGeneros(generos: string[]): void {
    this.actualizarUrl({ genero: generosParaUrl(generos) });
  }

  private actualizarUrl(queryParams: Record<string, string | null>): void {
    this.router.navigate([], { queryParams, queryParamsHandling: 'merge', replaceUrl: true });
  }
}
