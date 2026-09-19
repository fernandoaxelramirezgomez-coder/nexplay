import { ChangeDetectionStrategy, Component, input, linkedSignal } from '@angular/core';

// SVG inline: si la portada de Steam no carga, se muestra esto sin depender de otro servicio.
const RESPALDO =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(
    "<svg xmlns='http://www.w3.org/2000/svg' width='460' height='215'>" +
      "<rect width='100%' height='100%' fill='#4a4c55'/>" +
      "<text x='50%' y='50%' fill='#f2f2f3' font-family='sans-serif' font-size='20' " +
      "text-anchor='middle' dominant-baseline='middle'>Sin portada</text></svg>",
  );

@Component({
  selector: 'app-portada',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="marco" [class.cargando]="estado() === 'cargando'">
      <img
        [src]="estado() === 'fallida' ? respaldo : src()"
        alt=""
        width="460"
        height="215"
        [attr.loading]="prioritaria() ? 'eager' : 'lazy'"
        [attr.fetchpriority]="prioritaria() ? 'high' : null"
        (load)="estado.set(estado() === 'fallida' ? 'fallida' : 'lista')"
        (error)="estado.set('fallida')"
      />
    </div>
  `,
  styles: `
    .marco {
      aspect-ratio: 460 / 215;
      border-radius: var(--radio-tarjeta);
      overflow: hidden;
      background: var(--superficie-tarjeta-hover);
    }
    .marco.cargando {
      animation: pulso 1.2s ease-in-out infinite;
    }
    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      opacity: 1;
      transition: opacity var(--duracion) var(--curva);
    }
    .cargando img {
      opacity: 0;
    }
    @keyframes pulso {
      50% {
        opacity: 0.55;
      }
    }
  `,
})
export class Portada {
  readonly src = input.required<string>();
  readonly prioritaria = input(false);

  protected readonly respaldo = RESPALDO;
  protected readonly estado = linkedSignal<string, 'cargando' | 'lista' | 'fallida'>({
    source: this.src,
    computation: () => 'cargando',
  });
}
