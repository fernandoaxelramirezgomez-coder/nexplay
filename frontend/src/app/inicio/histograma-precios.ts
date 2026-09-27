import { ChangeDetectionStrategy, Component, computed, input, signal } from '@angular/core';

import { NivelRiesgo } from '../api/contrato';
import { NOMBRE_NIVEL, RangoDePrecio } from '../dominio/antes-de-pagar';
import { ORDEN_BANDAS } from '../dominio/estantes';

type Nivel = 'todos' | NivelRiesgo;

const OPCIONES: readonly { id: Nivel; nombre: string }[] = [
  { id: 'todos', nombre: 'Todos' },
  { id: 'bajo', nombre: 'Bajo' },
  { id: 'medio', nombre: 'Medio' },
  { id: 'alto', nombre: 'Alto' },
];

/** «¿Cuánto cuestan?»: los juegos del catálogo por rango de precio, apilados por nivel de
 * riesgo. Los botones dejan un nivel a la vez y las columnas se animan; la escala no
 * cambia al filtrar, para que se vea cuánto aporta cada nivel. Cada columna dice su cifra
 * en texto y, con el cursor o el foco, el detalle. */
@Component({
  selector: 'app-histograma-precios',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="histograma" data-testid="histograma-precios">
      <div class="cabeza">
        <p class="titulo" id="titulo-histograma">¿Cuánto cuestan?</p>
        <div class="niveles" role="group" aria-label="Ver un nivel de riesgo">
          @for (opcion of opciones; track opcion.id) {
            <button
              type="button"
              class="nivel"
              [attr.data-nivel]="opcion.id"
              [attr.aria-pressed]="nivel() === opcion.id"
              data-testid="histograma-nivel"
              (click)="nivel.set(opcion.id)"
            >
              @if (opcion.id !== 'todos') {
                <span class="muestra" [attr.data-banda]="opcion.id" aria-hidden="true"></span>
              }
              {{ opcion.nombre }}
            </button>
          }
        </div>
      </div>
      <ul class="columnas" aria-labelledby="titulo-histograma">
        @for (rango of rangos(); track rango.etiqueta) {
          <li
            class="columna"
            tabindex="0"
            data-testid="histograma-columna"
            [attr.data-rango]="rango.etiqueta"
            [attr.data-cuantos]="cuantos(rango)"
            [attr.aria-label]="detalle(rango)"
          >
            <!-- La cifra va dentro de la pista, después de los tramos: con column-reverse queda
                 justo encima de la columna, a la altura que tenga. -->
            <span class="pista" aria-hidden="true">
              @for (banda of bandas; track banda) {
                <span class="tramo" [attr.data-banda]="banda" [style.block-size]="alto(rango, banda)"></span>
              }
              <span class="valor mono">{{ cuantos(rango) }}</span>
            </span>
            <span class="nombre" aria-hidden="true">{{ rango.etiqueta }}</span>
            <span class="detalle" aria-hidden="true">{{ detalle(rango) }}</span>
          </li>
        }
      </ul>
      <p class="pie-histograma">Precios en pesos (MXN) de Steam México.</p>
    </div>
  `,
  styles: `
    .histograma {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-16);
    }
    .cabeza {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: var(--espacio-8) var(--espacio-16);
    }
    .titulo {
      margin: 0;
      color: var(--texto);
      font-size: 18px;
      font-weight: 700;
    }
    .niveles {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .nivel {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      min-height: 36px;
      padding: 0 var(--espacio-12);
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-pildora);
      background: var(--superficie-2);
      color: var(--texto);
      font: inherit;
      font-size: var(--texto-caption);
      cursor: pointer;
    }
    .nivel[aria-pressed='true'] {
      border-color: var(--neon);
      background: color-mix(in srgb, var(--accion) 16%, var(--superficie));
      box-shadow: inset 0 0 0 1px var(--neon);
    }
    .muestra {
      width: 10px;
      height: 10px;
      border-radius: 50%;
    }
    .columnas {
      list-style: none;
      margin: 0;
      padding: var(--espacio-24) 0 0;
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      align-items: end;
      gap: var(--espacio-8);
    }
    .columna {
      position: relative;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--espacio-4);
      min-width: 0;
      border-radius: 8px;
      outline: none;
    }
    .columna:focus-visible {
      box-shadow: 0 0 0 2px var(--foco);
    }
    /* Los tramos de abajo hacia arriba: bajo, medio, alto. */
    /* El relleno de arriba es el lugar de la cifra cuando la columna llega al tope. */
    .pista {
      display: flex;
      flex-direction: column-reverse;
      align-items: center;
      width: 100%;
      max-width: 56px;
      height: 210px;
      padding-top: 30px;
    }
    .pista .valor {
      padding-bottom: 4px;
    }
    .tramo {
      display: block;
      width: 100%;
      transition: block-size 0.7s var(--curva);
    }
    .tramo[data-banda='alto'] {
      border-radius: 6px 6px 0 0;
    }
    .tramo[data-banda='bajo'],
    .muestra[data-banda='bajo'] {
      background: var(--banda-bajo);
    }
    .tramo[data-banda='medio'],
    .muestra[data-banda='medio'] {
      background: var(--banda-medio);
    }
    .tramo[data-banda='alto'],
    .muestra[data-banda='alto'] {
      background: var(--banda-alto);
    }
    .valor,
    .nombre {
      font-size: var(--texto-caption);
      text-align: center;
    }
    .valor {
      color: var(--texto);
      font-weight: 600;
    }
    /* Se parte en el guion: «$200–» y «400» en dos renglones si no cabe. */
    .nombre {
      color: var(--texto-meta);
      overflow-wrap: anywhere;
      line-height: 1.2;
    }
    /* El detalle de la columna, arriba de ella, con el cursor o el foco. */
    .detalle {
      position: absolute;
      bottom: calc(100% + 6px);
      left: 50%;
      z-index: 2;
      width: max-content;
      max-width: 220px;
      padding: 6px 10px;
      border: 1px solid var(--borde-control);
      border-radius: 8px;
      background: var(--superficie-tarjeta);
      color: var(--texto);
      font-size: var(--texto-caption);
      line-height: 1.35;
      text-align: center;
      box-shadow: var(--sombra-suave);
      transform: translateX(-50%);
      opacity: 0;
      visibility: hidden;
      pointer-events: none;
      transition: opacity var(--duracion-rapida) var(--curva);
    }
    .columna:hover .detalle,
    .columna:focus-visible .detalle {
      opacity: 1;
      visibility: visible;
    }
    .columna:first-child .detalle {
      left: 0;
      transform: none;
    }
    .columna:last-child .detalle {
      left: auto;
      right: 0;
      transform: none;
    }
    .pie-histograma {
      margin: 0;
      color: var(--texto-meta);
      font-size: var(--texto-caption);
    }
    @media (max-width: 640px) {
      .pista {
        height: 170px;
      }
      .columnas {
        gap: 4px;
      }
    }
  `,
})
export class HistogramaPrecios {
  readonly rangos = input.required<RangoDePrecio[]>();
  /** Falso hasta que la sección entra en pantalla: entonces las columnas crecen. */
  readonly visible = input(true);

  protected readonly opciones = OPCIONES;
  protected readonly bandas = ORDEN_BANDAS;
  protected readonly nivel = signal<Nivel>('todos');

  /** La columna más alta con todos los niveles: la escala no cambia al filtrar. */
  private readonly tope = computed(() =>
    Math.max(1, ...this.rangos().map((r) => r.porNivel.bajo + r.porNivel.medio + r.porNivel.alto)),
  );

  protected cuantos(rango: RangoDePrecio): number {
    const nivel = this.nivel();
    return nivel === 'todos' ? rango.porNivel.bajo + rango.porNivel.medio + rango.porNivel.alto : rango.porNivel[nivel];
  }

  protected alto(rango: RangoDePrecio, banda: NivelRiesgo): string {
    const nivel = this.nivel();
    if (!this.visible() || (nivel !== 'todos' && nivel !== banda)) {
      return '0';
    }
    return `${((rango.porNivel[banda] / this.tope()) * 100).toFixed(1)}%`;
  }

  protected detalle(rango: RangoDePrecio): string {
    const nivel = this.nivel();
    const n = this.cuantos(rango);
    const juegos = n === 1 ? 'juego' : 'juegos';
    const verbo = n === 1 ? rango.detalle.replace(/^cuestan/, 'cuesta').replace(/^son/, 'es') : rango.detalle;
    if (nivel !== 'todos') {
      return `${n} ${juegos} de ${NOMBRE_NIVEL[nivel].toLowerCase()} ${verbo}`;
    }
    const { bajo, medio, alto } = rango.porNivel;
    return `${n} ${juegos} ${verbo}: ${bajo} de riesgo bajo, ${medio} medio y ${alto} alto`;
  }
}
