import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';

import { JuegoCatalogo } from '../api/contrato';
import { opcionesDeGenero } from '../dominio/generos';

/** Los géneros en un panel propio: tarjetas iguales en rejilla, cada una con su emoji y
 * cuántos juegos tiene, para que se lean con orden y llamen más que una fila de píldoras.
 * El filo y el relleno del elegido van en el color de la vista, no uno por género: en
 * Explorar los colores del riesgo ya están en cada tarjeta. En el teléfono, una tira que
 * se desliza. */
@Component({
  selector: 'app-filtros-catalogo',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="panel-generos">
      <p class="titulo-generos" id="titulo-generos">Filtra por género <span class="nota">(puedes elegir varios)</span></p>
      <div class="generos" role="group" aria-labelledby="titulo-generos">
        @for (opcion of opciones(); track opcion.genero) {
          <button
            type="button"
            class="genero"
            data-testid="filtro-genero"
            [attr.data-genero]="opcion.genero"
            [attr.aria-pressed]="opcion.genero ? elegidos().includes(opcion.genero) : !elegidos().length"
            (click)="alternar(opcion.genero)"
          >
            <span class="emoji" aria-hidden="true">{{ opcion.emoji }}</span>
            <span class="nombre">{{ opcion.nombre }}</span>
            <span class="cuantos">{{ opcion.juegos }}<span class="solo-lector"> juegos</span></span>
          </button>
        }
      </div>
    </div>
  `,
  styles: `
    .panel-generos {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
      padding: var(--espacio-16);
      border: 1px solid var(--borde);
      border-radius: var(--radio-tarjeta);
      background: var(--superficie);
    }
    .titulo-generos {
      margin: 0;
      text-align: center;
      color: var(--texto);
      font-size: var(--texto-body-sm);
      font-weight: 600;
    }
    .nota {
      color: var(--texto-meta);
      font-weight: 400;
    }
    .generos {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
      gap: var(--espacio-8);
    }
    /* position: relative ancla aquí el « juegos» oculto para el lector de pantalla: sin
       ella se ubicaba respecto a la página, la tira del teléfono no lo recortaba y la
       página entera se desplazaba 1,900 px a lo ancho. */
    .genero {
      position: relative;
      display: flex;
      align-items: center;
      gap: 10px;
      min-height: 52px;
      padding: var(--espacio-8) var(--espacio-12);
      border: 1px solid var(--borde-control);
      border-radius: 12px;
      background: var(--superficie-2);
      color: var(--texto);
      font-family: var(--fuente-texto);
      font-size: var(--texto-body-sm);
      font-weight: 600;
      text-align: start;
      white-space: nowrap;
      cursor: pointer;
      transition:
        border-color var(--duracion-rapida) var(--curva),
        background var(--duracion-rapida) var(--curva),
        transform var(--duracion-rapida) var(--curva);
    }
    .genero:hover {
      border-color: var(--neon);
      transform: translateY(-1px);
    }
    .genero:focus-visible {
      outline: 2px solid var(--foco);
      outline-offset: 2px;
    }
    .emoji {
      flex: none;
      width: 28px;
      font-size: 22px;
      line-height: 1;
      text-align: center;
    }
    /* El nombre entero, en dos renglones si hace falta: «Acceso anticipado» y
       «Multijugador masivo» cortados con «…» no se entendían. */
    .nombre {
      flex: 1;
      min-width: 0;
      white-space: normal;
      line-height: 1.2;
    }
    .cuantos {
      color: var(--texto-meta);
      font-family: var(--fuente-mono);
      font-size: var(--texto-caption);
      font-weight: 400;
    }
    /* El elegido: relleno y filo del color de la vista. */
    .genero[aria-pressed='true'] {
      border-color: var(--neon);
      background: color-mix(in srgb, var(--accion) 16%, var(--superficie));
      box-shadow: inset 0 0 0 1px var(--neon);
    }
    @media (max-width: 640px) {
      .generos {
        display: flex;
        overflow-x: auto;
        margin-inline-end: calc(var(--espacio-16) * -1);
        padding: 2px var(--espacio-16) var(--espacio-4) 2px;
        scrollbar-width: none;
      }
      .generos::-webkit-scrollbar {
        display: none;
      }
      .genero {
        flex: 0 0 auto;
      }
      .nombre {
        white-space: nowrap;
      }
    }
  `,
})
export class FiltrosCatalogo {
  /** Los géneros elegidos; vacío es «Todos». */
  readonly elegidos = input<readonly string[]>([]);
  readonly generos = input<string[]>([]);
  readonly juegos = input<readonly JuegoCatalogo[]>([]);

  readonly elegidosCambio = output<string[]>();

  protected readonly opciones = computed(() => opcionesDeGenero(this.generos(), this.juegos()));

  /** Cada género se prende y se apaga por su cuenta; «Todos» los apaga a todos. */
  protected alternar(genero: string): void {
    const elegidos = this.elegidos();
    if (!genero) {
      this.elegidosCambio.emit([]);
    } else {
      this.elegidosCambio.emit(
        elegidos.includes(genero) ? elegidos.filter((g) => g !== genero) : [...elegidos, genero],
      );
    }
  }
}
