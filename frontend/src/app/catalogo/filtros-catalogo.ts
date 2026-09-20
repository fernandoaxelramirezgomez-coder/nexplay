import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

/** Géneros como chips discretos: el protagonista del hero es el buscador. */
@Component({
  selector: 'app-filtros-catalogo',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="generos" role="group" aria-label="Filtrar por género">
      <button
        type="button"
        class="chip"
        data-testid="filtro-genero"
        data-genero=""
        [attr.aria-pressed]="!genero()"
        (click)="generoCambio.emit('')"
      >
        Todos
      </button>
      @for (opcion of generos(); track opcion) {
        <button
          type="button"
          class="chip"
          data-testid="filtro-genero"
          [attr.data-genero]="opcion"
          [attr.aria-pressed]="genero() === opcion"
          (click)="generoCambio.emit(genero() === opcion ? '' : opcion)"
        >
          {{ opcion }}
        </button>
      }
    </div>
  `,
  styles: `
    .generos {
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: var(--espacio-8);
    }
  `,
})
export class FiltrosCatalogo {
  readonly genero = input('');
  readonly generos = input<string[]>([]);

  readonly generoCambio = output<string>();
}
