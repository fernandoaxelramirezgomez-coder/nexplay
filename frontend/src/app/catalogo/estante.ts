import { ChangeDetectionStrategy, Component, ElementRef, input, viewChild } from '@angular/core';

import { ROTULO_RIESGO } from '../dominio/etiqueta-riesgo';
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
          <span class="banda" [attr.data-banda]="estante().banda">{{ rotulo }}: {{ estante().banda }}</span>
          <span class="conteo mono" data-testid="estante-conteo">({{ estante().juegos.length }})</span>
        </h2>
        @if (estante().juegos.length > 1) {
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
        <p class="meta">Ningún juego con este riesgo coincide con la búsqueda.</p>
      }
    </section>
  `,
  styles: `
    .estante {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-4);
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
      padding: 1px 11px;
      border: 1px solid var(--filo-banda);
      border-radius: var(--radio-pildora);
      color: var(--texto-sobre-banda);
      font-size: var(--texto-body-sm);
    }
    .banda[data-banda='bajo'] {
      background: var(--banda-bajo);
      --filo-banda: var(--banda-bajo-texto);
    }
    .banda[data-banda='medio'] {
      background: var(--banda-medio);
      --filo-banda: var(--banda-medio-texto);
    }
    .banda[data-banda='alto'] {
      background: var(--banda-alto);
      --filo-banda: var(--banda-alto-texto);
    }
    .conteo {
      color: var(--texto-meta);
      font-size: var(--texto-body-sm);
    }
    /* Junto al conteo, no pegadas al borde derecho: ahí es donde se posa la burbuja de
       Nia y las flechas quedaban debajo de ella a media página. */
    .controles {
      margin-inline-end: auto;
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
    /* El padding deja ver el resplandor de las portadas, que sale de las tarjetas (arriba
       sube 40 px: con menos, la fila lo cortaba en recto); el margen negativo devuelve la
       primera tarjeta a la línea del título. */
    .fila {
      list-style: none;
      margin: 0 calc(-1 * var(--espacio-24));
      padding: var(--espacio-40) var(--espacio-24) var(--espacio-24);
      scroll-padding-inline: var(--espacio-24);
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
    /* La fila termina antes de la columna de la burbuja de Nia (64 px más su margen): la
       tarjeta que queda cortada contra el borde tenía su píldora "Comparar" justo debajo,
       y al bajar por el catálogo cada estante la pasaba por ahí. En teléfono la fila es
       de una tarjeta y media y no llega a esa esquina. */
    @media (min-width: 641px) {
      .fila {
        margin-inline-end: calc(64px - var(--espacio-24));
      }
    }
    /* En teléfono la página tiene 16 px de margen y no 24: el sangrado de la fila también,
       o se saldría de la pantalla. */
    @media (max-width: 640px) {
      .fila {
        grid-auto-columns: 78vw;
        margin-inline: calc(-1 * var(--espacio-16));
        padding-inline: var(--espacio-16);
        scroll-padding-inline: var(--espacio-16);
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

  protected readonly rotulo = ROTULO_RIESGO;

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
