import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { Segmento } from './segmento';

/** Columnas verticales, para lo que se lee como una progresión: los tramos de horas
 * jugadas o los años de lanzamiento. La cifra va arriba de cada columna, en texto. */
@Component({
  selector: 'app-grafica-columnas',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <ul class="columnas" [class.densa]="densa()" [attr.data-testid]="idPrueba()">
      @for (segmento of segmentos(); track segmento.etiqueta; let i = $index) {
        <li
          class="columna"
          [attr.data-banda]="segmento.banda"
          [class.destacado]="segmento.destacado"
          [class.hito]="hitos().has(i)"
          [attr.title]="segmento.detalle ?? segmento.cifra"
        >
          <span class="valor mono">{{ segmento.cifra }}</span>
          <span class="pista">
            <span class="barra" [style.block-size]="alto(segmento.valor)">
              <span class="solo-lector">{{ segmento.detalle ?? segmento.cifra }}</span>
            </span>
          </span>
          <span class="nombre">{{ segmento.etiqueta }}</span>
        </li>
      }
    </ul>
  `,
  styles: `
    .columnas {
      container-type: inline-size;
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      grid-auto-flow: column;
      grid-auto-columns: minmax(0, 1fr);
      align-items: end;
      gap: var(--espacio-8);
    }
    .columna {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--espacio-4);
      min-width: 0;
    }
    .pista {
      display: flex;
      align-items: flex-end;
      width: 100%;
      height: 140px;
    }
    .barra {
      width: 100%;
      border-radius: var(--radio-boton) var(--radio-boton) 4px 4px;
      background: var(--neon);
      transition: block-size var(--duracion) var(--curva);
    }
    .columna[data-banda='bajo'] .barra {
      background: var(--banda-bajo);
    }
    .columna[data-banda='medio'] .barra {
      background: var(--banda-medio);
    }
    .columna[data-banda='alto'] .barra {
      background: var(--banda-alto);
    }
    /* El tramo que define la etiqueta va marcado, no solo coloreado. */
    .columna.destacado .barra {
      outline: 2px solid var(--foco);
      outline-offset: 2px;
    }
    .columna.destacado .nombre {
      color: var(--texto);
      font-weight: var(--peso-clave);
    }
    .nombre,
    .valor {
      font-size: var(--texto-caption);
      text-align: center;
      overflow-wrap: anywhere;
    }
    .nombre {
      color: var(--texto-meta);
    }
    @media (max-width: 520px) {
      .pista {
        height: 96px;
      }
    }
    /* Muchas columnas en poco ancho (los años en media tarjeta o en teléfono): "2004" no
       cabe en su columna y se partía en "20 / 04". Quedan el primero, el de en medio y el
       último como eje; cada columna sigue diciendo su cifra al pasar el cursor y al lector
       de pantalla. */
    @container (max-width: 900px) {
      .densa .valor {
        display: none;
      }
      .densa .nombre {
        white-space: nowrap;
        overflow-wrap: normal;
      }
      .densa .columna:not(.hito) .nombre {
        visibility: hidden;
      }
      .densa .columna:first-child {
        align-items: flex-start;
      }
      .densa .columna:last-child {
        align-items: flex-end;
      }
      .densa .columna:first-child .pista,
      .densa .columna:last-child .pista {
        align-self: stretch;
      }
    }
  `,
})
export class GraficaColumnas {
  readonly segmentos = input.required<Segmento[]>();
  readonly idPrueba = input('grafica-columnas');

  private readonly tope = computed(() => Math.max(1, ...this.segmentos().map((s) => s.valor)));

  /** Con más de ocho columnas, en poco ancho se rotulan solo los hitos del eje. */
  protected readonly densa = computed(() => this.segmentos().length > 8);
  protected readonly hitos = computed(() => {
    const n = this.segmentos().length;
    return new Set([0, Math.floor((n - 1) / 2), n - 1]);
  });

  protected alto(valor: number): string {
    return `max(4px, ${((valor / this.tope()) * 100).toFixed(1)}%)`;
  }
}
