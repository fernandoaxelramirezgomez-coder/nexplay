import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  inject,
  signal,
} from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';

import { OpinionNia } from '../api/contrato';
import { NexplayApi } from '../api/nexplay-api';
import { PildoraBanda } from '../compartido/pildora-banda';
import { CatalogoStore } from '../estado/catalogo-store';

/** Juegos curados a mano para el ejemplo del inicio: uno de cada nivel de riesgo (Hades
 * bajo, Cyberpunk 2077 medio, WILD HEARTS alto) y Outer Wilds de contraste. El nivel que
 * se muestra es el que dé el modelo, no el de esta lista. */
export const EJEMPLOS_PORTADA = [1145360, 1091500, 1938010, 753640];
/** Lento a propósito: da tiempo a leer la opinión antes de que cambie. */
const MS_ROTACION = 7000;

/** «Análisis crítico con nuestra asistente Nia»: la mascota de Nia con la cara de cada
 * nivel (celebra en bajo, piensa en medio, se preocupa en alto) y un chat corto con su
 * opinión del juego. La opinión sale de las reglas del chat sobre los datos del catálogo
 * (GET /nia/opiniones): no pasa por el modelo de lenguaje, así que el inicio no gasta
 * consultas a OpenAI. */
@Component({
  selector: 'app-carrusel-ejemplo',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, PildoraBanda],
  template: `
    @if (ejemplos().length) {
      <aside
        class="demostracion"
        role="region"
        aria-roledescription="carrusel"
        aria-labelledby="titulo-carrusel"
        data-vista="nia"
        data-testid="hero-carrusel"
        [attr.data-pausado]="pausado()"
        (mouseenter)="pausado.set(true)"
        (mouseleave)="pausado.set(false)"
        (focusin)="pausado.set(true)"
        (focusout)="alSalirDelEjemplo($event)"
      >
        <p class="demostracion-titulo" id="titulo-carrusel" data-testid="hero-etiqueta">
          Análisis crítico con nuestra asistente <span class="nombre-nia">Nia</span>
        </p>
        <!-- Las opiniones van apiladas en la misma celda y solo se ve la activa: así el
             carrusel mide lo que la más larga y no brinca al rotar. Mientras rota sola no
             se anuncia cada cambio; si alguien la detuvo o la movió a mano, sí. -->
        <div class="pila" [attr.aria-live]="rotaSolo && !pausado() ? 'off' : 'polite'">
          @for (juego of ejemplos(); track juego.appid; let i = $index) {
            @let activa = i === indiceActivo();
            @let opinion = opiniones().get(juego.appid);
            <div
              class="vistazo"
              [class.activa]="activa"
              role="group"
              aria-roledescription="diapositiva"
              [attr.aria-label]="'Nia opina de ' + juego.nombre"
              [attr.data-appid]="juego.appid"
              [attr.data-nivel]="juego.banda_riesgo"
              [attr.data-testid]="activa ? 'hero-ejemplo' : 'hero-ejemplo-oculto'"
            >
              <!-- La cara acompaña; el nivel lo dicen la respuesta y la píldora. -->
              <img
                class="mascota"
                [src]="'nia/ficha-' + juego.banda_riesgo + '.png'"
                alt=""
                width="220"
                height="230"
                data-testid="hero-mascota"
              />
              <div class="chat">
                <p class="globo-tu" data-testid="hero-pregunta">
                  <img class="miniatura" [src]="juego.portada_url" alt="" width="460" height="215" />
                  <span>{{ opinion?.pregunta ?? '¿Qué opinas de ' + juego.nombre + '?' }}</span>
                </p>
                @if (opinion) {
                  <p class="globo-nia" data-testid="hero-respuesta">
                    <span class="quien">Nia</span>{{ opinion.respuesta }}
                  </p>
                } @else if (escribiendo()) {
                  <p class="globo-nia escribiendo" aria-label="Nia está escribiendo">
                    <span class="quien">Nia</span><span aria-hidden="true">…</span>
                  </p>
                }
              </div>
              <div class="acciones">
                <app-pildora-banda [banda]="juego.banda_riesgo" />
                <a class="boton-texto" [routerLink]="['/juego', juego.appid]" data-testid="hero-ficha"
                  >Ver su ficha <span aria-hidden="true">→</span></a
                >
                <a
                  class="boton-texto"
                  routerLink="/nia"
                  [queryParams]="{ appid: juego.appid }"
                  data-testid="hero-seguir-nia"
                  >{{ opinion ? 'Seguir con Nia' : 'Pregúntale a Nia' }} <span aria-hidden="true">→</span></a
                >
              </div>
            </div>
          }
        </div>
        @if (ejemplos().length > 1) {
          <div class="carrusel-controles">
            <span class="carrusel-posicion" data-testid="hero-posicion"
              >{{ indiceActivo() + 1 }} / {{ ejemplos().length }}</span
            >
            <button
              type="button"
              class="carrusel-flecha toque-amplio"
              aria-label="Opinión anterior"
              data-testid="hero-anterior"
              (click)="moverEjemplo(-1)"
            >
              <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M15 6l-6 6 6 6" /></svg>
            </button>
            <button
              type="button"
              class="carrusel-flecha toque-amplio"
              aria-label="Opinión siguiente"
              data-testid="hero-siguiente"
              (click)="moverEjemplo(1)"
            >
              <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M9 6l6 6-6 6" /></svg>
            </button>
          </div>
        }
      </aside>
    }
  `,
  styles: `
    :host {
      display: block;
      min-width: 0;
    }

    /* Todo el carrusel es un panel con el violeta de Nia (data-vista), como su chat en
       cualquier vista: lo de adentro no queda sobre la nebulosa. */
    .demostracion {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
      padding: var(--espacio-16);
      border: 1px solid color-mix(in srgb, var(--neon) 45%, var(--linea));
      border-radius: var(--radio-tarjeta);
      background: var(--superficie-tarjeta);
    }

    /* Un título que se lee como frase, en la letra del texto: la etiqueta en mono y
       mayúsculas se veía técnica y cargada. */
    .demostracion-titulo {
      margin: 0;
      color: var(--texto);
      font-size: 18px;
      font-weight: 600;
      line-height: 1.3;
    }

    .nombre-nia {
      color: var(--neon);
    }

    /* Las flechas van al pie del panel, para que el título quede solo arriba. */
    .carrusel-controles {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: var(--espacio-12);
    }

    .carrusel-posicion {
      white-space: nowrap;
      color: var(--texto-meta);
      font-size: var(--texto-caption);
    }

    .carrusel-flecha {
      display: grid;
      place-items: center;
      width: 32px;
      height: 32px;
      padding: 0;
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-pildora);
      background: none;
      color: var(--texto);
      cursor: pointer;
      transition:
        border-color var(--duracion-rapida) var(--curva),
        color var(--duracion-rapida) var(--curva);
    }

    .carrusel-flecha:hover {
      border-color: var(--neon);
      color: var(--neon);
    }

    .carrusel-flecha svg {
      width: 16px;
      height: 16px;
      fill: none;
      stroke: currentColor;
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
    }

    .pila {
      display: grid;
    }

    /* El chat arriba, pegado al título, y la mascota abajo a su lado: en las opiniones
       cortas el aire que sobra queda al pie y no entre el título y la pregunta. */
    .vistazo {
      display: grid;
      grid-area: 1 / 1;
      grid-template-columns: 120px minmax(0, 1fr);
      grid-template-rows: auto 1fr;
      grid-template-areas:
        'mascota chat'
        'mascota acciones';
      gap: var(--espacio-8) var(--espacio-16);
      visibility: hidden;
    }

    .vistazo.activa {
      visibility: visible;
      animation: entrar-ejemplo 0.45s var(--curva);
    }

    /* Cada opinión entra con un fundido corto; con movimiento reducido la regla global lo
       deja en instantáneo. Entra desde 0.55 y no desde 0: a mitad del fundido la
       diapositiva se veía vacía, que es peor que un cambio un poco más seco. */
    @keyframes entrar-ejemplo {
      from {
        opacity: 0.55;
        transform: translateY(4px);
      }
      to {
        opacity: 1;
        transform: none;
      }
    }

    .mascota {
      grid-area: mascota;
      align-self: end;
      width: 120px;
      height: auto;
    }

    /* Sus globos a la izquierda y los tuyos a la derecha, como en el chat de Nia. */
    .chat {
      grid-area: chat;
      display: flex;
      min-width: 0;
      flex-direction: column;
      gap: var(--espacio-8);
    }

    .globo-tu {
      display: flex;
      max-width: 100%;
      align-self: flex-end;
      align-items: center;
      gap: var(--espacio-8);
      margin: 0;
      padding: var(--espacio-8) var(--espacio-12);
      border-radius: var(--radio-tarjeta) 4px var(--radio-tarjeta) var(--radio-tarjeta);
      background: var(--acento-sistema);
      color: var(--texto);
      font-size: var(--texto-body-sm);
      line-height: 1.3;
    }

    .miniatura {
      width: 52px;
      height: 24px;
      flex: none;
      object-fit: cover;
      border-radius: 4px;
    }

    /* El globo es el de Nia en todo el sitio (base.css); aquí solo se aprieta, porque la
       columna del chat es angosta. */
    .globo-nia {
      padding: var(--espacio-8) var(--espacio-12) var(--espacio-12);
      line-height: 1.45;
      overflow-wrap: anywhere;
    }

    .escribiendo span[aria-hidden] {
      letter-spacing: 0.2em;
    }

    .acciones {
      grid-area: acciones;
      align-self: start;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--espacio-4) var(--espacio-16);
      font-size: var(--texto-body-sm);
    }

    /* El corte mide .contenido (app.css): con la barra lateral abierta la ventana sigue
       siendo ancha aunque al hero le queden 736 px, y ahí el ejemplo tiene que encogerse. */
    @container contenido (max-width: 900px) {
      :host {
        max-width: 620px;
      }
    }
    /* En el teléfono la mascota se achica y sube junto a tu pregunta, y la píldora con los
       enlaces pasa a todo el ancho: en la columna del chat la píldora no cabía. */
    @media (max-width: 640px) {
      .demostracion {
        padding: var(--espacio-12);
      }
      .vistazo {
        grid-template-columns: 72px minmax(0, 1fr);
        grid-template-rows: auto 1fr;
        grid-template-areas:
          'mascota chat'
          'acciones acciones';
        column-gap: var(--espacio-12);
      }
      .mascota {
        align-self: start;
        width: 72px;
      }
    }
  `,
})
export class CarruselEjemplo {
  private readonly catalogo = inject(CatalogoStore);
  private readonly api = inject(NexplayApi);

  /** Los curados que existan en el catálogo; si faltara alguno, el carrusel sigue. */
  protected readonly ejemplos = computed(() =>
    EJEMPLOS_PORTADA.map((appid) => this.catalogo.porAppid().get(appid)).filter((juego) => !!juego),
  );
  protected readonly indiceEjemplo = signal(0);
  protected readonly indiceActivo = computed(() => this.indiceEjemplo() % Math.max(this.ejemplos().length, 1));

  /** Una sola petición por visita. Si falla, cada diapositiva queda con tu pregunta y
   * «Pregúntale a Nia», que lleva al chat con el juego elegido. */
  private readonly recursoOpiniones = rxResource({
    stream: () => this.api.opinionesDeNia(EJEMPLOS_PORTADA),
  });
  protected readonly opiniones = computed(
    () =>
      new Map<number, OpinionNia>(
        (this.recursoOpiniones.hasValue() ? this.recursoOpiniones.value() : []).map((o) => [o.appid, o]),
      ),
  );
  protected readonly escribiendo = this.recursoOpiniones.isLoading;

  /** Quieto con el ratón encima o el foco dentro: nadie lee una opinión que se le escapa. */
  protected readonly pausado = signal(false);
  /** Con prefers-reduced-motion no rota solo; las flechas siguen funcionando. */
  protected readonly rotaSolo = !this.prefiereMenosMovimiento();

  constructor() {
    if (this.rotaSolo) {
      const reloj = setInterval(() => {
        if (!this.pausado() && this.ejemplos().length > 1) {
          this.moverEjemplo(1);
        }
      }, MS_ROTACION);
      inject(DestroyRef).onDestroy(() => clearInterval(reloj));
    }
  }

  protected moverEjemplo(paso: 1 | -1): void {
    const total = this.ejemplos().length;
    if (total) {
      this.indiceEjemplo.update((i) => (i + paso + total) % total);
    }
  }

  protected alSalirDelEjemplo(evento: FocusEvent): void {
    const adonde = evento.relatedTarget as Node | null;
    if (!adonde || !(evento.currentTarget as HTMLElement).contains(adonde)) {
      this.pausado.set(false);
    }
  }

  private prefiereMenosMovimiento(): boolean {
    return typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
  }
}
