import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

/** Géneros preferidos: cero o más, como pastillas grandes que se prenden. Viajan en
 * tags_preferidos y sirven para la afinidad y las sugerencias; no cambian el riesgo. El
 * título y la explicación los pone la página. */
@Component({
  selector: 'app-selector-generos',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="chips" role="group" [attr.aria-labelledby]="etiquetadoPor()" data-testid="grupo-generos">
      @for (genero of generos(); track genero) {
        <button
          type="button"
          class="genero"
          data-testid="chip-genero"
          [attr.data-genero]="genero"
          [attr.aria-pressed]="elegidos().includes(genero)"
          (click)="alternar.emit(genero)"
        >
          @if (elegidos().includes(genero)) {
            <span class="marca" aria-hidden="true">✓</span>
          }
          {{ genero }}
        </button>
      } @empty {
        <p class="meta">El catálogo todavía no cargó sus géneros.</p>
      }
    </div>
  `,
  styles: `
    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: var(--espacio-8);
    }
    .genero {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-height: 44px;
      padding: 0 var(--espacio-16);
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-pildora);
      background: var(--superficie-2);
      color: var(--texto);
      font-size: var(--texto-body-sm);
      cursor: pointer;
    }
    .genero:hover {
      border-color: var(--neon);
    }
    .genero[aria-pressed='true'] {
      border-color: var(--neon);
      background:
        linear-gradient(rgb(var(--accion-canal) / 0.16), rgb(var(--accion-canal) / 0.16)),
        var(--superficie-2);
      box-shadow: inset 0 0 0 1px var(--neon);
    }
    .marca {
      color: var(--accion-tinta);
      font-weight: var(--peso-clave);
    }
  `,
})
export class SelectorGeneros {
  readonly generos = input.required<string[]>();
  readonly elegidos = input.required<string[]>();
  readonly etiquetadoPor = input.required<string>();
  readonly alternar = output<string>();
}
