import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { JuegoCatalogo } from '../api/contrato';
import { Portada } from '../compartido/portada';
import { textoMetacritic, textoPrecio } from '../dominio/formato';
import { CompararStore } from '../estado/comparar-store';
import { MotivosStore } from '../estado/motivos-store';

@Component({
  selector: 'app-tarjeta-juego',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, Portada],
  host: {
    '(pointerenter)': 'pedirMotivo()',
    '(focusin)': 'pedirMotivo()',
  },
  template: `
    <article class="tarjeta-juego" data-testid="tarjeta-juego" [attr.data-appid]="juego().appid">
      <div class="lienzo">
        <app-portada [src]="juego().portada_url" [prioritaria]="prioritaria()" radio="0" />
        <button
          type="button"
          class="comparar"
          data-testid="boton-comparar"
          [attr.aria-pressed]="enComparacion()"
          [attr.aria-label]="
            (enComparacion() ? 'Quitar de la comparación: ' : 'Agregar a la comparación: ') + juego().nombre
          "
          (click)="comparar.alternar(juego().appid)"
        >
          {{ enComparacion() ? 'Comparando' : 'Comparar' }}
        </button>
      </div>
      <div class="cuerpo">
        <h3 class="nombre">
          <a class="enlace" [routerLink]="['/juego', juego().appid]">{{ juego().nombre }}</a>
        </h3>
        <p class="meta mono datos">{{ metacritic() }}<br />{{ precio() }}</p>
        <p class="meta mono motivo" data-testid="tarjeta-motivo">{{ textoMotivo() }}</p>
      </div>
    </article>
  `,
  styles: `
    .tarjeta-juego {
      position: relative;
      height: 100%;
      display: flex;
      flex-direction: column;
      background: var(--superficie-tarjeta);
      border-radius: var(--radio-tarjeta);
      overflow: hidden;
      transition:
        background var(--duracion) var(--curva),
        transform var(--duracion) var(--curva);
    }
    .tarjeta-juego:hover,
    .tarjeta-juego:has(.enlace:focus-visible) {
      background: var(--superficie-tarjeta-hover);
      transform: translateY(-2px);
    }
    .tarjeta-juego:has(.enlace:focus-visible) {
      outline: 2px solid var(--foco);
      outline-offset: 2px;
    }
    .lienzo {
      position: relative;
    }
    .cuerpo {
      padding: var(--espacio-12) var(--espacio-12) var(--espacio-8);
      display: flex;
      flex-direction: column;
      gap: var(--espacio-4);
    }
    .nombre {
      font-size: var(--texto-body-sm);
      line-height: 1.25;
      /* Dos líneas fijas: todas las tarjetas del estante miden igual. */
      min-height: calc(2 * 1.25 * var(--texto-body-sm));
      display: -webkit-box;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
      line-clamp: 2;
      overflow: hidden;
    }
    .enlace {
      text-decoration: none;
    }
    .enlace:focus-visible {
      outline: none;
    }
    /* El enlace del título cubre toda la tarjeta: un solo destino, sin anidar interactivos. */
    .enlace::after {
      content: '';
      position: absolute;
      inset: 0;
    }
    .meta {
      line-height: 1.35;
      min-height: calc(2 * 1.35 * var(--texto-caption));
    }
    /* Al pasar el cursor o enfocar, el motivo ocupa el lugar de los metadatos:
       la portada nunca se tapa. */
    .motivo {
      display: none;
      color: var(--texto);
    }
    .tarjeta-juego:hover .datos,
    .tarjeta-juego:focus-within .datos {
      display: none;
    }
    .tarjeta-juego:hover .motivo,
    .tarjeta-juego:focus-within .motivo {
      display: block;
    }
    .comparar {
      position: absolute;
      opacity: 0;
      transition: opacity var(--duracion) var(--curva);
      top: var(--espacio-8);
      right: var(--espacio-8);
      z-index: 1;
      min-height: 32px;
      padding: 4px var(--espacio-12);
      border: 1px solid var(--texto);
      border-radius: var(--radio-pildora);
      background: var(--superficie-lienzo);
      color: var(--texto);
      font-size: var(--texto-caption);
      cursor: pointer;
    }
    .comparar[aria-pressed='true'] {
      background: var(--acento-sistema);
    }
    .tarjeta-juego:hover .comparar,
    .tarjeta-juego:focus-within .comparar {
      opacity: 1;
    }
    /* Sin cursor (táctil) no hay hover: el botón queda siempre visible y más grande. */
    @media (hover: none) {
      .comparar {
        opacity: 1;
        min-height: 44px;
        padding: var(--espacio-8) var(--espacio-16);
      }
    }
  `,
})
export class TarjetaJuego {
  readonly juego = input.required<JuegoCatalogo>();
  readonly prioritaria = input(false);

  protected readonly comparar = inject(CompararStore);
  private readonly motivos = inject(MotivosStore);

  protected readonly enComparacion = computed(() => this.comparar.appids().includes(this.juego().appid));
  protected readonly metacritic = computed(() => textoMetacritic(this.juego().metacritic));
  protected readonly precio = computed(() => textoPrecio(this.juego()));

  protected readonly textoMotivo = computed(() => {
    const motivo = this.motivos.principal(this.juego().appid);
    if (motivo === undefined) {
      return 'Buscando el motivo principal…';
    }
    return motivo ? `Motivo principal: ${motivo}` : 'Sin motivos suficientes';
  });

  protected pedirMotivo(): void {
    this.motivos.pedir(this.juego().appid);
  }
}
