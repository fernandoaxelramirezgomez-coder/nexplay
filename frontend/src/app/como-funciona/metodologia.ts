import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';

import { definicionDeNiveles } from '../dominio/etiqueta-riesgo';
import { CatalogoStore } from '../estado/catalogo-store';

/** La metodología en tres frases, con el texto completo plegado. Vive en el panel del pie
 * (se abre desde cualquier vista) y la reúsa Cómo funciona. Lleva su propio contenedor:
 * el pie queda fuera de «contenido», y sin él las tres columnas no pasaban a una en teléfono. */
@Component({
  selector: 'app-metodologia',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { '[class.enmarcada]': 'enmarcada()' },
  template: `
    <section class="metodologia" data-testid="metodologia" aria-labelledby="titulo-metodologia">
      <h2 class="rotulo" id="titulo-metodologia">Metodología</h2>
      <p class="niveles" data-testid="metodologia-niveles">{{ niveles() }}</p>
      <ul class="hechos" data-testid="metodologia-hechos">
        <li>
          <strong>Una señal, no un sentimiento</strong>
          <span>Reseña negativa con menos de 2 h jugadas: la ventana de reembolso de Steam.</span>
        </li>
        <li>
          <strong>Probado con juegos que no vio</strong>
          <span>Se valida agrupando por juego; la métrica es PR-AUC, no la exactitud.</span>
        </li>
        <li>
          <strong>Ordena, no predice</strong>
          <span>Es un nivel, no una probabilidad. Es del juego, no tuyo.</span>
        </li>
      </ul>
      <details class="completa" data-testid="metodologia-completa">
        <summary>Leer la metodología completa</summary>
        <p class="lectura">
          NexPlay estima el riesgo de arrepentimiento temprano al comprar un videojuego, antes de la compra. Es una
          señal <em>proxy</em>: se construye con reseñas donde el autor jugó poco (menos de 120 minutos, la ventana de
          reembolso de Steam) y calificó negativo. Steam no pregunta directamente si alguien se arrepintió.
        </p>
        <p class="lectura">
          El modelo se valida con <span class="mono">GroupKFold</span> agrupando por juego, así que el riesgo mide
          generalización a juegos que el modelo no vio, no memorización. La métrica es PR-AUC: la clase está muy
          desbalanceada (alrededor del 2.2% de las reseñas), así que la exactitud no sirve.
        </p>
        <p class="lectura">
          El riesgo ordena riesgo relativo; no es una probabilidad calibrada. Por eso se muestra como nivel (bajo, medio
          o alto) y nunca como porcentaje. El riesgo es del juego y es el mismo para todos: el perfil que declaras no lo
          cambia.
        </p>
      </details>
    </section>
  `,
  styles: `
    :host {
      display: block;
      container: metodologia / inline-size;
    }
    .metodologia {
      display: flex;
      flex-direction: column;
      gap: 14px;
    }
    :host(.enmarcada) .metodologia {
      padding: 22px var(--espacio-24);
      border: 1px solid var(--borde);
      border-radius: var(--radio-tarjeta);
      background: var(--superficie);
    }
    .rotulo {
      margin: 0;
      font-family: var(--fuente-display);
      font-size: 22px;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }
    .niveles {
      margin: 0;
      padding: 10px 14px;
      border-inline-start: 3px solid var(--t-neutro);
      border-radius: var(--radio-boton);
      background: var(--superficie-2);
      font-size: var(--texto-body-sm);
    }
    .hechos {
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: var(--espacio-12);
    }
    .hechos li {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-4);
      padding: 14px;
      border-radius: var(--radio-boton);
      background: var(--superficie-2);
    }
    .hechos strong {
      font-size: 17px;
    }
    .hechos span {
      color: var(--texto-meta);
      font-size: var(--texto-body-sm);
      line-height: 1.4;
    }
    summary {
      display: inline-flex;
      align-items: center;
      min-height: 44px;
      color: var(--enlace);
      font-size: var(--texto-caption);
      text-decoration: underline;
      text-underline-offset: 3px;
      cursor: pointer;
      list-style: none;
    }
    summary::-webkit-details-marker {
      display: none;
    }
    .completa .lectura {
      margin: var(--espacio-8) 0 0;
    }
    @container metodologia (max-width: 760px) {
      .hechos {
        grid-template-columns: 1fr;
      }
      :host(.enmarcada) .metodologia {
        padding: 18px var(--espacio-16) 20px;
      }
    }
  `,
})
export class Metodologia {
  /** En Cómo funciona va en su propio panel; en el pie, el panel ya lo pone el pie. */
  readonly enmarcada = input(true);

  private readonly catalogo = inject(CatalogoStore);
  protected readonly niveles = computed(() => definicionDeNiveles(this.catalogo.juegos()));
}
