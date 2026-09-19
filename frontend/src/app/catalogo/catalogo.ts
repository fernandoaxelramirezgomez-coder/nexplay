import { ChangeDetectionStrategy, Component, computed, inject, input, linkedSignal } from '@angular/core';
import { Router } from '@angular/router';

import { Skeleton } from '../compartido/skeleton';
import { agruparEnEstantes, ORDEN_BANDAS } from '../dominio/estantes';
import { filtrarJuegos } from '../dominio/filtros';
import { CatalogoStore } from '../estado/catalogo-store';
import { CompararStore } from '../estado/comparar-store';
import { Estante } from './estante';
import { FiltrosCatalogo } from './filtros-catalogo';

@Component({
  selector: 'app-catalogo',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Estante, FiltrosCatalogo, Skeleton],
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
