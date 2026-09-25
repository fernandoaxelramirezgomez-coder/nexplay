import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  computed,
  effect,
  inject,
  signal,
  viewChild,
} from '@angular/core';

import { JuegoCatalogo } from '../api/contrato';
import { Portada } from '../compartido/portada';
import { filtrarJuegos } from '../dominio/filtros';
import { CatalogoStore } from '../estado/catalogo-store';
import { Nia } from './nia';

const MAXIMO_SUGERENCIAS = 6;

/** Nia en la esquina, para las pantallas donde no hay un juego abierto. La API responde
 * siempre sobre un juego concreto, así que lo primero que hace el panel es preguntar de
 * cuál hablar; elegido, monta el mismo chat de la ficha. */
@Component({
  selector: 'app-nia-flotante',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Nia, Portada],
  template: `
    <div class="flotante" [class.abierto]="abierto()" (document:keydown.escape)="cerrar()">
      @if (abierto()) {
        <div
          class="panel superficie"
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

          @if (elegido(); as juego) {
            <div class="elegido">
              <p class="meta mono" data-testid="nia-flotante-juego">{{ juego.nombre }}</p>
              <button type="button" class="boton-texto" data-testid="nia-flotante-cambiar" (click)="soltarJuego()">
                Cambiar de juego
              </button>
            </div>
            <app-nia [appid]="juego.appid" [muestraTitulo]="false" />
          } @else {
            <p class="meta intro">
              Nia responde con los datos de un juego. Dime de cuál quieres hablar.
            </p>
            <label class="buscar">
              <span class="solo-lector">Busca el juego del que quieres hablar</span>
              <input
                type="search"
                autocomplete="off"
                placeholder="Busca por nombre…"
                data-testid="nia-flotante-buscar"
                #buscador
                [value]="texto()"
                (input)="texto.set($any($event.target).value)"
              />
            </label>
            <ul class="sugerencias" data-testid="nia-flotante-sugerencias">
              @for (juego of sugerencias(); track juego.appid) {
                <li>
                  <button type="button" class="sugerencia" data-testid="nia-flotante-sugerencia" (click)="elegir(juego)">
                    <app-portada class="miniatura" [src]="juego.portada_url" />
                    <span class="nombre">{{ juego.nombre }}</span>
                  </button>
                </li>
              } @empty {
                <li class="meta vacio" data-testid="nia-flotante-vacio">Ningún juego del catálogo se llama así.</li>
              }
            </ul>
          }
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
    .flotante {
      position: fixed;
      right: max(var(--espacio-24), env(safe-area-inset-right));
      bottom: max(var(--espacio-24), env(safe-area-inset-bottom));
      z-index: 20;
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: var(--espacio-12);
    }
    /* La burbuja es la cara de Nia dentro de un anillo neón que respira despacio: se
       nota que está ahí sin reclamar atención. Al abrirse, el anillo se queda encendido. */
    .burbuja {
      width: 80px;
      height: 80px;
      padding: 3px;
      border: 2px solid var(--neon);
      border-radius: 50%;
      background: var(--superficie-lienzo);
      cursor: pointer;
      animation: respirar-anillo 4.5s ease-in-out infinite;
      transition: transform var(--duracion-rapida) var(--curva);
    }
    @keyframes respirar-anillo {
      0%,
      100% {
        box-shadow:
          0 0 0 0 rgb(var(--neon-canal) / 0),
          0 0 6px rgb(var(--neon-canal) / calc(0.25 * var(--halo-alfa)));
      }
      50% {
        box-shadow:
          0 0 0 3px rgb(var(--neon-canal) / calc(0.12 * var(--halo-alfa))),
          0 0 calc(14px * var(--halo-radio)) rgb(var(--neon-canal) / calc(0.45 * var(--halo-alfa)));
      }
    }
    .burbuja:hover {
      transform: translateY(-2px) scale(1.04);
    }
    .abierto .burbuja {
      animation: none;
      box-shadow: var(--resplandor);
    }
    /* Nia saludando (Wave, de la hoja v2): el sprite entero cabe en el círculo. */
    .avatar {
      display: block;
      width: 100%;
      height: 100%;
      padding: 5px 5px 0;
      object-fit: contain;
      object-position: center bottom;
      border-radius: 50%;
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
      .burbuja {
        animation: none;
      }
    }
    /* En móvil el margen baja a 16 px, el mismo de la página, siempre por dentro del área
       segura. Abierto, el panel toma el ancho entre los dos márgenes, centrado. */
    @media (max-width: 640px) {
      .flotante {
        right: calc(var(--espacio-16) + env(safe-area-inset-right));
        bottom: calc(var(--espacio-16) + env(safe-area-inset-bottom));
      }
      .flotante.abierto {
        left: calc(var(--espacio-16) + env(safe-area-inset-left));
      }
      .abierto .panel {
        width: 100%;
      }
    }
    .panel {
      width: min(380px, calc(100vw - var(--espacio-48)));
      max-height: min(70vh, 560px);
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
    }
    .cabecera,
    .elegido {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: var(--espacio-12);
    }
    .elegido p {
      margin: 0;
      color: var(--texto);
    }
    .intro {
      margin: 0;
      line-height: var(--interlineado-largo);
    }
    .buscar {
      display: flex;
      flex-direction: column;
    }
    input {
      min-height: 44px;
      font: inherit;
      letter-spacing: inherit;
      color: var(--texto);
      background: var(--superficie-lienzo);
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-pildora);
      padding: var(--espacio-8) var(--espacio-16);
      transition: border-color var(--duracion-rapida) var(--curva);
    }
    input:hover,
    input:focus {
      border-color: var(--neon);
    }
    .sugerencias {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: var(--espacio-4);
    }
    .sugerencia {
      width: 100%;
      min-height: 44px;
      display: flex;
      align-items: center;
      gap: var(--espacio-12);
      padding: var(--espacio-4);
      border: 0;
      border-radius: var(--radio-tarjeta);
      background: none;
      color: var(--texto);
      text-align: start;
      cursor: pointer;
      transition: background var(--duracion-rapida) var(--curva);
    }
    .sugerencia:hover {
      background: var(--superficie-tarjeta-hover);
    }
    .miniatura {
      flex: 0 0 72px;
    }
    .nombre {
      font-size: var(--texto-caption);
    }
    .vacio {
      padding: var(--espacio-8) 0;
    }
    /* En móvil solo queda la burbuja hasta que se abre; el panel ocupa el ancho útil. */
    @media (max-width: 640px) {
      .panel {
        width: calc(100vw - var(--espacio-24));
      }
    }
  `,
})
export class NiaFlotante {
  private readonly catalogo = inject(CatalogoStore);
  private readonly burbuja = viewChild<ElementRef<HTMLButtonElement>>('burbuja');
  private readonly buscador = viewChild<ElementRef<HTMLInputElement>>('buscador');

  protected readonly abierto = signal(false);
  protected readonly texto = signal('');
  protected readonly elegido = signal<JuegoCatalogo | null>(null);

  protected readonly sugerencias = computed(() =>
    filtrarJuegos(this.catalogo.juegos(), { texto: this.texto(), genero: '' }).slice(0, MAXIMO_SUGERENCIAS),
  );

  constructor() {
    // Al abrir, el foco entra al buscador: quien navega con teclado no tiene que
    // recorrer la página entera para llegar.
    effect(() => {
      if (this.abierto()) {
        this.buscador()?.nativeElement.focus();
      }
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

  protected elegir(juego: JuegoCatalogo): void {
    this.elegido.set(juego);
    this.texto.set('');
  }

  protected soltarJuego(): void {
    this.elegido.set(null);
  }
}
