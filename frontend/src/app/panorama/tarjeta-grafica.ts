import { ChangeDetectionStrategy, Component, input, signal } from '@angular/core';

let siguiente = 0;

/** Una gráfica del tablero: qué se ve, qué se concluye con el corte de ahora, de dónde sale
 * y, detrás de la ⓘ, el texto largo. La ayuda se abre dentro de la tarjeta y empuja la
 * gráfica hacia abajo: flotando encima tapaba justo lo que explica.
 *
 * La ⓘ va dibujada, como en nota-info.ts: Inter no tiene el carácter. */
@Component({
  selector: 'app-tarjeta-grafica',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { '[attr.data-testid]': 'idPrueba()', 'data-tarjeta-grafica': '' },
  template: `
    <article class="tarjeta" [attr.aria-labelledby]="idTitulo">
      <header class="cabeza">
        <h3 class="titulo" [id]="idTitulo">{{ titulo() }}</h3>
        <button
          type="button"
          class="info"
          data-testid="tarjeta-info"
          [attr.aria-expanded]="abierta()"
          [attr.aria-controls]="idAyuda"
          [attr.aria-label]="'Cómo se lee: ' + titulo()"
          (click)="abierta.set(!abierta())"
        >
          <svg viewBox="0 0 20 20" width="20" height="20" aria-hidden="true">
            <circle cx="10" cy="10" r="8.25" fill="none" stroke="currentColor" stroke-width="1.5" />
            <circle cx="10" cy="5.9" r="1.1" fill="currentColor" />
            <path d="M10 9.2v5.4" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
          </svg>
        </button>
        <p class="conclusion" data-testid="tarjeta-conclusion" aria-live="polite">{{ conclusion() }}</p>
      </header>
      <div class="ayuda" data-testid="tarjeta-ayuda" [id]="idAyuda" [hidden]="!abierta()">
        <ng-content select="[ayuda]" />
      </div>
      <div class="cuerpo" data-testid="tarjeta-cuerpo">
        <ng-content />
      </div>
      <p class="fuente" data-testid="tarjeta-fuente">Fuente: {{ fuente() }}</p>
    </article>
  `,
  styles: `
    :host {
      display: block;
      min-width: 0;
    }
    .tarjeta {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
      height: 100%;
      box-sizing: border-box;
      padding: 18px 20px 16px;
      border: 1px solid var(--borde);
      border-radius: var(--radio-tarjeta);
      background: var(--superficie);
    }
    .cabeza {
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: var(--espacio-4) var(--espacio-12);
      align-items: start;
    }
    .titulo {
      margin: 0;
      color: var(--accion-tinta);
      font-family: var(--fuente-display);
      font-size: 18px;
      font-weight: 700;
      line-height: 1.2;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }
    .conclusion {
      grid-column: 1;
      margin: 0;
      font-size: 18px;
      font-weight: 600;
      line-height: 1.35;
    }
    .info {
      grid-column: 2;
      grid-row: 1 / span 2;
      display: grid;
      place-items: center;
      width: 44px;
      height: 44px;
      padding: 0;
      border: 1px solid var(--borde-control);
      border-radius: 50%;
      background: var(--superficie-2);
      color: var(--texto);
      cursor: pointer;
    }
    .info:hover,
    .info[aria-expanded='true'] {
      border-color: var(--accion-tinta);
      box-shadow: inset 0 0 0 1px var(--accion-tinta);
    }
    .ayuda {
      padding: var(--espacio-12) 14px;
      border-inline-start: 3px solid var(--accion-tinta);
      border-radius: var(--radio-boton);
      background: var(--superficie-2);
      font-size: var(--texto-body-sm);
      line-height: var(--interlineado-largo);
    }
    .ayuda[hidden] {
      display: none;
    }
    .ayuda ::ng-deep p {
      margin: 0;
    }
    .ayuda ::ng-deep p + p {
      margin-top: var(--espacio-8);
    }
    /* Media tarjeta no da para los 11rem de etiqueta que usa la gráfica a lo ancho. */
    .cuerpo {
      min-width: 0;
      --ancho-etiqueta: 9rem;
    }
    .fuente {
      margin: auto 0 0;
      padding-top: 10px;
      border-top: 1px solid var(--borde);
      color: var(--texto-meta);
      font-size: var(--texto-caption);
      line-height: 1.4;
    }
  `,
})
export class TarjetaGrafica {
  readonly titulo = input.required<string>();
  readonly conclusion = input.required<string>();
  readonly fuente = input.required<string>();
  readonly idPrueba = input<string>();

  protected readonly abierta = signal(false);
  private readonly n = ++siguiente;
  protected readonly idTitulo = `tarjeta-titulo-${this.n}`;
  protected readonly idAyuda = `tarjeta-ayuda-${this.n}`;
}
