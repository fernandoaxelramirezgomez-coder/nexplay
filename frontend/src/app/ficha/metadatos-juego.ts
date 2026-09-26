import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';

import { JuegoCatalogo } from '../api/contrato';
import { CriticaPublico } from '../compartido/critica-publico';
import { NotaInfo } from '../compartido/nota-info';
import { lineaCritica, sentimientoSteam } from '../dominio/critica';
import { textoPrecio } from '../dominio/formato';
import { PanoramaStore } from '../estado/panorama-store';

@Component({
  selector: 'app-metadatos-juego',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [NotaInfo, CriticaPublico],
  template: `
    <section class="bloque" data-testid="metadatos">
      <header class="bloque-cabecera">
        <span class="insignia" aria-hidden="true">
          <svg viewBox="0 0 24 24"><rect x="4" y="3" width="16" height="18" rx="2" /><path d="M8 8h8M8 12h8M8 16h5" /></svg>
        </span>
        <h2 class="bloque-titulo">Ficha técnica</h2>
      </header>
      <dl class="datos">
        <dt class="meta">Crítica</dt>
        <dd class="critica" data-testid="ficha-critica">{{ metacritic() }}</dd>
        <dt class="meta">Géneros</dt>
        <dd class="generos">
          @for (genero of juego().generos; track genero) {
            <span class="chip">{{ genero }}</span>
          } @empty {
            <span class="mono">Sin género registrado</span>
          }
        </dd>
        <dt class="meta">Precio</dt>
        <dd class="mono">{{ precio() }}</dd>
        <dt class="meta">Lanzamiento</dt>
        <dd class="mono">{{ juego().fecha_lanzamiento ?? 'Sin fecha registrada' }}</dd>
        @if (horasTipicas(); as horas) {
          <dt class="meta">
            Horas típicas
            <app-nota-info etiqueta="Qué son las horas típicas" idPrueba="horas-tipicas-info">
              La mediana de horas que llevaba jugadas quien lo recomendó en su reseña de Steam, de las reseñas que
              descargamos. Dice cuánto suele pedir antes de gustar; no entra al cálculo del riesgo.
            </app-nota-info>
          </dt>
          <dd class="mono" data-testid="horas-tipicas">{{ horas }}</dd>
        }
      </dl>
      <!-- Sin Metacritic, la ficha técnica suma qué dicen los jugadores en Steam. Lo de
           NexPlay no va aquí: la ficha ya tiene «Tu opinión» y «Comentarios». -->
      @if (juego().metacritic === null) {
        <app-critica-publico [juego]="juego()" [incrustado]="true" />
      }
    </section>
  `,
  styles: `
    .datos {
      display: grid;
      grid-template-columns: auto 1fr;
      gap: var(--espacio-8) var(--espacio-24);
      margin: 0;
    }
    dd {
      margin: 0;
    }
    .critica {
      line-height: 1.4;
    }
    .generos {
      display: flex;
      flex-wrap: wrap;
      gap: 0 var(--espacio-12);
    }
    /* Sin puntos entre chips: el ::before de .chip es su área de toque, así que el
       separador quedaba flotando a media altura y, al envolverse, abría renglón. El aire
       del gap ya separa, y aquí los chips no se pulsan. */
    .generos .chip {
      padding-inline: 0;
      color: var(--texto);
      font-family: var(--fuente-texto);
      cursor: default;
    }
    .generos .chip::after {
      content: none;
    }
  `,
})
export class MetadatosJuego {
  readonly juego = input.required<JuegoCatalogo>();

  private readonly panorama = inject(PanoramaStore);

  /** «Metacritic 82 · Steam 94 % positivas (87,051 reseñas)». Sin Metacritic basta decirlo:
   * lo de Steam va debajo, en «Crítica y público», con su advertencia. */
  protected readonly metacritic = computed(() =>
    this.juego().metacritic === null
      ? lineaCritica(this.juego(), null)
      : lineaCritica(this.juego(), sentimientoSteam(this.panorama.porAppid().get(this.juego().appid))),
  );

  protected readonly horasTipicas = computed(() => {
    const horas = this.panorama.porAppid().get(this.juego().appid)?.horas_al_recomendar;
    if (horas == null) {
      return null;
    }
    return horas < 1 ? 'menos de 1 h' : `${Math.round(horas)} h`;
  });
  protected readonly precio = computed(() => textoPrecio(this.juego()));
}
