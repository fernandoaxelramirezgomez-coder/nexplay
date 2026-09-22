import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';

import { JuegoCatalogo } from '../api/contrato';
import { NexplayApi } from '../api/nexplay-api';
import { Portada } from '../compartido/portada';
import { Skeleton } from '../compartido/skeleton';
import { generosEnComun } from '../dominio/afinidad';
import { ROTULO_RIESGO } from '../dominio/etiqueta-riesgo';
import { factoresVisibles } from '../dominio/factores';
import { porcentaje, textoMetacritic, textoPrecio } from '../dominio/formato';
import { segundaOpinion } from '../dominio/segunda-opinion';
import { CompararStore } from '../estado/comparar-store';
import { PerfilStore } from '../estado/perfil-store';
import { FactoresModelo } from '../ficha/factores-modelo';

const MOTIVOS_VISIBLES = 3;

/** Una columna de la comparación. Sus secciones son filas de un subgrid, así la
 * segunda opinión, los motivos, los factores y la ficha técnica empiezan a la misma
 * altura en todas las columnas. */
@Component({
  selector: 'app-columna-comparar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, Portada, Skeleton, FactoresModelo],
  template: `
    <article class="columna" data-testid="columna-comparar" [attr.data-appid]="juego().appid">
      <app-portada [src]="juego().portada_url" [prioritaria]="true" radio="0" />

      <h2 class="nombre">
        <a class="toque-amplio" [routerLink]="['/juego', juego().appid]">{{ juego().nombre }}</a>
      </h2>

      <div class="fila-veredicto">
        @if (prediccion(); as prediccion) {
          <p class="veredicto" [attr.data-banda]="prediccion.nivel">
            <span class="rotulo mono">{{ rotulo }}</span>
            <span class="titular">Riesgo <span class="palabra">{{ prediccion.nivel }}</span></span>
          </p>
        } @else if (error()) {
          <p class="meta">No se pudo calcular el riesgo.</p>
        } @else {
          <app-skeleton alto="44px" radio="var(--radio-boton)" />
        }
      </div>

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

      <dl class="datos mono">
        <div><dt class="meta">Crítica</dt><dd>{{ metacritic() }}</dd></div>
        <div><dt class="meta">Precio</dt><dd>{{ precio() }}</dd></div>
        <div><dt class="meta">Lanzamiento</dt><dd>{{ juego().fecha_lanzamiento ?? 'Sin fecha' }}</dd></div>
      </dl>

      @if (muestraAfinidad()) {
        <p class="meta mono afinidad" data-testid="columna-afinidad">
          @if (generosAfines().length) {
            Dentro de tus géneros: {{ generosAfines().join(', ') }}
          } @else {
            Fuera de tus géneros habituales
          }
        </p>
      }

      <div class="fila-accion">
        <button type="button" class="boton-fantasma" data-testid="quitar-comparar" (click)="comparar.quitar(juego().appid)">
          Quitar
        </button>
      </div>
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
      border-color: var(--banda-bajo);
    }
    .veredicto[data-banda='medio'] {
      border-color: var(--banda-medio);
    }
    .veredicto[data-banda='alto'] {
      border-color: var(--banda-alto);
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
      color: var(--banda-bajo);
    }
    .veredicto[data-banda='medio'] .palabra {
      color: var(--banda-medio);
    }
    .veredicto[data-banda='alto'] .palabra {
      color: var(--banda-alto);
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
  protected readonly comparar = inject(CompararStore);

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
  protected readonly error = computed(() => this.prediccionRecurso.error());
  protected readonly rotulo = ROTULO_RIESGO;

  protected readonly motivos = computed(
    () => this.explicacionRecurso.value()?.motivos.slice(0, MOTIVOS_VISIBLES) ?? [],
  );

  protected readonly opinion = computed(() => {
    const prediccion = this.prediccion();
    if (!prediccion || this.explicacionRecurso.isLoading()) {
      return [];
    }
    return segundaOpinion(prediccion.nivel, this.explicacionRecurso.value()?.motivos ?? [], this.juego().metacritic);
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
