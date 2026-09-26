import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { rangoDeFechas } from '../dominio/formato';
import { PanoramaStore } from '../estado/panorama-store';

/** El pie de todas las vistas: de dónde salen los datos y cuándo se bajaron, en una línea,
 * y los enlaces a Fuentes y a la metodología. El texto de las dos vive en /como-funciona,
 * una sola vez. Va en panel: el pie queda sobre la nebulosa, y el enlace de color directo
 * sobre ella no llegaba a 4.5:1 en el tema claro. */
@Component({
  selector: 'app-pie',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <div class="panel-pie" data-testid="pie-fuentes">
      <p class="linea" data-testid="pie-linea">
        Fuentes: Steam (appreviews y appdetails) y Metacritic{{ descarga() ? ', descargadas ' + descarga() : '' }}.
      </p>
      <a class="boton-texto" routerLink="/como-funciona" fragment="titulo-fuentes" data-testid="enlace-fuentes">
        Ver fuentes →
      </a>
      <a
        class="compacto"
        data-tono="neutro"
        routerLink="/como-funciona"
        fragment="titulo-metodologia"
        data-testid="enlace-metodologia"
      >
        Metodología: cómo se calcula el riesgo →
      </a>
    </div>
  `,
  styles: `
    .panel-pie {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--espacio-8) var(--espacio-16);
      padding: 14px 18px;
      border: 1px solid var(--borde);
      border-radius: var(--radio-tarjeta);
      background: var(--superficie);
    }
    .linea {
      margin: 0;
      font-size: var(--texto-body-sm);
      line-height: 1.4;
    }
  `,
})
export class Pie {
  private readonly panorama = inject(PanoramaStore);

  /** Del primer al último registro de las dos fuentes: la nota de Metacritic llega con
   * appdetails, así que no tiene fecha propia. */
  protected readonly descarga = computed(() => {
    const descargas = this.panorama.datos()?.descargas;
    if (!descargas) {
      return '';
    }
    const desde = [descargas.appdetails.desde, descargas.appreviews.desde].filter(Boolean).sort()[0];
    const hasta = [descargas.appdetails.hasta, descargas.appreviews.hasta].filter(Boolean).sort().at(-1);
    return desde && hasta ? rangoDeFechas(desde, hasta) : '';
  });
}
