import { ChangeDetectionStrategy, Component, computed, effect, inject, input, signal, untracked } from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { Skeleton } from '../compartido/skeleton';
import { CatalogoStore } from '../estado/catalogo-store';
import { CompararStore, MAXIMO_COMPARAR } from '../estado/comparar-store';
import { ColumnaComparar } from './columna-comparar';

function aNumeros(appids: string | undefined): number[] {
  return (appids ?? '')
    .split(',')
    .map((valor) => Number(valor.trim()))
    .filter((appid) => Number.isInteger(appid) && appid > 0);
}

@Component({
  selector: 'app-comparar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, ColumnaComparar, Skeleton],
  templateUrl: './comparar.html',
  styleUrl: './comparar.css',
})
export class Comparar {
  /** La selección vive en la URL: así se puede compartir y el botón de atrás funciona. */
  readonly appids = input<string>();

  protected readonly catalogo = inject(CatalogoStore);
  protected readonly comparar = inject(CompararStore);
  private readonly router = inject(Router);

  protected readonly maximo = MAXIMO_COMPARAR;

  protected readonly juegos = computed(() => {
    const porAppid = this.catalogo.porAppid();
    return this.comparar
      .appids()
      .map((appid) => porAppid.get(appid))
      .filter((juego) => juego !== undefined);
  });

  /** Columna a la vista cuando se desplazan en horizontal (pantallas angostas). */
  protected readonly visible = signal(0);

  protected alDesplazar(evento: Event): void {
    const pista = evento.target as HTMLElement;
    const total = this.juegos().length;
    // Con scroll-snap cada columna encaja completa: el paso es el ancho entre columnas.
    const paso = total ? pista.scrollWidth / total : 0;
    this.visible.set(paso ? Math.min(total - 1, Math.round(pista.scrollLeft / paso)) : 0);
  }

  protected readonly faltantes = computed(
    () => !this.catalogo.cargando() && this.comparar.cantidad() > this.juegos().length,
  );

  constructor() {
    // La URL manda al entrar o al volver atrás; la bandeja manda al quitar un juego.
    effect(() => {
      const deLaUrl = aNumeros(this.appids());
      if (deLaUrl.join(',') !== untracked(() => this.comparar.appids()).join(',')) {
        this.comparar.reemplazar(deLaUrl);
      }
    });

    effect(() => {
      const elegidos = this.comparar.appids().join(',');
      if (elegidos !== untracked(() => aNumeros(this.appids()).join(','))) {
        this.router.navigate([], {
          queryParams: { appids: elegidos || null },
          queryParamsHandling: 'merge',
          replaceUrl: true,
        });
      }
    });
  }
}
