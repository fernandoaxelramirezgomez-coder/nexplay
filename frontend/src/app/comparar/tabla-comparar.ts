import { ChangeDetectionStrategy, Component, computed, effect, inject, input } from '@angular/core';

import { JuegoCatalogo } from '../api/contrato';
import { PildoraBanda } from '../compartido/pildora-banda';
import { ROTULO_RIESGO } from '../dominio/etiqueta-riesgo';
import { lineaCritica, sentimientoSteam } from '../dominio/critica';
import { textoPrecio } from '../dominio/formato';
import { PanoramaStore } from '../estado/panorama-store';
import { MotivosStore } from '../estado/motivos-store';

/** La comparación de un vistazo: una fila por dato y una columna por juego, para leer en
 * horizontal en vez de comparar tres párrafos parecidos uno al lado del otro. Debajo de
 * esta tabla siguen las columnas con la segunda opinión completa. */
@Component({
  selector: 'app-tabla-comparar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [PildoraBanda],
  template: `
    <div class="marco">
      <table data-testid="tabla-comparar" [class.pocos]="juegos().length < 2">
        <caption class="solo-lector">
          Riesgo, motivo principal, precio, crítica y lanzamiento de los juegos en comparación
        </caption>
        <thead>
          <tr>
            <th scope="col"><span class="solo-lector">Dato</span></th>
            @for (juego of juegos(); track juego.appid) {
              <th scope="col" class="juego">{{ juego.nombre }}</th>
            }
          </tr>
        </thead>
        <tbody>
          <tr data-testid="fila-banda">
            <th scope="row">{{ rotulo }}</th>
            @for (juego of juegos(); track juego.appid) {
              <td><app-pildora-banda [banda]="juego.banda_riesgo" [compacta]="true" /></td>
            }
          </tr>
          <tr data-testid="fila-motivo">
            <th scope="row">Motivo principal</th>
            @for (juego of juegos(); track juego.appid) {
              <td>{{ motivo(juego.appid) }}</td>
            }
          </tr>
          <tr data-testid="fila-precio">
            <th scope="row">Precio</th>
            @for (juego of juegos(); track juego.appid) {
              <td class="mono">{{ precio(juego) }}</td>
            }
          </tr>
          <tr data-testid="fila-critica">
            <th scope="row">Crítica</th>
            @for (juego of juegos(); track juego.appid) {
              <td class="critica" [class.sin-critica]="juego.metacritic === null">{{ critica(juego) }}</td>
            }
          </tr>
          <tr data-testid="fila-lanzamiento">
            <th scope="row">Lanzamiento</th>
            @for (juego of juegos(); track juego.appid) {
              <td class="mono">{{ juego.fecha_lanzamiento ?? 'Sin fecha' }}</td>
            }
          </tr>
        </tbody>
      </table>
    </div>
  `,
  styles: `
    /* En panel: sobre la nebulosa, el texto va en superficie. */
    .marco {
      overflow-x: auto;
      border: 1px solid var(--borde);
      border-radius: var(--radio-tarjeta);
      background: var(--superficie);
    }
    .critica {
      font-family: var(--fuente-mono);
      line-height: 1.4;
    }
    .sin-critica {
      color: var(--texto);
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: var(--texto-body-sm);
    }
    /* Con un solo juego la tabla no se estira a todo el ancho: el valor quedaría a media
       pantalla de su etiqueta. */
    table.pocos {
      width: auto;
      min-width: min(100%, 30rem);
    }
    th,
    td {
      padding: var(--espacio-12);
      text-align: start;
      vertical-align: middle;
      border-bottom: var(--filete);
    }
    thead th {
      border-bottom: 1px solid var(--borde-control);
    }
    tbody th {
      color: var(--texto-meta);
      font-weight: var(--peso-regular);
      white-space: nowrap;
    }
    .juego {
      min-width: 12rem;
    }
    td.mono {
      font-family: var(--fuente-mono);
      letter-spacing: 0;
    }
  `,
})
export class TablaComparar {
  readonly juegos = input.required<JuegoCatalogo[]>();

  private readonly motivos = inject(MotivosStore);
  private readonly panorama = inject(PanoramaStore);
  protected readonly rotulo = ROTULO_RIESGO;
  protected readonly precio = textoPrecio;

  /** «Metacritic 82 · Steam 94 % positivas (87,051 reseñas)», o sin Metacritic, lo dice. */
  protected critica(juego: JuegoCatalogo): string {
    return lineaCritica(juego, sentimientoSteam(this.panorama.porAppid().get(juego.appid)));
  }

  constructor() {
    // El motivo principal se pide una vez por juego y queda en caché del store.
    effect(() => this.juegos().forEach((juego) => this.motivos.pedir(juego.appid)));
  }

  protected motivo(appid: number): string {
    const principal = this.motivos.principal(appid);
    if (principal === undefined) {
      return 'Buscando…';
    }
    return principal ?? 'Sin motivos suficientes';
  }
}
