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

import { FICHAS_BURBUJA, SALUDO_BURBUJA } from '../dominio/textos-nia';
import { CatalogoStore } from '../estado/catalogo-store';
import { CompararStore } from '../estado/comparar-store';
import { NiaBurbujaStore } from '../estado/nia-burbuja-store';
import { Nia } from './nia';

/** Cuánto hay que desplazarse para que la burbuja reaccione, y a qué distancia del final
 * vuelve aunque se siga bajando: ahí la página ya le dejó su espacio vacío. */
const UMBRAL_DESPLAZAMIENTO = 8;
const CERCA_DEL_FINAL = 120;

/** Nia en la esquina, en todas las vistas menos la ficha y la suya. Al abrirse saluda y
 * conversa sobre el catálogo; si hace falta un juego, lo pide dentro del chat.
 *
 * Lo que cada vista ofrece de Nia va en su franja (chat/franja-nia.ts), dentro de la
 * página: flotando tapaba columnas y tarjetas. El botón de la franja abre esta burbuja
 * por NiaBurbujaStore.
 *
 * En pantallas angostas la burbuja se esconde mientras se baja y vuelve al subir o al
 * llegar al final: fija en la esquina, siempre caía sobre algún texto. */
@Component({
  selector: 'app-nia-flotante',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Nia],
  // La burbuja es de Nia en cualquier vista: su anillo y sus botones van en su violeta,
  // no en el color de la vista donde está.
  host: { 'data-vista': 'nia' },
  template: `
    <div
      class="flotante"
      [class.abierto]="abierto()"
      [class.oculta]="oculta() && !abierto()"
      data-testid="nia-flotante"
      [attr.data-oculta]="oculta() && !abierto()"
      (document:keydown.escape)="cerrar()"
    >
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
          <app-nia
            [appid]="null"
            [muestraTitulo]="false"
            [muestraIntro]="false"
            [llenaAlto]="true"
            [saludo]="saludo"
            [fichas]="fichas"
          />
        </div>
      }

      <button
        type="button"
        class="burbuja"
        data-testid="nia-flotante-burbuja"
        [attr.aria-expanded]="abierto()"
        [attr.aria-label]="abierto() ? 'Cerrar el chat de Nia' : 'Abrir el chat de Nia'"
        [attr.tabindex]="oculta() && !abierto() ? -1 : null"
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
      transition:
        transform var(--duracion) var(--curva),
        opacity var(--duracion) var(--curva);
    }
    /* Escondida baja fuera de la pantalla: sigue en el DOM, pero no recibe toques. */
    .flotante.oculta {
      transform: translateY(calc(100% + var(--espacio-16) + var(--elevacion-burbuja, 0px)));
      opacity: 0;
      pointer-events: none;
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
    @media (prefers-reduced-motion: reduce) {
      .flotante {
        transition: none;
      }
      .burbuja {
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
    /* La conversación se desplaza por dentro y el campo de escribir se queda abajo, a la
       vista: antes se desplazaba el panel entero y el campo se iba con la conversación. */
    .panel {
      width: min(400px, calc(100vw - var(--espacio-48)));
      max-height: min(72vh, 600px);
      overflow: hidden;
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
    }
    .panel > app-nia {
      display: flex;
      flex-direction: column;
      flex: 1 1 auto;
      min-height: 0;
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
  private readonly catalogo = inject(CatalogoStore);
  private readonly comparar = inject(CompararStore);
  private readonly pedidos = inject(NiaBurbujaStore);
  private readonly burbuja = viewChild<ElementRef<HTMLButtonElement>>('burbuja');
  private readonly chat = viewChild(Nia);

  protected readonly saludo = SALUDO_BURBUJA;
  protected readonly fichas = FICHAS_BURBUJA;

  protected readonly abierto = signal(false);
  /** Escondida porque se está bajando en una pantalla angosta. */
  protected readonly oculta = signal(false);

  /** Los nombres de lo que hay en Comparar, para resumirlo. */
  private readonly enComparacion = computed(() => {
    const porAppid = this.catalogo.porAppid();
    return this.comparar
      .appids()
      .map((appid) => porAppid.get(appid)?.nombre)
      .filter((nombre): nombre is string => !!nombre);
  });

  constructor() {
    // El botón de una franja abre el chat; lo que pidió se hace cuando el chat ya existe.
    effect(() => {
      const pedido = this.pedidos.pedido();
      if (!pedido) {
        return;
      }
      untracked(() => this.abierto.set(true));
      const chat = this.chat();
      if (!chat) {
        return;
      }
      untracked(() => {
        this.pedidos.atendido();
        if (pedido === 'explorar') {
          chat.ofrecerFiltros();
        } else if (pedido === 'perfil') {
          chat.preguntar('¿Qué me recomiendas?');
        } else {
          chat.preguntar(`Compara ${this.enComparacion().slice(0, 4).join(' y ')}`);
        }
      });
    });

    this.esconderAlBajar();
  }

  private esconderAlBajar(): void {
    if (typeof window === 'undefined' || typeof matchMedia !== 'function') {
      return;
    }
    const angosta = matchMedia('(max-width: 640px)');
    let ultimo = window.scrollY;
    const alDesplazar = () => {
      const y = window.scrollY;
      const delta = y - ultimo;
      if (Math.abs(delta) < UMBRAL_DESPLAZAMIENTO) {
        return;
      }
      ultimo = y;
      const alFinal = y + window.innerHeight >= document.documentElement.scrollHeight - CERCA_DEL_FINAL;
      this.oculta.set(angosta.matches && delta > 0 && !alFinal);
    };
    const alCambiarAncho = () => this.oculta.set(false);
    window.addEventListener('scroll', alDesplazar, { passive: true });
    // Con ?.: el matchMedia de las pruebas no trae los listeners.
    angosta.addEventListener?.('change', alCambiarAncho);
    inject(DestroyRef).onDestroy(() => {
      window.removeEventListener('scroll', alDesplazar);
      angosta.removeEventListener?.('change', alCambiarAncho);
    });
  }

  protected alternar(): void {
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
