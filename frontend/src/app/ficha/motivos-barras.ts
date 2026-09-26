import { ChangeDetectionStrategy, Component, computed, input, signal } from '@angular/core';

import { ExplicacionJuego } from '../api/contrato';
import { NotaInfo } from '../compartido/nota-info';
import { porcentaje } from '../dominio/formato';

/** Cuántos motivos se ven sin pedir más. */
const MOTIVOS_DE_ENTRADA = 3;

/** Por debajo de esto los porcentajes de motivos se avisan como muestra chica. La API ya
 * no los calcula con menos de cinco casos; entre cinco y diez se muestran, con reparo. */
const MINIMO_PARA_FIARSE = 10;

/** Con una o dos reseñas clasificadas, una barra al 100% es una raya que dice "todas", y
 * "todas" es una: se nombran los motivos y ya. */
const MINIMO_PARA_BARRAS = 3;

@Component({
  selector: 'app-motivos-barras',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [NotaInfo],
  template: `
    <section class="bloque" data-seccion="motivos" data-testid="motivos">
      <header class="bloque-cabecera">
        <span class="insignia" aria-hidden="true">
          <svg viewBox="0 0 24 24">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /><path d="M12 7v4m0 3h.01" />
          </svg>
        </span>
        <h2 class="bloque-titulo">
          Motivos más frecuentes
          <!-- La nota explica los porcentajes: donde no hay porcentajes, no hay nada que explicar. -->
          @if (conBarras()) {
            <app-nota-info etiqueta="Cómo se leen estos porcentajes" idPrueba="motivos-info">
              Cada porcentaje es sobre las reseñas que mencionan algún motivo, no sobre todas las analizadas.
              Suman más de 100% porque una misma reseña puede mencionar varios.
            </app-nota-info>
          }
        </h2>
        <p class="bloque-sub">De qué se quejan las reseñas negativas de las primeras dos horas.</p>
      </header>
      @if (explicacion(); as datos) {
        @if (datos.motivos.length && !conBarras()) {
          <p class="lectura escueto" data-testid="motivos-escueto">
            Solo {{ clasificadas(datos) }}
            {{ clasificadas(datos) === 1 ? 'reseña menciona un motivo' : 'reseñas mencionan un motivo' }}:
            {{ nombres(datos) }}.
          </p>
        } @else if (datos.motivos.length) {
          <ul class="lista">
            @for (motivo of datos.motivos.slice(0, visibles()); track motivo.motivo) {
              <li class="fila">
                <span class="nombre">{{ motivo.motivo }}</span>
                <span class="pista">
                  <span class="barra" [style.width.%]="motivo.frecuencia * 100"></span>
                </span>
                <span class="valor mono">{{ pct(motivo.frecuencia) }}</span>
              </li>
            }
          </ul>
          @if (datos.motivos.length > visibles()) {
            <button type="button" class="boton-texto" data-testid="motivos-ver-todos" (click)="verTodos()">
              Ver los {{ datos.motivos.length }} motivos →
            </button>
          }
          <p class="meta contexto" data-testid="motivos-cuantas">
            Sobre {{ clasificadas(datos) }}
            {{ clasificadas(datos) === 1 ? 'reseña clasificada' : 'reseñas clasificadas' }}.
            @if (pocas(clasificadas(datos))) {
              <span data-testid="motivos-pocas">Con tan pocas, tómalo como una pista y no como una medida.</span>
            }
          </p>
        } @else {
          <p class="meta">
            Sin motivos disponibles: hay muy pocas reseñas de arrepentimiento temprano de este juego
            ({{ datos.n_casos }}).
          </p>
        }
      } @else {
        <p class="meta">No se pudieron cargar los motivos.</p>
      }
    </section>
  `,
  styles: `
    .lista {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: var(--espacio-8);
    }
    .fila {
      display: grid;
      grid-template-columns: 9rem 1fr 3rem;
      align-items: center;
      gap: var(--espacio-12);
    }
    .pista {
      height: 10px;
      border-radius: var(--radio-pildora);
      background: var(--superficie-2);
      overflow: hidden;
    }
    .barra {
      display: block;
      height: 100%;
      background: var(--tono, var(--neon));
    }
    .valor {
      text-align: right;
      color: var(--texto-meta);
      font-size: var(--texto-caption);
    }
    .aviso-pocas {
      margin: 0 0 var(--espacio-8);
      padding: var(--espacio-8) var(--espacio-12);
      border-inline-start: 3px solid var(--banda-medio-texto);
      max-width: var(--medida-lectura);
      line-height: var(--interlineado-largo);
    }
    .escueto {
      margin: 0;
      max-width: var(--medida-lectura);
    }
    .contexto {
      margin: 0;
      max-width: var(--medida-lectura);
      line-height: var(--interlineado-largo);
    }
    @media (max-width: 520px) {
      .fila {
        grid-template-columns: 1fr 3rem;
      }
      .pista {
        grid-column: 1 / -1;
        order: 3;
      }
    }
  `,
})
export class MotivosBarras {
  readonly explicacion = input.required<ExplicacionJuego | undefined>();

  /** Tres bastan para ver de qué se queja la gente; el resto, a un clic. */
  protected readonly visibles = signal(MOTIVOS_DE_ENTRADA);

  protected verTodos(): void {
    this.visibles.set(Number.MAX_SAFE_INTEGER);
  }

  protected readonly pct = porcentaje;

  /** Las reseñas sobre las que se calcula cada porcentaje: las que mencionan algún
   * motivo, no todas las analizadas. Hades tiene 5 casos y una sola clasificada, y el
   * "100%" salía de esa una. */
  protected clasificadas(datos: ExplicacionJuego): number {
    return Math.round(datos.n_casos * datos.pct_clasificados);
  }

  /** Con menos de diez, un porcentaje es una anécdota con decimales. */
  protected pocas(clasificadas: number): boolean {
    return clasificadas < MINIMO_PARA_FIARSE;
  }

  /** Si los porcentajes se pueden dibujar: hacen falta al menos tres reseñas clasificadas. */
  protected readonly conBarras = computed(() => {
    const datos = this.explicacion();
    return !!datos?.motivos.length && this.clasificadas(datos) >= MINIMO_PARA_BARRAS;
  });

  /** Los motivos por su nombre, sin porcentajes: es lo único que se puede decir con una
   * o dos reseñas. */
  protected nombres(datos: ExplicacionJuego): string {
    const nombres = datos.motivos.map((motivo) => motivo.motivo);
    return nombres.length === 1 ? nombres[0] : `${nombres.slice(0, -1).join(', ')} y ${nombres[nombres.length - 1]}`;
  }
}
