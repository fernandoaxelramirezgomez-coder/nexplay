import { ChangeDetectionStrategy, Component, inject } from '@angular/core';

import { numero, porcentaje, porcentajeFino } from '../dominio/formato';
import { PanoramaStore } from '../estado/panorama-store';

/** Lo que el catálogo servido no sabe de sí mismo: con qué corte se entrenó el modelo.
 * Sale de docs/evidencia/README.md, que es la salida de esa validación; si algún día se
 * reentrena, estos cuatro números se actualizan ahí y aquí. */
const ENTRENAMIENTO = {
  release: 'data-v1',
  juegos: 83,
  resenas: 123972,
  juegosPrueba: 40,
  prAuc: 0.0356,
  prAucTrivial: 0.0234,
};

/** Las tres fuentes, con un enlace a cada una. appdetails no tiene documentación oficial
 * de Steam: se enlaza una respuesta real, que es lo más honesto que hay. La nota de
 * Metacritic llega dentro de appdetails. */
const ORIGENES = [
  {
    quien: 'Steam',
    api: 'appreviews',
    que: 'Las reseñas, su voto y las horas que llevaba jugadas quien escribió cada una.',
    enlace: 'https://partner.steamgames.com/doc/store/getreviews',
    textoEnlace: 'Documentación de Steam',
  },
  {
    quien: 'Steam',
    api: 'appdetails',
    que: 'Precio, géneros, fecha de lanzamiento, descripción y tráileres de cada juego.',
    enlace: 'https://store.steampowered.com/api/appdetails?appids=1938010',
    textoEnlace: 'Ver una respuesta de ejemplo',
  },
  {
    quien: 'Metacritic',
    api: 'nota de la crítica',
    que: 'La calificación de la crítica; llega a través de appdetails de Steam.',
    enlace: 'https://www.metacritic.com/',
    textoEnlace: 'metacritic.com',
  },
] as const;

/** De dónde salen los datos, con las cifras de la base y no escritas a mano, y qué no es
 * NexPlay. Va junto: el tamaño de la muestra y sus límites se leen mejor de corrido. */
@Component({
  selector: 'app-fuentes-datos',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="fuentes" aria-labelledby="titulo-fuentes" data-testid="inicio-fuentes">
      <h2 class="rotulo-seccion" id="titulo-fuentes">De dónde salen los datos</h2>

      <ul class="origenes" data-testid="inicio-origenes">
        @for (origen of origenes; track origen.api) {
          <li class="origen">
            <span class="quien">{{ origen.quien }}</span>
            <span class="api mono">{{ origen.api }}</span>
            <p>{{ origen.que }}</p>
            <a [href]="origen.enlace" target="_blank" rel="noopener">{{ origen.textoEnlace }} ↗</a>
          </li>
        }
      </ul>

      @if (datos(); as p) {
        <ol class="cadena" data-testid="cadena-datos">
          <li>
            <span class="cifra mono">{{ num(p.resenas_en_steam) }}</span>
            <span class="que">reseñas que Steam reporta para estos juegos</span>
          </li>
          <li>
            <span class="cifra mono">{{ num(p.resenas_descargadas) }}</span>
            <span class="que">
              descargadas con la API <span class="mono">appreviews</span> de Steam, el
              <strong>{{ pct(p.cobertura) }}</strong> de esas, repartidas en {{ p.juegos }} juegos y escritas
              entre <span class="fecha">{{ p.ventana.desde }}</span> y
              <span class="fecha">{{ p.ventana.hasta }}</span>
            </span>
          </li>
          <li>
            <span class="cifra mono">{{ num(p.casos_senal) }}</span>
            <span class="que">
              traen señal de arrepentimiento temprano: menos de 120 minutos jugados (la ventana en la que
              Steam devuelve el dinero) y voto negativo. Son el <strong>{{ pctFino(p.prevalencia) }}</strong>
              de la muestra.
            </span>
          </li>
          <li>
            <span class="cifra mono">{{ num(entrenamiento.resenas) }}</span>
            <span class="que">
              son las que entrenan el modelo: el corte <span class="mono">{{ entrenamiento.release }}</span>,
              de {{ entrenamiento.juegos }} juegos. Los otros {{ entrenamiento.juegosPrueba }} títulos del
              catálogo nunca entraron al entrenamiento; con ellos se probó después, y ahí el modelo sacó
              PR-AUC {{ entrenamiento.prAuc }} contra {{ entrenamiento.prAucTrivial }} de un clasificador
              trivial.
            </span>
          </li>
        </ol>

        <h2 class="rotulo-seccion" id="titulo-limites">Qué no es</h2>
        <ul class="limites" data-testid="inicio-limites">
          <li>
            Es una muestra, no el censo: el {{ pct(p.cobertura) }} de las reseñas que Steam reporta, las más
            recientes de cada juego.
          </li>
          <li>
            Casi todas están en inglés, {{ num(p.muestra.resenas_en_ingles) }} de
            {{ num(p.resenas_descargadas) }}. Lo que se dice en otros idiomas no entró.
          </li>
          <li>
            La señal es un indicio, no una predicción. Steam nunca pregunta si alguien se arrepintió; lo que se
            toma como pista es haber jugado poco y haber calificado negativo.
          </li>
          <li>
            El riesgo es del juego y no tuyo. Es el mismo para todos, tu perfil no lo mueve, y lo que el perfil
            sí hace es decir qué tanto encaja un juego contigo, que es otra cosa.
          </li>
        </ul>

        <p class="meta ficha-tecnica">
          El {{ pct(p.muestra.compradas_en_steam) }} de esas reseñas son de gente que compró el juego en
          Steam y el {{ pct(p.muestra.con_voto_util) }} recibieron al menos un voto de «útil». El
          {{ pct(p.muestra.perfiles_privados) }} vienen de perfiles privados, que no dejan ver cuántos juegos
          tiene quien escribe: por eso el modelo mira el juego y no a la persona.
        </p>
      } @else if (panorama.cargando()) {
        <p class="meta" role="status">Contando las reseñas…</p>
      } @else {
        <p class="meta" role="alert" data-testid="inicio-fuentes-error">
          No se pudo leer el panorama de la muestra. Revisa que la API esté corriendo.
        </p>
      }
    </section>
  `,
  styles: `
    .fuentes {
      padding-top: var(--espacio-24);
      border-top: var(--filete);
    }
    .origenes {
      list-style: none;
      margin: var(--espacio-16) 0 var(--espacio-40);
      padding: 0;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(min(100%, 240px), 1fr));
      gap: var(--espacio-12);
    }
    .origen {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-8);
      padding: 18px;
      border: 1px solid var(--borde);
      border-radius: var(--radio-tarjeta);
      background: var(--superficie);
    }
    .quien {
      font-family: var(--fuente-display);
      font-size: 18px;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }
    .api {
      color: var(--neon);
    }
    .origen p {
      flex: 1;
      margin: 0;
      color: var(--texto-meta);
      line-height: 1.45;
    }
    .origen a {
      color: var(--enlace);
      text-underline-offset: 4px;
    }
    .rotulo-seccion + .rotulo-seccion,
    .cadena + .rotulo-seccion {
      margin-top: var(--espacio-40);
    }
    .cadena {
      list-style: none;
      margin: var(--espacio-16) 0 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: var(--espacio-16);
    }
    /* 11rem: la cifra más larga del catálogo (18,313,851) no cabía en 8.5rem y se salía
       de su columna, así que era la única que no alineaba con las demás. */
    .cadena li {
      display: grid;
      grid-template-columns: 11rem minmax(0, 1fr);
      gap: var(--espacio-16);
      align-items: baseline;
    }
    /* El hilo que une los pasos: la cadena se lee como una sola cuenta que se estrecha. */
    .cadena li + li {
      padding-top: var(--espacio-16);
      border-top: var(--filete);
    }
    /* Una sola tinta para las cuatro: en dos colores parecía que dos cifras eran de otra
       cuenta, y son la misma que se va estrechando. */
    .cifra {
      font-size: var(--texto-subheading);
      line-height: 1.1;
      text-align: right;
      color: var(--texto);
    }
    .que {
      max-width: var(--medida-lectura);
      color: var(--texto-meta);
      font-size: var(--texto-body-sm);
      line-height: var(--interlineado-largo);
    }
    .que strong {
      color: var(--texto);
    }
    /* Una fecha partida por la mitad al final del renglón se lee como dos cosas. */
    .fecha {
      white-space: nowrap;
    }
    /* Cuatro límites en dos columnas cuando hay ancho: en una sola, la mitad derecha de
       la sección quedaba vacía y la lista se iba muy abajo. */
    .limites {
      margin: var(--espacio-16) 0 0;
      padding-inline-start: var(--espacio-24);
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(min(100%, 24rem), 1fr));
      gap: var(--espacio-12) var(--espacio-40);
      font-size: var(--texto-body-sm);
      line-height: var(--interlineado-largo);
    }
    .limites li {
      max-width: var(--medida-lectura);
    }
    .ficha-tecnica {
      margin-top: var(--espacio-24);
      max-width: var(--medida-lectura);
      line-height: var(--interlineado-largo);
    }
    @media (max-width: 640px) {
      .cadena li {
        grid-template-columns: 1fr;
        gap: var(--espacio-4);
      }
      .cifra {
        text-align: start;
      }
    }
  `,
})
export class FuentesDatos {
  protected readonly panorama = inject(PanoramaStore);
  protected readonly datos = this.panorama.datos;
  protected readonly entrenamiento = ENTRENAMIENTO;
  protected readonly origenes = ORIGENES;

  protected readonly num = numero;
  protected readonly pct = porcentaje;
  protected readonly pctFino = porcentajeFino;
}
