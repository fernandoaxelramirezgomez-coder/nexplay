import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  inject,
  input,
  signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';

import { PildoraBanda } from '../compartido/pildora-banda';
import { Portada, arteVertical } from '../compartido/portada';
import { CatalogoStore } from '../estado/catalogo-store';

/** Juegos curados a mano para el ejemplo del inicio: uno de cada banda de riesgo con el
 * perfil neutro de hoy (Hades bajo, Cyberpunk 2077 medio, WILD HEARTS alto) y Outer Wilds
 * de contraste. La banda que se muestra es la que dé el modelo, no la de esta lista. */
const EJEMPLOS_PORTADA = [1145360, 1091500, 1938010, 753640];
/** Lento a propósito: da tiempo a leer el nombre y la banda antes de que cambie. */
const MS_ROTACION = 7000;

/** El ejemplo del inicio: una ficha de verdad del catálogo, rotando. Vive aparte del
 * inicio porque es lo más grande de esa página y no se mezcla con nada más. */
@Component({
  selector: 'app-carrusel-ejemplo',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, PildoraBanda, Portada],
  template: `
    @if (destacado(); as juego) {
    <aside
        class="demostracion"
        role="region"
        aria-roledescription="carrusel"
        aria-label="Ejemplos de segunda opinión"
        data-testid="hero-carrusel"
        [attr.data-pausado]="ejemploPausado()"
        (mouseenter)="pausadoAqui.set(true)"
        (mouseleave)="pausadoAqui.set(false)"
        (focusin)="pausadoAqui.set(true)"
        (focusout)="alSalirDelEjemplo($event)"
      >
        <div class="demostracion-fila">
          <p class="demostracion-etiqueta mono">Así se ve una segunda opinión</p>
          @if (ejemplos().length > 1) {
            <div class="carrusel-controles">
              <span class="carrusel-posicion mono" data-testid="hero-posicion"
                >{{ indiceEjemplo() + 1 }} / {{ ejemplos().length }}</span
              >
              <button
                type="button"
                class="carrusel-flecha toque-amplio"
                aria-label="Ejemplo anterior"
                data-testid="hero-anterior"
                (click)="moverEjemplo(-1)"
              >
                <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M15 6l-6 6 6 6" /></svg>
              </button>
              <button
                type="button"
                class="carrusel-flecha toque-amplio"
                aria-label="Ejemplo siguiente"
                data-testid="hero-siguiente"
                (click)="moverEjemplo(1)"
              >
                <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M9 6l6 6-6 6" /></svg>
              </button>
            </div>
          }
        </div>
        <!-- El track por appid rehace la tarjeta en cada cambio: así entra con su fundido.
             Mientras rota solo no se anuncia cada cambio; si alguien lo detuvo o lo movió a
             mano, sí. -->
        @for (juego of [juego]; track juego.appid) {
        <a
          class="vistazo"
          [routerLink]="['/juego', juego.appid]"
          [attr.aria-label]="'Ver el análisis de ' + juego.nombre"
          [attr.aria-live]="rotaSolo && !ejemploPausado() ? 'off' : 'polite'"
          aria-roledescription="diapositiva"
          [attr.data-appid]="juego.appid"
          data-testid="hero-ejemplo"
        >
          <div class="vistazo-portada">
            <app-portada
              [src]="juego.portada_url"
              [alta]="arteVertical(juego.appid)"
              [prioritaria]="true"
              radio="0"
            />
          </div>
          <div class="vistazo-cuerpo">
            <div class="vistazo-cabecera">
              <div>
                <p class="vistazo-sobrelinea mono">Ejemplo del catálogo</p>
                <h2 id="titulo-ejemplo">{{ juego.nombre }}</h2>
              </div>
              <app-pildora-banda [banda]="juego.banda_riesgo" />
            </div>
            <ul class="vistazo-lista">
              <li>
                <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M5 12.5 9.2 17 19 7" /></svg>
                Motivos frecuentes en reseñas
              </li>
              <li>
                <svg aria-hidden="true" viewBox="0 0 24 24"><path d="M4 18V9m8 9V5m8 13v-6" /></svg>
                Factores que mueven la estimación
              </li>
              <li>
                <svg aria-hidden="true" viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="8" />
                  <path d="M12 11v5m0-8h.01" />
                </svg>
                Contexto para decidir por tu cuenta
              </li>
            </ul>
            <span class="vistazo-accion"
              >Ver análisis completo <span aria-hidden="true">→</span></span
            >
          </div>
        </a>
        }
      </aside>
    }
  `,
  styles: `
    :host {
      display: block;
      min-width: 0;
    }
    .demostracion-fila {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: var(--espacio-12);
      margin: 0 0 var(--espacio-8);
    }

    .demostracion-fila .demostracion-etiqueta {
      margin: 0;
    }

    .carrusel-controles {
      display: flex;
      align-items: center;
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

    /* Cada ejemplo entra con un fundido corto; con movimiento reducido la regla global lo
       deja en instantáneo. */
    .demostracion .vistazo {
      animation: entrar-ejemplo 0.45s var(--curva);
    }

    /* Entra desde 0.55 y no desde 0: a mitad del fundido la tarjeta se veía vacía, que es
       peor que un cambio un poco más seco. */
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

    .demostracion-etiqueta {
      margin: 0 0 var(--espacio-8);
      color: var(--texto-meta);
      font-size: var(--texto-caption);
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .vistazo {
      display: grid;
      grid-template-columns: 142px minmax(0, 1fr);
      min-height: 248px;
      overflow: hidden;
      color: inherit;
      text-decoration: none;
      background: var(--superficie-tarjeta);
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-tarjeta);
      transition:
        border-color var(--duracion) var(--curva),
        background var(--duracion) var(--curva),
        transform var(--duracion) var(--curva);
    }

    .vistazo:hover {
      border-color: var(--neon);
      background: var(--superficie-tarjeta-hover);
      transform: translateY(-2px);
    }

    .vistazo:focus-visible {
      outline: 2px solid var(--foco);
      outline-offset: 3px;
    }

    .vistazo-portada {
      min-height: 100%;
      overflow: hidden;
      background: var(--superficie-lienzo);
    }

    .vistazo-portada app-portada {
      display: block;
      height: 100%;
    }

    .vistazo-portada ::ng-deep .marco {
      height: 100%;
      aspect-ratio: auto;
    }

    .vistazo-portada ::ng-deep img {
      object-fit: cover;
    }

    .vistazo-cuerpo {
      display: flex;
      min-width: 0;
      padding: var(--espacio-24);
      flex-direction: column;
    }

    /* La píldora va debajo del nombre y no a su lado: con "Riesgo de arrepentimiento:
       medio" no cabían los dos en la tarjeta, la píldora se cortaba contra el borde y el
       rótulo de arriba se partía en tres líneas. */
    .vistazo-cabecera {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: var(--espacio-8);
    }

    /* 16 px como todo lo demás: a 10 no se leía, y era lo primero de la tarjeta. */
    .vistazo-sobrelinea {
      margin: 0 0 var(--espacio-4);
      color: var(--neon);
      font-family: var(--fuente-display);
      font-size: var(--texto-caption);
      font-weight: 600;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .vistazo h2 {
      margin: 0;
      color: var(--texto);
      font-size: 21px;
      line-height: 1.15;
      letter-spacing: -0.025em;
    }

    .vistazo-lista {
      display: grid;
      gap: 10px;
      margin: var(--espacio-24) 0 var(--espacio-24);
      padding: 0;
      list-style: none;
    }

    .vistazo-lista li {
      display: flex;
      gap: 9px;
      align-items: center;
      color: var(--texto-meta);
      font-size: var(--texto-body-sm);
      line-height: 1.3;
    }

    .vistazo-lista svg {
      width: 16px;
      height: 16px;
      flex: none;
      fill: none;
      stroke: var(--neon);
      stroke-linecap: round;
      stroke-linejoin: round;
      stroke-width: 1.8;
    }

    .vistazo-accion {
      margin-top: auto;
      color: var(--texto);
      font-size: var(--texto-body-sm);
      font-weight: var(--peso-clave);
    }

    .vistazo-accion span {
      margin-left: var(--espacio-4);
      color: var(--neon);
    }


    /* El corte mide .contenido (app.css): con la barra lateral abierta la ventana sigue
       siendo ancha aunque al hero le queden 736 px, y ahí el ejemplo tiene que encogerse. */
    @container contenido (max-width: 900px) {
      :host {
        max-width: 620px;
      }
    }
    @media (max-width: 640px) {
      .vistazo {
        grid-template-columns: 1fr;
        min-height: 0;
      }
      .vistazo-portada {
        aspect-ratio: 460 / 215;
      }
      .vistazo-cuerpo {
        padding: var(--espacio-16);
      }
      .vistazo h2 {
        font-size: 18px;
      }
      .vistazo-lista {
        gap: 7px;
        margin: var(--espacio-12) 0;
      }
      .vistazo-lista li {
        font-size: var(--texto-caption);
      }
      .vistazo-lista li:nth-child(3) {
        display: none;
      }
      .vistazo-accion {
        font-size: var(--texto-caption);
      }
    }
  `,
})
export class CarruselEjemplo {
  private readonly catalogo = inject(CatalogoStore);

  /** Los curados que existan en el catálogo; si faltara alguno, el carrusel sigue. */
  protected readonly ejemplos = computed(() =>
    EJEMPLOS_PORTADA.map((appid) => this.catalogo.porAppid().get(appid)).filter((juego) => !!juego),
  );
  protected readonly indiceEjemplo = signal(0);
  protected readonly destacado = computed(() => {
    const ejemplos = this.ejemplos();
    return ejemplos.length ? ejemplos[this.indiceEjemplo() % ejemplos.length] : undefined;
  });
  /** Quieto mientras alguien usa el buscador: el panel de resultados cae encima del
   * ejemplo y verlo cambiar debajo mientras se escribe distrae de lo que se busca. */
  readonly pausado = input(false);

  /** Quieto también con el ratón encima o el foco dentro: nadie lee un ejemplo que se le
   * escapa. Junta la pausa de fuera con la de aquí. */
  protected readonly arteVertical = arteVertical;
  protected readonly pausadoAqui = signal(false);
  protected readonly ejemploPausado = computed(() => this.pausado() || this.pausadoAqui());
  /** Con prefers-reduced-motion no rota solo; las flechas siguen funcionando. */
  protected readonly rotaSolo = !this.prefiereMenosMovimiento();

  constructor() {
    if (this.rotaSolo) {
      const reloj = setInterval(() => {
        if (!this.ejemploPausado() && this.ejemplos().length > 1) {
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
      this.pausadoAqui.set(false);
    }
  }

  private prefiereMenosMovimiento(): boolean {
    return typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
  }
}
