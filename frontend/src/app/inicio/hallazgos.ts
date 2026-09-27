import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';

import { hallazgosDelInicio } from '../dominio/hallazgos-inicio';
import { CatalogoStore } from '../estado/catalogo-store';
import { PanoramaStore } from '../estado/panorama-store';

/** «Qué encontramos»: tres cifras que se leen en un minuto de exposición, calculadas con
 * el catálogo y el panorama de la API (dominio/hallazgos-inicio.ts). */
@Component({
  selector: 'app-hallazgos',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (hallazgos().length) {
      <section class="hallazgos-seccion" aria-labelledby="titulo-hallazgos" data-testid="inicio-hallazgos">
        <h2 id="titulo-hallazgos">Qué encontramos</h2>
        <div class="hallazgos">
          @for (hallazgo of hallazgos(); track hallazgo.id) {
            <article class="hallazgo" [attr.data-hallazgo]="hallazgo.id" data-testid="hallazgo">
              <p class="cifra" data-testid="hallazgo-cifra">
                {{ hallazgo.cifra }}
                @if (hallazgo.union) {
                  <small>{{ hallazgo.union }}</small> {{ hallazgo.otra }}
                }
              </p>
              <p class="frase" data-testid="hallazgo-frase">{{ hallazgo.frase }}</p>
              <p class="dato">{{ hallazgo.dato }}</p>
              <p class="fuente">{{ hallazgo.fuente }}</p>
            </article>
          }
        </div>
      </section>
    }
  `,
  styles: `
    .hallazgos-seccion {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-16);
    }
    h2 {
      margin: 0;
      font-size: clamp(var(--texto-subheading), 2.4vw, var(--texto-heading-sm));
    }
    .hallazgos {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: var(--espacio-16);
    }
    .hallazgo {
      display: flex;
      flex-direction: column;
      gap: 10px;
      padding: 22px;
      border: 1px solid var(--borde);
      border-radius: var(--radio-tarjeta);
      background: var(--superficie);
      box-shadow: inset 0 3px 0 var(--accion-tinta);
    }
    .cifra {
      margin: 0;
      color: var(--accion-tinta);
      font-family: var(--fuente-display);
      font-size: clamp(40px, 4.4cqw, 56px);
      font-weight: 700;
      line-height: 1;
    }
    .cifra small {
      color: var(--texto-meta);
      font-size: 0.5em;
    }
    .frase {
      margin: 0;
      font-size: 18px;
      line-height: 1.45;
    }
    .dato {
      margin: 0;
      color: var(--texto-meta);
      font-size: var(--texto-body-sm);
      line-height: 1.45;
    }
    .fuente {
      margin: auto 0 0;
      padding-top: 10px;
      border-top: 1px solid var(--borde);
      color: var(--texto-meta);
      font-size: var(--texto-caption);
    }
    @container contenido (max-width: 860px) {
      .hallazgos {
        grid-template-columns: 1fr;
      }
    }
  `,
})
export class Hallazgos {
  private readonly catalogo = inject(CatalogoStore);
  private readonly panorama = inject(PanoramaStore);

  protected readonly hallazgos = computed(() =>
    this.panorama.datos() ? hallazgosDelInicio(this.catalogo.juegos(), this.panorama.porAppid()) : [],
  );
}
