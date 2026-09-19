import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

/** Géneros preferidos: cero o más. Viajan en tags_preferidos y sirven para mostrar
 * afinidad en la ficha; no cambian el riesgo. */
@Component({
  selector: 'app-selector-generos',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="grupo" role="group" aria-labelledby="generos-titulo" data-testid="grupo-generos">
      <p class="titulo" id="generos-titulo">Géneros que sueles jugar</p>
      <p class="meta ayuda">
        Opcional, los que quieras. Sirven para ver si un juego entra en lo tuyo; no cambian el riesgo estimado.
      </p>
      <div class="chips">
        @for (genero of generos(); track genero) {
          <button
            type="button"
            class="chip"
            data-testid="chip-genero"
            [attr.data-genero]="genero"
            [attr.aria-pressed]="elegidos().includes(genero)"
            (click)="alternar.emit(genero)"
          >
            {{ genero }}
          </button>
        } @empty {
          <p class="meta">El catálogo todavía no cargó sus géneros.</p>
        }
      </div>
    </div>
  `,
  styles: `
    .grupo {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
    }
    .titulo {
      font-size: var(--texto-body);
    }
    .ayuda {
      margin: 0;
      max-width: var(--medida-lectura);
      line-height: var(--interlineado-largo);
    }
    .chips {
      display: flex;
      flex-wrap: wrap;
      gap: var(--espacio-8);
    }
  `,
})
export class SelectorGeneros {
  readonly generos = input.required<string[]>();
  readonly elegidos = input.required<string[]>();

  readonly alternar = output<string>();
}
