import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

@Component({
  selector: 'app-filtros-catalogo',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="filtros">
      <label class="busqueda">
        <span class="meta">Buscar por nombre</span>
        <input
          type="search"
          placeholder="half-life"
          autocomplete="off"
          data-testid="filtro-texto"
          [value]="texto()"
          (input)="textoCambio.emit($any($event.target).value)"
        />
      </label>
      <div class="generos" role="group" aria-label="Género">
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
    </div>
  `,
  styles: `
    .filtros {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-16);
    }
    .busqueda {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-8);
      max-width: 420px;
    }
    input {
      font: inherit;
      letter-spacing: inherit;
      color: var(--texto);
      background: var(--superficie-tarjeta);
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-boton);
      padding: 10px var(--espacio-16);
      transition: border-color var(--duracion-rapida) var(--curva);
    }
    input::placeholder {
      color: var(--texto-meta);
    }
    input:hover,
    input:focus {
      border-color: var(--texto);
    }
    .generos {
      display: flex;
      flex-wrap: wrap;
      gap: var(--espacio-8);
    }
  `,
})
export class FiltrosCatalogo {
  readonly texto = input('');
  readonly genero = input('');
  readonly generos = input<string[]>([]);

  readonly textoCambio = output<string>();
  readonly generoCambio = output<string>();
}
