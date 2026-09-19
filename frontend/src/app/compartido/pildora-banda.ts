import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { NivelRiesgo } from '../api/contrato';

/** Banda de riesgo: relleno del color de banda con texto oscuro (el blanco encima no
 * pasa AA). El rótulo dice de dónde sale la banda: "Riesgo general" o "Riesgo para tu perfil". */
@Component({
  selector: 'app-pildora-banda',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<span class="pildora" [attr.data-banda]="banda()" data-testid="pildora-banda"
    >{{ rotulo() }} · {{ banda() }}</span
  >`,
  styles: `
    .pildora {
      display: inline-block;
      padding: 2px var(--espacio-12);
      border-radius: var(--radio-pildora);
      color: var(--texto-sobre-banda);
      font-size: var(--texto-caption);
      white-space: nowrap;
    }
    .pildora[data-banda='bajo'] {
      background: var(--banda-bajo);
    }
    .pildora[data-banda='medio'] {
      background: var(--banda-medio);
    }
    .pildora[data-banda='alto'] {
      background: var(--banda-alto);
    }
  `,
})
export class PildoraBanda {
  readonly banda = input.required<NivelRiesgo>();
  readonly rotulo = input('Riesgo general');
}
