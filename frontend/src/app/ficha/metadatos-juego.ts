import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

import { JuegoCatalogo } from '../api/contrato';
import { textoMetacritic, textoPrecio } from '../dominio/formato';

@Component({
  selector: 'app-metadatos-juego',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="seccion" data-testid="metadatos">
      <h2 class="rotulo-seccion">Ficha técnica</h2>
      <dl class="datos">
        <dt class="meta">Crítica</dt>
        <dd class="mono">{{ metacritic() }}</dd>
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
      </dl>
    </section>
  `,
  styles: `
    .rotulo-seccion {
      margin-bottom: var(--espacio-16);
    }
    .datos {
      display: grid;
      grid-template-columns: auto 1fr;
      gap: var(--espacio-8) var(--espacio-24);
      margin: 0;
    }
    dd {
      margin: 0;
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

  protected readonly metacritic = computed(() => textoMetacritic(this.juego().metacritic));
  protected readonly precio = computed(() => textoPrecio(this.juego()));
}
