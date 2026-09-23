import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { PildoraBanda } from '../compartido/pildora-banda';
import { Portada } from '../compartido/portada';
import { textoMetacritic, textoPrecio } from '../dominio/formato';
import { NOTA_DESEMPATE, hayEmpates, porQueCoincide, sugerenciasPara } from '../dominio/sugerencias';
import { CatalogoStore } from '../estado/catalogo-store';
import { PerfilStore } from '../estado/perfil-store';

/** Juegos del catálogo que comparten géneros con los declarados en el perfil.
 *
 * Es lo único del sitio donde el perfil declarado hace algo, y por eso la sección dice
 * dos veces de dónde sale cada cosa: la coincidencia viene de los géneros que la persona
 * eligió; la banda de riesgo, del modelo, que solo usa datos del juego. No se mezclan en
 * un mismo número ni en una misma frase.
 *
 * No es un modelo: no hay ningún dato que diga si a alguien le gustó un juego, así que
 * esto no se puede medir como el riesgo (ver docs/evidencia/README.md). */
@Component({
  selector: 'app-sugerencias-perfil',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, PildoraBanda, Portada],
  template: `
    <section class="seccion sugerencias" data-testid="sugerencias" aria-labelledby="titulo-sugerencias">
      <h2 class="rotulo-seccion" id="titulo-sugerencias">Juegos con características parecidas a lo que declaraste</h2>
      <p class="lectura entrada">
        Esto no es una recomendación de compra ni una predicción: son juegos del catálogo que comparten géneros con los
        que elegiste. El riesgo de cada uno se calcula aparte, solo con datos del juego, y no cambia con lo que
        declares.
      </p>

      @switch (resultado().motivo) {
        @case ('sin-generos') {
          <p class="meta" data-testid="sugerencias-sin-generos">
            No declaraste géneros, así que no hay con qué comparar.
          </p>
        }
        @case ('sin-candidatos') {
          <p class="meta" data-testid="sugerencias-sin-candidatos">
            Ningún juego del catálogo comparte los géneros que elegiste.
          </p>
        }
        @default {
          <ul class="lista" data-testid="sugerencias-lista">
            @for (sugerencia of resultado().sugerencias; track sugerencia.juego.appid) {
              <li class="juego" [attr.data-appid]="sugerencia.juego.appid" data-testid="sugerencia">
                <a class="enlace" [routerLink]="['/juego', sugerencia.juego.appid]">
                  <app-portada [src]="sugerencia.juego.portada_url" radio="0" />
                  <div class="cuerpo">
                    <h3 class="nombre">{{ sugerencia.juego.nombre }}</h3>
                    <p class="porque" data-testid="sugerencia-porque">{{ porque(sugerencia) }}</p>
                    <p class="datos mono">
                      {{ precio(sugerencia.juego) }} · {{ critica(sugerencia.juego.metacritic) }}
                    </p>
                    <app-pildora-banda [banda]="sugerencia.juego.banda_riesgo" />
                    @if (sugerencia.juego.banda_riesgo === 'alto') {
                      <span class="nota-alto" data-testid="sugerencia-nota-alto"
                        >Su segunda opinión detalla los motivos más frecuentes <span aria-hidden="true">→</span></span
                      >
                    }
                  </div>
                </a>
              </li>
            }
          </ul>
          <p class="meta" data-testid="sugerencias-cuantos">
            {{ cuantos() }}
            @if (empatan()) {
              {{ notaDesempate }}
            }
          </p>
        }
      }
    </section>
  `,
  styles: `
    .sugerencias {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
    }
    .entrada {
      margin: 0;
      color: var(--texto-meta);
      font-size: var(--texto-body-sm);
    }
    .lista {
      list-style: none;
      margin: var(--espacio-12) 0 0;
      padding: 0;
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: var(--espacio-16);
    }
    .juego {
      border: 1px solid var(--linea);
      border-radius: var(--radio-tarjeta);
      background: var(--superficie-tarjeta);
      overflow: hidden;
      transition:
        border-color var(--duracion) var(--curva),
        transform var(--duracion) var(--curva);
    }
    .juego:hover {
      border-color: var(--neon);
      transform: translateY(-2px);
    }
    .enlace {
      display: flex;
      flex-direction: column;
      height: 100%;
      color: inherit;
      text-decoration: none;
    }
    .cuerpo {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: var(--espacio-8);
      padding: var(--espacio-16);
    }
    .nombre {
      margin: 0;
      font-size: var(--texto-body);
    }
    .porque {
      margin: 0;
      color: var(--texto-meta);
      font-size: var(--texto-caption);
      line-height: var(--interlineado-largo);
    }
    /* Solo en banda alta: la tarjeta ya lleva a la ficha, y aquí se dice qué hay ahí.
       Describe lo que se va a encontrar; no dice qué hacer con ello. */
    .nota-alto {
      color: var(--neon);
      font-size: var(--texto-caption);
      line-height: var(--interlineado-largo);
    }
    .datos {
      margin: 0;
      color: var(--texto-meta);
      font-size: var(--texto-caption);
    }
    .meta {
      margin: 0;
    }
  `,
})
export class SugerenciasPerfil {
  private readonly catalogo = inject(CatalogoStore);
  private readonly perfil = inject(PerfilStore);

  protected readonly resultado = computed(() => sugerenciasPara(this.catalogo.juegos(), this.perfil.perfil()));

  protected readonly cuantos = computed(() => {
    const { candidatos, sugerencias } = this.resultado();
    const juegos = candidatos === 1 ? 'juego comparte' : 'juegos comparten';
    const mostrados = candidatos > sugerencias.length ? `; se muestran ${sugerencias.length}` : '';
    return `En el catálogo, ${candidatos} ${juegos} géneros con los que elegiste${mostrados}.`;
  });

  protected porque(sugerencia: Parameters<typeof porQueCoincide>[0]): string {
    return porQueCoincide(sugerencia, this.catalogo.juegos().length);
  }

  protected readonly empatan = computed(() => hayEmpates(this.resultado().sugerencias));
  protected readonly notaDesempate = NOTA_DESEMPATE;

  protected precio = textoPrecio;
  protected critica = textoMetacritic;
}
