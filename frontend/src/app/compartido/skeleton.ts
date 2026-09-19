import { ChangeDetectionStrategy, Component, input } from '@angular/core';

/** Bloque de carga: pulso de opacidad, sin gradiente de brillo. */
@Component({
  selector: 'app-skeleton',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { 'aria-hidden': 'true', '[style.height]': 'alto()', '[style.border-radius]': 'radio()' },
  template: '',
  styles: `
    :host {
      display: block;
      width: 100%;
      background: var(--superficie-tarjeta-hover);
      animation: pulso 1.2s ease-in-out infinite;
    }
    @keyframes pulso {
      50% {
        opacity: 0.55;
      }
    }
  `,
})
export class Skeleton {
  readonly alto = input('1em');
  readonly radio = input('var(--radio-tarjeta)');
}
