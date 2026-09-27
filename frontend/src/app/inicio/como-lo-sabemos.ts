import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';

import { cifrasDeLaMuestra } from '../dominio/hallazgos-inicio';
import { CatalogoStore } from '../estado/catalogo-store';
import { PanoramaStore } from '../estado/panorama-store';

/** «Cómo lo sabemos»: el tamaño de la muestra y con cuántos juegos que no vio se probó el
 * modelo, en una franja. El detalle está en el panel de metodología del pie. */
@Component({
  selector: 'app-como-lo-sabemos',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (cifras().length) {
      <section class="como-lo-sabemos" aria-labelledby="titulo-como-lo-sabemos" data-testid="inicio-como-lo-sabemos">
        <h2 id="titulo-como-lo-sabemos">Cómo lo sabemos</h2>
        <dl class="franja">
          @for (cifra of cifras(); track cifra.id) {
            <div [attr.data-cifra]="cifra.id" data-testid="cifra-muestra">
              <dt class="mono">{{ cifra.cifra }}</dt>
              <dd>{{ cifra.texto }}</dd>
            </div>
          }
        </dl>
      </section>
    }
  `,
  styles: `
    .como-lo-sabemos {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-16);
    }
    h2 {
      margin: 0;
      font-size: clamp(var(--texto-subheading), 2.4vw, var(--texto-heading-sm));
    }
    .franja {
      margin: 0;
      display: grid;
      grid-auto-flow: column;
      grid-auto-columns: minmax(0, 1fr);
      border: 1px solid var(--borde);
      border-radius: var(--radio-tarjeta);
      background: var(--superficie);
      overflow: hidden;
    }
    .franja div {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-4);
      padding: var(--espacio-16) 18px;
    }
    .franja div + div {
      border-inline-start: 1px solid var(--borde);
    }
    dt {
      font-size: 26px;
    }
    dd {
      margin: 0;
      color: var(--texto-meta);
      font-size: var(--texto-body-sm);
      line-height: 1.35;
    }
    @container contenido (max-width: 860px) {
      .franja {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        grid-auto-flow: row;
      }
      .franja div:nth-child(3) {
        border-inline-start: 0;
      }
      .franja div:nth-child(n + 3) {
        border-top: 1px solid var(--borde);
      }
    }
  `,
})
export class ComoLoSabemos {
  private readonly catalogo = inject(CatalogoStore);
  private readonly panorama = inject(PanoramaStore);

  protected readonly cifras = computed(() => {
    const datos = this.panorama.datos();
    return datos ? cifrasDeLaMuestra(this.catalogo.juegos(), datos) : [];
  });
}
