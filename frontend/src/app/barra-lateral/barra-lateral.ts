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
import { CatalogoStore } from '../estado/catalogo-store';
import { CompararStore } from '../estado/comparar-store';
import { PerfilStore } from '../estado/perfil-store';
import { TemaStore } from '../estado/tema-store';

/** La barra lateral: la navegación del sitio, el logo y el interruptor de tema.
 *
 * En escritorio es una columna de 256 px que se puede encoger a 72 px (solo íconos, con
 * el nombre en el `title` y como texto para lector de pantalla). En pantallas angostas
 * no cabe ninguna de las dos: ahí es un cajón que entra desde la izquierda, se cierra al
 * navegar, con Escape, con el velo o con su propia X, y mientras está abierto la página
 * queda `inert` para que el tabulador no se escape detrás del velo.
 *
 * Cada sección lleva el color de su vista en el ícono, un nombre y una línea que dice qué
 * hay ahí. Los íconos son SVG en línea al estilo de Lucide: trazo de currentColor y nada
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
    <nav
      class="riel"
      id="riel"
      aria-label="Secciones"
      [class.pildora-larga]="perfil.faltaGasto()"
      (keydown.escape)="barra.cerrarCajon()"
    >
      <div class="cima">
        <a routerLink="/" class="marca" aria-label="NexPlay, ir al inicio" (click)="barra.cerrarCajon()">
          <!-- El logotipo tiene dos versiones: "Nex" es blanco en una y azul marino en
               la otra, así que sobre papel hace falta la segunda o esa palabra desaparece.
               Encogida, la ventana de .logo recorta el mismo archivo y deja solo la marca. -->
          <span class="logo">
            <img
              [src]="tema.esClaro() ? 'logo-header.png' : 'logo-oscuro.png'"
              alt=""
              width="1035"
              height="894"
            />
          </span>
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
      </div>

      <div class="grupos" (click)="cerrarSiEsEnlace($event)">
        <ul aria-label="Principal">
          <li>
            <a
              class="item"
              data-tono="inicio"
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
              <span class="insignia" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <path d="M3.5 10.5 12 4l8.5 6.5V19a1 1 0 0 1-1 1h-15a1 1 0 0 1-1-1z" />
                  <path d="M9.5 20v-6h5v6" />
                </svg>
              </span>
              <span class="etiqueta nombre">Inicio</span>
              <span class="etiqueta sub">Qué es NexPlay</span>
            </a>
          </li>
          <li>
            <a
              class="item"
              data-tono="explorar"
              routerLink="/explorar"
              routerLinkActive="activo"
              ariaCurrentWhenActive="page"
              [class.activo]="enUnaFicha()"
              [attr.aria-current]="enUnaFicha() ? 'page' : null"
              data-testid="nav-explorar"
              [attr.title]="barra.expandida() ? null : 'Explorar'"
            >
              <span class="insignia" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" />
                  <path d="m16.24 7.76-2.12 6.36-6.36 2.12 2.12-6.36z" />
                </svg>
              </span>
              <span class="etiqueta nombre">Explorar</span>
              <span class="etiqueta sub">{{ subtituloExplorar() }}</span>
            </a>
          </li>
          <li>
            <a
              class="item"
              data-tono="comparar"
              [routerLink]="'/comparar'"
              [queryParams]="parametrosComparar()"
              routerLinkActive="activo"
              ariaCurrentWhenActive="page"
              data-testid="nav-comparar"
              [attr.title]="barra.expandida() ? null : 'Comparar'"
            >
              <span class="insignia" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <rect x="3" y="3" width="18" height="18" rx="2" /><path d="M12 3v18" />
                </svg>
              </span>
              <span class="etiqueta nombre">Comparar</span>
              <span class="etiqueta sub">Hasta 4 lado a lado</span>
              @if (comparar.cantidad()) {
                <span class="cuenta mono" data-testid="nav-comparar-cantidad">({{ comparar.cantidad() }})</span>
              }
            </a>
          </li>
          <li>
            <a
              class="item"
              data-tono="nia"
              routerLink="/nia"
              routerLinkActive="activo"
              ariaCurrentWhenActive="page"
              data-testid="nav-nia"
              [attr.title]="barra.expandida() ? null : 'Nia'"
            >
              <span class="insignia" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <path d="M20 14.5a3 3 0 0 1-3 3H9l-4 3v-3a3 3 0 0 1-1-2.2V8a3 3 0 0 1 3-3h10a3 3 0 0 1 3 3z" />
                </svg>
              </span>
              <span class="etiqueta nombre">Nia</span>
              <span class="etiqueta sub">Tu asistente</span>
            </a>
          </li>
        </ul>

        <ul aria-label="Tu actividad">
          <li>
            <a
              class="item"
              data-tono="perfil"
              routerLink="/perfil"
              routerLinkActive="activo"
              ariaCurrentWhenActive="page"
              data-testid="nav-perfil"
              [attr.title]="barra.expandida() ? null : 'Tu perfil'"
            >
              <span class="insignia" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" /><circle cx="12" cy="10" r="3.4" />
                  <path d="M6.2 19.2a6 6 0 0 1 11.6 0" />
                </svg>
              </span>
              <span class="etiqueta nombre">Tu perfil</span>
              <span class="etiqueta sub">Cómo juegas tú</span>
            </a>
          </li>
          <li>
            <a
              class="item"
              data-tono="neutro"
              routerLink="/historial"
              routerLinkActive="activo"
              ariaCurrentWhenActive="page"
              data-testid="nav-historial"
              [attr.title]="barra.expandida() ? null : 'Historial'"
            >
              <span class="insignia" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <path d="M3.5 12a8.5 8.5 0 1 0 2.6-6.1" /><path d="M3.5 5v4h4" />
                  <path d="M12 8v4.3l3 1.8" />
                </svg>
              </span>
              <span class="etiqueta nombre">Historial</span>
              <span class="etiqueta sub">Lo que ya viste</span>
            </a>
          </li>
        </ul>

        <ul aria-label="Transparencia">
          <li>
            <a
              class="item"
              data-tono="panorama"
              routerLink="/panorama"
              routerLinkActive="activo"
              ariaCurrentWhenActive="page"
              data-testid="nav-panorama"
              [attr.title]="barra.expandida() ? null : 'Panorama'"
            >
              <span class="insignia" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <path d="M4 19V5" /><path d="M4 19h16" />
                  <path d="M8 19v-6m4 6V8m4 11v-4" />
                </svg>
              </span>
              <span class="etiqueta nombre">Panorama</span>
              <span class="etiqueta sub">Los datos en gráficas</span>
            </a>
          </li>
          <li>
            <a
              class="item"
              data-tono="neutro"
              routerLink="/como-funciona"
              routerLinkActive="activo"
              ariaCurrentWhenActive="page"
              data-testid="nav-como-funciona"
              [attr.title]="barra.expandida() ? null : 'Cómo funciona'"
            >
              <span class="insignia" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <circle cx="12" cy="12" r="10" />
                  <path d="M9.2 9.3a2.9 2.9 0 0 1 5.6 1c0 1.9-2.8 2.5-2.8 4" /><path d="M12 17.2h.01" />
                </svg>
              </span>
              <span class="etiqueta nombre">Cómo funciona</span>
              <span class="etiqueta sub">Método y fuentes</span>
            </a>
          </li>
        </ul>
      </div>

      <!-- La píldora está siempre: con perfil dice que está activo (y si le falta la
           pregunta nueva); sin perfil, invita a crearlo. Encogida queda el icono. -->
      @if (perfil.hayPerfil()) {
        <p class="perfil-activo" data-testid="perfil-activo" [attr.title]="resumenPerfil()">
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6 9 17l-5-5" /></svg>
          <span class="etiqueta">{{ resumenPerfil() }}</span>
        </p>
      } @else {
        <a
          class="perfil-activo vacio"
          routerLink="/perfil"
          data-testid="perfil-inactivo"
          title="Sin perfil · Crear en 1 minuto"
          (click)="barra.cerrarCajon()"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="10" /><circle cx="12" cy="10" r="3.4" /><path d="M6.2 19.2a6 6 0 0 1 11.6 0" />
          </svg>
          <span class="etiqueta">Sin perfil · <span class="ir">Crear · 1 min</span></span>
        </a>
      }

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
        <button
          type="button"
          class="icono colapsar"
          data-testid="colapsar-barra"
          [attr.aria-label]="barra.expandida() ? 'Encoger la barra lateral' : 'Ampliar la barra lateral'"
          [attr.title]="barra.expandida() ? 'Encoger la barra lateral' : 'Ampliar la barra lateral'"
          [attr.aria-expanded]="barra.expandida()"
          aria-controls="riel"
          (click)="barra.alternarExpandida()"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="3" y="3" width="18" height="18" rx="2" /><path d="M9 3v18" />
          </svg>
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
       de alto visible), con perfil activo incluido. El logo es lo único que cede: en una
       pantalla alta ocupa el ancho de la barra y en la de portátil se achica a lo que
       sobra. --resto-riel es lo que mide todo lo demás. */
    .riel {
      --resto-riel: 548px;
      display: flex;
      flex-direction: column;
      gap: var(--espacio-8);
      height: 100%;
      padding: var(--espacio-12);
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
      justify-content: center;
      border-radius: var(--radio-tarjeta);
      text-decoration: none;
    }
    .logo {
      display: block;
      max-width: 100%;
      /* La animación va en la ventana y no en la imagen: encogida, la ventana recorta y
         un brillo puesto en la imagen quedaría cortado contra sus bordes. Flota tres
         píxeles y el halo late con ella; la regla global de prefers-reduced-motion la
         deja quieta. */
      animation: respirar 6s var(--curva) infinite;
    }
    /* «Perfil activo · 1 pregunta nueva» no cabe en un renglón: va en dos, y el logo cede
       esos 20 px para que todo siga cabiendo en 674. */
    .riel.pildora-larga {
      --resto-riel: 568px;
    }
    .logo img {
      display: block;
      width: auto;
      max-width: 100%;
      height: clamp(100px, calc(100vh - var(--resto-riel)), 200px);
      object-fit: contain;
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
    .marca:hover .logo {
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
      border: 1px solid var(--borde-control);
      border-radius: 50%;
      background: var(--superficie-2);
      color: var(--texto);
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
    /* Sin rótulos de grupo: los tres grupos se separan con un filete y el nombre de cada
       uno queda para el lector de pantalla, en el aria-label de su lista. */
    .grupos {
      display: flex;
      flex-direction: column;
      flex: 1;
    }
    .grupos ul {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .grupos ul + ul {
      margin-top: var(--espacio-4);
      padding-top: var(--espacio-4);
      border-top: 1px solid var(--linea);
    }
    .item {
      position: relative;
      display: grid;
      grid-template-columns: 36px minmax(0, 1fr);
      align-items: center;
      column-gap: var(--espacio-12);
      min-height: 44px;
      padding: 3px var(--espacio-8);
      border: 1px solid transparent;
      border-radius: var(--radio-tarjeta);
      color: var(--texto);
      text-decoration: none;
      white-space: nowrap;
      transition:
        color var(--duracion-rapida) var(--curva),
        background var(--duracion-rapida) var(--curva);
    }
    .insignia {
      grid-column: 1;
      grid-row: 1 / span 2;
      display: grid;
      place-items: center;
      width: 36px;
      height: 36px;
      border-radius: 10px;
      color: var(--tono);
      background: rgb(var(--tono-canal) / 0.14);
    }
    .nombre {
      grid-column: 2;
      grid-row: 1;
      font-family: var(--fuente-display);
      font-weight: 600;
      font-size: 17px;
      line-height: 1.1;
      letter-spacing: 0.04em;
    }
    .sub {
      grid-column: 2;
      grid-row: 2;
      overflow: hidden;
      text-overflow: ellipsis;
      color: var(--texto-meta);
      font-size: var(--texto-caption);
      line-height: 1.2;
    }
    .item:hover {
      background: var(--superficie-2);
    }
    /* El activo es lo único con fondo propio: relleno y filo del color de la vista
       abierta, que es el mismo del fondo y del botón principal. */
    .item.activo {
      background: var(--acento-sistema);
      border-color: var(--neon);
    }
    .item.activo .nombre {
      color: var(--neon);
    }
    /* La cuenta comparte fila con el nombre: una tercera columna le quitaría su hueco
       a todos los subtítulos aunque esté vacía, y "Los datos en gráficas" ya no cabría. */
    .cuenta {
      grid-column: 2;
      grid-row: 1;
      justify-self: end;
      line-height: 1.1;
      color: var(--texto-meta);
      font-size: var(--texto-caption);
    }
    /* Perfil activo: una píldora con lo declarado, no un punto que nadie sabe leer. Va
       en el color de Tu perfil; el verde queda para el riesgo. */
    .perfil-activo {
      display: flex;
      align-items: center;
      gap: var(--espacio-8);
      min-width: 0;
      margin: 0;
      padding: 6px var(--espacio-12);
      border: 1px solid color-mix(in srgb, var(--t-perfil) var(--mezcla-filo), var(--superficie));
      border-radius: var(--radio-pildora);
      background: rgb(var(--canal-perfil) / 0.1);
      color: var(--texto);
      font-size: var(--texto-caption);
      line-height: 1.25;
    }
    .perfil-activo svg {
      flex: none;
      color: var(--t-perfil);
      stroke-width: 2.25;
    }
    .perfil-activo .etiqueta {
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .pildora-larga .perfil-activo {
      border-radius: var(--radio-tarjeta);
    }
    .pildora-larga .perfil-activo .etiqueta {
      white-space: normal;
    }
    /* Sin perfil: punteada y en gris, con el enlace a crearlo. */
    .perfil-activo.vacio {
      border: 1px dashed var(--borde-control);
      background: var(--superficie-2);
      text-decoration: none;
    }
    .perfil-activo.vacio:hover {
      border-color: var(--t-perfil);
    }
    .ir {
      color: var(--enlace);
      text-decoration: underline;
      text-underline-offset: 3px;
    }
    .pie-riel {
      display: flex;
      align-items: center;
      gap: var(--espacio-8);
      padding-top: var(--espacio-8);
      border-top: 1px solid var(--linea);
    }
    .interruptor {
      flex: 1;
      display: flex;
      align-items: center;
      gap: var(--espacio-12);
      min-height: 44px;
      padding: var(--espacio-8) var(--espacio-12);
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-pildora);
      background: var(--superficie-2);
      color: var(--texto);
      font-size: var(--texto-body-sm);
      text-align: start;
      white-space: nowrap;
      cursor: pointer;
    }
    .icono:hover,
    .interruptor:hover {
      border-color: var(--neon);
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
      :host(.corta) .etiqueta {
        position: absolute;
        width: 1px;
        height: 1px;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
      }
      :host(.corta) .riel {
        align-items: center;
        padding-inline: var(--espacio-8);
      }
      :host(.corta) .cima,
      :host(.corta) .grupos,
      :host(.corta) .pie-riel {
        align-self: stretch;
      }
      :host(.corta) .marca {
        flex: none;
        margin-inline: auto;
      }
      /* La marca sin el nombre: una ventana del tamaño del triángulo sobre el mismo PNG.
         En el archivo, la marca ocupa x 214–884 e y 2–593 de 1035 × 894; a 80 px de ancho
         eso deja 52 × 46 a partir de x = 16.5. */
      :host(.corta) .logo {
        width: 52px;
        height: 46px;
        overflow: hidden;
      }
      :host(.corta) .logo img {
        width: 80px;
        max-width: none;
        height: auto;
        margin-inline-start: -16.5px;
      }
      :host(.corta) .cuenta {
        display: none;
      }
      :host(.corta) .item {
        grid-template-columns: 1fr;
        justify-items: center;
        padding-inline: 0;
      }
      :host(.corta) .insignia {
        grid-row: auto;
      }
      :host(.corta) .perfil-activo {
        justify-content: center;
        width: 44px;
        height: 44px;
        padding: 0;
        border-radius: 50%;
      }
      :host(.corta) .pie-riel {
        flex-direction: column;
      }
      :host(.corta) .interruptor {
        flex: none;
        justify-content: center;
        width: 44px;
        padding: 0;
        border-radius: 50%;
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
  private readonly catalogo = inject(CatalogoStore);

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

  /** Mientras el catálogo carga no hay cifra que dar, y "Los 0 juegos" sería mentira. */
  protected readonly subtituloExplorar = computed(() => {
    const cuantos = this.catalogo.juegos().length;
    return cuantos ? `Los ${cuantos} juegos` : 'El catálogo';
  });

  protected readonly resumenPerfil = computed(() => {
    if (this.perfil.faltaGasto()) {
      return 'Perfil activo · 1 pregunta nueva';
    }
    const generos = this.perfil.valores()?.generos ?? [];
    return generos.length ? `Perfil activo · ${generos.join(', ')}` : 'Perfil activo';
  });

  /** Cualquier enlace del riel cierra el cajón, incluso el de la ruta abierta, que no
   * dispararía un cambio de ruta. */
  protected cerrarSiEsEnlace(evento: Event): void {
    if ((evento.target as HTMLElement).closest('a')) {
      this.barra.cerrarCajon();
    }
  }
}
