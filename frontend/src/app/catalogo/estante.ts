import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { Estante as EstanteDatos } from '../dominio/estantes';
import { TarjetaJuego } from './tarjeta-juego';

@Component({
  selector: 'app-estante',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TarjetaJuego],
  template: `
    <section class="estante" [attr.data-testid]="'estante-' + estante().banda" [attr.aria-labelledby]="idTitulo()">
      <h2 class="titulo" [id]="idTitulo()">
        <span class="punto" [attr.data-banda]="estante().banda" aria-hidden="true"></span>
        Riesgo general · {{ estante().banda }}
        <span class="conteo mono" data-testid="estante-conteo">({{ estante().juegos.length }})</span>
      </h2>
      @if (estante().juegos.length) {
        <ul class="rejilla">
          @for (juego of estante().juegos; track juego.appid; let i = $index) {
            <li><app-tarjeta-juego [juego]="juego" [prioritaria]="prioritario() && i < 4" /></li>
          }
        </ul>
      } @else {
        <p class="meta">Ningún juego de esta banda coincide con el filtro.</p>
      }
    </section>
  `,
  styles: `
    .estante {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-16);
    }
    .titulo {
      display: flex;
      align-items: center;
      gap: var(--espacio-12);
      font-size: var(--texto-subheading);
    }
    .punto {
      width: 10px;
      height: 10px;
      border-radius: 50%;
    }
    .punto[data-banda='bajo'] {
      background: var(--banda-bajo);
    }
    .punto[data-banda='medio'] {
      background: var(--banda-medio);
    }
    .punto[data-banda='alto'] {
      background: var(--banda-alto);
    }
    .conteo {
      color: var(--texto-meta);
      font-size: var(--texto-body-sm);
    }
    .rejilla {
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: var(--espacio-16);
    }
  `,
})
export class Estante {
  readonly estante = input.required<EstanteDatos>();
  /** Solo el primer estante carga sus primeras portadas sin esperar al scroll. */
  readonly prioritario = input(false);

  protected idTitulo(): string {
    return `estante-${this.estante().banda}-titulo`;
  }
}
