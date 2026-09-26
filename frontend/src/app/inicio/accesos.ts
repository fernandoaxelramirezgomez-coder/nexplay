import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

interface Acceso {
  ruta: string;
  /** Decorativo: va con aria-hidden y nunca carga el significado solo. */
  emoji: string;
  titulo: string;
  texto: string;
}

const ACCESOS: readonly Acceso[] = [
  {
    ruta: '/explorar',
    emoji: '🎮',
    titulo: 'Explorar',
    texto: '123 juegos de Steam repartidos en tres estantes, de menor a mayor riesgo general.',
  },
  {
    ruta: '/comparar',
    emoji: '⚖️',
    titulo: 'Comparar',
    texto: 'Hasta cuatro juegos lado a lado: banda, motivos, factores y ficha técnica.',
  },
  {
    ruta: '/nia',
    emoji: '💬',
    titulo: 'Preguntar a Nia',
    texto: 'Responde con los datos del juego que elijas. No recomienda comprar ni no comprar.',
  },
  {
    ruta: '/panorama',
    emoji: '📊',
    titulo: 'Ver el panorama',
    texto: 'Cómo se reparte el catálogo y qué hay en las reseñas que lo sostienen.',
  },
];

/** Los cuatro accesos del inicio: para qué sirve cada parte del sitio, en una frase. */
@Component({
  selector: 'app-accesos',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <section class="accesos" aria-labelledby="titulo-accesos" data-testid="inicio-accesos">
      <h2 class="rotulo-seccion" id="titulo-accesos">Qué puedes hacer aquí</h2>
      <ul class="rejilla">
        @for (acceso of accesos; track acceso.ruta) {
          <li>
            <a
              class="acceso panel-vidrio"
              [routerLink]="acceso.ruta"
              [attr.data-testid]="'acceso-' + acceso.ruta.slice(1)"
            >
              <span class="emoji" aria-hidden="true">{{ acceso.emoji }}</span>
              <span class="titulo">{{ acceso.titulo }}</span>
              <span class="texto meta">{{ acceso.texto }}</span>
              <span class="flecha" aria-hidden="true">→</span>
            </a>
          </li>
        }
      </ul>
    </section>
  `,
  styles: `
    .accesos {
      padding-top: var(--espacio-24);
      border-top: var(--filete);
    }
    .rejilla {
      list-style: none;
      margin: var(--espacio-16) 0 0;
      padding: 0;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(min(100%, 230px), 1fr));
      gap: var(--espacio-12);
    }
    /* El emoji en una columna de ancho fijo: con 'auto', cada uno mide lo suyo y el
       título de cada tarjeta empezaba en un sitio distinto. La fila del medio se lleva el
       hueco que sobra, así las cuatro flechas quedan a la misma altura. */
    .acceso {
      display: grid;
      grid-template-columns: 28px minmax(0, 1fr);
      grid-template-rows: auto 1fr auto;
      align-items: start;
      gap: var(--espacio-4) var(--espacio-12);
      height: 100%;
      padding: var(--espacio-16);
      color: inherit;
      text-decoration: none;
      transition:
        border-color var(--duracion-rapida) var(--curva),
        transform var(--duracion-rapida) var(--curva);
    }
    .acceso:hover {
      border-color: var(--neon);
      transform: translateY(-2px);
    }
    .emoji {
      grid-area: 1 / 1;
      align-self: center;
      font-size: 22px;
      line-height: 1;
      text-align: center;
    }
    .titulo {
      grid-area: 1 / 2;
      align-self: center;
      font-size: var(--texto-body-sm);
    }
    .texto {
      grid-area: 2 / 2;
      line-height: var(--interlineado-largo);
    }
    .flecha {
      grid-area: 3 / 2;
      align-self: end;
      color: var(--neon);
    }
  `,
})
export class Accesos {
  protected readonly accesos = ACCESOS;
}
