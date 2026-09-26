import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

import { Opcion } from '../dominio/opciones-perfil';

/** Grupo de radios con aspecto de tarjeta. El radio nativo queda oculto para lectores
 * de pantalla y teclado, así el grupo sigue siendo un radiogroup de verdad. */
@Component({
  selector: 'app-tarjetas-opcion',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <fieldset class="grupo" [attr.data-testid]="'grupo-' + nombre()">
      <legend>{{ etiqueta() }}</legend>
      @if (ayuda()) {
        <p class="meta ayuda">{{ ayuda() }}</p>
      }
      <div class="opciones">
        @for (opcion of opciones(); track opcion.valor) {
          <label class="opcion" [class.elegida]="opcion.valor === valor()">
            <input
              type="radio"
              class="solo-lector"
              [name]="nombre()"
              [value]="opcion.valor"
              [checked]="opcion.valor === valor()"
              (change)="valorCambio.emit(opcion.valor)"
            />
            <span>{{ opcion.etiqueta }}</span>
          </label>
        }
      </div>
    </fieldset>
  `,
  styles: `
    .grupo {
      border: 0;
      padding: 0;
      margin: 0;
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
    }
    legend {
      padding: 0;
      font-size: var(--texto-body);
    }
    .ayuda {
      margin: 0;
    }
    /* En rejilla y no en fila: con flex-wrap, "Muchos (más de 15 al año)" se quedaba
       solo en un segundo renglón y el grupo parecía cortado. Columnas de ancho igual que
       se acomodan solas. */
    .opciones {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(min(100%, 13rem), 1fr));
      gap: var(--espacio-8);
    }
    /* Son respuestas que se pulsan: llevan filo y superficie, como cualquier botón. */
    .opcion {
      display: flex;
      align-items: center;
      min-height: 44px;
      padding: var(--espacio-8) var(--espacio-12);
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-tarjeta);
      background: transparent;
      color: var(--texto-meta);
      font-size: var(--texto-body-sm);
      cursor: pointer;
      transition:
        color var(--duracion-rapida) var(--curva),
        border-color var(--duracion-rapida) var(--curva),
        background var(--duracion-rapida) var(--curva);
    }
    .opcion:hover {
      border-color: var(--neon);
      color: var(--texto);
    }
    .opcion.elegida {
      border-color: var(--neon);
      background: var(--acento-sistema);
      color: var(--texto);
    }
    .opcion.elegida span::before {
      content: '✓ ';
      color: var(--neon);
    }
    .opcion:has(input:focus-visible) {
      outline: 2px solid var(--foco);
      outline-offset: 2px;
    }
  `,
})
export class TarjetasOpcion<T> {
  readonly nombre = input.required<string>();
  readonly etiqueta = input.required<string>();
  readonly ayuda = input('');
  readonly opciones = input.required<Opcion<T>[]>();
  readonly valor = input.required<T | null>();

  readonly valorCambio = output<T>();
}
