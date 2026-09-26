import { ChangeDetectionStrategy, Component, input } from '@angular/core';

/** La explicación que no hace falta leer cada vez, detrás de una ⓘ. Es un <details>: sin
 * JavaScript, se abre con teclado y los lectores de pantalla ya saben contarlo.
 *
 * La ⓘ va dibujada y no escrita: como carácter (U+24D8) depende de la fuente que toque, e
 * Inter no lo tiene, así que en el veredicto salía la caja vacía del glifo que falta
 * mientras en los rótulos, en la mono, se veía bien. Dibujada es la misma en todas. */
@Component({
  selector: 'app-nota-info',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <details class="nota" [attr.data-testid]="idPrueba()">
      <summary [attr.aria-label]="etiqueta()">
        <svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true">
          <circle cx="10" cy="10" r="8.25" fill="none" stroke="currentColor" stroke-width="1.4" />
          <circle cx="10" cy="5.9" r="1.05" fill="currentColor" />
          <path d="M10 9.2v5.4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
        </svg>
      </summary>
      <div class="cuerpo meta">
        <ng-content />
      </div>
    </details>
  `,
  styles: `
    .nota {
      display: inline-block;
    }
    /* El texto de la nota no hereda de donde esté: dentro de .rotulo-seccion salía en
       mono, en mayúsculas y con tracking, aunque no sea un rótulo sino una explicación. */
    .cuerpo {
      font-family: var(--fuente-texto);
      text-transform: none;
      letter-spacing: normal;
    }
    summary {
      display: inline-grid;
      place-items: center;
      width: 22px;
      height: 22px;
      border-radius: 50%;
      color: var(--texto-meta);
      cursor: pointer;
      list-style: none;
    }
    summary::-webkit-details-marker {
      display: none;
    }
    summary:hover {
      color: var(--neon);
    }
    summary:focus-visible {
      outline: 2px solid var(--foco);
      outline-offset: 2px;
    }
    .cuerpo {
      display: block;
      margin-top: var(--espacio-8);
      padding: var(--espacio-12);
      border: 1px solid var(--linea);
      border-radius: var(--radio-tarjeta);
      background: var(--superficie-tarjeta);
      max-width: var(--medida-lectura);
      line-height: var(--interlineado-largo);
    }
    /* Dentro de un flujo de texto el detalle no puede quedar de 22 px: al abrirse ocupa
       el ancho que tenga disponible. */
    .nota[open] {
      display: block;
    }
  `,
})
export class NotaInfo {
  /** Qué explica, para quien no ve la ⓘ. */
  readonly etiqueta = input('Más información');
  readonly idPrueba = input('nota-info');
}
