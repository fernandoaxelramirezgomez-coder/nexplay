import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  afterNextRender,
  computed,
  inject,
  signal,
  viewChild,
} from '@angular/core';

import { GraficaBarras } from '../compartido/graficas/grafica-barras';
import {
  MetricaAntesDePagar,
  PESTANAS_ANTES_DE_PAGAR,
  barrasAntesDePagar,
  histogramaDePrecios,
} from '../dominio/antes-de-pagar';
import { numero } from '../dominio/formato';
import { CatalogoStore } from '../estado/catalogo-store';
import { PanoramaStore } from '../estado/panorama-store';
import { HistogramaPrecios } from './histograma-precios';

/** «Antes de pagar, esto importa»: lo que le sirve a quien va a comprar, en dos gráficas
 * con los datos de la API. A la izquierda, una por nivel de riesgo con dos pestañas
 * (señal y reseñas positivas); a la derecha, cuánto cuestan los juegos de cada nivel.
 * «Precio» salió de las pestañas: el precio es una variable del modelo, así que compararlo
 * por nivel era circular. Las barras crecen al entrar en pantalla y se animan al cambiar
 * de pestaña. Al pie, la confianza en una línea, con la frase acordada: el riesgo sale de
 * datos del juego. La metodología se abre desde el pie del Inicio. */
@Component({
  selector: 'app-antes-de-pagar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [GraficaBarras, HistogramaPrecios],
  template: `
    <section class="antes" #seccion aria-labelledby="titulo-antes" data-testid="antes-de-pagar">
      <h2 id="titulo-antes">Antes de pagar, esto importa</h2>
      <div class="panel">
        <div class="lado barras-lado">
          <div class="pestanas" role="tablist" aria-label="Qué comparar entre niveles de riesgo">
            @for (pestana of pestanas; track pestana.id) {
              <button
                type="button"
                role="tab"
                class="pestana"
                [id]="'pestana-' + pestana.id"
                [attr.aria-selected]="metrica() === pestana.id"
                aria-controls="panel-antes"
                [tabIndex]="metrica() === pestana.id ? 0 : -1"
                data-testid="antes-pestana"
                [attr.data-metrica]="pestana.id"
                (click)="metrica.set(pestana.id)"
                (keydown)="alTeclear($event)"
              >
                {{ pestana.nombre }}
              </button>
            }
          </div>
          <div id="panel-antes" role="tabpanel" class="panel-pestana" [attr.aria-labelledby]="'pestana-' + metrica()">
            @if (barras(); as barras) {
              <p class="titular">
                <strong class="cifra" data-testid="antes-cifra">{{ barras.cifra }}</strong>
                <span class="linea" data-testid="antes-linea">{{ barras.linea }}</span>
              </p>
              <app-grafica-barras [segmentos]="segmentos()" [maximo]="tope()" idPrueba="antes-barras" />
            }
          </div>
        </div>
        <div class="lado">
          <app-histograma-precios [rangos]="rangos()" [visible]="visible()" />
        </div>
        <p class="confianza" data-testid="antes-confianza">
          Con {{ resenas() }} reseñas de Steam. El riesgo sale de datos del juego, sin leer las reseñas.
        </p>
      </div>
    </section>
  `,
  styles: `
    .antes {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--espacio-24);
      margin: var(--espacio-24) 0;
    }
    h2 {
      text-align: center;
      font-size: clamp(var(--texto-subheading), 2.6vw, 34px);
    }
    /* Un solo panel con aire: las dos gráficas lado a lado y la confianza al pie. */
    .panel {
      width: 100%;
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      padding: clamp(24px, 4cqw, 44px);
      border: 1px solid var(--borde);
      border-radius: 24px;
      background: var(--superficie);
    }
    .lado {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-16);
      min-width: 0;
      padding: 0 clamp(16px, 2.6cqw, 36px);
    }
    .lado:first-child {
      padding-inline-start: 0;
    }
    .lado + .lado {
      padding-inline-end: 0;
      border-inline-start: 1px solid var(--borde);
    }
    .pestanas {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }
    .pestana {
      min-height: 44px;
      padding: 0 var(--espacio-16);
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-pildora);
      background: var(--superficie-2);
      color: var(--texto);
      font: inherit;
      font-size: var(--texto-caption);
      font-weight: 600;
      cursor: pointer;
    }
    .pestana[aria-selected='true'] {
      border-color: var(--neon);
      background: color-mix(in srgb, var(--accion) 16%, var(--superficie));
      box-shadow: inset 0 0 0 1px var(--neon);
    }
    .panel-pestana {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-24);
    }
    .titular {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-8);
      margin: var(--espacio-8) 0 0;
    }
    .cifra {
      color: var(--accion-tinta);
      font-family: var(--fuente-display);
      font-size: clamp(52px, 6cqw, 80px);
      font-weight: 700;
      line-height: 1;
    }
    .linea {
      max-width: 30ch;
      color: var(--texto);
      font-size: 19px;
      line-height: 1.4;
    }
    /* Las barras crecen despacio: con la duración de la interfaz (rápida) no se notaba. */
    app-grafica-barras {
      --duracion: 0.7s;
      --ancho-etiqueta: 8rem;
    }
    .confianza {
      grid-column: 1 / -1;
      margin: clamp(28px, 4cqw, 40px) 0 0;
      padding-top: 20px;
      border-top: 1px solid var(--borde);
      color: var(--texto-meta);
      font-size: var(--texto-body-sm);
      line-height: 1.5;
      text-align: center;
    }
    @container contenido (max-width: 860px) {
      .panel {
        grid-template-columns: 1fr;
        gap: var(--espacio-40);
      }
      .lado {
        padding: 0;
      }
      .lado + .lado {
        padding-top: var(--espacio-40);
        border-inline-start: 0;
        border-top: 1px solid var(--borde);
      }
      .confianza {
        margin-top: 0;
      }
    }
  `,
})
export class AntesDePagar {
  private readonly catalogo = inject(CatalogoStore);
  private readonly panorama = inject(PanoramaStore);
  private readonly seccion = viewChild.required<ElementRef<HTMLElement>>('seccion');

  protected readonly pestanas = PESTANAS_ANTES_DE_PAGAR;
  protected readonly metrica = signal<MetricaAntesDePagar>('senal');
  /** Falso hasta que la sección entra en pantalla: entonces las gráficas crecen. */
  protected readonly visible = signal(false);

  protected readonly barras = computed(() =>
    barrasAntesDePagar(this.metrica(), this.catalogo.juegos(), this.panorama.porAppid()),
  );
  /** Antes de verse, las barras en cero y con su escala ya puesta: al entrar, crecen. */
  protected readonly segmentos = computed(() => {
    const segmentos = this.barras()?.segmentos ?? [];
    return this.visible() ? segmentos : segmentos.map((s) => ({ ...s, valor: 0 }));
  });
  protected readonly tope = computed(() => Math.max(0, ...(this.barras()?.segmentos ?? []).map((s) => s.valor)) || 1);
  protected readonly rangos = computed(() => histogramaDePrecios(this.catalogo.juegos()));
  protected readonly resenas = computed(() => numero(this.panorama.datos()?.resenas_descargadas ?? 0));

  constructor() {
    const destruir = inject(DestroyRef);
    afterNextRender(() => {
      // Sin IntersectionObserver (el DOM de las pruebas), se ven de una vez.
      if (typeof IntersectionObserver === 'undefined') {
        this.visible.set(true);
        return;
      }
      const observador = new IntersectionObserver(
        (entradas) => {
          if (entradas.some((e) => e.isIntersecting)) {
            this.visible.set(true);
            observador.disconnect();
          }
        },
        { threshold: 0.25 },
      );
      observador.observe(this.seccion().nativeElement);
      destruir.onDestroy(() => observador.disconnect());
    });
  }

  /** Flechas, Inicio y Fin entre pestañas, como en cualquier lista de pestañas. */
  protected alTeclear(evento: KeyboardEvent): void {
    const ids = this.pestanas.map((p) => p.id);
    const actual = ids.indexOf(this.metrica());
    const destino = {
      ArrowRight: (actual + 1) % ids.length,
      ArrowLeft: (actual - 1 + ids.length) % ids.length,
      Home: 0,
      End: ids.length - 1,
    }[evento.key];
    if (destino === undefined) {
      return;
    }
    evento.preventDefault();
    this.metrica.set(ids[destino]);
    const boton = (evento.currentTarget as HTMLElement).parentElement?.querySelector<HTMLElement>(
      `#pestana-${ids[destino]}`,
    );
    boton?.focus();
  }
}
