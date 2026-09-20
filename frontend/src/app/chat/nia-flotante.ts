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
            <h2 class="rotulo-seccion" id="nia-flotante-titulo">Pregúntale a Nia</h2>
            <button type="button" class="boton-texto" data-testid="nia-flotante-cerrar" (click)="cerrar()">
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
        <span aria-hidden="true" class="inicial">N</span>
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
    .burbuja {
      width: 56px;
      height: 56px;
      border-radius: var(--radio-pildora);
      border: 1px solid var(--neon);
      background: var(--superficie-tarjeta);
      color: var(--neon);
      font-size: var(--texto-subheading);
      cursor: pointer;
      transition:
        background var(--duracion-rapida) var(--curva),
        transform var(--duracion-rapida) var(--curva);
    }
    .burbuja:hover {
      background: var(--acento-sistema);
      transform: translateY(-2px);
    }
    .abierto .burbuja {
      background: var(--acento-sistema);
      box-shadow: var(--resplandor);
    }
    .inicial {
      font-weight: var(--peso-titular);
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
