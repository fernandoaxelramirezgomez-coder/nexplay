import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  computed,
  effect,
  input,
  linkedSignal,
  signal,
  viewChild,
} from '@angular/core';

type EstadoVideo = 'cargando' | 'reproduciendo' | 'pausado' | 'fallido';

const CLAVE_VOLUMEN = 'nexplay.video.v1';
const VOLUMEN_POR_OMISION = 0.6;

/** Lo que se recuerda del tráiler es el volumen, no el permiso de sonar: cada ficha
 * arranca muda. Un video que empieza a sonar solo en cada juego que abres es justo lo
 * que nadie quiere, y además el navegador lo bloquearía. */
function volumenGuardado(): number {
  try {
    const valor = Number(localStorage.getItem(CLAVE_VOLUMEN));
    return valor >= 0 && valor <= 1 ? valor : VOLUMEN_POR_OMISION;
  } catch {
    return VOLUMEN_POR_OMISION;
  }
}

function guardarVolumen(valor: number): void {
  try {
    localStorage.setItem(CLAVE_VOLUMEN, String(valor));
  } catch {
    // Sin almacenamiento el volumen dura lo que dure la pestaña.
  }
}

/** Cabecera de la ficha: Steam publica por appid una imagen de 616×353 con el arte y
 * el título del juego; si falta, se usa la portada del catálogo (460×215). Se prefiere
 * esta a library_hero.jpg, que está pensada para llevar el logo encima y recortada al
 * centro suele quedar casi vacía.
 *
 * Encima va el primer tráiler, en loop y mudo. La portada en gris queda debajo hasta que
 * el video dispara canplay, y se queda sola si el juego no tiene video, si el video falla
 * o si se pidió menos movimiento: en ese caso ni siquiera se pide el video. Solo la usa
 * la ficha; en la rejilla del catálogo serían veinte videos a la vez.
 *
 * Los controles son el mínimo de WCAG: 2.2.2 pide poder parar el movimiento automático de
 * más de 5 s y 1.4.2 poder callar el audio. Aparecen al pasar el ratón o con foco de
 * teclado, y en pantallas táctiles siempre. */
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
          <div class="controles" data-testid="portada-controles">
            <button
              type="button"
              class="control"
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

            <button
              type="button"
              class="control"
              data-testid="portada-silenciar"
              [attr.aria-pressed]="silenciado()"
              [attr.aria-label]="silenciado() ? 'Activar el sonido del tráiler' : 'Silenciar el tráiler'"
              (click)="alternarSonido()"
            >
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 9h3l5-4v14l-5-4H4z" />
                @if (silenciado()) {
                  <path d="m15 9.5 5 5m0-5-5 5" fill="none" stroke="currentColor" stroke-width="2" />
                } @else {
                  <path d="M15.5 8.5a5 5 0 0 1 0 7" fill="none" stroke="currentColor" stroke-width="2" />
                  @if (volumen() > 0.5) {
                    <path d="M18 6a8.5 8.5 0 0 1 0 12" fill="none" stroke="currentColor" stroke-width="2" />
                  }
                }
              </svg>
            </button>
            <input
              class="volumen"
              type="range"
              min="0"
              max="1"
              step="0.05"
              aria-label="Volumen del tráiler"
              data-testid="portada-volumen"
              [value]="volumen()"
              (input)="cambiarVolumen($any($event.target).valueAsNumber)"
            />
          </div>
        }
      }
    </div>
  `,
  styles: `
    .marco {
      position: relative;
      /* 240 y no 340: con la franja más alta, el veredicto no entraba en una pantalla de
         portátil (674 px de alto visible) sin desplazarse, y el riesgo es lo que se viene
         a ver. El alto va fijo y el ancho lo manda la columna: con aspect-ratio, el techo
         de alto encogía también el ancho y la portada quedaba más angosta que el título. */
      width: 100%;
      height: 240px;
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
    /* Los dos botones y el volumen en una sola barra: con tres piezas absolutas sueltas,
       la corredera tapaba la pausa en cuanto la franja se angostaba. */
    .controles {
      position: absolute;
      inset-block-end: var(--espacio-8);
      inset-inline-end: var(--espacio-8);
      display: flex;
      align-items: center;
      gap: var(--espacio-8);
      opacity: 0;
      transition: opacity var(--duracion-rapida) var(--curva);
    }
    .control {
      display: grid;
      place-items: center;
      width: 44px;
      height: 44px;
      padding: 0;
      border: 1px solid color-mix(in srgb, var(--neon) 45%, transparent);
      border-radius: var(--radio-pildora);
      /* Flota sobre el video, no sobre la página: sigue siendo oscuro en los dos temas. */
      background: rgba(11, 12, 36, 0.72);
      color: var(--texto);
      cursor: pointer;
    }
    .control svg {
      width: 18px;
      height: 18px;
      fill: currentColor;
    }
    .marco:hover .controles,
    .controles:focus-within {
      opacity: 1;
    }
    .control:focus-visible,
    .volumen:focus-visible {
      outline: 2px solid var(--neon);
      outline-offset: 2px;
    }
    /* La corredera no se despliega: ocupa su ancho desde el principio y aparece con la
       barra entera. Cuando crecía al pasar el ratón por el botón de sonido, la barra —que
       está anclada por su borde derecho— empujaba los dos botones 88 px a la izquierda, y
       el segundo clic en el mismo sitio caía en la corredera en vez de silenciar. */
    .volumen {
      width: 88px;
      height: 44px;
      margin: 0;
      padding: 0;
      accent-color: var(--neon);
      cursor: pointer;
    }
    /* Sin ratón no hay hover que lo descubra: en pantallas táctiles queda a la vista. */
    @media (hover: none) {
      .controles {
        opacity: 1;
      }
    }
    @keyframes pulso {
      50% {
        opacity: 0.55;
      }
    }
    /* La franja de 1200×340 está pensada para escritorio; en una pantalla angosta queda
       de ~100 px de alto. Ahí toma la proporción del tráiler y de la imagen de 616×353. */
    @media (max-width: 900px) {
      .marco {
        height: auto;
        aspect-ratio: 16 / 9;
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

  /** Cada tráiler empieza mudo, aunque en el anterior se hubiera activado el sonido. */
  protected readonly silenciado = linkedSignal<string | null, boolean>({
    source: this.video,
    computation: () => true,
  });

  protected readonly volumen = signal(volumenGuardado());

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

    // Las señales son la fuente de verdad del sonido; el elemento solo las refleja.
    effect(() => {
      const elemento = this.elementoVideo()?.nativeElement;
      if (elemento) {
        elemento.muted = this.silenciado();
        elemento.volume = this.volumen();
      }
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

  /** Quitar el mute con el volumen en cero no haría nada: se sube a lo mínimo audible. */
  protected alternarSonido(): void {
    const silenciar = !this.silenciado();
    if (!silenciar && this.volumen() === 0) {
      this.cambiarVolumen(VOLUMEN_POR_OMISION);
    }
    this.silenciado.set(silenciar);
  }

  protected cambiarVolumen(valor: number): void {
    const volumen = Math.min(1, Math.max(0, valor));
    this.volumen.set(volumen);
    guardarVolumen(volumen);
    // Mover la corredera es pedir sonido; dejarla en cero es pedir silencio.
    this.silenciado.set(volumen === 0);
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
