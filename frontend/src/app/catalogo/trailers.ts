import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { PildoraBanda } from '../compartido/pildora-banda';
import { PortadaAncha } from '../compartido/portada-ancha';
import { Skeleton } from '../compartido/skeleton';
import { elegirTrailers } from '../dominio/trailers';
import { CatalogoStore } from '../estado/catalogo-store';
import { PanoramaStore } from '../estado/panorama-store';

/** Tráileres del catálogo, arriba de los estantes: dos por nivel de riesgo, los más
 * reseñados en Steam. El escenario reproduce uno, mudo; al terminar pasa al siguiente.
 *
 * Deja de pasar solo en cuanto la persona muestra interés: mientras el cursor o el foco
 * están encima, y para siempre desde que toca un tráiler o un control. Cada
 * tráiler arranca mudo: solo suena el que alguien activó (lo hace la portada ancha, que
 * reinicia el sonido con cada video). */
@Component({
  selector: 'app-trailers',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, PildoraBanda, PortadaAncha, Skeleton],
  template: `
    @if (actual(); as juego) {
      <section
        class="trailers"
        aria-roledescription="carrusel"
        aria-label="Tráileres del catálogo"
        data-testid="trailers"
        [attr.data-avanza-solo]="avanzaSolo()"
        (pointerenter)="alEntrar($event)"
        (pointerleave)="encima.set(false)"
        (focusin)="conFoco.set(true)"
        (focusout)="alSalirElFoco($event)"
      >
        <div class="escenario" data-testid="trailer-escenario">
          <app-portada-ancha
            modo="carrusel"
            [appid]="juego.appid"
            [respaldo]="juego.portada_url"
            [video]="juego.video_url"
            [enBucle]="!avanzaSolo()"
            (terminado)="siguiente()"
            (interaccion)="tomado.set(true)"
          />
          <div class="velo" data-fondo-peor="#404350">
            <app-pildora-banda [banda]="juego.banda_riesgo" />
            <p class="nombre" data-testid="trailer-nombre">{{ juego.nombre }}</p>
            <p class="detalle">
              @if (motivo(juego.appid); as motivo) {
                <span class="motivo">Motivo principal: {{ motivo }}</span>
              }
              <a class="ver-ficha" [routerLink]="['/juego', juego.appid]" data-testid="trailer-ver-ficha">Ver ficha →</a>
            </p>
          </div>
        </div>

        <ol class="lista">
          @for (opcion of trailers(); track opcion.appid; let i = $index) {
            <li>
              <button
                type="button"
                data-testid="trailer-opcion"
                [attr.aria-current]="i === indice()"
                [attr.aria-label]="'Ver el tráiler de ' + opcion.nombre + ', riesgo ' + opcion.banda_riesgo"
                (click)="elegir(i)"
              >
                <img [src]="opcion.portada_url" alt="" width="460" height="215" loading="lazy" />
                <span class="datos">
                  <span class="t-nombre">{{ opcion.nombre }}</span>
                  <span class="t-nivel"><i class="punto" [attr.data-banda]="opcion.banda_riesgo"></i>Riesgo {{ opcion.banda_riesgo }}</span>
                </span>
              </button>
            </li>
          }
        </ol>

        <!-- Qué tráiler se ve, solo para el lector de pantalla: la barra visible con el
             contador y las flechas no se veía bien, y la lista ya deja elegir cualquiera. -->
        <p class="solo-lector" aria-live="polite">
          Tráiler {{ indice() + 1 }} de {{ trailers().length }}: {{ actual()?.nombre }}
        </p>
      </section>
    } @else if (panorama.cargando() || catalogo.cargando()) {
      <app-skeleton alto="320px" />
    }
  `,
  styles: `
    .trailers {
      display: grid;
      grid-template-columns: minmax(0, 1.9fr) minmax(0, 1fr);
      gap: var(--espacio-16);
    }
    .escenario {
      position: relative;
      min-width: 0;
    }
    /* Sobre el video y no sobre la página: el velo es oscuro en los dos temas y el texto
       va siempre claro. Solo el enlace recibe clics; el resto deja pasar al video. */
    .velo {
      position: absolute;
      inset: auto 0 0;
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: var(--espacio-8);
      padding: 56px clamp(16px, 2.4cqw, 28px) clamp(16px, 2.4cqw, 24px);
      border-radius: 0 0 var(--radio-tarjeta) var(--radio-tarjeta);
      background: linear-gradient(to top, rgb(11 15 31 / 0.94), rgb(11 15 31 / 0.78) 55%, transparent);
      color: #f2f4ff;
      pointer-events: none;
    }
    .nombre {
      font-family: var(--fuente-display);
      font-size: clamp(22px, 3cqw, 34px);
      font-weight: 700;
      line-height: 1.05;
      text-transform: uppercase;
    }
    .detalle {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--espacio-8) var(--espacio-16);
      font-size: var(--texto-body-sm);
    }
    .motivo {
      color: #d6dbf5;
    }
    .ver-ficha {
      display: inline-flex;
      align-items: center;
      min-height: 44px;
      padding: 0 var(--espacio-16);
      border-radius: var(--radio-pildora);
      background: #f2f4ff;
      color: #0b0f1f;
      font-weight: 700;
      text-decoration: none;
      pointer-events: auto;
    }
    .ver-ficha:hover {
      background: #ffffff;
      text-decoration: underline;
    }
    .lista {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 6px;
      min-width: 0;
    }
    /* Compacta: la lista es la que decide el alto de los tráileres a lo ancho, y con
       miniaturas de 112 px empujaba la nave 📚 fuera de la primera pantalla. */
    .lista button {
      width: 100%;
      display: grid;
      grid-template-columns: 96px minmax(0, 1fr);
      align-items: center;
      gap: var(--espacio-12);
      padding: 5px;
      border: 1px solid var(--borde);
      border-radius: 12px;
      background: var(--superficie);
      color: var(--texto);
      text-align: start;
      cursor: pointer;
    }
    .lista button:hover {
      border-color: var(--borde-control);
    }
    .lista button[aria-current='true'] {
      border-color: var(--neon);
      background: var(--acento-sistema);
      box-shadow: inset 0 0 0 1px var(--neon);
    }
    .lista img {
      width: 96px;
      height: auto;
      aspect-ratio: 460 / 215;
      object-fit: cover;
      border-radius: 8px;
    }
    .datos {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-4);
      min-width: 0;
    }
    .t-nombre {
      overflow: hidden;
      font-weight: 700;
      line-height: 1.2;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .t-nivel {
      display: flex;
      align-items: center;
      gap: 6px;
      color: var(--texto-meta);
    }
    .punto {
      flex: none;
      width: 10px;
      height: 10px;
      border-radius: 50%;
    }
    .punto[data-banda='bajo'] {
      background: var(--banda-bajo);
    }
    .punto[data-banda='medio'] {
      background: var(--banda-medio);
    }
    .punto[data-banda='alto'] {
      background: var(--banda-alto);
    }
    /* Angosto (tableta y teléfono): el escenario arriba y la lista como una tira que se
       desliza. A 1024 px la columna de la lista ya no daba para el nombre y el nivel. */
    @container contenido (max-width: 780px) {
      .trailers {
        grid-template-columns: 1fr;
      }
      /* En una columna el escenario no pasa del alto que deja ver la nave 📚 en la
         primera pantalla: a 1024×768 medía 405 px y la nave quedaba abajo. En el teléfono
         manda el 16:9 (56.25 % del ancho), que ya es menor. */
      .escenario ::ng-deep .marco.carrusel {
        aspect-ratio: auto;
        height: max(180px, min(56.25cqw, calc(100svh - 470px)));
      }
      .lista {
        flex-direction: row;
        overflow-x: auto;
        padding-bottom: var(--espacio-4);
        scroll-snap-type: x mandatory;
      }
      .lista li {
        flex: 0 0 168px;
        scroll-snap-align: start;
      }
      .lista button {
        grid-template-columns: 1fr;
      }
      .lista img {
        width: 100%;
      }
      .motivo {
        display: none;
      }
    }
  `,
})
export class Trailers {
  protected readonly catalogo = inject(CatalogoStore);
  protected readonly panorama = inject(PanoramaStore);


  protected readonly trailers = computed(() =>
    this.panorama.datos() ? elegirTrailers(this.catalogo.juegos(), this.panorama.porAppid()) : [],
  );

  protected readonly indice = signal(0);
  protected readonly actual = computed(() => this.trailers()[this.indice()] ?? null);

  /** Cursor encima (solo ratón: un toque es elegir, no pasar por encima). */
  protected readonly encima = signal(false);
  protected readonly conFoco = signal(false);
  /** La persona eligió un tráiler o tocó un control: ya no avanza solo. */
  protected readonly tomado = signal(false);

  private readonly menosMovimiento =
    typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;

  protected readonly avanzaSolo = computed(
    () => !this.menosMovimiento && !this.tomado() && !this.encima() && !this.conFoco(),
  );

  protected motivo(appid: number): string | null {
    return this.panorama.porAppid().get(appid)?.motivo_principal ?? null;
  }

  protected alEntrar(evento: PointerEvent): void {
    if (evento.pointerType === 'mouse') {
      this.encima.set(true);
    } else {
      this.tomado.set(true);
    }
  }

  protected alSalirElFoco(evento: FocusEvent): void {
    const dentro = (evento.currentTarget as HTMLElement).contains(evento.relatedTarget as Node | null);
    if (!dentro) {
      this.conFoco.set(false);
    }
  }

  protected elegir(i: number): void {
    this.tomado.set(true);
    this.indice.set(i);
  }

  /** Al terminar un tráiler se avanza solo si nadie tomó el control. */
  protected siguiente(): void {
    if (!this.avanzaSolo()) {
      return;
    }
    const total = this.trailers().length;
    if (total) {
      this.indice.set((this.indice() + 1) % total);
    }
  }
}
