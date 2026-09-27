import { ChangeDetectionStrategy, Component, ElementRef, afterNextRender, computed, inject, output, signal, viewChild } from '@angular/core';

import { JuegoCatalogo } from '../api/contrato';
import { PildoraBanda } from '../compartido/pildora-banda';
import { Portada } from '../compartido/portada';
import { filtrarJuegos } from '../dominio/filtros';
import { CatalogoStore } from '../estado/catalogo-store';

const MAXIMO_RESULTADOS = 5;

/** El buscador que Nia pone dentro de su mensaje cuando la pregunta es de un juego y no
 * hay ninguno fijado. Elegir uno lo fija en el chat y responde la pregunta pendiente. */
@Component({
  selector: 'app-elegir-juego-chat',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Portada, PildoraBanda],
  template: `
    <div class="elegir" data-testid="nia-elegir-juego">
      <label class="buscar">
        <span class="solo-lector">Busca el juego del que quieres hablar</span>
        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
        <input
          #campo
          type="search"
          autocomplete="off"
          placeholder="Busca por nombre…"
          data-testid="nia-elegir-buscar"
          [value]="texto()"
          (input)="texto.set($any($event.target).value)"
        />
      </label>
      @if (texto().trim()) {
        <ul class="resultados">
          @for (juego of resultados(); track juego.appid) {
            <li>
              <button type="button" class="resultado" data-testid="nia-elegir-resultado" (click)="elegido.emit(juego)">
                <app-portada class="mini" [src]="juego.portada_url" radio="6px" />
                <span class="nombre">{{ juego.nombre }}</span>
                <app-pildora-banda [banda]="juego.banda_riesgo" [compacta]="true" />
              </button>
            </li>
          } @empty {
            <li class="vacio">Ningún juego del catálogo se llama así.</li>
          }
        </ul>
      }
    </div>
  `,
  styles: `
    .elegir {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-8);
      margin-top: var(--espacio-8);
    }
    .buscar {
      display: flex;
      align-items: center;
      gap: var(--espacio-8);
      min-height: 44px;
      padding: 0 var(--espacio-12);
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-boton);
      background: var(--superficie);
    }
    .buscar svg {
      width: 18px;
      height: 18px;
      flex: none;
      fill: none;
      stroke: var(--texto-meta);
      stroke-width: 2;
      stroke-linecap: round;
    }
    .buscar input {
      flex: 1;
      min-width: 0;
      min-height: 42px;
      border: 0;
      background: transparent;
      color: var(--texto);
      font: inherit;
      font-size: 17px;
      outline: none;
    }
    .buscar:focus-within {
      border-color: var(--info);
      box-shadow: 0 0 0 2px color-mix(in srgb, var(--info) 35%, transparent);
    }
    .resultados {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .resultado {
      display: flex;
      align-items: center;
      gap: 10px;
      width: 100%;
      min-height: 44px;
      padding: 4px 8px;
      border: 1px solid var(--borde);
      border-radius: var(--radio-boton);
      background: var(--superficie);
      color: var(--texto);
      font: inherit;
      font-size: var(--texto-body-sm);
      text-align: start;
      cursor: pointer;
    }
    .resultado:hover,
    .resultado:focus-visible {
      border-color: var(--info);
    }
    .mini {
      width: 64px;
      flex: none;
    }
    .nombre {
      flex: 1;
      min-width: 0;
    }
    .vacio {
      color: var(--texto-meta);
      font-size: var(--texto-body-sm);
    }
  `,
})
export class ElegirJuegoChat {
  readonly elegido = output<JuegoCatalogo>();

  private readonly catalogo = inject(CatalogoStore);
  private readonly campo = viewChild<ElementRef<HTMLInputElement>>('campo');
  protected readonly texto = signal('');

  protected readonly resultados = computed(() =>
    filtrarJuegos(this.catalogo.juegos(), { texto: this.texto(), generos: [] }).slice(0, MAXIMO_RESULTADOS),
  );

  constructor() {
    // Nia acaba de pedir el juego: el foco va al buscador, sin tener que buscarlo.
    afterNextRender(() => this.campo()?.nativeElement.focus({ preventScroll: true }));
  }
}
