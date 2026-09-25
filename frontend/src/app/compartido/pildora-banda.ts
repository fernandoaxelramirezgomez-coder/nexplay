import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { NivelRiesgo } from '../api/contrato';
import { ROTULO_RIESGO } from '../dominio/etiqueta-riesgo';

/** Banda de riesgo: relleno del color de banda con texto oscuro (el blanco encima no
 * pasa AA) y un filo de la tinta de la banda, que en el tema claro es lo que separa el
 * relleno del papel. El rótulo es uno solo: la banda es del juego, no del perfil. */
@Component({
  selector: 'app-pildora-banda',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<span class="pildora" [attr.data-banda]="banda()" data-testid="pildora-banda"
    >{{ rotulo }} · {{ banda() }}</span
  >`,
  styles: `
    .pildora {
      display: inline-block;
      padding: 1px 11px;
      border: 1px solid var(--filo-banda);
      border-radius: var(--radio-pildora);
      color: var(--texto-sobre-banda);
      font-size: var(--texto-caption);
      white-space: nowrap;
    }
    .pildora[data-banda='bajo'] {
      background: var(--banda-bajo);
      --filo-banda: var(--banda-bajo-texto);
    }
    .pildora[data-banda='medio'] {
      background: var(--banda-medio);
      --filo-banda: var(--banda-medio-texto);
    }
    .pildora[data-banda='alto'] {
      background: var(--banda-alto);
      --filo-banda: var(--banda-alto-texto);
    }
  `,
})
export class PildoraBanda {
  readonly banda = input.required<NivelRiesgo>();
  protected readonly rotulo = ROTULO_RIESGO;
}
