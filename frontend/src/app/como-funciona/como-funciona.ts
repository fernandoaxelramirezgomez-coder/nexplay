import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Fuentes } from './fuentes';

export type IconoPaso = 'explorar' | 'panorama' | 'perfil' | 'nia';

export interface Paso {
  titulo: string;
  /** Lo que se lee de un vistazo: una frase. */
  linea: string;
  /** El texto completo, detrás de «Ver más». */
  texto: string;
  /** El icono y el color de la vista a la que lleva el paso, los mismos del menú. */
  icono: IconoPaso;
  enlace: { ruta: string; texto: string };
}

/** Los pasos describen qué se ve en cada lugar, no qué conviene comprar. */
export const PASOS: readonly Paso[] = [
  {
    titulo: 'Busca un juego',
    linea: 'Entre los juegos de Steam del catálogo, por nivel de riesgo.',
    texto: 'El catálogo reúne juegos de Steam ordenados en tres estantes, de menor a mayor riesgo de arrepentimiento.',
    icono: 'explorar',
    enlace: { ruta: '/explorar', texto: 'Ir al catálogo' },
  },
  {
    titulo: 'Mira su riesgo',
    linea: 'Si tiende a más o menos arrepentimiento temprano, y por qué.',
    texto:
      'La ficha muestra si el juego tiende a generar más o menos arrepentimiento temprano que el resto del catálogo, y los motivos que más aparecen en esas reseñas.',
    icono: 'panorama',
    enlace: { ruta: '/panorama', texto: 'Ver el panorama' },
  },
  {
    titulo: 'Cuéntanos cómo juegas',
    linea: 'Opcional: dice qué tanto encaja contigo; el riesgo no cambia.',
    texto:
      'Con tus géneros, lo que pagas por juego, tus horas por semana y tu tolerancia a la fricción, la ficha cuenta qué tanto encaja el juego contigo y el perfil te sugiere juegos. El riesgo no cambia: es del juego.',
    icono: 'perfil',
    enlace: { ruta: '/perfil', texto: 'Crear tu perfil' },
  },
  {
    titulo: 'Pregúntale a Nia',
    linea: 'Responde con los datos del juego que tenga a la vista.',
    texto:
      'Nia responde con los datos del juego que tenga a la vista: su riesgo de arrepentimiento, los motivos, la crítica y el precio. Tiene su propia página, está en cada ficha y asoma como burbuja en el catálogo.',
    icono: 'nia',
    enlace: { ruta: '/nia', texto: 'Hablar con Nia' },
  },
];

@Component({
  selector: 'app-como-funciona',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, Fuentes],
  template: `
    <div class="como-funciona" data-testid="como-funciona">
      <header class="cabecera">
        <p class="sobrelinea mono">Cómo funciona</p>
        <h1>Cómo funciona NexPlay</h1>
        <p class="lectura entrada">Una segunda opinión antes de comprar, hecha con reseñas de Steam.</p>
      </header>

      <ol class="pasos" data-testid="pasos">
        @for (paso of pasos; track paso.titulo; let i = $index) {
          <li class="paso" data-testid="paso" [attr.data-tono]="paso.icono">
            <div class="cabeza">
              <span class="insignia" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  @switch (paso.icono) {
                    @case ('explorar') {
                      <circle cx="12" cy="12" r="10" /><path d="m16.24 7.76-2.12 6.36-6.36 2.12 2.12-6.36z" />
                    }
                    @case ('panorama') {
                      <path d="M4 19V5" /><path d="M4 19h16" /><path d="M8 19v-6m4 6V8m4 11v-4" />
                    }
                    @case ('perfil') {
                      <circle cx="12" cy="12" r="10" /><circle cx="12" cy="10" r="3.4" />
                      <path d="M6.2 19.2a6 6 0 0 1 11.6 0" />
                    }
                    @case ('nia') {
                      <path d="M20 14.5a3 3 0 0 1-3 3H9l-4 3v-3a3 3 0 0 1-1-2.2V8a3 3 0 0 1 3-3h10a3 3 0 0 1 3 3z" />
                    }
                  }
                </svg>
              </span>
              <span class="numero mono">Paso {{ i + 1 }}</span>
            </div>
            <h2 class="titulo">{{ paso.titulo }}</h2>
            <p class="linea" data-testid="paso-linea">{{ paso.linea }}</p>
            <a class="boton-texto toque-amplio" [routerLink]="paso.enlace.ruta">{{ paso.enlace.texto }} →</a>
            <details class="mas" data-testid="paso-mas">
              <summary>Ver más <span class="solo-lector">sobre «{{ paso.titulo }}»</span></summary>
              <p class="texto">{{ paso.texto }}</p>
            </details>
          </li>
        }
      </ol>

      <section class="panel metodologia" data-testid="metodologia" aria-labelledby="titulo-metodologia">
        <h2 class="rotulo-panel" id="titulo-metodologia">Metodología</h2>
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
            <span>Es un nivel relativo al catálogo, no una probabilidad. Es del juego, no tuyo.</span>
          </li>
        </ul>
        <details class="completa" data-testid="metodologia-completa">
          <summary>Leer la metodología completa</summary>
          <p class="lectura">
            NexPlay estima el riesgo de arrepentimiento temprano al comprar un videojuego, antes de la compra. Es una
            señal <em>proxy</em>: se construye con reseñas donde el autor jugó poco (menos de 120 minutos, la ventana
            de reembolso de Steam) y calificó negativo. Steam no pregunta directamente si alguien se arrepintió.
          </p>
          <p class="lectura">
            El modelo se valida con <span class="mono">GroupKFold</span> agrupando por juego, así que el riesgo mide
            generalización a juegos que el modelo no vio, no memorización. La métrica es PR-AUC: la clase está muy
            desbalanceada (alrededor del 2.2% de las reseñas), así que la exactitud no sirve.
          </p>
          <p class="lectura">
            El riesgo ordena riesgo relativo; no es una probabilidad calibrada. Por eso se muestra como nivel (bajo,
            medio o alto) y nunca como porcentaje. El riesgo es del juego y es el mismo para todos: el perfil que
            declaras no lo cambia.
          </p>
        </details>
      </section>

      <app-fuentes />
    </div>
  `,
  styles: `
    .como-funciona {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-24);
    }
    .cabecera {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
    }
    .cabecera .sobrelinea {
      margin: 0;
    }
    .entrada {
      margin: 0;
    }
    .pasos {
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: var(--espacio-16);
    }
    /* Cada paso lleva arriba el filete del color de la vista a la que lleva. */
    .paso {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 10px;
      padding: 18px;
      border: 1px solid var(--borde);
      border-radius: var(--radio-tarjeta);
      background: var(--superficie);
      box-shadow: inset 0 3px 0 var(--tono);
    }
    .cabeza {
      display: flex;
      align-items: center;
      gap: var(--espacio-12);
    }
    .insignia {
      display: grid;
      place-items: center;
      width: 44px;
      height: 44px;
      border-radius: 12px;
      color: var(--tono);
      background: rgb(var(--tono-canal) / 0.14);
    }
    .insignia svg {
      width: 20px;
      height: 20px;
      fill: none;
      stroke: currentColor;
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .numero {
      color: var(--texto-meta);
      font-size: var(--texto-caption);
    }
    .titulo {
      margin: 0;
      font-family: var(--fuente-display);
      font-size: 19px;
      font-weight: 700;
      line-height: 1.2;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }
    .linea {
      margin: 0;
      font-size: 17px;
      line-height: 1.4;
    }
    .mas {
      margin-top: auto;
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
    .texto {
      margin: 0;
      color: var(--texto-meta);
      font-size: var(--texto-body-sm);
      line-height: var(--interlineado-largo);
    }
    .panel {
      display: flex;
      flex-direction: column;
      gap: 14px;
      padding: 22px var(--espacio-24);
      border: 1px solid var(--borde);
      border-radius: var(--radio-tarjeta);
      background: var(--superficie);
    }
    .rotulo-panel {
      margin: 0;
      font-family: var(--fuente-display);
      font-size: 22px;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
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
    .completa .lectura {
      margin: var(--espacio-8) 0 0;
    }
    @container contenido (max-width: 900px) {
      .pasos {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
      .hechos {
        grid-template-columns: 1fr;
      }
    }
    @container contenido (max-width: 560px) {
      .pasos {
        grid-template-columns: 1fr;
      }
      .panel {
        padding: 18px var(--espacio-16) 20px;
      }
    }
  `,
})
export class ComoFunciona {
  protected readonly pasos = PASOS;
}
