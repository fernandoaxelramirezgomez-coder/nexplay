import { ChangeDetectionStrategy, Component, input } from '@angular/core';

/** Un emoji en un círculo, en medio de una línea que se desvanece a los lados: separa dos
 * partes de una vista e invita a bajar. Al tocarlo baja hasta el destino y le pasa el foco
 * a su título, para que un lector de pantalla también llegue. Flota sin parar, como pidió
 * el dueño; se detiene con el cursor o el foco, y con movimiento reducido no se mueve. */
@Component({
  selector: 'app-separador-nave',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <button type="button" class="nave" [attr.aria-label]="etiqueta()" [attr.data-testid]="testid()" (click)="bajar()">
      <span class="emoji" aria-hidden="true" [style.transform]="giro() ? 'rotate(' + giro() + 'deg)' : null">{{
        emoji()
      }}</span>
    </button>
  `,
  styles: `
    :host {
      display: flex;
      align-items: center;
      gap: var(--espacio-16);
      margin-top: var(--espacio-24);
    }
    :host::before,
    :host::after {
      content: '';
      flex: 1;
      height: 1px;
    }
    :host::before {
      background: linear-gradient(to right, transparent, var(--linea));
    }
    :host::after {
      background: linear-gradient(to left, transparent, var(--linea));
    }
    .nave {
      display: grid;
      place-items: center;
      width: 64px;
      height: 64px;
      padding: 0;
      border: 1px solid color-mix(in srgb, var(--neon) 45%, var(--linea));
      border-radius: 50%;
      background: var(--superficie);
      cursor: pointer;
      box-shadow: 0 0 24px rgb(var(--accion-canal) / 0.18);
      animation: flotar 2.4s var(--curva) infinite;
      transition:
        border-color var(--duracion-rapida) var(--curva),
        box-shadow var(--duracion-rapida) var(--curva);
    }
    .nave:hover,
    .nave:focus-visible {
      animation-play-state: paused;
    }
    .nave:hover {
      border-color: var(--neon);
      box-shadow: 0 0 32px rgb(var(--accion-canal) / 0.35);
    }
    .nave:focus-visible {
      outline: 2px solid var(--foco);
      outline-offset: 3px;
    }
    .emoji {
      display: block;
      font-size: 32px;
      line-height: 1;
    }
    /* Baja y sube despacio, como invitando a seguir hacia abajo. */
    @keyframes flotar {
      0%,
      100% {
        transform: translateY(0);
      }
      50% {
        transform: translateY(6px);
      }
    }
  `,
})
export class SeparadorNave {
  readonly emoji = input.required<string>();
  /** Lo que lee el lector de pantalla: adónde lleva. */
  readonly etiqueta = input.required<string>();
  readonly destino = input.required<HTMLElement>();
  /** El título del destino, con tabindex="-1" para poder recibir el foco. */
  readonly foco = input<HTMLElement | null>(null);
  /** Grados que se gira el emoji; el cohete, por ejemplo, mira arriba a la derecha. */
  readonly giro = input(0);
  readonly testid = input<string | null>(null);

  /** Con movimiento reducido baja de golpe. Con ?. porque el DOM de las pruebas no
   * implementa scrollIntoView. */
  protected bajar(): void {
    const suave = !(typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches);
    this.destino().scrollIntoView?.({ behavior: suave ? 'smooth' : 'auto', block: 'start' });
    this.foco()?.focus({ preventScroll: true });
  }
}
