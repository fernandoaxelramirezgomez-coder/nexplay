import { ChangeDetectionStrategy, Component, ElementRef, input, viewChild } from '@angular/core';

import { Estante as EstanteDatos } from '../dominio/estantes';
import { TarjetaJuego } from './tarjeta-juego';

@Component({
  selector: 'app-estante',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TarjetaJuego],
  template: `
    <section class="estante" [attr.data-testid]="'estante-' + estante().banda" [attr.aria-labelledby]="idTitulo()">
      <header class="cabecera">
        <h2 class="titulo" [id]="idTitulo()">
          <span class="banda" [attr.data-banda]="estante().banda">Riesgo general · {{ estante().banda }}</span>
          <span class="conteo mono" data-testid="estante-conteo">({{ estante().juegos.length }})</span>
        </h2>
        @if (estante().juegos.length) {
          <div class="controles">
            <button type="button" [attr.aria-label]="'Ver juegos anteriores de riesgo ' + estante().banda" (click)="desplazar(-1)">
              <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
                <path d="M15 5 8 12l7 7" fill="none" stroke="currentColor" stroke-width="2" />
              </svg>
            </button>
            <button type="button" [attr.aria-label]="'Ver más juegos de riesgo ' + estante().banda" (click)="desplazar(1)">
              <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
                <path d="m9 5 7 7-7 7" fill="none" stroke="currentColor" stroke-width="2" />
              </svg>
            </button>
          </div>
        }
      </header>

      @if (estante().juegos.length) {
        <ul class="fila" #fila>
          @for (juego of estante().juegos; track juego.appid; let i = $index) {
            <li><app-tarjeta-juego [juego]="juego" [prioritaria]="prioritario() && i < 5" /></li>
          }
        </ul>
      } @else {
        <p class="meta">Ningún juego de esta banda coincide con la búsqueda.</p>
      }
    </section>
  `,
  styles: `
    .estante {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
    }
    .cabecera {
      display: flex;
      align-items: center;
      gap: var(--espacio-12);
    }
    .titulo {
      display: flex;
      align-items: center;
      gap: var(--espacio-12);
      font-size: var(--texto-body);
    }
    .banda {
      padding: 2px var(--espacio-12);
      border-radius: var(--radio-pildora);
      color: var(--texto-sobre-banda);
      font-size: var(--texto-body-sm);
    }
    .banda[data-banda='bajo'] {
      background: var(--banda-bajo);
    }
    .banda[data-banda='medio'] {
      background: var(--banda-medio);
    }
    .banda[data-banda='alto'] {
      background: var(--banda-alto);
    }
    .conteo {
      color: var(--texto-meta);
      font-size: var(--texto-body-sm);
    }
    .controles {
      margin-inline-start: auto;
      display: flex;
      gap: var(--espacio-8);
    }
    .controles button {
      width: 44px;
      height: 44px;
      display: grid;
      place-items: center;
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-pildora);
      background: transparent;
      color: var(--texto);
      cursor: pointer;
      transition: border-color var(--duracion-rapida) var(--curva);
    }
    .controles button:hover {
      border-color: var(--neon);
    }
    /* Estante horizontal: las tres bandas caben casi sin bajar. */
    .fila {
      list-style: none;
      margin: 0;
      padding: 0 var(--espacio-4) var(--espacio-8);
      display: grid;
      grid-auto-flow: column;
      grid-auto-columns: 296px;
      gap: var(--espacio-16);
      overflow-x: auto;
      scroll-snap-type: x proximity;
      /* Sin barra visible; el trackpad, el teclado y las flechas siguen desplazando. */
      scrollbar-width: none;
      -ms-overflow-style: none;
    }
    .fila::-webkit-scrollbar {
      display: none;
    }
    .fila > li {
      scroll-snap-align: start;
    }
    @media (max-width: 640px) {
      .fila {
        grid-auto-columns: 78vw;
      }
      .controles {
        display: none;
      }
    }
  `,
})
export class Estante {
  readonly estante = input.required<EstanteDatos>();
  /** El primer estante carga sus primeras portadas sin esperar al scroll. */
  readonly prioritario = input(false);

  private readonly fila = viewChild<ElementRef<HTMLElement>>('fila');

  protected idTitulo(): string {
    return `estante-${this.estante().banda}-titulo`;
  }

  protected desplazar(sentido: 1 | -1): void {
    const fila = this.fila()?.nativeElement;
    if (!fila) {
      return;
    }
    const sinMovimiento = matchMedia('(prefers-reduced-motion: reduce)').matches;
    fila.scrollBy({ left: sentido * fila.clientWidth * 0.8, behavior: sinMovimiento ? 'auto' : 'smooth' });
  }
}
