import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { NivelRiesgo } from '../../api/contrato';

export interface Tajada {
  etiqueta: string;
  valor: number;
  /** 0, 1, 2… en el orden de la escala; el color sale de ahí. */
  tono: number;
}

export interface FilaApilada {
  etiqueta: string;
  banda?: NivelRiesgo;
  total: number;
  tajadas: Tajada[];
}

/** Una barra por fila repartida en categorías. Se usa para el consenso de Steam por
 * banda: cada banda es una fila y cada tajada, una valoración de Steam. Debajo va la
 * leyenda con las cifras en texto, porque cinco tonos no se distinguen de un vistazo. */
@Component({
  selector: 'app-grafica-apilada',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="apilada" [attr.data-testid]="idPrueba()">
      @for (fila of filas(); track fila.etiqueta) {
        <div class="fila">
          <span class="nombre">{{ fila.etiqueta }}</span>
          <span class="pista">
            @for (tajada of fila.tajadas; track tajada.etiqueta) {
              @if (tajada.valor) {
                <span
                  class="tajada"
                  [attr.data-tono]="tajada.tono"
                  [style.inline-size.%]="(tajada.valor / fila.total) * 100"
                  [attr.title]="tajada.etiqueta + ': ' + tajada.valor"
                >
                  <span class="solo-lector">{{ tajada.etiqueta }}: {{ tajada.valor }}</span>
                </span>
              }
            }
          </span>
          <span class="valor mono">{{ fila.total }}</span>
        </div>
      }
      <ul class="leyenda">
        @for (entrada of leyenda(); track entrada.etiqueta) {
          <li>
            <span class="muestra" [attr.data-tono]="entrada.tono" aria-hidden="true"></span>
            {{ entrada.etiqueta }}
          </li>
        }
      </ul>
    </div>
  `,
  styles: `
    .apilada {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-8);
    }
    .fila {
      display: grid;
      grid-template-columns: 11rem 1fr 3rem;
      align-items: center;
      gap: var(--espacio-12);
      font-size: var(--texto-body-sm);
    }
    .pista {
      display: flex;
      height: 16px;
      border-radius: var(--radio-pildora);
      background: var(--superficie-tarjeta);
      overflow: hidden;
    }
    .tajada {
      display: block;
      height: 100%;
      transition: inline-size var(--duracion) var(--curva);
    }
    /* Escala de cinco pasos del consenso, de lo más positivo a lo más negativo. */
    .tajada[data-tono='0'],
    .muestra[data-tono='0'] {
      background: var(--banda-bajo);
    }
    .tajada[data-tono='1'],
    .muestra[data-tono='1'] {
      background: color-mix(in srgb, var(--banda-bajo) 55%, var(--banda-medio));
    }
    .tajada[data-tono='2'],
    .muestra[data-tono='2'] {
      background: var(--banda-medio);
    }
    .tajada[data-tono='3'],
    .muestra[data-tono='3'] {
      background: color-mix(in srgb, var(--banda-medio) 45%, var(--banda-alto));
    }
    .tajada[data-tono='4'],
    .muestra[data-tono='4'] {
      background: var(--banda-alto);
    }
    .tajada[data-tono='5'],
    .muestra[data-tono='5'] {
      background: var(--borde-control);
    }
    .valor {
      text-align: right;
      color: var(--texto-meta);
      font-size: var(--texto-caption);
    }
    .leyenda {
      list-style: none;
      margin: var(--espacio-4) 0 0;
      padding: 0;
      display: flex;
      flex-wrap: wrap;
      gap: var(--espacio-8) var(--espacio-16);
      color: var(--texto-meta);
      font-size: var(--texto-caption);
    }
    .leyenda li {
      display: flex;
      align-items: center;
      gap: var(--espacio-8);
    }
    .muestra {
      width: 12px;
      height: 12px;
      border-radius: 3px;
      flex: none;
    }
    @media (max-width: 520px) {
      .fila {
        grid-template-columns: 1fr 3rem;
      }
      .pista {
        grid-column: 1 / -1;
        order: 3;
      }
    }
  `,
})
export class GraficaApilada {
  readonly filas = input.required<FilaApilada[]>();
  readonly leyenda = input.required<{ etiqueta: string; tono: number }[]>();
  readonly idPrueba = input('grafica-apilada');
}
