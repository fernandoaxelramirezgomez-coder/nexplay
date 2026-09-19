import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  selector: 'app-metodologia',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <details class="metodologia" data-testid="metodologia">
      <summary>Metodología</summary>
      <div class="cuerpo">
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
          o alto) y nunca como porcentaje. El «riesgo general» usa un perfil neutro; el «riesgo para tu perfil» usa el
          perfil que declaras.
        </p>
      </div>
    </details>
  `,
  styles: `
    .metodologia summary {
      cursor: pointer;
      color: var(--texto-meta);
      width: fit-content;
      transition: color var(--duracion-rapida) var(--curva);
    }
    .metodologia summary:hover,
    .metodologia[open] summary {
      color: var(--texto);
    }
    .cuerpo {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
      margin-top: var(--espacio-12);
    }
  `,
})
export class Metodologia {}
