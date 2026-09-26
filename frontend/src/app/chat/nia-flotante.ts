import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  computed,
  effect,
  inject,
  signal,
  untracked,
  viewChild,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router } from '@angular/router';
import { filter, map, startWith } from 'rxjs';

import { CLAVE_GLOBITOS, GlobitosVistos, debeMostrarGlobito, hoyLocal, marcarGlobito, vistaConGlobito } from '../dominio/globito-nia';
import { FICHAS_BURBUJA, SALUDO_BURBUJA, VistaConGlobito, textoGlobito } from '../dominio/textos-nia';
import { CatalogoStore } from '../estado/catalogo-store';
import { CompararStore } from '../estado/comparar-store';
import { Nia } from './nia';

/** Cuánto espera el globito para salir y cuánto se queda si nadie lo toca. */
const ESPERA_GLOBITO_MS = 2000;
const DURA_GLOBITO_MS = 10000;

function leerVistos(): GlobitosVistos {
  try {
    return JSON.parse(localStorage.getItem(CLAVE_GLOBITOS) ?? '{}') as GlobitosVistos;
  } catch {
    return {};
  }
}

function guardarVistos(vistos: GlobitosVistos): void {
  try {
    localStorage.setItem(CLAVE_GLOBITOS, JSON.stringify(vistos));
  } catch {
    // Sin almacenamiento el globito puede volver a salir; no es motivo para fallar.
  }
}

/** Nia en la esquina, en todas las vistas menos la ficha y la suya. Al abrirse saluda y
 * conversa sobre el catálogo; si hace falta un juego, lo pide dentro del chat.
 *
 * En Explorar, Tu perfil y Comparar ofrece una cosa de esa vista en un globito: sale una
 * vez, se va solo o con la ×, y no vuelve hasta el día siguiente. */
@Component({
  selector: 'app-nia-flotante',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Nia],
  // La burbuja es de Nia en cualquier vista: su anillo, su globito y sus botones van en
  // su violeta, no en el color de la vista donde está.
  host: { 'data-vista': 'nia' },
  template: `
    <div class="flotante" [class.abierto]="abierto()" (document:keydown.escape)="cerrar()">
      @if (abierto()) {
        <div
          class="panel panel-vidrio"
          role="dialog"
          aria-modal="false"
          aria-labelledby="nia-flotante-titulo"
          data-testid="nia-flotante-panel"
        >
          <header class="cabecera">
            <div class="quien">
              <img class="avatar-chico" src="nia/chat.png" alt="" width="200" height="233" />
              <div>
                <h2 class="nombre" id="nia-flotante-titulo">Nia</h2>
                <p class="meta subtitulo">Asistente de NexPlay</p>
              </div>
            </div>
            <button type="button" class="boton-texto toque-amplio" data-testid="nia-flotante-cerrar" (click)="cerrar()">
              Cerrar
            </button>
          </header>
          <app-nia [appid]="null" [muestraTitulo]="false" [muestraIntro]="false" [saludo]="saludo" [fichas]="fichas" />
        </div>
      } @else if (globito(); as mensaje) {
        <div class="globito" role="status" data-testid="nia-globito">
          <p>{{ mensaje.texto }}</p>
          <button type="button" class="compacto" data-testid="nia-globito-accion" (click)="aceptarGlobito()">
            {{ mensaje.accion }}
          </button>
          <button
            type="button"
            class="cerrar-globito"
            aria-label="Cerrar el mensaje de Nia"
            data-testid="nia-globito-cerrar"
            (click)="cerrarGlobito()"
          >
            ×
          </button>
        </div>
      }

      <button
        type="button"
        class="burbuja"
        data-testid="nia-flotante-burbuja"
        [attr.aria-expanded]="abierto()"
        [attr.aria-label]="abierto() ? 'Cerrar el chat de Nia' : 'Abrir el chat de Nia'"
        #burbuja
        (click)="alternar()"
      >
        <img class="avatar" src="nia/chat.png" alt="" width="200" height="233" />
      </button>
    </div>
  `,
  styles: `
    /* El único elemento fijo de la app. Se ancla al área segura para no quedar debajo
       de la barra del navegador en móvil. */
    /* --elevacion-burbuja la sube encima de lo que una vista fija abajo (la barra de
       guardar de /perfil, en base.css). */
    .flotante {
      position: fixed;
      right: max(var(--espacio-16), env(safe-area-inset-right));
      bottom: calc(max(var(--espacio-16), env(safe-area-inset-bottom)) + var(--elevacion-burbuja, 0px));
      z-index: 20;
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: var(--espacio-12);
    }
    /* 84 px con Nia asomándose por encima del anillo: se ve de lejos, que era la queja.
       El anillo respira despacio; abierta, se queda encendido. */
    .burbuja {
      position: relative;
      width: 84px;
      height: 84px;
      padding: 0;
      border: 3px solid var(--neon);
      border-radius: 50%;
      background: radial-gradient(
        circle at 50% 35%,
        color-mix(in srgb, var(--neon) 30%, var(--superficie-lienzo)),
        var(--superficie-lienzo)
      );
      box-shadow: 0 12px 30px rgb(0 0 0 / 0.35);
      cursor: pointer;
      animation: respirar-anillo 4.5s ease-in-out infinite;
      transition: transform var(--duracion-rapida) var(--curva);
    }
    @keyframes respirar-anillo {
      0%,
      100% {
        box-shadow:
          0 0 0 4px rgb(var(--neon-canal) / calc(0.12 * var(--halo-alfa))),
          0 12px 30px rgb(0 0 0 / 0.35);
      }
      50% {
        box-shadow:
          0 0 0 8px rgb(var(--neon-canal) / calc(0.2 * var(--halo-alfa))),
          0 0 calc(18px * var(--halo-radio)) rgb(var(--neon-canal) / calc(0.45 * var(--halo-alfa))),
          0 12px 30px rgb(0 0 0 / 0.35);
      }
    }
    .burbuja:hover {
      transform: translateY(-2px) scale(1.04);
    }
    .abierto .burbuja {
      animation: none;
      box-shadow: var(--resplandor);
    }
    /* Nia saludando, más ancha que el círculo y apoyada en su borde de abajo: las orejas
       salen del anillo. */
    .avatar {
      position: absolute;
      left: 50%;
      bottom: 0;
      width: 96px;
      height: auto;
      transform: translateX(-50%);
      pointer-events: none;
    }
    .quien {
      display: flex;
      align-items: center;
      gap: var(--espacio-12);
    }
    .avatar-chico {
      width: 44px;
      height: 44px;
      padding: 3px 3px 0;
      object-fit: contain;
      object-position: center bottom;
      border-radius: 50%;
      background: var(--superficie-lienzo);
      box-shadow:
        0 0 0 1px var(--neon),
        0 0 calc(8px * var(--halo-radio)) rgb(var(--neon-canal) / calc(0.35 * var(--halo-alfa)));
    }
    .nombre {
      margin: 0;
      font-size: var(--texto-body-sm);
    }
    .subtitulo {
      margin: 0;
    }
    /* El globito: un mensaje de la vista, en panel (nunca texto de color sobre la
       nebulosa), con su botón y la × a la mano. */
    .globito {
      position: relative;
      max-width: 300px;
      padding: var(--espacio-12) 44px var(--espacio-12) 14px;
      border: 1px solid color-mix(in srgb, var(--neon) var(--mezcla-filo), var(--superficie));
      border-radius: var(--radio-tarjeta) var(--radio-tarjeta) 4px var(--radio-tarjeta);
      background: var(--superficie);
      box-shadow: 0 10px 30px rgb(0 0 0 / 0.25);
      animation: asomar var(--duracion) var(--curva);
    }
    .globito p {
      margin: 0 0 var(--espacio-8);
      font-size: 17px;
      line-height: 1.45;
    }
    .cerrar-globito {
      position: absolute;
      top: 4px;
      right: 4px;
      width: 40px;
      height: 40px;
      display: grid;
      place-items: center;
      padding: 0;
      border: 0;
      border-radius: 50%;
      background: transparent;
      color: var(--texto-meta);
      font-size: 22px;
      cursor: pointer;
    }
    .cerrar-globito:hover {
      color: var(--texto);
    }
    @keyframes asomar {
      from {
        opacity: 0;
        transform: translateY(6px);
      }
    }
    @media (prefers-reduced-motion: reduce) {
      .burbuja,
      .globito {
        animation: none;
      }
    }
    /* En móvil el margen baja a 16 px, el mismo de la página, siempre por dentro del área
       segura. Abierto, el panel toma el ancho entre los dos márgenes, centrado. */
    @media (max-width: 640px) {
      .flotante {
        right: calc(var(--espacio-16) + env(safe-area-inset-right));
        bottom: calc(var(--espacio-16) + env(safe-area-inset-bottom) + var(--elevacion-burbuja, 0px));
      }
      .flotante.abierto {
        left: calc(var(--espacio-16) + env(safe-area-inset-left));
      }
      .abierto .panel {
        width: 100%;
      }
      .burbuja {
        width: 72px;
        height: 72px;
      }
      .avatar {
        width: 82px;
      }
    }
    .panel {
      width: min(400px, calc(100vw - var(--espacio-48)));
      max-height: min(72vh, 600px);
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
    }
    .cabecera {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: var(--espacio-12);
    }
  `,
})
export class NiaFlotante {
  private readonly router = inject(Router);
  private readonly catalogo = inject(CatalogoStore);
  private readonly comparar = inject(CompararStore);
  private readonly burbuja = viewChild<ElementRef<HTMLButtonElement>>('burbuja');
  private readonly chat = viewChild(Nia);

  protected readonly saludo = SALUDO_BURBUJA;
  protected readonly fichas = FICHAS_BURBUJA;

  protected readonly abierto = signal(false);
  /** La vista cuyo globito está a la vista, o null. */
  private readonly vistaDelGlobito = signal<VistaConGlobito | null>(null);
  /** Lo que el botón del globito dejó pedido, para cuando el chat ya esté montado. */
  private readonly pendiente = signal<VistaConGlobito | null>(null);
  private relojes: ReturnType<typeof setTimeout>[] = [];

  private readonly ruta = toSignal(
    this.router.events.pipe(
      filter((evento): evento is NavigationEnd => evento instanceof NavigationEnd),
      map((evento) => evento.urlAfterRedirects),
      startWith(this.router.url),
    ),
    { initialValue: this.router.url },
  );

  /** Los nombres de lo que hay en Comparar, para resumirlo. */
  private readonly enComparacion = computed(() => {
    const porAppid = this.catalogo.porAppid();
    return this.comparar
      .appids()
      .map((appid) => porAppid.get(appid)?.nombre)
      .filter((nombre): nombre is string => !!nombre);
  });

  protected readonly globito = computed(() => {
    const vista = this.vistaDelGlobito();
    return vista ? textoGlobito(vista, this.enComparacion().length) : null;
  });

  constructor() {
    // Cada vez que se entra a una vista con globito, si hoy no ha salido, sale a los 2 s.
    effect(() => {
      const vista = vistaConGlobito(this.ruta());
      untracked(() => this.programarGlobito(vista));
    });

    // El botón del globito abre el chat; lo que pidió se hace cuando el chat ya existe.
    effect(() => {
      const chat = this.chat();
      const pedido = this.pendiente();
      if (!chat || !pedido) {
        return;
      }
      untracked(() => {
        this.pendiente.set(null);
        if (pedido === 'explorar') {
          chat.ofrecerFiltros();
        } else if (pedido === 'perfil') {
          chat.preguntar('¿Qué me recomiendas?');
        } else {
          chat.preguntar(`Compara ${this.enComparacion().slice(0, 4).join(' y ')}`);
        }
      });
    });

    inject(DestroyRef).onDestroy(() => this.limpiarRelojes());
  }

  private programarGlobito(vista: VistaConGlobito | null): void {
    this.limpiarRelojes();
    this.vistaDelGlobito.set(null);
    if (!vista || !debeMostrarGlobito(vista, hoyLocal(), leerVistos())) {
      return;
    }
    this.relojes.push(
      setTimeout(() => {
        // En Comparar solo hay algo que resumir con dos juegos o más.
        if (this.abierto() || (vista === 'comparar' && this.enComparacion().length < 2)) {
          return;
        }
        guardarVistos(marcarGlobito(vista, hoyLocal(), leerVistos()));
        this.vistaDelGlobito.set(vista);
        this.relojes.push(setTimeout(() => this.vistaDelGlobito.set(null), DURA_GLOBITO_MS));
      }, ESPERA_GLOBITO_MS),
    );
  }

  private limpiarRelojes(): void {
    this.relojes.forEach(clearTimeout);
    this.relojes = [];
  }

  protected aceptarGlobito(): void {
    const vista = this.vistaDelGlobito();
    this.cerrarGlobito();
    this.pendiente.set(vista);
    this.abierto.set(true);
  }

  protected cerrarGlobito(): void {
    this.limpiarRelojes();
    this.vistaDelGlobito.set(null);
  }

  protected alternar(): void {
    this.cerrarGlobito();
    this.abierto.update((valor) => !valor);
  }

  protected cerrar(): void {
    if (!this.abierto()) {
      return;
    }
    this.abierto.set(false);
    this.burbuja()?.nativeElement.focus();
  }
}
