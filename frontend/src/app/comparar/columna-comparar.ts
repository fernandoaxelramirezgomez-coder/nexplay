import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';

import { JuegoCatalogo } from '../api/contrato';
import { NexplayApi } from '../api/nexplay-api';
import { PildoraBanda } from '../compartido/pildora-banda';
import { Portada } from '../compartido/portada';
import { Skeleton } from '../compartido/skeleton';
import { generosEnComun } from '../dominio/afinidad';
import { rotuloRiesgo } from '../dominio/etiqueta-riesgo';
import { factoresVisibles, fraseFactor } from '../dominio/factores';
import { porcentaje, textoMetacritic, textoPrecio } from '../dominio/formato';
import { segundaOpinion } from '../dominio/segunda-opinion';
import { CompararStore } from '../estado/comparar-store';
import { PerfilStore } from '../estado/perfil-store';

const MOTIVOS_VISIBLES = 3;

@Component({
  selector: 'app-columna-comparar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, Portada, PildoraBanda, Skeleton],
  template: `
    <article class="columna tarjeta" data-testid="columna-comparar" [attr.data-appid]="juego().appid">
      <app-portada [src]="juego().portada_url" [prioritaria]="true" />
      <h2 class="nombre">
        <a [routerLink]="['/juego', juego().appid]">{{ juego().nombre }}</a>
      </h2>

      @if (prediccion(); as prediccion) {
        <app-pildora-banda [banda]="prediccion.nivel" [rotulo]="rotulo()" />
      } @else if (error()) {
        <p class="meta">No se pudo calcular el riesgo.</p>
      } @else {
        <app-skeleton alto="24px" radio="var(--radio-pildora)" />
      }

      <section>
        <h3 class="rotulo meta">Segunda opinión</h3>
        @if (opinion().length) {
          <p class="lectura texto">
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

      <section>
        <h3 class="rotulo meta">Motivos principales</h3>
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

      <section>
        <h3 class="rotulo meta">Factores del modelo</h3>
        @if (factores().length) {
          <ul class="factores">
            @for (factor of factores(); track factor.etiqueta) {
              <li>{{ frasePara(factor) }}</li>
            }
          </ul>
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
        <p class="meta mono" data-testid="columna-afinidad">
          @if (generosAfines().length) {
            Dentro de tus géneros: {{ generosAfines().join(', ') }}
          } @else {
            Fuera de tus géneros habituales
          }
        </p>
      }

      <button type="button" class="boton-fantasma" data-testid="quitar-comparar" (click)="comparar.quitar(juego().appid)">
        Quitar
      </button>
    </article>
  `,
  styles: `
    .columna {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: var(--espacio-12);
      padding: var(--espacio-16);
      height: 100%;
    }
    .nombre {
      font-size: var(--texto-body);
    }
    .nombre a {
      text-decoration: none;
    }
    .rotulo {
      font-size: var(--texto-caption);
      text-transform: uppercase;
      letter-spacing: 0.04em;
      margin-bottom: var(--espacio-8);
    }
    .texto {
      font-size: var(--texto-body-sm);
      margin: 0;
    }
    .motivos,
    .factores {
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
      background: var(--texto);
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
    button {
      margin-top: auto;
    }
  `,
})
export class ColumnaComparar {
  readonly juego = input.required<JuegoCatalogo>();

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
  protected readonly rotulo = computed(() => rotuloRiesgo(this.perfil.hayPerfil()));

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
  protected readonly frasePara = fraseFactor;
}
