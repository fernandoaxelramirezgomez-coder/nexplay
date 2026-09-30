import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { FactorPrediccion } from '../api/contrato';
import { TEXTO_TIPICO, lecturaDeJugador, textoEvidencia } from '../dominio/factores';

/** Cada factor en el orden en que más aporta según el modelo, con una flecha según suba o
 * baje el riesgo. Un factor cerca de lo típico va sin flecha: casi no mueve la estimación, y
 * una flecha ahí podía contradecir la cifra (una nota de 86 sobre un promedio de 85.5 que el
 * modelo lee por debajo de su media). Cada uno dice su nivel de evidencia. Lo usan la ficha y
 * Comparar. */
@Component({
  selector: 'app-factores-modelo',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <p class="leyenda meta">
      <span class="marca" data-direccion="aumenta" aria-hidden="true">↑</span> sube el riesgo estimado ·
      <span class="marca" data-direccion="reduce" aria-hidden="true">↓</span> lo baja ·
      <span class="marca" data-direccion="neutra" aria-hidden="true">–</span> casi no lo mueve
    </p>
    <ul class="factores" data-testid="factores-lista">
      @for (factor of factores(); track factor.etiqueta) {
        <li
          class="factor"
          data-testid="factor"
          [attr.data-direccion]="factor.cerca_de_lo_tipico ? 'neutra' : factor.direccion"
          [attr.data-evidencia]="factor.evidencia"
        >
          <svg class="flecha" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            @if (factor.cerca_de_lo_tipico) {
              <path d="M6 12h12" fill="none" stroke="currentColor" stroke-width="2" />
            } @else if (factor.direccion === 'aumenta') {
              <path d="M12 19V5m0 0-6 6m6-6 6 6" fill="none" stroke="currentColor" stroke-width="2" />
            } @else {
              <path d="M12 5v14m0 0 6-6m-6 6-6-6" fill="none" stroke="currentColor" stroke-width="2" />
            }
          </svg>
          <div>
            <p class="etiqueta">{{ comoSeLee(factor) }}</p>
            @if (factor.cerca_de_lo_tipico) {
              <p class="detalle meta" data-testid="factor-tipico">{{ tipico }}.</p>
            }
            <p class="evidencia meta" data-testid="factor-evidencia">{{ evidencia(factor) }}</p>
          </div>
        </li>
      }
    </ul>
  `,
  styles: `
    .leyenda {
      margin: 0 0 var(--espacio-16);
    }
    .marca[data-direccion='aumenta'] {
      color: var(--banda-alto-texto);
    }
    .marca[data-direccion='reduce'] {
      color: var(--banda-bajo-texto);
    }
    .marca[data-direccion='neutra'] {
      color: var(--texto-2);
    }
    .factores {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: var(--espacio-16);
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
    .factor[data-direccion='neutra'] .flecha {
      color: var(--texto-2);
    }
    .etiqueta {
      font-size: var(--texto-body-sm);
    }
    .detalle,
    .evidencia {
      margin: 0;
      line-height: 1.45;
    }
    .factor[data-evidencia='debil'] .evidencia {
      font-style: italic;
    }
  `,
})
export class FactoresModelo {
  readonly factores = input.required<FactorPrediccion[]>();

  protected readonly tipico = TEXTO_TIPICO.charAt(0).toUpperCase() + TEXTO_TIPICO.slice(1);

  protected comoSeLee(factor: FactorPrediccion): string {
    return lecturaDeJugador(factor);
  }

  protected evidencia(factor: FactorPrediccion): string {
    const texto = textoEvidencia(factor);
    return texto.charAt(0).toUpperCase() + texto.slice(1);
  }
}
