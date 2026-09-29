import { ChangeDetectionStrategy, Component, computed, effect, inject, input, signal, untracked } from '@angular/core';

import { CLAVE_GLOBITOS, GlobitosVistos, debeMostrarGlobito, hoyLocal, marcarGlobito } from '../dominio/globito-nia';
import { VistaConGlobito, textoGlobito } from '../dominio/textos-nia';
import { NiaBurbujaStore } from '../estado/nia-burbuja-store';

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
    // Sin almacenamiento la franja puede volver a salir; no es motivo para fallar.
  }
}

/** Lo que Nia ofrece en Explorar, Comparar y Tu perfil, en una franja dentro de la vista.
 * Antes era un globito que flotaba junto a la burbuja y tapaba columnas y tarjetas; aquí
 * ocupa su propio lugar. Sale una vez al día por vista, se queda mientras dura la visita
 * (irse sola movería la página) y la × la cierra hasta el día siguiente. Su botón abre la
 * burbuja con lo que ofrecía. */
@Component({
  selector: 'app-franja-nia',
  changeDetection: ChangeDetectionStrategy.OnPush,
  // En su violeta en cualquier vista, como la burbuja.
  host: { 'data-vista': 'nia' },
  template: `
    @if (visible()) {
      <aside class="franja" aria-label="Nia" data-testid="franja-nia" [attr.data-franja]="vista()">
        <img class="avatar" src="nia/chat.png" alt="" width="200" height="233" />
        <p class="texto">{{ mensaje().texto }}</p>
        <button type="button" class="compacto accion" data-testid="franja-nia-accion" (click)="aceptar()">
          {{ mensaje().accion }}
        </button>
        <button
          type="button"
          class="cerrar"
          aria-label="Cerrar el mensaje de Nia"
          data-testid="franja-nia-cerrar"
          (click)="cerrada.set(true)"
        >
          ×
        </button>
      </aside>
    }
  `,
  styles: `
    :host {
      display: block;
    }
    .franja {
      display: flex;
      align-items: center;
      gap: var(--espacio-12) var(--espacio-16);
      padding: var(--espacio-8) var(--espacio-8) var(--espacio-8) var(--espacio-16);
      border: 1px solid color-mix(in srgb, var(--neon) var(--mezcla-filo), var(--superficie));
      border-radius: var(--radio-tarjeta);
      background: var(--superficie);
    }
    .avatar {
      flex: none;
      width: 48px;
      height: 48px;
      padding: 3px 3px 0;
      object-fit: contain;
      object-position: center bottom;
      border-radius: 50%;
      background: var(--superficie-lienzo);
      box-shadow: 0 0 0 1px var(--neon);
    }
    .texto {
      flex: 1;
      min-width: 0;
      margin: 0;
      color: var(--texto);
      font-size: var(--texto-body);
      line-height: 1.4;
    }
    .accion {
      flex: none;
      min-height: 44px;
    }
    .cerrar {
      flex: none;
      width: 44px;
      height: 44px;
      display: grid;
      place-items: center;
      padding: 0;
      border: 0;
      border-radius: 50%;
      background: transparent;
      color: var(--texto-meta);
      font-size: 24px;
      cursor: pointer;
    }
    .cerrar:hover {
      color: var(--texto);
    }
    .cerrar:focus-visible {
      outline: 2px solid var(--foco);
      outline-offset: 2px;
    }
    /* Angosta: el texto arriba a todo lo ancho y el botón debajo, con la × en su esquina. */
    @media (max-width: 640px) {
      .franja {
        display: grid;
        grid-template-columns: auto minmax(0, 1fr) auto;
        grid-template-areas:
          'avatar texto cerrar'
          'accion accion accion';
        padding: var(--espacio-12);
      }
      .avatar {
        grid-area: avatar;
      }
      .texto {
        grid-area: texto;
      }
      .cerrar {
        grid-area: cerrar;
        align-self: start;
      }
      .accion {
        grid-area: accion;
        width: 100%;
      }
    }
  `,
})
export class FranjaNia {
  readonly vista = input.required<VistaConGlobito>();
  /** Si la vista tiene algo que ofrecer ahora: Comparar con dos juegos, Perfil con perfil. */
  readonly disponible = input(true);
  /** Cuántos juegos hay en Comparar, para el texto. */
  readonly cuantos = input(0);

  private readonly pedidos = inject(NiaBurbujaStore);

  protected readonly cerrada = signal(false);
  /** Se decide una vez por visita: marcarla como vista no la esconde mientras sigue aquí. */
  private readonly tocaHoy = computed(() => debeMostrarGlobito(this.vista(), hoyLocal(), leerVistos()));

  protected readonly visible = computed(() => this.disponible() && this.tocaHoy() && !this.cerrada());
  protected readonly mensaje = computed(() => textoGlobito(this.vista(), this.cuantos()));

  constructor() {
    effect(() => {
      if (this.visible()) {
        const vista = this.vista();
        untracked(() => guardarVistos(marcarGlobito(vista, hoyLocal(), leerVistos())));
      }
    });
  }

  protected aceptar(): void {
    this.pedidos.pedir(this.vista());
    this.cerrada.set(true);
  }
}
