import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

export interface Paso {
  titulo: string;
  texto: string;
  /** A dónde lleva el paso, si tiene una página propia. */
  enlace?: { ruta: string; texto: string };
}

/** Los pasos describen qué se ve en cada lugar, no qué conviene comprar. */
export const PASOS: readonly Paso[] = [
  {
    titulo: 'Buscar un juego',
    texto: 'El catálogo reúne juegos de Steam ordenados en tres estantes, de menor a mayor riesgo general.',
    enlace: { ruta: '/', texto: 'Ir al catálogo' },
  },
  {
    titulo: 'Ver su banda y sus motivos',
    texto:
      'La ficha muestra si el juego tiende a generar más o menos arrepentimiento temprano que el resto del catálogo, y los motivos que más aparecen en esas reseñas.',
  },
  {
    titulo: 'Crear tu perfil (opcional)',
    texto:
      'Con cuántos juegos compras al año, tus horas por semana y tu tolerancia a la fricción, la estimación deja el perfil neutro y se ajusta a cómo juegas.',
    enlace: { ruta: '/perfil', texto: 'Crear tu perfil' },
  },
  {
    titulo: 'Preguntarle a Nia',
    texto:
      'Nia responde con los datos del juego abierto: su banda, los motivos, la crítica y el precio. Está en cada ficha y en la burbuja del resto de las páginas.',
  },
];

@Component({
  selector: 'app-como-funciona',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <div class="como-funciona" data-testid="como-funciona">
      <header class="hero">
        <h1>Cómo funciona NexPlay</h1>
        <p class="lectura entrada">
          Una segunda opinión antes de comprar: qué tan seguido un juego deja señales de arrepentimiento temprano, según
          las reseñas de Steam.
        </p>
      </header>

      <ol class="pasos" data-testid="pasos">
        @for (paso of pasos; track paso.titulo; let i = $index) {
          <li class="paso" data-testid="paso">
            <span class="numero mono" aria-hidden="true">{{ i + 1 }}</span>
            <h2 class="titulo">{{ paso.titulo }}</h2>
            <p class="texto">{{ paso.texto }}</p>
            @if (paso.enlace; as enlace) {
              <a class="boton-texto toque-amplio" [routerLink]="enlace.ruta">{{ enlace.texto }} →</a>
            }
          </li>
        }
      </ol>

      <section class="seccion metodologia" data-testid="metodologia" aria-labelledby="titulo-metodologia">
        <h2 class="rotulo-seccion" id="titulo-metodologia">Metodología</h2>
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
      </section>
    </div>
  `,
  styles: `
    .como-funciona {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-40);
    }
    /* Mismo hero centrado que el catálogo y el perfil. */
    .hero {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--espacio-12);
      text-align: center;
      padding: var(--espacio-24) 0 0;
    }
    .hero h1 {
      font-size: clamp(var(--texto-heading-sm), 3.5vw, var(--texto-heading));
    }
    .entrada {
      margin: 0;
    }
    .pasos {
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: var(--espacio-16);
    }
    .paso {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: var(--espacio-8);
      padding: var(--espacio-24);
      border: 1px solid var(--linea);
      border-radius: var(--radio-tarjeta);
      background: var(--superficie-tarjeta);
    }
    .numero {
      display: grid;
      place-items: center;
      width: 32px;
      height: 32px;
      border: 1px solid color-mix(in srgb, var(--neon) 55%, var(--linea));
      border-radius: var(--radio-pildora);
      color: var(--neon);
      font-size: var(--texto-caption);
      box-shadow: 0 0 12px rgba(34, 224, 255, 0.18);
    }
    .titulo {
      margin: var(--espacio-4) 0 0;
      font-size: var(--texto-body);
    }
    .texto {
      margin: 0;
      color: var(--texto-meta);
      font-size: var(--texto-body-sm);
      line-height: var(--interlineado-largo);
    }
    .paso .boton-texto {
      margin-top: auto;
    }
    .metodologia {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
    }
    .metodologia .lectura {
      margin: 0;
    }
  `,
})
export class ComoFunciona {
  protected readonly pasos = PASOS;
}
