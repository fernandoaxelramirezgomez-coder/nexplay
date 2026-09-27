import { ChangeDetectionStrategy, Component, DestroyRef, ElementRef, computed, inject, signal, viewChild } from '@angular/core';
import { NavigationEnd, Router } from '@angular/router';
import { filter } from 'rxjs';

import { Fuentes } from '../como-funciona/fuentes';
import { Metodologia } from '../como-funciona/metodologia';
import { rangoDeFechas } from '../dominio/formato';
import { PanoramaStore } from '../estado/panorama-store';

/** El pie de todas las vistas: de dónde salen los datos y cuándo se bajaron, en una línea,
 * y «Ver metodología», que despliega ahí mismo la metodología y las fuentes. Es el lugar
 * de lo que antes eran Panorama y Cómo funciona: sus rutas llevan a /#metodologia, y con
 * ese ancla el panel se abre solo. Todo va en panel: el pie queda sobre la nebulosa. */
@Component({
  selector: 'app-pie',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Metodologia, Fuentes],
  template: `
    <div class="panel-pie" data-testid="pie-fuentes">
      <div class="linea">
        <p class="texto" data-testid="pie-linea">
          Fuentes: Steam (appreviews y appdetails) y Metacritic{{ descarga() ? ', descargadas ' + descarga() : '' }}.
        </p>
        <button
          type="button"
          class="compacto"
          data-tono="neutro"
          data-testid="pie-ver-metodologia"
          aria-controls="metodologia"
          [attr.aria-expanded]="abierto()"
          (click)="alternar()"
        >
          {{ abierto() ? 'Ocultar metodología ▴' : 'Ver metodología ▾' }}
        </button>
      </div>
      <div class="panel-metodologia" id="metodologia" #panel data-testid="pie-panel" [hidden]="!abierto()">
        @if (abierto()) {
          <app-metodologia [enmarcada]="false" />
          <app-fuentes />
        }
      </div>
    </div>
  `,
  styles: `
    .panel-pie {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-16);
      padding: 14px 18px;
      border: 1px solid var(--borde);
      border-radius: var(--radio-tarjeta);
      background: var(--superficie);
    }
    .linea {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--espacio-8) var(--espacio-16);
    }
    .texto {
      margin: 0;
      font-size: var(--texto-body-sm);
      line-height: 1.4;
    }
    .panel-metodologia {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-24);
      padding-top: var(--espacio-16);
      border-top: 1px solid var(--borde);
      scroll-margin-top: var(--espacio-16);
    }
    .panel-metodologia[hidden] {
      display: none;
    }
  `,
})
export class Pie {
  private readonly panorama = inject(PanoramaStore);
  private readonly router = inject(Router);
  private readonly panel = viewChild<ElementRef<HTMLElement>>('panel');

  protected readonly abierto = signal(false);

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

  constructor() {
    // /#metodologia (adonde llevan /panorama y /como-funciona) abre el panel y lo muestra.
    const revisar = (url: string) => {
      if (this.router.parseUrl(url).fragment === 'metodologia') {
        this.abrir('start');
      }
    };
    const suscripcion = this.router.events
      .pipe(filter((evento): evento is NavigationEnd => evento instanceof NavigationEnd))
      .subscribe((evento) => revisar(evento.urlAfterRedirects));
    inject(DestroyRef).onDestroy(() => suscripcion.unsubscribe());
    revisar(this.router.url);
  }

  protected alternar(): void {
    if (this.abierto()) {
      this.abierto.set(false);
    } else {
      this.abrir('nearest');
    }
  }

  /** Llegando por el ancla, el panel sube al principio; tocando el botón, solo lo necesario
   * para verlo. */
  private abrir(bloque: ScrollLogicalPosition): void {
    this.abierto.set(true);
    // Tras pintar el contenido: antes, el panel mide cero y no hay adónde bajar. Con ?.
    // porque el DOM de las pruebas no implementa scrollIntoView.
    setTimeout(() => this.panel()?.nativeElement.scrollIntoView?.({ block: bloque }), 0);
  }
}
