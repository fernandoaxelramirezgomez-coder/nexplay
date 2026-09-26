import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { Segmento } from './segmento';

/** Barras horizontales: una fila por segmento, con su cifra en texto a la derecha.
 * Mismo patrón que ficha/motivos-barras.ts, que es de donde sale. */
@Component({
  selector: 'app-grafica-barras',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <ul class="lista" [attr.data-testid]="idPrueba()">
      @for (segmento of segmentos(); track segmento.etiqueta) {
        <li class="fila" [attr.data-banda]="segmento.banda" [class.destacado]="segmento.destacado">
          <span class="nombre">{{ segmento.etiqueta }}</span>
          <span class="pista">
            <span class="barra" [style.inline-size]="ancho(segmento.valor)">
              <span class="solo-lector">{{ segmento.detalle ?? segmento.cifra }}</span>
            </span>
          </span>
          <span class="valor mono">{{ segmento.cifra }}</span>
        </li>
      }
    </ul>
  `,
  styles: `
    .lista {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: var(--espacio-8);
    }
    .fila {
      display: grid;
      /* 7rem para el valor: a 16 px en mono, "100% de 123" mide ~106 px. Fijo y no
         max-content, porque cada fila es su propia rejilla y las barras tienen que terminar
         todas en el mismo borde. */
      grid-template-columns: var(--ancho-etiqueta, 11rem) 1fr 7rem;
      align-items: center;
      gap: var(--espacio-12);
      font-size: var(--texto-body-sm);
    }
    .nombre {
      overflow-wrap: anywhere;
    }
    .pista {
      height: 12px;
      border-radius: var(--radio-pildora);
      background: var(--superficie-tarjeta);
      overflow: hidden;
    }
    .barra {
      display: block;
      height: 100%;
      border-radius: var(--radio-pildora);
      background: var(--neon);
      transition: inline-size var(--duracion) var(--curva);
    }
    .fila[data-banda='bajo'] .barra {
      background: var(--banda-bajo);
    }
    .fila[data-banda='medio'] .barra {
      background: var(--banda-medio);
    }
    .fila[data-banda='alto'] .barra {
      background: var(--banda-alto);
    }
    .fila.destacado .nombre {
      color: var(--texto);
      font-weight: var(--peso-clave);
    }
    .valor {
      text-align: right;
      color: var(--texto-meta);
      font-size: var(--texto-caption);
      white-space: nowrap;
    }
    @media (max-width: 520px) {
      .fila {
        grid-template-columns: 1fr 7rem;
      }
      .pista {
        grid-column: 1 / -1;
        order: 3;
      }
    }
  `,
})
export class GraficaBarras {
  readonly segmentos = input.required<Segmento[]>();
  /** Con qué comparar el largo. Sin él, la barra más larga llena la pista. */
  readonly maximo = input<number>();
  readonly idPrueba = input('grafica-barras');

  private readonly tope = computed(() => {
    const declarado = this.maximo();
    const mayor = Math.max(0, ...this.segmentos().map((s) => s.valor));
    return declarado && declarado > 0 ? declarado : mayor || 1;
  });

  protected ancho(valor: number): string {
    // Sin mínimo: con max(6px, …) un valor de cero pintaba una barra igual que uno de un
    // caso, y el borde derecho de las barras cortas no coincidía con su porcentaje.
    return valor <= 0 ? '0' : `${((valor / this.tope()) * 100).toFixed(1)}%`;
  }
}
