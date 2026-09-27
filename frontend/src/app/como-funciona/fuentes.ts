import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';

import { numero, rangoDeFechas } from '../dominio/formato';
import { ClaveOrigen, ENTRENAMIENTO, ORIGENES, SERVICIOS } from '../dominio/fuentes';
import { CatalogoStore } from '../estado/catalogo-store';
import { PanoramaStore } from '../estado/panorama-store';

/** Las fuentes de los datos, una fila por fuente: qué da, cuánto y cuándo se descargó, con
 * su enlace. Debajo, en dos líneas, los servicios que usa la app y con qué se entrenó el
 * modelo. Las cifras y las fechas salen de la API; si /panorama no responde, la fila se
 * queda con lo que no depende de ella. Lleva su propio contenedor: vive en el pie, fuera
 * de «contenido». Una fuente que se sume (IGDB, si pasa su cobertura) entra como fila. */
@Component({
  selector: 'app-fuentes',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="fuentes" data-testid="fuentes" aria-labelledby="titulo-fuentes">
      <h2 class="rotulo" id="titulo-fuentes">Fuentes</h2>
      <ul class="filas">
        @for (origen of origenes; track origen.clave) {
          <li class="fila" data-testid="fuente">
            <p class="quien">
              <strong>{{ origen.quien }}</strong>
              <span class="sobre">{{ origen.sobre }}</span>
            </p>
            <p class="da">{{ origen.da }}</p>
            <p class="cuanto mono">{{ cuanto()[origen.clave] ?? '' }}</p>
            <p class="cuando" data-testid="fuente-descarga">{{ descarga()[origen.clave] ?? '' }}</p>
            <a [href]="origen.enlace" target="_blank" rel="noopener">{{ origen.textoEnlace }} ↗</a>
          </li>
        }
      </ul>
      <ul class="notas">
        @for (servicio of servicios; track servicio.quien) {
          <li data-testid="fuente-servicios">
            <strong>{{ servicio.quien }}</strong> {{ servicio.que }}
            <a [href]="servicio.enlace" target="_blank" rel="noopener">{{ servicio.textoEnlace }} ↗</a>
          </li>
        }
        <li data-testid="fuentes-entrenamiento">
          El modelo se entrenó con <span class="mono">{{ entrenamiento.release }}</span>: {{ entrenamiento.juegos }}
          juegos y {{ num(entrenamiento.resenas) }} reseñas. Los otros {{ entrenamiento.juegosPrueba }} son la
          prueba.
        </li>
      </ul>
    </section>
  `,
  styles: `
    :host {
      display: block;
      container: fuentes / inline-size;
    }
    .fuentes {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-16);
      scroll-margin-top: var(--espacio-16);
    }
    /* Como «Metodología», arriba: los dos títulos del panel se leen iguales. */
    .rotulo {
      margin: 0;
      font-family: var(--fuente-display);
      font-size: 22px;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }
    /* Una fila por fuente y columnas alineadas: se lee como una tabla, sin tarjetas. */
    .filas {
      list-style: none;
      margin: 0;
      padding: 0;
      border-top: 1px solid var(--borde);
    }
    .fila {
      display: grid;
      grid-template-columns: 13rem minmax(0, 1fr) 11rem 11rem 8.5rem;
      align-items: baseline;
      gap: var(--espacio-8) var(--espacio-24);
      padding: var(--espacio-16) 0;
      border-bottom: 1px solid var(--borde);
    }
    .fila p {
      margin: 0;
    }
    .quien {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .quien strong {
      font-size: 18px;
    }
    .sobre {
      color: var(--neon);
      font-size: var(--texto-caption);
    }
    .da {
      color: var(--texto);
      font-size: var(--texto-body-sm);
      line-height: 1.4;
    }
    .cuanto {
      color: var(--texto);
      font-size: var(--texto-caption);
      font-weight: 600;
    }
    .cuando {
      color: var(--texto-meta);
      font-size: var(--texto-caption);
    }
    a {
      color: var(--enlace);
      font-size: var(--texto-caption);
      text-underline-offset: 3px;
      white-space: nowrap;
    }
    .fila a {
      justify-self: end;
    }
    .notas {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: var(--espacio-8);
      color: var(--texto-meta);
      font-size: var(--texto-body-sm);
      line-height: 1.5;
    }
    .notas strong {
      color: var(--texto);
    }
    /* Angosto: cada fuente en bloque: quién y su enlace arriba; debajo, qué da, la cifra
       y la fecha, cada una en su renglón. */
    @container fuentes (max-width: 820px) {
      .fila {
        grid-template-columns: minmax(0, 1fr) auto;
        gap: var(--espacio-4) var(--espacio-16);
      }
      .quien {
        flex-direction: row;
        flex-wrap: wrap;
        align-items: baseline;
        column-gap: var(--espacio-8);
      }
      .da,
      .cuanto,
      .cuando {
        grid-column: 1 / -1;
      }
      .fila a {
        grid-column: 2;
        grid-row: 1;
      }
    }
  `,
})
export class Fuentes {
  private readonly panorama = inject(PanoramaStore);
  private readonly catalogo = inject(CatalogoStore);

  protected readonly origenes = ORIGENES;
  protected readonly servicios = SERVICIOS;
  protected readonly entrenamiento = ENTRENAMIENTO;

  protected readonly cuanto = computed<Partial<Record<ClaveOrigen, string>>>(() => {
    const p = this.panorama.datos();
    const juegos = this.catalogo.juegos();
    const conNota = juegos.filter((juego) => juego.metacritic !== null).length;
    return {
      appreviews: p ? `${numero(p.resenas_descargadas)} reseñas` : undefined,
      appdetails: juegos.length ? `${juegos.length} juegos` : undefined,
      metacritic: juegos.length ? `${conNota} de ${juegos.length} juegos` : undefined,
    };
  });

  /** La nota de Metacritic llega con appdetails: su fecha es la de appdetails. */
  protected readonly descarga = computed<Partial<Record<ClaveOrigen, string>>>(() => {
    const descargas = this.panorama.datos()?.descargas;
    if (!descargas) {
      return {};
    }
    const juegos = rangoDeFechas(descargas.appdetails.desde, descargas.appdetails.hasta);
    return {
      appreviews: rangoDeFechas(descargas.appreviews.desde, descargas.appreviews.hasta),
      appdetails: juegos,
      metacritic: juegos,
    };
  });

  protected readonly num = numero;
}
