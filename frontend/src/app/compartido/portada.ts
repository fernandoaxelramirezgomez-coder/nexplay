import { ChangeDetectionStrategy, Component, computed, input, linkedSignal } from '@angular/core';

// SVG inline: si la portada de Steam no carga, se muestra esto sin depender de otro servicio.
const RESPALDO =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(
    "<svg xmlns='http://www.w3.org/2000/svg' width='460' height='215'>" +
      "<rect width='100%' height='100%' fill='#4a4c55'/>" +
      "<text x='50%' y='50%' fill='#f2f2f3' font-family='sans-serif' font-size='20' " +
      "text-anchor='middle' dominant-baseline='middle'>Sin portada</text></svg>",
  );

/** El arte vertical que Steam publica por appid. No existe para todos los juegos, así
 * que quien lo use tiene que poder quedarse sin él. */
export function arteVertical(appid: number): string {
  return `https://cdn.cloudflare.steamstatic.com/steam/apps/${appid}/library_600x900.jpg`;
}

@Component({
  selector: 'app-portada',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="marco" [class.cargando]="cargando()" [style.border-radius]="radio()">
      <picture>
        <!-- En una ranura alta, el arte vertical de Steam; la imagen ancha en la misma
             ranura solo cabe recortada por la mitad del logo. -->
        @if (usarAlta()) {
          <source [srcset]="alta()" [attr.media]="mediaAlta()" width="600" height="900" />
        }
        <img
          [src]="fuente()"
          alt=""
          width="460"
          height="215"
          [attr.loading]="prioritaria() ? 'eager' : 'lazy'"
          [attr.fetchpriority]="prioritaria() ? 'high' : null"
          (load)="cargando.set(false)"
          (error)="fallar()"
        />
      </picture>
    </div>
  `,
  styles: `
    :host {
      display: block;
    }
    picture {
      display: contents;
    }
    .marco {
      aspect-ratio: var(--proporcion-portada, 460 / 215);
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
  /** '0' cuando la tarjeta ya recorta las esquinas con su propio overflow. */
  readonly radio = input('var(--radio-tarjeta)');
  /** El arte vertical de Steam (600×900), para ranuras más altas que anchas. Se usa solo
   * donde la consulta de medios diga; si no carga, queda la imagen ancha de siempre. */
  readonly alta = input<string | null>(null);
  /** Desde qué ancho de ventana se usa el arte vertical. */
  readonly mediaAlta = input('(min-width: 861px)');

  protected readonly fallida = linkedSignal<string, boolean>({
    source: this.src,
    computation: () => false,
  });
  protected readonly cargando = linkedSignal<string, boolean>({
    source: this.src,
    computation: () => true,
  });
  /** Si el arte vertical no está publicado, el <source> se retira y queda la ancha. */
  private readonly altaViva = linkedSignal<string | null, boolean>({
    source: this.alta,
    computation: () => true,
  });

  protected readonly usarAlta = computed(() => !!this.alta() && this.altaViva() && !this.fallida());
  protected readonly fuente = computed(() => (this.fallida() ? RESPALDO : this.src()));

  /** El error puede venir del arte vertical o de la imagen ancha: primero se descarta el
   * vertical, y solo si también falla la ancha se enseña el respaldo gris. */
  protected fallar(): void {
    if (this.usarAlta()) {
      this.altaViva.set(false);
      return;
    }
    this.fallida.set(true);
    this.cargando.set(false);
  }
}
