import { ChangeDetectionStrategy, Component, computed, effect, inject, input, signal, untracked } from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { Skeleton } from '../compartido/skeleton';
import { CatalogoStore } from '../estado/catalogo-store';
import { CompararStore, MAXIMO_COMPARAR } from '../estado/comparar-store';
import { HistorialStore } from '../estado/historial-store';
import { CapsulasComparar } from './capsulas-comparar';
import { ColumnaComparar } from './columna-comparar';
import { TablaComparar } from './tabla-comparar';

function aNumeros(appids: string | undefined): number[] {
  return (appids ?? '')
    .split(',')
    .map((valor) => Number(valor.trim()))
    .filter((appid) => Number.isInteger(appid) && appid > 0);
}

@Component({
  selector: 'app-comparar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, CapsulasComparar, ColumnaComparar, TablaComparar, Skeleton],
  templateUrl: './comparar.html',
  styleUrl: './comparar.css',
})
export class Comparar {
  /** La selección vive en la URL: así se puede compartir y el botón de atrás funciona. */
  readonly appids = input<string>();

  protected readonly catalogo = inject(CatalogoStore);
  protected readonly comparar = inject(CompararStore);
  private readonly router = inject(Router);
  private readonly historial = inject(HistorialStore);

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
    effect(() => {
      const juegos = this.juegos();
      if (juegos.length > 1) {
        this.historial.registrar({
          tipo: 'comparado',
          titulo: juegos.map((juego) => juego.nombre).join(' · '),
          appids: juegos.map((juego) => juego.appid),
        });
      }
    });

    // La URL manda al entrar con ?appids= o al volver atrás; la bandeja manda al quitar un
    // juego. Sin el parámetro, la URL no dice nada y la bandeja se queda como estaba:
    // antes, entrar a /comparar desde el menú borraba la selección guardada.
    effect(() => {
      const crudo = this.appids();
      if (crudo === undefined) {
        return;
      }
      const deLaUrl = aNumeros(crudo);
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
