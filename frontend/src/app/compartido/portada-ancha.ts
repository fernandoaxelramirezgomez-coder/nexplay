import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  computed,
  effect,
  input,
  linkedSignal,
  viewChild,
} from '@angular/core';

type EstadoVideo = 'cargando' | 'reproduciendo' | 'pausado' | 'fallido';

/** Cabecera de la ficha: Steam publica por appid una imagen de 616×353 con el arte y
 * el título del juego; si falta, se usa la portada del catálogo (460×215). Se prefiere
 * esta a library_hero.jpg, que está pensada para llevar el logo encima y recortada al
 * centro suele quedar casi vacía.
 *
 * Encima va el primer tráiler, mudo y en loop. La portada en gris queda debajo hasta que
 * el video dispara canplay, y se queda sola si el juego no tiene video, si el video falla
 * o si se pidió menos movimiento: en ese caso ni siquiera se pide el video. Solo la usa
 * la ficha; en la rejilla del catálogo serían veinte videos a la vez.
 *
 * El botón de pausa es el mínimo de WCAG 2.2.2 para movimiento automático de más de
 * 5 s: aparece al pasar el ratón o con foco de teclado, y en pantallas táctiles siempre. */
@Component({
  selector: 'app-portada-ancha',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="marco" [class.cargando]="estado() === 'cargando'" data-testid="portada-ancha">
      <img
        [src]="fuente()"
        alt=""
        width="616"
        height="353"
        fetchpriority="high"
        (load)="estado.set('lista')"
        (error)="fallar()"
      />
      @if (videoActivo()) {
        <video
          #video
          muted
          loop
          playsinline
          preload="auto"
          aria-hidden="true"
          data-testid="portada-video"
          [attr.data-estado]="estadoVideo()"
          [class.visible]="listo()"
          (canplay)="alPoderReproducir($event)"
          (error)="estadoVideo.set('fallido')"
        ></video>
        @if (listo()) {
          <button
            type="button"
            class="pausa"
            data-testid="portada-pausa"
            [attr.aria-label]="estadoVideo() === 'pausado' ? 'Reproducir el tráiler' : 'Pausar el tráiler'"
            (click)="alternar()"
          >
            @if (estadoVideo() === 'pausado') {
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.5v13l10.5-6.5z" /></svg>
            } @else {
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 5h3.5v14H7zM13.5 5H17v14h-3.5z" /></svg>
            }
          </button>
        }
      }
    </div>
  `,
  styles: `
    .marco {
      position: relative;
      aspect-ratio: 1200 / 340;
      max-height: 340px;
      border-radius: var(--radio-tarjeta);
      overflow: hidden;
      background: var(--superficie-tarjeta-hover);
    }
    .marco.cargando {
      animation: pulso 1.2s ease-in-out infinite;
    }
    img,
    video {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    img {
      /* 35%: con 'center' se corta el título de Wild Hearts y con 'top' el logo de
         Cyberpunk y media portada de GTA V (ver docs/capturas/angular). */
      object-position: center 35%;
      filter: grayscale(1);
      opacity: 1;
      transition: opacity var(--duracion) var(--curva);
    }
    .cargando img {
      opacity: 0;
    }
    video {
      position: absolute;
      inset: 0;
      opacity: 0;
      transition: opacity var(--duracion) var(--curva);
    }
    video.visible {
      opacity: 1;
    }
    .pausa {
      position: absolute;
      inset-block-end: var(--espacio-8);
      inset-inline-end: var(--espacio-8);
      display: grid;
      place-items: center;
      width: 36px;
      height: 36px;
      padding: 0;
      border: 1px solid color-mix(in srgb, var(--neon) 45%, transparent);
      border-radius: var(--radio-pildora);
      background: rgba(11, 12, 36, 0.72);
      color: var(--texto);
      cursor: pointer;
      opacity: 0;
      transition: opacity var(--duracion-rapida) var(--curva);
    }
    .pausa svg {
      width: 18px;
      height: 18px;
      fill: currentColor;
    }
    .marco:hover .pausa,
    .pausa:focus-visible {
      opacity: 1;
    }
    .pausa:focus-visible {
      outline: 2px solid var(--neon);
      outline-offset: 2px;
    }
    /* Sin ratón no hay hover que lo descubra: en pantallas táctiles queda a la vista. */
    @media (hover: none) {
      .pausa {
        opacity: 1;
      }
    }
    @keyframes pulso {
      50% {
        opacity: 0.55;
      }
    }
  `,
})
export class PortadaAncha {
  readonly appid = input.required<number>();
  /** portada_url del catálogo: el respaldo si no hay imagen ancha. */
  readonly respaldo = input.required<string>();
  /** video_url del catálogo: el tráiler en HLS, o null si el juego no tiene. */
  readonly video = input<string | null>(null);

  protected readonly estado = linkedSignal<number, 'cargando' | 'lista' | 'fallida'>({
    source: this.appid,
    computation: () => 'cargando',
  });

  protected readonly fuente = computed(() =>
    this.estado() === 'fallida'
      ? this.respaldo()
      : `https://cdn.cloudflare.steamstatic.com/steam/apps/${this.appid()}/capsule_616x353.jpg`,
  );

  protected readonly estadoVideo = linkedSignal<string | null, EstadoVideo>({
    source: this.video,
    computation: () => 'cargando',
  });

  private readonly menosMovimiento =
    typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;

  protected readonly videoActivo = computed(
    () => !!this.video() && !this.menosMovimiento && this.estadoVideo() !== 'fallido',
  );

  protected readonly listo = computed(
    () => this.estadoVideo() === 'reproduciendo' || this.estadoVideo() === 'pausado',
  );

  private readonly elementoVideo = viewChild<ElementRef<HTMLVideoElement>>('video');

  constructor() {
    effect((alLimpiar) => {
      const elemento = this.elementoVideo()?.nativeElement;
      const url = this.video();
      if (!elemento || !url) {
        return;
      }
      let cancelado = false;
      let hls: { destroy(): void } | undefined;
      // El atributo muted del template no siempre llega a la propiedad antes del primer
      // play(), y sin la propiedad el navegador bloquea el autoplay.
      elemento.muted = true;

      if (elemento.canPlayType('application/vnd.apple.mpegurl')) {
        elemento.src = url;
      } else {
        // hls.js solo se descarga aquí, en un chunk aparte, cuando el navegador no
        // reproduce HLS por sí mismo.
        import('hls.js')
          .then(({ default: Hls }) => {
            if (cancelado) {
              return;
            }
            if (!Hls.isSupported()) {
              this.estadoVideo.set('fallido');
              return;
            }
            const instancia = new Hls();
            instancia.on(Hls.Events.ERROR, (_evento, datos) => {
              if (datos.fatal) {
                this.estadoVideo.set('fallido');
              }
            });
            instancia.loadSource(url);
            instancia.attachMedia(elemento);
            hls = instancia;
          })
          .catch(() => this.estadoVideo.set('fallido'));
      }

      alLimpiar(() => {
        cancelado = true;
        hls?.destroy();
        elemento.removeAttribute('src');
        elemento.load();
      });
    });
  }

  protected fallar(): void {
    this.estado.set(this.estado() === 'fallida' ? 'lista' : 'fallida');
  }

  protected alternar(): void {
    const elemento = this.elementoVideo()?.nativeElement;
    if (!elemento) {
      return;
    }
    if (this.estadoVideo() === 'pausado') {
      elemento
        .play()
        .then(() => this.estadoVideo.set('reproduciendo'))
        .catch(() => this.estadoVideo.set('fallido'));
    } else {
      elemento.pause();
      this.estadoVideo.set('pausado');
    }
  }

  protected alPoderReproducir(evento: Event): void {
    // canplay vuelve a dispararse tras un rebúfer: si la persona pausó, se respeta.
    if (this.estadoVideo() === 'pausado') {
      return;
    }
    const elemento = evento.target as HTMLVideoElement;
    elemento
      .play()
      .then(() => this.estadoVideo.set('reproduciendo'))
      .catch(() => this.estadoVideo.set('fallido'));
  }
}
