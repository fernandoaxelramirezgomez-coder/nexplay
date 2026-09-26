import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';

import { numero, rangoDeFechas } from '../dominio/formato';
import { ClaveOrigen, ENTRENAMIENTO, ORIGENES, SERVICIOS } from '../dominio/fuentes';
import { CatalogoStore } from '../estado/catalogo-store';
import { PanoramaStore } from '../estado/panorama-store';

/** Las fuentes de los datos, con qué se toma de cada una, cuánto y cuándo se descargó, y
 * los servicios que usa la app. Las cifras y las fechas salen de la API; si /panorama no
 * responde, las tarjetas se quedan con lo que no depende de ella. Una fuente que se sume
 * (IGDB, si pasa su cobertura) entra aquí como tarjeta rotulada «fuente secundaria». */
@Component({
  selector: 'app-fuentes',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="fuentes" data-testid="fuentes" aria-labelledby="titulo-fuentes">
      <h2 class="rotulo" id="titulo-fuentes">Fuentes</h2>
      <ul class="lista">
        @for (origen of origenes; track origen.clave) {
          <li class="tarjeta" data-testid="fuente">
            <span class="quien">{{ origen.quien }}</span>
            <span class="api mono">{{ origen.api }}</span>
            <dl>
              <dt>Qué se toma</dt>
              <dd>{{ origen.toma }}</dd>
              @if (cuanto()[origen.clave]; as cifra) {
                <dt>Cuánto</dt>
                <dd>{{ cifra }}</dd>
              }
              @if (descarga()[origen.clave]; as fecha) {
                <dt>Descarga</dt>
                <dd data-testid="fuente-descarga">{{ fecha }}</dd>
              }
            </dl>
            <a [href]="origen.enlace" target="_blank" rel="noopener">{{ origen.textoEnlace }} ↗</a>
          </li>
        }
        <li class="tarjeta" data-testid="fuente-servicios">
          <span class="quien">Servicios</span>
          <span class="api mono">lo que usa la app</span>
          @for (servicio of servicios; track servicio.quien) {
            <div class="servicio">
              <p class="nombre">
                <strong>{{ servicio.quien }}</strong><span class="para">{{ " · " + servicio.para }}</span>
              </p>
              <p class="que">{{ servicio.que }}</p>
              <a [href]="servicio.enlace" target="_blank" rel="noopener">{{ servicio.textoEnlace }} ↗</a>
            </div>
          }
        </li>
      </ul>
      <p class="entrenamiento" data-testid="fuentes-entrenamiento">
        El modelo se entrenó con el corte <span class="mono">{{ entrenamiento.release }}</span>:
        {{ entrenamiento.juegos }} juegos y {{ num(entrenamiento.resenas) }} reseñas. Los otros
        {{ entrenamiento.juegosPrueba }} del catálogo nunca entraron al entrenamiento.
      </p>
    </section>
  `,
  styles: `
    .fuentes {
      display: flex;
      flex-direction: column;
      gap: 14px;
      scroll-margin-top: var(--espacio-16);
    }
    .rotulo {
      margin: var(--espacio-8) 0 0;
      font-size: clamp(var(--texto-subheading), 2.4vw, var(--texto-heading-sm));
    }
    .lista {
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(min(100%, 240px), 1fr));
      gap: var(--espacio-12);
    }
    .tarjeta {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-8);
      padding: 18px;
      border: 1px solid var(--borde);
      border-radius: var(--radio-tarjeta);
      background: var(--superficie);
    }
    .quien {
      font-family: var(--fuente-display);
      font-size: 18px;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }
    .api {
      color: var(--neon);
      font-size: var(--texto-caption);
    }
    dl {
      margin: 0;
      display: flex;
      flex-direction: column;
      gap: 2px;
      font-size: var(--texto-body-sm);
      line-height: 1.4;
    }
    dt {
      color: var(--texto-meta);
    }
    dt:not(:first-child) {
      margin-top: var(--espacio-8);
    }
    dd {
      margin: 0;
    }
    a {
      margin-top: auto;
      color: var(--enlace);
      font-size: var(--texto-caption);
      text-underline-offset: 3px;
    }
    .servicio {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-4);
    }
    .servicio + .servicio {
      margin-top: var(--espacio-8);
      padding-top: var(--espacio-12);
      border-top: 1px solid var(--borde);
    }
    .servicio a {
      margin-top: 0;
    }
    .nombre,
    .que {
      margin: 0;
      font-size: var(--texto-body-sm);
      line-height: 1.4;
    }
    .para,
    .que {
      color: var(--texto-meta);
    }
    .entrenamiento {
      margin: 0;
      padding: var(--espacio-12) var(--espacio-16);
      border: 1px solid var(--borde);
      border-radius: var(--radio-boton);
      background: var(--superficie);
      font-size: var(--texto-body-sm);
      line-height: 1.45;
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
      appreviews: p
        ? `${numero(p.resenas_descargadas)} reseñas, las más recientes de cada juego; ${numero(p.muestra.resenas_en_ingles)} en inglés.`
        : undefined,
      appdetails: juegos.length ? `${juegos.length} juegos.` : undefined,
      metacritic: juegos.length ? `${conNota} de los ${juegos.length} juegos tienen nota.` : undefined,
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
      metacritic: juegos ? `con appdetails, ${juegos}` : '',
    };
  });

  protected readonly num = numero;
}
