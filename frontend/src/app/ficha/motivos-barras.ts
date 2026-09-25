import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { ExplicacionJuego } from '../api/contrato';
import { porcentaje } from '../dominio/formato';

@Component({
  selector: 'app-motivos-barras',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="seccion" data-testid="motivos">
      <h2 class="rotulo-seccion">Motivos de insatisfacción más frecuentes</h2>
      @if (explicacion(); as datos) {
        @if (datos.motivos.length) {
          <ul class="lista">
            @for (motivo of datos.motivos; track motivo.motivo) {
              <li class="fila">
                <span class="nombre">{{ motivo.motivo }}</span>
                <span class="pista">
                  <span class="barra" [style.width.%]="motivo.frecuencia * 100"></span>
                </span>
                <span class="valor mono">{{ pct(motivo.frecuencia) }}</span>
              </li>
            }
          </ul>
          <p class="meta contexto">
            {{ datos.n_casos }} reseñas de arrepentimiento temprano analizadas, {{ pct(datos.pct_clasificados) }}
            mencionan alguno de estos motivos. Los porcentajes son sobre las clasificadas, no sobre el total.
          </p>
        } @else {
          <p class="meta">
            Sin motivos disponibles: hay muy pocas reseñas de arrepentimiento temprano de este juego
            ({{ datos.n_casos }}).
          </p>
        }
      } @else {
        <p class="meta">No se pudieron cargar los motivos.</p>
      }
    </section>
  `,
  styles: `
    .rotulo-seccion {
      margin-bottom: var(--espacio-16);
    }
    .lista {
      list-style: none;
      margin: 0 0 var(--espacio-16);
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: var(--espacio-8);
    }
    .fila {
      display: grid;
      grid-template-columns: 9rem 1fr 3rem;
      align-items: center;
      gap: var(--espacio-12);
    }
    .pista {
      height: 10px;
      border-radius: var(--radio-pildora);
      background: var(--superficie-lienzo);
      overflow: hidden;
    }
    .barra {
      display: block;
      height: 100%;
      background: var(--neon);
    }
    .valor {
      text-align: right;
      color: var(--texto-meta);
      font-size: var(--texto-caption);
    }
    .contexto {
      margin: 0;
      max-width: var(--medida-lectura);
      line-height: var(--interlineado-largo);
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
export class MotivosBarras {
  readonly explicacion = input.required<ExplicacionJuego | undefined>();

  protected readonly pct = porcentaje;
}
