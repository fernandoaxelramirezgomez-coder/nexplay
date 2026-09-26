import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  computed,
  effect,
  input,
  linkedSignal,
  output,
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
    // Sin nada guardado, Number(null) daba 0 y la corredera arrancaba en cero.
    const crudo = localStorage.getItem(CLAVE_VOLUMEN);
    const valor = crudo === null ? NaN : Number(crudo);
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
 * Encima va el primer tráiler, mudo. La portada en gris queda debajo hasta que el video
 * dispara canplay, y se queda sola si el juego no tiene video o si el video falla. Con
 * «reducir movimiento» el video no se pide solo: un botón lo trae si la persona quiere.
 * La usan la ficha (modo 'ficha', en loop) y el escenario de tráileres de Explorar (modo
 * 'carrusel', que avisa al terminar para pasar al siguiente); en la rejilla del catálogo
 * serían veinte videos a la vez.
 *
 * Los controles son el mínimo de WCAG: 2.2.2 pide poder parar el movimiento automático de
 * más de 5 s y 1.4.2 poder callar el audio. Van siempre a la vista, con fondo propio y de
 * 48 px: escondidos hasta el hover, la revisión del usuario final no los encontró. */
@Component({
  selector: 'app-portada-ancha',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      class="marco"
      [class.cargando]="estado() === 'cargando'"
      [class.carrusel]="modo() === 'carrusel'"
      data-testid="portada-ancha"
    >
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
          [loop]="enBucle()"
          playsinline
          preload="auto"
          aria-hidden="true"
          data-testid="portada-video"
          [attr.data-estado]="estadoVideo()"
          [class.visible]="listo()"
          (canplay)="alPoderReproducir($event)"
          (ended)="terminado.emit()"
          (error)="estadoVideo.set('fallido')"
        ></video>
        @if (listo()) {
          <!-- data-fondo-peor: el fondo de la barra encima de la parte más clara posible
               del video, para el comprobador de contraste del recorrido. -->
          <div class="controles" data-testid="portada-controles" data-fondo-peor="#3c3f4c">
            <button
              type="button"
              class="control"
              data-testid="portada-pausa"
              [attr.aria-label]="estadoVideo() === 'pausado' ? 'Reproducir el tráiler' : 'Pausar el tráiler'"
              (click)="alternar(); interaccion.emit()"
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
              (click)="alternarSonido(); interaccion.emit()"
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
              (input)="cambiarVolumen($any($event.target).valueAsNumber); interaccion.emit()"
            />
            @if (modo() === 'ficha') {
              <span class="estado-sonido" data-testid="portada-estado">
                Tráiler · {{ silenciado() ? 'sin sonido' : 'con sonido' }}
              </span>
            }
          </div>
        }
      } @else if (video() && menosMovimiento && estadoVideo() !== 'fallido') {
        <div class="controles" data-fondo-peor="#3c3f4c">
          <button
            type="button"
            class="control con-texto"
            data-testid="portada-pedir-video"
            (click)="pedido.set(true); interaccion.emit()"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.5v13l10.5-6.5z" /></svg>
            Ver el tráiler
          </button>
        </div>
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
    /* Los dos botones, el volumen y el estado en una sola barra con fondo propio, abajo a
       la izquierda. Flota sobre el video, no sobre la página: es oscura en los dos temas. */
    .controles {
      position: absolute;
      inset-block-end: var(--espacio-12);
      inset-inline-start: var(--espacio-12);
      display: flex;
      align-items: center;
      gap: var(--espacio-8);
      max-width: calc(100% - 2 * var(--espacio-12));
      padding: 6px;
      border: 1px solid rgb(255 255 255 / 0.28);
      border-radius: var(--radio-pildora);
      background: rgb(11 15 31 / 0.8);
      color: #f2f4ff;
    }
    /* En el escenario de tráileres el pie es de la información del juego: la barra sube a
       la esquina de arriba. */
    .carrusel .controles {
      inset-block: var(--espacio-12) auto;
      inset-inline: auto var(--espacio-12);
    }
    .control {
      display: grid;
      place-items: center;
      flex: none;
      width: 48px;
      height: 48px;
      padding: 0;
      border: 1px solid rgb(255 255 255 / 0.4);
      border-radius: var(--radio-pildora);
      background: rgb(255 255 255 / 0.12);
      color: #ffffff;
      cursor: pointer;
    }
    .control:hover {
      background: rgb(255 255 255 / 0.22);
    }
    .control.con-texto {
      display: inline-flex;
      gap: var(--espacio-8);
      width: auto;
      padding: 0 var(--espacio-16) 0 var(--espacio-12);
      font-size: var(--texto-body-sm);
    }
    .control svg {
      width: 20px;
      height: 20px;
      fill: currentColor;
    }
    .control:focus-visible,
    .volumen:focus-visible {
      outline: 2px solid #22d3ee;
      outline-offset: 2px;
    }
    /* La corredera ocupa su ancho desde el principio: cuando crecía al pasar el ratón por
       el botón de sonido, empujaba los botones y el segundo clic en el mismo sitio caía
       en la corredera en vez de silenciar. */
    .volumen {
      flex: 0 1 96px;
      min-width: 56px;
      height: 44px;
      margin: 0;
      padding: 0;
      accent-color: #22d3ee;
      cursor: pointer;
    }
    .estado-sonido {
      padding-inline: 2px var(--espacio-8);
      font-size: var(--texto-caption);
      white-space: nowrap;
    }
    @media (max-width: 480px) {
      .estado-sonido {
        display: none;
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
    .marco.carrusel {
      height: auto;
      aspect-ratio: 16 / 9;
    }
  `,
})
export class PortadaAncha {
  readonly appid = input.required<number>();
  /** portada_url del catálogo: el respaldo si no hay imagen ancha. */
  readonly respaldo = input.required<string>();
  /** video_url del catálogo: el tráiler en HLS, o null si el juego no tiene. */
  readonly video = input<string | null>(null);
  readonly modo = input<'ficha' | 'carrusel'>('ficha');
  /** Sin bucle, el video termina y avisa con `terminado`: el carrusel pasa al siguiente. */
  readonly enBucle = input(true);

  readonly terminado = output<void>();
  /** Cualquier control tocado por la persona: el carrusel deja de avanzar solo. */
  readonly interaccion = output<void>();

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

  protected readonly menosMovimiento =
    typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;

  /** Con menos movimiento el video no se pide solo; lo pide la persona con el botón. */
  protected readonly pedido = linkedSignal<string | null, boolean>({
    source: this.video,
    computation: () => !this.menosMovimiento,
  });

  protected readonly videoActivo = computed(
    () => !!this.video() && this.pedido() && this.estadoVideo() !== 'fallido',
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
