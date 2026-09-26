import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';

import { JuegoCatalogo } from '../api/contrato';
import { NexplayApi } from '../api/nexplay-api';
import { CriticaPublico } from '../compartido/critica-publico';
import { Skeleton } from '../compartido/skeleton';
import { generosEnComun } from '../dominio/afinidad';
import { factoresVisibles } from '../dominio/factores';
import { porcentaje, textoMetacritic, textoPrecio } from '../dominio/formato';
import { segundaOpinion } from '../dominio/segunda-opinion';
import { PerfilStore } from '../estado/perfil-store';
import { FactoresModelo } from '../ficha/factores-modelo';

const MOTIVOS_VISIBLES = 3;

/** Una columna de la comparación. El nombre, la banda, el precio, la crítica y la fecha
 * viven arriba, en las cápsulas y en la tabla; aquí queda lo que hay que leer entero y no
 * cabe en una celda: la segunda opinión, los motivos y los factores.
 *
 * (documentación anterior) Una columna de la comparación. Sus secciones son filas de un subgrid, así la
 * segunda opinión, los motivos, los factores y la ficha técnica empiezan a la misma
 * altura en todas las columnas. */
@Component({
  selector: 'app-columna-comparar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, Skeleton, FactoresModelo, CriticaPublico],
  template: `
    <article class="columna" data-testid="columna-comparar" [attr.data-appid]="juego().appid">
      <h2 class="nombre">
        <a class="toque-amplio" [routerLink]="['/juego', juego().appid]">{{ juego().nombre }}</a>
      </h2>

      <section class="bloque">
        <h3 class="titulo-bloque meta">Segunda opinión</h3>
        @if (opinion().length) {
          <p class="texto">
            @for (segmento of opinion(); track $index) {
              @if (segmento.clave) {
                <strong>{{ segmento.texto }}</strong>
              } @else {
                {{ segmento.texto }}
              }
            }
          </p>
        } @else {
          <app-skeleton alto="64px" />
        }
      </section>

      <section class="bloque">
        <h3 class="titulo-bloque meta">Motivos principales</h3>
        @if (motivos().length) {
          <ul class="motivos">
            @for (motivo of motivos(); track motivo.motivo) {
              <li class="motivo">
                <span>{{ motivo.motivo }}</span>
                <span class="pista"><span class="barra" [style.width.%]="motivo.frecuencia * 100"></span></span>
                <span class="mono valor">{{ pct(motivo.frecuencia) }}</span>
              </li>
            }
          </ul>
          <p class="meta cuantas" data-testid="columna-motivos-n">
            Sobre {{ clasificadas() }} {{ clasificadas() === 1 ? 'reseña clasificada' : 'reseñas clasificadas' }}.
            @if (clasificadas() < 10) {
              Con tan pocas, tómalo como una pista.
            }
          </p>
        } @else {
          <p class="meta">Sin motivos: muy pocas reseñas de arrepentimiento temprano.</p>
        }
      </section>

      <section class="bloque">
        <h3 class="titulo-bloque meta">Factores del modelo</h3>
        @if (factores().length) {
          <app-factores-modelo
            [factores]="factores()"
            [metacritic]="juego().metacritic"
            [promedio]="promedioMetacritic()"
          />
        } @else {
          <p class="meta">Sin factores que mostrar.</p>
        }
      </section>

      <app-critica-publico
        [juego]="juego()"
        [promedio]="promedioMetacritic()"
        [conNexplay]="true"
        [angosto]="true"
      />

      @if (muestraAfinidad()) {
        <p class="meta mono afinidad" data-testid="columna-afinidad">
          @if (generosAfines().length) {
            Dentro de tus géneros: {{ generosAfines().join(', ') }}
          } @else {
            Fuera de tus géneros habituales
          }
        </p>
      }

    </article>
  `,
  styles: `
    /* Dos niveles de subgrid (host y artículo) para heredar las filas de .columnas. */
    :host,
    .columna {
      display: grid;
      grid-row: 1 / -1;
      grid-template-rows: subgrid;
    }
    .columna {
      background: var(--superficie-tarjeta);
      border-radius: var(--radio-tarjeta);
      overflow: hidden;
      align-content: start;
    }
    .columna > *:not(app-portada) {
      padding-inline: var(--espacio-16);
    }
    .nombre {
      font-size: var(--texto-body);
      padding-top: var(--espacio-12);
    }
    .nombre a {
      text-decoration: none;
    }
    .veredicto {
      margin: 0;
      padding-left: var(--espacio-12);
      border-left: 4px solid;
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .veredicto[data-banda='bajo'] {
      border-color: var(--banda-bajo-texto);
    }
    .veredicto[data-banda='medio'] {
      border-color: var(--banda-medio-texto);
    }
    .veredicto[data-banda='alto'] {
      border-color: var(--banda-alto-texto);
    }
    .rotulo {
      font-size: var(--texto-caption);
      color: var(--texto-meta);
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }
    .titular {
      font-size: var(--texto-subheading);
    }
    .veredicto[data-banda='bajo'] .palabra {
      color: var(--banda-bajo-texto);
    }
    .veredicto[data-banda='medio'] .palabra {
      color: var(--banda-medio-texto);
    }
    .veredicto[data-banda='alto'] .palabra {
      color: var(--banda-alto-texto);
    }
    .fila-veredicto,
    .bloque,
    .datos,
    .afinidad,
    .fila-accion {
      padding-top: var(--espacio-12);
    }
    .titulo-bloque {
      font-size: var(--texto-caption);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: var(--espacio-8);
    }
    .texto {
      margin: 0;
      font-size: var(--texto-body-sm);
      line-height: var(--interlineado-largo);
    }
    .cuantas {
      margin: var(--espacio-8) 0 0;
      line-height: var(--interlineado-largo);
    }
    .motivos {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: var(--espacio-8);
      font-size: var(--texto-body-sm);
    }
    /* En columna angosta la barra va debajo, a todo el ancho. */
    .motivo {
      display: grid;
      grid-template-columns: 1fr auto;
      grid-template-areas: 'nombre valor' 'pista pista';
      gap: var(--espacio-4) var(--espacio-8);
    }
    .motivo > span:first-child {
      grid-area: nombre;
    }
    .pista {
      grid-area: pista;
      height: 8px;
      border-radius: var(--radio-pildora);
      background: var(--superficie-lienzo);
      overflow: hidden;
    }
    .barra {
      display: block;
      height: 100%;
      background: var(--neon);
    }
    .valor {
      grid-area: valor;
      text-align: right;
      color: var(--texto-meta);
      font-size: var(--texto-caption);
    }
    .datos {
      margin: 0;
      display: flex;
      flex-direction: column;
      gap: var(--espacio-4);
      font-size: var(--texto-caption);
    }
    .datos div {
      display: flex;
      gap: var(--espacio-8);
    }
    .datos dd {
      margin: 0;
    }
    .afinidad {
      margin: 0;
    }
    .fila-accion {
      display: flex;
      align-items: end;
      padding-bottom: var(--espacio-16);
    }
  `,
})
export class ColumnaComparar {
  readonly juego = input.required<JuegoCatalogo>();
  /** Promedio de Metacritic del catálogo, para el factor de la nota. */
  readonly promedioMetacritic = input<number | null>(null);

  private readonly api = inject(NexplayApi);
  private readonly perfil = inject(PerfilStore);

  private readonly prediccionRecurso = rxResource({
    params: () => {
      const perfil = this.perfil.efectivo();
      return perfil ? { perfil, appid: this.juego().appid } : undefined;
    },
    stream: ({ params }) => this.api.predecir(params),
  });

  private readonly explicacionRecurso = rxResource({
    params: () => this.juego().appid,
    stream: ({ params }) => this.api.explicacion(params),
  });

  protected readonly prediccion = this.prediccionRecurso.value;

  protected readonly clasificadas = computed(() => {
    const datos = this.explicacionRecurso.value();
    return datos ? Math.round(datos.n_casos * datos.pct_clasificados) : 0;
  });

  protected readonly motivos = computed(
    () => this.explicacionRecurso.value()?.motivos.slice(0, MOTIVOS_VISIBLES) ?? [],
  );

  protected readonly opinion = computed(() => {
    const prediccion = this.prediccion();
    if (!prediccion || this.explicacionRecurso.isLoading()) {
      return [];
    }
    return segundaOpinion(
      prediccion.nivel,
      this.explicacionRecurso.value()?.motivos ?? [],
      this.juego().metacritic,
      this.factores().some((factor) => factor.etiqueta === 'nota de Metacritic'),
      this.clasificadas(),
    );
  });

  protected readonly factores = computed(() => {
    const prediccion = this.prediccion();
    return prediccion ? factoresVisibles(prediccion.factores, this.juego()) : [];
  });

  protected readonly generosAfines = computed(() =>
    generosEnComun(this.juego().generos, this.perfil.perfil()?.tags_preferidos ?? []),
  );
  protected readonly muestraAfinidad = computed(() => (this.perfil.perfil()?.tags_preferidos.length ?? 0) > 0);

  protected readonly metacritic = computed(() => textoMetacritic(this.juego().metacritic));
  protected readonly precio = computed(() => textoPrecio(this.juego()));
  protected readonly pct = porcentaje;
}
