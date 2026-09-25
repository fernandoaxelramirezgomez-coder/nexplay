import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

/** Géneros como controles secundarios, con estado visible y desplazamiento horizontal en móvil. */
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
      gap: var(--espacio-8);
    }
    .chip {
      min-height: 36px;
      padding: 7px var(--espacio-12);
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-pildora);
      background: transparent;
      white-space: nowrap;
      transition:
        color var(--duracion-rapida) var(--curva),
        border-color var(--duracion-rapida) var(--curva),
        background var(--duracion-rapida) var(--curva);
    }
    .chip::after {
      display: none;
    }
    .chip:hover {
      border-color: var(--neon);
      background: var(--superficie-tarjeta);
    }
    .chip[aria-pressed='true'] {
      border-color: var(--neon);
      background: var(--neon-tenue);
      color: var(--texto);
    }
    @media (max-width: 640px) {
      .generos {
        flex-wrap: nowrap;
        overflow-x: auto;
        margin-inline-end: calc(var(--espacio-16) * -1);
        padding: 2px var(--espacio-16) var(--espacio-8) 2px;
        scrollbar-width: none;
      }
      .generos::-webkit-scrollbar {
        display: none;
      }
    }
  `,
})
export class FiltrosCatalogo {
  readonly genero = input('');
  readonly generos = input<string[]>([]);

  readonly generoCambio = output<string>();
}
