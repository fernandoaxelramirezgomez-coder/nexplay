import { ChangeDetectionStrategy, Component, input } from '@angular/core';

/** Pulgar dibujado, no emoji: el emoji depende de una fuente que no todos los sistemas
 * traen (en Linux sin fuente de emoji salía un cuadro). El pulgar hacia abajo es el
 * mismo trazo girado media vuelta, así que la geometría vive en un solo lugar. */
@Component({
  selector: 'app-icono-pulgar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="1.6"
      stroke-linecap="round"
      stroke-linejoin="round"
      aria-hidden="true"
      [class.abajo]="abajo()"
    >
      <rect x="3" y="10.2" width="4.4" height="9.6" rx="1.3" />
      <path d="M9.6 19.8V10.4l4.2-6.5a1.9 1.9 0 0 1 3.3 1.9l-1.5 4.4h4a1.9 1.9 0 0 1 1.9 2.3l-1.4 6.1a1.9 1.9 0 0 1-1.9 1.2z" />
    </svg>
  `,
  styles: `
    svg {
      display: block;
      width: 1em;
      height: 1em;
    }
    .abajo {
      transform: rotate(180deg);
    }
  `,
})
export class IconoPulgar {
  /** Gira el pulgar media vuelta: el "no me sirvió". */
  readonly abajo = input(false);
}
