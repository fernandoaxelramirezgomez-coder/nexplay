import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { PildoraBanda } from '../compartido/pildora-banda';
import { Portada } from '../compartido/portada';
import { ValoresPerfil } from '../dominio/opciones-perfil';
import { NOTA_DESEMPATE, criteriosDesde, hayEmpates, sugerenciasPara } from '../dominio/sugerencias';
import { CatalogoStore } from '../estado/catalogo-store';
import { PanoramaStore } from '../estado/panorama-store';

const PESOS = new Intl.NumberFormat('es-MX', { maximumFractionDigits: 0 });

/** Sugerencias según el perfil: juegos del catálogo que encajan con lo declarado —géneros,
 * gasto, horas y fricción—, recalculadas en vivo con lo que se está respondiendo, antes de
 * guardar.
 *
 * Es lo único del sitio donde el perfil declarado hace algo, y por eso la sección dice de
 * dónde sale cada cosa: las razones vienen de lo declarado; el riesgo, del modelo, que
 * solo usa datos del juego. Van por separado, rotuladas, y el riesgo no ordena la lista.
 *
 * No es un modelo: no hay ningún dato que diga si a alguien le gustó un juego, así que
 * esto no se puede medir como el riesgo (ver docs/evidencia/README.md). */
@Component({
  selector: 'app-sugerencias-perfil',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, PildoraBanda, Portada],
  template: `
    <section class="sugerencias" data-testid="sugerencias" aria-labelledby="titulo-sugerencias">
      <div class="cabecera">
        <h2 id="titulo-sugerencias">Sugerencias según tu perfil</h2>
        <span class="etiqueta" data-testid="sugerencias-etiqueta">No cambian el riesgo del juego</span>
        <span class="en-vivo">Se recalculan mientras respondes</span>
      </div>
      <p class="entrada">
        Juegos del catálogo que encajan con lo que declaraste. Esto no es una recomendación de compra ni una
        predicción: el riesgo de cada juego se calcula aparte, solo con datos del juego, y no se usa para ordenar.
      </p>
      @if (soloConsolas()) {
        <p class="aviso" data-testid="sugerencias-solo-consolas">
          Estos juegos son de Steam (PC); no hay dato de en qué consolas salió cada uno.
        </p>
      }

      @switch (resultado().motivo) {
        @case ('sin-respuestas') {
          <p class="aviso" data-testid="sugerencias-sin-respuestas">
            Responde tus géneros, cuánto pagas por juego, tus horas o tu tolerancia a la fricción, y aquí aparecen
            juegos que encajan.
          </p>
        }
        @case ('sin-candidatos') {
          <p class="aviso" data-testid="sugerencias-sin-candidatos">
            Ningún juego del catálogo comparte los géneros que elegiste.
          </p>
        }
        @default {
          @if (resultado().topeRelajado; as relajado) {
            <p class="aviso" role="status" data-testid="sugerencias-tope-relajado">
              Con tu tope de {{ pesos(relajado.pedido) }} por juego no queda ningún juego
              {{ valores().generos.length ? 'de tus géneros' : 'del catálogo' }}; se muestran
              {{ relajado.usado === null ? 'sin tope' : 'hasta ' + pesos(relajado.usado) }}.
            </p>
          }
          <ul class="lista" data-testid="sugerencias-lista">
            @for (sugerencia of resultado().sugerencias; track sugerencia.juego.appid) {
              <li class="juego" [attr.data-appid]="sugerencia.juego.appid" data-testid="sugerencia">
                <a class="enlace" [routerLink]="['/juego', sugerencia.juego.appid]">
                  <app-portada [src]="sugerencia.juego.portada_url" radio="0" />
                  <div class="cuerpo">
                    <h3 class="nombre">{{ sugerencia.juego.nombre }}</h3>
                    <ul class="razones" data-testid="sugerencia-razones">
                      @for (razon of sugerencia.razones; track razon.tipo) {
                        <li
                          [class.no]="!razon.cumple"
                          [attr.data-tipo]="razon.tipo"
                          [attr.data-testid]="razon.tipo === 'generos' ? 'sugerencia-porque' : null"
                        >
                          <span class="icono" aria-hidden="true">
                            <svg viewBox="0 0 24 24">
                              @switch (razon.tipo) {
                                @case ('generos') {
                                  <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6" />
                                }
                                @case ('precio') {
                                  <path d="M20 12 12 20l-8-8V4h8z" /><circle cx="8" cy="8" r="1.5" />
                                }
                                @case ('horas') {
                                  <circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" />
                                }
                                @case ('friccion') {
                                  <path d="M12 3 5 6v6c0 4 3 7 7 9 4-2 7-5 7-9V6z" />
                                }
                              }
                            </svg>
                          </span>
                          <span>{{ razon.texto }}</span>
                          @if (!razon.cumple) {
                            <span class="solo-lector">(no cumple)</span>
                          }
                        </li>
                      }
                    </ul>
                    <p class="riesgo-aparte">
                      <span>Aparte:</span>
                      <app-pildora-banda [banda]="sugerencia.juego.banda_riesgo" />
                    </p>
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
      gap: var(--espacio-16);
    }
    .cabecera {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--espacio-12) var(--espacio-16);
    }
    h2 {
      margin: 0;
      font-family: var(--fuente-display);
      font-size: clamp(22px, 2.4cqw, 28px);
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }
    /* Etiquetas y avisos van en su panel: sobre la nebulosa, el texto va en superficie. */
    .etiqueta,
    .en-vivo {
      display: inline-flex;
      align-items: center;
      gap: var(--espacio-8);
      padding: 4px var(--espacio-12);
      border-radius: var(--radio-pildora);
      background: var(--superficie);
      font-size: var(--texto-caption);
    }
    .etiqueta {
      border: 1px solid color-mix(in srgb, var(--t-perfil) var(--mezcla-filo), var(--superficie));
      color: var(--texto);
    }
    .en-vivo {
      border: 1px solid var(--borde);
      color: var(--texto-meta);
    }
    .en-vivo::before {
      content: '';
      width: 8px;
      height: 8px;
      border-radius: 50%;
      background: var(--accion-tinta);
    }
    .entrada {
      margin: 0;
      max-width: var(--medida-lectura);
      color: var(--texto);
      line-height: var(--interlineado-largo);
    }
    .aviso {
      margin: 0;
      padding: var(--espacio-12) var(--espacio-16);
      border: 1px solid var(--borde);
      border-radius: var(--radio-tarjeta);
      border-inline-start: 4px solid var(--t-perfil);
      background: var(--superficie);
      color: var(--texto);
      line-height: var(--interlineado-largo);
    }
    .lista {
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(min(100%, 280px), 1fr));
      gap: var(--espacio-16);
    }
    .juego {
      border: 1px solid var(--borde);
      border-radius: var(--radio-tarjeta);
      background: var(--superficie);
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
      gap: var(--espacio-12);
      padding: var(--espacio-16);
    }
    .nombre {
      margin: 0;
      font-size: 19px;
      font-weight: var(--peso-clave);
    }
    .razones {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: 6px;
      font-size: var(--texto-caption);
      line-height: 1.35;
    }
    .razones li {
      display: grid;
      grid-template-columns: 18px minmax(0, 1fr);
      gap: var(--espacio-8);
      align-items: start;
    }
    .razones .no {
      color: var(--texto-meta);
    }
    .icono {
      display: grid;
      place-items: center;
      padding-top: 1px;
      color: var(--t-perfil);
    }
    .no .icono {
      color: var(--texto-meta);
    }
    .icono svg {
      width: 18px;
      height: 18px;
      fill: none;
      stroke: currentColor;
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    .riesgo-aparte {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--espacio-8);
      align-self: stretch;
      margin: 0;
      padding-top: var(--espacio-12);
      border-top: 1px solid var(--borde);
      color: var(--texto-meta);
      font-size: var(--texto-caption);
    }
    /* Solo en banda alta: la tarjeta ya lleva a la ficha, y aquí se dice qué hay ahí.
       Describe lo que se va a encontrar; no dice qué hacer con ello. */
    .nota-alto {
      color: var(--texto-meta);
      font-size: var(--texto-caption);
      line-height: var(--interlineado-largo);
    }
    .meta {
      margin: 0;
      padding: var(--espacio-8) var(--espacio-12);
      border-radius: var(--radio-tarjeta);
      background: var(--superficie);
      line-height: var(--interlineado-largo);
    }
  `,
})
export class SugerenciasPerfil {
  /** Lo que se está respondiendo, guardado o no: las sugerencias van en vivo. */
  readonly valores = input.required<ValoresPerfil>();

  private readonly catalogo = inject(CatalogoStore);
  private readonly panorama = inject(PanoramaStore);

  protected readonly resultado = computed(() =>
    sugerenciasPara(this.catalogo.juegos(), criteriosDesde(this.valores()), this.panorama.porAppid()),
  );

  /** Con solo consolas marcadas, las sugerencias lo aclaran: el catálogo es de Steam. */
  protected readonly soloConsolas = computed(() => {
    const plataformas = this.valores().plataformas;
    return plataformas.length > 0 && !plataformas.includes('pc');
  });

  protected readonly cuantos = computed(() => {
    const { candidatos, sugerencias } = this.resultado();
    const juegos = candidatos === 1 ? 'juego encaja' : 'juegos encajan';
    const mostrados = candidatos > sugerencias.length ? `; se muestran ${sugerencias.length}` : '';
    return `En el catálogo, ${candidatos} ${juegos} con lo que declaraste${mostrados}.`;
  });

  protected readonly empatan = computed(() => hayEmpates(this.resultado().sugerencias));
  protected readonly notaDesempate = NOTA_DESEMPATE;

  protected pesos(valor: number): string {
    return `$${PESOS.format(valor)}`;
  }
}
