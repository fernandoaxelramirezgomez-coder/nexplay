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
    .opciones {
      display: flex;
      flex-wrap: wrap;
      gap: var(--espacio-8);
    }
    .opcion {
      padding: 10px var(--espacio-16);
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-boton);
      color: var(--texto-meta);
      cursor: pointer;
      transition:
        color var(--duracion-rapida) var(--curva),
        border-color var(--duracion-rapida) var(--curva),
        background var(--duracion-rapida) var(--curva);
    }
    .opcion:hover {
      color: var(--texto);
      border-color: var(--texto);
    }
    /* Elegida: índigo MÁS borde claro y una marca; el color solo no basta. */
    .opcion.elegida {
      background: var(--acento-sistema);
      border-color: var(--texto);
      color: var(--texto);
    }
    .opcion.elegida span::before {
      content: '✓ ';
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
  readonly valor = input.required<T>();

  readonly valorCambio = output<T>();
}
