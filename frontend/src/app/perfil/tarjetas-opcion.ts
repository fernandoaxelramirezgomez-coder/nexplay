import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

import { Opcion } from '../dominio/opciones-perfil';

/** Las respuestas de una pregunta del perfil, como tarjetas grandes: icono (o el medidor
 * de la fricción), nombre, una línea de detalle y la marca ✓ en la elegida. Debajo hay
 * radios —o casillas, con `multiple`— nativos escondidos para lector de pantalla y
 * teclado, así el grupo sigue siendo un radiogroup (o un grupo de casillas) de verdad.
 *
 * El título y la explicación de la pregunta los pone la página: aquí el grupo se nombra
 * con aria-labelledby. Los iconos de plataforma son propios, no los logotipos oficiales
 * (son marcas registradas); solo el icono lleva el color de la marca. */
@Component({
  selector: 'app-tarjetas-opcion',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      class="opciones"
      [class.cuatro]="opciones().length === 4"
      [class.cinco]="opciones().length === 5"
      [attr.role]="multiple() ? 'group' : 'radiogroup'"
      [attr.aria-labelledby]="etiquetadoPor()"
      [attr.data-testid]="'grupo-' + nombre()"
    >
      @for (opcion of opciones(); track opcion.valor) {
        <label class="opcion" [class.elegida]="elegida(opcion.valor)" [attr.data-marca]="opcion.icono ?? null">
          <input
            [type]="multiple() ? 'checkbox' : 'radio'"
            class="solo-lector"
            [name]="nombre()"
            [checked]="elegida(opcion.valor)"
            (change)="valorCambio.emit(opcion.valor)"
          />
          @if (opcion.nivel) {
            <span class="medidor" aria-hidden="true">
              @for (barra of barras; track barra) {
                <i [class.llena]="barra <= opcion.nivel"></i>
              }
            </span>
          } @else if (opcion.icono) {
            <span class="icono-op" aria-hidden="true">
              <svg viewBox="0 0 24 24">
                @switch (opcion.icono) {
                  @case ('bolsa-1') {
                    <path d="M6 8h12l-1 12H7z" /><path d="M9 8a3 3 0 0 1 6 0" />
                  }
                  @case ('bolsa-2') {
                    <path d="M3 9h10l-1 11H4z" /><path d="M5.5 9a2.5 2.5 0 0 1 5 0" /><path d="M13 6h8l-1 9h-6" />
                    <path d="M15 6a2 2 0 0 1 4 0" />
                  }
                  @case ('bolsa-3') {
                    <path d="M2 11h8l-1 9H3z" /><path d="M8 7h8l-1 9" /><path d="M14 3h8l-1 9h-4" />
                  }
                  @case ('bolsa-4') {
                    <rect x="3" y="4" width="18" height="16" rx="2" /><path d="M3 9h18M8 4v5M16 4v5M7 14h2M11 14h2M15 14h2" />
                  }
                  @case ('moneda-1') {
                    <circle cx="12" cy="12" r="7" /><path d="M12 9v6" />
                  }
                  @case ('moneda-2') {
                    <circle cx="9" cy="13" r="6" /><circle cx="15" cy="11" r="6" />
                  }
                  @case ('moneda-3') {
                    <ellipse cx="12" cy="6" rx="7" ry="3" />
                    <path d="M5 6v4c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 10v4c0 1.7 3.1 3 7 3s7-1.3 7-3v-4" />
                  }
                  @case ('moneda-4') {
                    <ellipse cx="12" cy="5" rx="7" ry="2.5" />
                    <path d="M5 5v14c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5V5M5 10c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5M5 15c0 1.4 3.1 2.5 7 2.5s7-1.1 7-2.5" />
                  }
                  @case ('reloj-1') {
                    <circle cx="12" cy="12" r="9" /><path d="M12 12V7" />
                  }
                  @case ('reloj-2') {
                    <circle cx="12" cy="12" r="9" /><path d="M12 12V7M12 12l4 2" />
                  }
                  @case ('reloj-3') {
                    <circle cx="12" cy="12" r="9" /><path d="M12 12V7M12 12l4 2M12 12l-4 2" />
                  }
                  @case ('pc') {
                    <rect x="3" y="4" width="18" height="12" rx="2" /><path d="M8 20h8M12 16v4" />
                  }
                  @case ('playstation') {
                    <path d="M7 9h10a4 4 0 0 1 4 4l.6 3.4a2 2 0 0 1-3.5 1.6L16 16H8l-2.1 2a2 2 0 0 1-3.5-1.6L3 13a4 4 0 0 1 4-4z" />
                    <path d="M15.5 11.5h.01M17.5 13.5h.01M7 12v3M5.5 13.5h3" />
                  }
                  @case ('xbox') {
                    <circle cx="12" cy="12" r="9" /><path d="M8 8l8 8M16 8l-8 8" />
                  }
                  @case ('nintendo') {
                    <rect x="3" y="5" width="7" height="14" rx="3.5" /><rect x="14" y="5" width="7" height="14" rx="3.5" />
                    <circle cx="6.5" cy="9" r="1.2" /><circle cx="17.5" cy="14.5" r="1.2" />
                  }
                }
              </svg>
            </span>
          }
          <span class="nombre">{{ opcion.etiqueta }}</span>
          @if (opcion.detalle) {
            <span class="detalle">{{ opcion.detalle }}</span>
          }
          <span class="marca" aria-hidden="true">
            <svg viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5" /></svg>
          </span>
        </label>
      }
    </div>
  `,
  styles: `
    .opciones {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(min(100%, 150px), 1fr));
      gap: var(--espacio-8);
    }
    /* Cuatro opciones en 2 × 2: en fila de tres, la cuarta quedaba sola abajo. */
    .opciones.cuatro {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .opciones.cinco {
      grid-template-columns: repeat(5, minmax(0, 1fr));
    }
    /* Son respuestas que se pulsan: llevan filo y superficie, como cualquier control. */
    .opcion {
      position: relative;
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: var(--espacio-8);
      min-height: 104px;
      padding: 14px;
      border: 1px solid var(--borde-control);
      border-radius: 14px;
      background: var(--superficie-2);
      color: var(--texto);
      cursor: pointer;
      transition:
        border-color var(--duracion-rapida) var(--curva),
        box-shadow var(--duracion-rapida) var(--curva);
    }
    .opcion:hover {
      border-color: var(--neon);
    }
    .opcion.elegida {
      border-color: var(--neon);
      background:
        linear-gradient(135deg, rgb(var(--accion-canal) / 0.18), transparent 70%),
        var(--superficie-2);
      box-shadow:
        inset 0 0 0 1px var(--neon),
        0 0 22px rgb(var(--accion-canal) / var(--brillo-boton));
    }
    .opcion:has(input:focus-visible) {
      outline: 2px solid var(--foco);
      outline-offset: 2px;
    }
    .icono-op {
      display: grid;
      place-items: center;
      width: 36px;
      height: 36px;
      border-radius: 10px;
      color: var(--texto-meta);
      background: rgb(var(--canal-neutro) / 0.14);
    }
    .icono-op svg {
      width: 20px;
      height: 20px;
      fill: none;
      stroke: currentColor;
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .elegida .icono-op {
      color: var(--accion-tinta);
      background: rgb(var(--accion-canal) / 0.16);
    }
    /* Plataformas: el color de la marca va solo en el icono, nunca en el relleno, para no
       competir con los colores del riesgo. */
    [data-marca='pc'] .icono-op,
    [data-marca='playstation'] .icono-op,
    [data-marca='xbox'] .icono-op,
    [data-marca='nintendo'] .icono-op {
      border: 1px solid var(--borde);
      background: var(--superficie);
    }
    [data-marca='pc'] .icono-op {
      color: var(--t-inicio);
    }
    [data-marca='playstation'] .icono-op {
      color: #4d9bff;
    }
    [data-marca='xbox'] .icono-op {
      color: #52b043;
    }
    [data-marca='nintendo'] .icono-op {
      color: #ff4a57;
    }
    :host-context([data-tema='claro']) [data-marca='playstation'] .icono-op {
      color: #0062b8;
    }
    :host-context([data-tema='claro']) [data-marca='xbox'] .icono-op {
      color: #107c10;
    }
    :host-context([data-tema='claro']) [data-marca='nintendo'] .icono-op {
      color: #c8000f;
    }
    .nombre {
      font-weight: var(--peso-clave);
      font-size: 18px;
      line-height: 1.2;
    }
    .detalle {
      color: var(--texto-meta);
      font-size: var(--texto-caption);
      line-height: 1.3;
    }
    .marca {
      position: absolute;
      top: 10px;
      right: 10px;
      display: none;
      place-items: center;
      width: 26px;
      height: 26px;
      border-radius: 50%;
      background: var(--accion);
      color: #0b0f1f;
    }
    .marca svg {
      width: 16px;
      height: 16px;
      fill: none;
      stroke: currentColor;
      stroke-width: 3;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .elegida .marca {
      display: grid;
    }
    /* El medidor de la fricción: cinco barras que se llenan con el nivel. */
    .medidor {
      display: flex;
      align-items: flex-end;
      gap: 3px;
      height: 22px;
    }
    .medidor i {
      width: 6px;
      border-radius: 2px;
      background: var(--borde-control);
    }
    .medidor i:nth-child(1) {
      height: 30%;
    }
    .medidor i:nth-child(2) {
      height: 45%;
    }
    .medidor i:nth-child(3) {
      height: 60%;
    }
    .medidor i:nth-child(4) {
      height: 80%;
    }
    .medidor i:nth-child(5) {
      height: 100%;
    }
    .medidor i.llena {
      background: var(--accion-tinta);
    }
    @media (max-width: 640px) {
      .opciones.cinco {
        grid-template-columns: 1fr;
      }
      .opciones.cinco .opcion {
        flex-direction: row;
        align-items: center;
        min-height: 56px;
      }
    }
  `,
})
export class TarjetasOpcion<T> {
  readonly nombre = input.required<string>();
  /** El id del título de la pregunta, que nombra al grupo. */
  readonly etiquetadoPor = input.required<string>();
  readonly opciones = input.required<Opcion<T>[]>();
  /** Con una respuesta: la elegida. */
  readonly valor = input<T | null>(null);
  /** Con `multiple`: las elegidas; cada clic emite la que se alterna. */
  readonly valores = input<readonly T[]>([]);
  readonly multiple = input(false);

  readonly valorCambio = output<T>();

  protected readonly barras = [1, 2, 3, 4, 5];

  protected elegida(valor: T): boolean {
    return this.multiple() ? this.valores().includes(valor) : valor === this.valor();
  }
}
