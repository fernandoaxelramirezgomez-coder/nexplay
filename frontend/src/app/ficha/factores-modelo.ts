import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { FactorPrediccion } from '../api/contrato';
import { lecturaDeJugador } from '../dominio/factores';

const NOTA_METACRITIC = 'nota de Metacritic';

/** Cada factor con una flecha según suba o baje el riesgo, en vez de viñetas de texto.
 * En "nota de Metacritic" se muestra la nota del juego y el promedio del catálogo contra
 * el que se lee, para que "por encima" o "por debajo" tenga referencia. */
@Component({
  selector: 'app-factores-modelo',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <p class="leyenda meta">
      <span class="marca" data-direccion="aumenta" aria-hidden="true">↑</span> sube el riesgo estimado ·
      <span class="marca" data-direccion="reduce" aria-hidden="true">↓</span> lo baja
    </p>
    <ul class="factores" data-testid="factores-lista">
      @for (factor of factores(); track factor.etiqueta) {
        <li class="factor" [attr.data-direccion]="factor.direccion">
          <svg class="flecha" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            @if (factor.direccion === 'aumenta') {
              <path d="M12 19V5m0 0-6 6m6-6 6 6" fill="none" stroke="currentColor" stroke-width="2" />
            } @else {
              <path d="M12 5v14m0 0 6-6m-6 6-6-6" fill="none" stroke="currentColor" stroke-width="2" />
            }
          </svg>
          <div>
            <p class="etiqueta">
              @if (factor.etiqueta === notaMetacritic && metacritic() !== null) {
                Su nota de Metacritic está {{ factor.valor_relativo === 'alto' ? 'por encima' : 'por debajo' }} del
                promedio
              } @else {
                {{ comoSeLee(factor) }}
              }
            </p>
            @if (factor.etiqueta === notaMetacritic && metacritic() !== null) {
              <p class="detalle meta">{{ metacritic() }} contra {{ promedioTexto() }} del catálogo</p>
            }
          </div>
        </li>
      }
    </ul>
  `,
  styles: `
    .leyenda {
      margin: 0 0 var(--espacio-12);
    }
    .marca[data-direccion='aumenta'] {
      color: var(--banda-alto-texto);
    }
    .marca[data-direccion='reduce'] {
      color: var(--banda-bajo-texto);
    }
    .factores {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
    }
    .factor {
      display: grid;
      grid-template-columns: auto 1fr;
      gap: var(--espacio-12);
      align-items: start;
    }
    .flecha {
      margin-top: 2px;
    }
    .factor[data-direccion='aumenta'] .flecha {
      color: var(--banda-alto-texto);
    }
    .factor[data-direccion='reduce'] .flecha {
      color: var(--banda-bajo-texto);
    }
    .etiqueta {
      font-size: var(--texto-body-sm);
    }
    .detalle {
      margin: 0;
      line-height: 1.4;
    }
  `,
})
export class FactoresModelo {
  readonly factores = input.required<FactorPrediccion[]>();
  /** Nota del juego, para el factor de Metacritic. */
  readonly metacritic = input<number | null>(null);
  /** Promedio del catálogo; se calcula en el frontend (la API no lo expone). */
  readonly promedio = input<number | null>(null);

  protected readonly notaMetacritic = NOTA_METACRITIC;

  protected comoSeLee(factor: FactorPrediccion): string {
    return lecturaDeJugador(factor);
  }

  protected promedioTexto(): string {
    const promedio = this.promedio();
    return promedio === null ? 'sin datos' : promedio.toFixed(1);
  }
}
