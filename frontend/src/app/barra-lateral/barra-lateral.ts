import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  computed,
  effect,
  inject,
  viewChild,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink, RouterLinkActive } from '@angular/router';
import { filter, map, startWith } from 'rxjs';

import { BarraStore } from '../estado/barra-store';
import { CompararStore } from '../estado/comparar-store';
import { PerfilStore } from '../estado/perfil-store';
import { TemaStore } from '../estado/tema-store';

/** La barra lateral: la navegación del sitio, el logo y el interruptor de tema.
 *
 * En escritorio es una columna de 240 px que se puede encoger a 64 px (solo íconos, con
 * el nombre en el `title` y como texto para lector de pantalla). En pantallas angostas
 * no cabe ninguna de las dos: ahí es un cajón que entra desde la izquierda, se cierra al
 * navegar, con Escape, con el velo o con su propia X, y mientras está abierto la página
 * queda `inert` para que el tabulador no se escape detrás del velo.
 *
 * Los íconos son SVG en línea al estilo de Lucide (`menu`, `sidebar`, `compass`,
 * `columns`, `circle-user`, `circle-help`, `sun`, `moon`): trazo de currentColor y nada
 * de emoji, que no se pueden colorear ni se leen igual en cada sistema. */
@Component({
  selector: 'app-barra-lateral',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, RouterLinkActive],
  host: {
    '[class.corta]': '!barra.expandida()',
    '[class.abierta]': 'barra.cajonAbierto()',
  },
  template: `
    <nav class="riel" id="riel" aria-label="Secciones" (keydown.escape)="barra.cerrarCajon()">
      <div class="cima">
        <a routerLink="/" class="marca" aria-label="NexPlay, ir al inicio" (click)="barra.cerrarCajon()">
          <!-- El logotipo tiene dos versiones: "Nex" es blanco en una y azul marino en
               la otra, así que sobre papel hace falta la segunda o esa palabra desaparece. -->
          <img
            [src]="tema.esClaro() ? 'logo-header.png' : 'logo-oscuro.png'"
            alt=""
            width="81"
            height="70"
          />
        </a>
        <button
          #cerrar
          type="button"
          class="icono cerrar"
          aria-label="Cerrar el menú"
          data-testid="cerrar-menu"
          (click)="barra.cerrarCajon()"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M18 6 6 18" /><path d="m6 6 12 12" /></svg>
        </button>
        <button
          type="button"
          class="icono colapsar"
          data-testid="colapsar-barra"
          [attr.aria-label]="barra.expandida() ? 'Encoger la barra lateral' : 'Ampliar la barra lateral'"
          [attr.aria-expanded]="barra.expandida()"
          aria-controls="riel"
          (click)="barra.alternarExpandida()"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="3" y="3" width="18" height="18" rx="2" /><path d="M9 3v18" />
          </svg>
        </button>
      </div>

      <div class="grupos" (click)="cerrarSiEsEnlace($event)">
        <div class="grupo">
          <p class="rotulo-seccion">Principal</p>
          <ul>
            <li>
              <a
                class="item"
                routerLink="/"
                routerLinkActive="activo"
                [routerLinkActiveOptions]="{
                  paths: 'exact',
                  queryParams: 'ignored',
                  fragment: 'ignored',
                  matrixParams: 'ignored'
                }"
                ariaCurrentWhenActive="page"
                data-testid="nav-inicio"
                [attr.title]="barra.expandida() ? null : 'Inicio'"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M3.5 10.5 12 4l8.5 6.5V19a1 1 0 0 1-1 1h-15a1 1 0 0 1-1-1z" />
                  <path d="M9.5 20v-6h5v6" />
                </svg>
                <span class="etiqueta">Inicio</span>
              </a>
            </li>
            <li>
              <a
                class="item"
                routerLink="/explorar"
                routerLinkActive="activo"
                ariaCurrentWhenActive="page"
                [class.activo]="enUnaFicha()"
                [attr.aria-current]="enUnaFicha() ? 'page' : null"
                data-testid="nav-explorar"
                [attr.title]="barra.expandida() ? null : 'Explorar'"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <circle cx="12" cy="12" r="10" />
                  <path d="m16.24 7.76-2.12 6.36-6.36 2.12 2.12-6.36z" />
                </svg>
                <span class="etiqueta">Explorar</span>
              </a>
            </li>
            <li>
              <a
                class="item"
                [routerLink]="'/comparar'"
                [queryParams]="parametrosComparar()"
                routerLinkActive="activo"
                ariaCurrentWhenActive="page"
                data-testid="nav-comparar"
                [attr.title]="barra.expandida() ? null : 'Comparar'"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <rect x="3" y="3" width="18" height="18" rx="2" /><path d="M12 3v18" />
                </svg>
                <span class="etiqueta">Comparar</span>
                @if (comparar.cantidad()) {
                  <span class="cuenta mono" data-testid="nav-comparar-cantidad">({{ comparar.cantidad() }})</span>
                }
              </a>
            </li>
            <li>
              <a
                class="item"
                routerLink="/nia"
                routerLinkActive="activo"
                ariaCurrentWhenActive="page"
                data-testid="nav-nia"
                [attr.title]="barra.expandida() ? null : 'Nia'"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M20 14.5a3 3 0 0 1-3 3H9l-4 3v-3a3 3 0 0 1-1-2.2V8a3 3 0 0 1 3-3h10a3 3 0 0 1 3 3z" />
                </svg>
                <span class="etiqueta">Nia</span>
              </a>
            </li>
          </ul>
        </div>

        <div class="grupo">
          <p class="rotulo-seccion">Tu actividad</p>
          <ul>
            <li>
              <a
                class="item"
                routerLink="/perfil"
                routerLinkActive="activo"
                ariaCurrentWhenActive="page"
                data-testid="nav-perfil"
                [attr.title]="barra.expandida() ? null : 'Tu perfil'"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <circle cx="12" cy="12" r="10" /><circle cx="12" cy="10" r="3.4" />
                  <path d="M6.2 19.2a6 6 0 0 1 11.6 0" />
                </svg>
                <span class="etiqueta">Tu perfil</span>
                @if (perfil.hayPerfil()) {
                  <span class="senal" data-testid="perfil-activo" title="Perfil activo">
                    <span class="solo-lector">Perfil activo</span>
                  </span>
                }
              </a>
            </li>
            <li>
              <a
                class="item"
                routerLink="/historial"
                routerLinkActive="activo"
                ariaCurrentWhenActive="page"
                data-testid="nav-historial"
                [attr.title]="barra.expandida() ? null : 'Historial'"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M3.5 12a8.5 8.5 0 1 0 2.6-6.1" /><path d="M3.5 5v4h4" />
                  <path d="M12 8v4.3l3 1.8" />
                </svg>
                <span class="etiqueta">Historial</span>
              </a>
            </li>
          </ul>
        </div>

        <div class="grupo">
          <p class="rotulo-seccion">Transparencia</p>
          <ul>
            <li>
              <a
                class="item"
                routerLink="/panorama"
                routerLinkActive="activo"
                ariaCurrentWhenActive="page"
                data-testid="nav-panorama"
                [attr.title]="barra.expandida() ? null : 'Panorama'"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M4 19V5" /><path d="M4 19h16" />
                  <path d="M8 19v-6m4 6V8m4 11v-4" />
                </svg>
                <span class="etiqueta">Panorama</span>
              </a>
            </li>
            <li>
              <a
                class="item"
                routerLink="/como-funciona"
                routerLinkActive="activo"
                ariaCurrentWhenActive="page"
                data-testid="nav-como-funciona"
                [attr.title]="barra.expandida() ? null : 'Cómo funciona'"
              >
                <svg viewBox="0 0 24 24" aria-hidden="true">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M9.2 9.3a2.9 2.9 0 0 1 5.6 1c0 1.9-2.8 2.5-2.8 4" /><path d="M12 17.2h.01" />
                </svg>
                <span class="etiqueta">Cómo funciona</span>
              </a>
            </li>
          </ul>
        </div>
      </div>

      <div class="pie-riel">
        <button
          type="button"
          class="interruptor"
          role="switch"
          data-testid="cambiar-tema"
          [attr.aria-checked]="tema.esClaro()"
          [attr.title]="barra.expandida() ? null : 'Modo claro'"
          (click)="tema.alternar()"
        >
          <span class="astro" aria-hidden="true">
            @if (tema.esClaro()) {
              <svg viewBox="0 0 24 24">
                <circle cx="12" cy="12" r="4" />
                <path d="M12 2v2M12 20v2M2 12h2M20 12h2" />
                <path d="m4.9 4.9 1.5 1.5M17.6 17.6l1.5 1.5M19.1 4.9l-1.5 1.5M6.4 17.6l-1.5 1.5" />
              </svg>
            } @else {
              <svg viewBox="0 0 24 24"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" /></svg>
            }
          </span>
          <span class="etiqueta">Modo claro</span>
        </button>
      </div>
    </nav>
  `,
  styles: `
    :host {
      display: block;
      position: sticky;
      top: 0;
      height: 100vh;
      background: var(--superficie-barra);
      border-inline-end: 1px solid var(--linea);
    }
    /* Todo el riel tiene que caber sin scroll propio en una pantalla de portátil (674 px
       de alto visible): con ocho ítems, tres rótulos y el interruptor, el aire va justo. */
    .riel {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-16);
      height: 100%;
      padding: var(--espacio-16);
      overflow-y: auto;
    }
    .cima {
      display: flex;
      align-items: flex-start;
      gap: var(--espacio-8);
    }
    .marca {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: var(--espacio-8);
      text-decoration: none;
    }
    .marca img {
      width: 81px;
      height: 70px;
      object-fit: contain;
      /* El logo es un PNG, así que la animación va por fuera: flota tres píxeles y el
         halo late con ella. La regla global de prefers-reduced-motion la deja quieta. */
      animation: respirar 6s var(--curva) infinite;
    }
    @keyframes respirar {
      0%,
      100% {
        transform: translateY(0);
        filter: drop-shadow(0 0 1px rgb(var(--neon-canal) / 0.15)) brightness(1);
      }
      50% {
        transform: translateY(-3px);
        filter: drop-shadow(0 0 calc(5px * var(--halo-radio)) rgb(var(--neon-canal) / calc(0.5 * var(--halo-alfa))))
          brightness(1.12);
      }
    }
    .marca:hover img {
      filter: drop-shadow(0 0 calc(6px * var(--halo-radio)) rgb(var(--neon-canal) / calc(0.65 * var(--halo-alfa))))
        brightness(1.15);
    }
    .icono {
      display: grid;
      place-items: center;
      width: 44px;
      height: 44px;
      flex: none;
      padding: 0;
      border: 1px solid transparent;
      border-radius: var(--radio-boton);
      background: none;
      color: var(--texto-meta);
      cursor: pointer;
      transition:
        color var(--duracion-rapida) var(--curva),
        border-color var(--duracion-rapida) var(--curva);
    }
    svg {
      width: 20px;
      height: 20px;
      fill: none;
      stroke: currentColor;
      stroke-width: 1.75;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    /* La X solo existe en el cajón; el botón de encoger solo en escritorio. */
    .cerrar {
      display: none;
    }
    .grupos {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-16);
      flex: 1;
    }
    .grupo ul {
      list-style: none;
      margin: var(--espacio-8) 0 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: var(--espacio-4);
    }
    .item,
    .interruptor {
      position: relative;
      display: flex;
      align-items: center;
      gap: var(--espacio-12);
      min-height: 44px;
      padding: var(--espacio-8) var(--espacio-12);
      border: 1px solid transparent;
      border-radius: var(--radio-boton);
      color: var(--texto-meta);
      font-size: var(--texto-body-sm);
      text-decoration: none;
      white-space: nowrap;
      transition:
        color var(--duracion-rapida) var(--curva),
        background var(--duracion-rapida) var(--curva);
    }
    .item:hover {
      color: var(--texto);
      background: var(--superficie-tarjeta-hover);
    }
    /* El activo es lo único con fondo propio: relleno del sistema más filo de neón, como
       el resto de los estados elegidos del proyecto. */
    .item.activo {
      color: var(--texto);
      background: var(--acento-sistema);
      border-color: var(--neon);
    }
    .item.activo svg {
      color: var(--neon);
    }
    .cuenta {
      color: var(--texto-meta);
      font-size: var(--texto-caption);
    }
    /* Perfil activo: un punto, no una píldora. El texto va para el lector de pantalla. */
    .senal {
      width: 8px;
      height: 8px;
      margin-inline-start: auto;
      border-radius: 50%;
      background: var(--neon);
      flex: none;
    }
    .pie-riel {
      padding-top: var(--espacio-16);
      border-top: 1px solid var(--linea);
    }
    .interruptor {
      width: 100%;
      background: none;
      text-align: start;
      cursor: pointer;
    }
    .icono:hover,
    .interruptor:hover {
      color: var(--texto);
      border-color: var(--borde-control);
    }
    .astro {
      display: grid;
      flex: none;
      color: var(--neon);
    }
    /* Encogida: solo la columna de íconos. El nombre no se quita del DOM —se esconde
       con la técnica de .solo-lector— y reaparece como title al pasar el ratón. Todo esto
       vale solo en escritorio: en el cajón de móvil la barra siempre va con sus nombres. */
    @media (min-width: 901px) {
      :host(.corta) .etiqueta,
      :host(.corta) .rotulo-seccion {
        position: absolute;
        width: 1px;
        height: 1px;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
      }
      :host(.corta) .riel {
        padding-inline: var(--espacio-8);
        gap: var(--espacio-16);
      }
      :host(.corta) .cima {
        flex-direction: column;
        align-items: center;
      }
      :host(.corta) .marca {
        flex: none;
      }
      :host(.corta) .marca img {
        width: 40px;
        height: 35px;
      }
      :host(.corta) .cuenta {
        display: none;
      }
      :host(.corta) .item,
      :host(.corta) .interruptor {
        justify-content: center;
        gap: 0;
        padding-inline: 0;
      }
      :host(.corta) .senal {
        position: absolute;
        inset-block-start: 6px;
        inset-inline-end: 8px;
        margin: 0;
      }
      :host(.corta) .grupo ul {
        margin-top: 0;
      }
    }
    /* Cajón: a 900 px la barra ya no cabe al lado del contenido, así que sale del flujo y
       entra encima cuando se pide. Cerrada, visibility la saca del tabulador. */
    @media (max-width: 900px) {
      :host {
        position: fixed;
        inset-block: 0;
        inset-inline-start: 0;
        z-index: 50;
        width: min(280px, 82vw);
        height: 100%;
        visibility: hidden;
        transform: translateX(-100%);
        transition:
          transform var(--duracion) var(--curva),
          visibility var(--duracion) var(--curva);
      }
      :host(.abierta) {
        visibility: visible;
        transform: none;
      }
      .cerrar {
        display: grid;
      }
      .colapsar {
        display: none;
      }
    }
  `,
})
export class BarraLateral {
  protected readonly barra = inject(BarraStore);
  protected readonly tema = inject(TemaStore);
  protected readonly comparar = inject(CompararStore);
  protected readonly perfil = inject(PerfilStore);

  private readonly botonCerrar = viewChild<ElementRef<HTMLButtonElement>>('cerrar');
  private readonly router = inject(Router);

  /** La ficha de un juego no tiene entrada propia en el menú: se llega desde el catálogo,
   * así que es Explorar lo que queda marcado mientras está abierta. */
  protected readonly enUnaFicha = toSignal(
    this.router.events.pipe(
      filter((evento): evento is NavigationEnd => evento instanceof NavigationEnd),
      map((evento) => evento.urlAfterRedirects.startsWith('/juego/')),
      startWith(this.router.url.startsWith('/juego/')),
    ),
    { initialValue: this.router.url.startsWith('/juego/') },
  );

  constructor() {
    // Al abrir el cajón el foco entra en él; si no, el tabulador seguiría en la página.
    effect(() => {
      if (this.barra.cajonAbierto()) {
        this.botonCerrar()?.nativeElement.focus();
      }
    });
  }

  protected readonly parametrosComparar = computed(() =>
    this.comparar.cantidad() ? { appids: this.comparar.appids().join(',') } : {},
  );

  /** Cualquier enlace del riel cierra el cajón, incluso el de la ruta abierta, que no
   * dispararía un cambio de ruta. */
  protected cerrarSiEsEnlace(evento: Event): void {
    if ((evento.target as HTMLElement).closest('a')) {
      this.barra.cerrarCajon();
    }
  }
}
