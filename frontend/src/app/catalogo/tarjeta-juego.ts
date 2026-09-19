import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { JuegoCatalogo } from '../api/contrato';
import { PildoraBanda } from '../compartido/pildora-banda';
import { Portada } from '../compartido/portada';
import { textoMetacritic, textoPrecio } from '../dominio/formato';
import { CompararStore } from '../estado/comparar-store';

@Component({
  selector: 'app-tarjeta-juego',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, Portada, PildoraBanda],
  template: `
    <article class="tarjeta" data-testid="tarjeta-juego" [attr.data-appid]="juego().appid">
      <app-portada [src]="juego().portada_url" [prioritaria]="prioritaria()" />
      <div class="cuerpo">
        <h3 class="nombre">
          <a class="enlace" [routerLink]="['/juego', juego().appid]">{{ juego().nombre }}</a>
        </h3>
        <p class="meta mono">{{ metacritic() }} · {{ precio() }}</p>
        <app-pildora-banda [banda]="juego().banda_riesgo" />
        <div class="acciones">
          <span class="cta" aria-hidden="true">Segunda opinión →</span>
          <button
            type="button"
            class="boton-fantasma comparar"
            data-testid="boton-comparar"
            [attr.aria-pressed]="enComparacion()"
            (click)="comparar.alternar(juego().appid)"
          >
            {{ enComparacion() ? 'En comparación' : 'Comparar' }}
          </button>
        </div>
      </div>
    </article>
  `,
  styles: `
    .tarjeta {
      position: relative;
      height: 100%;
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
      padding: var(--espacio-12);
      background: var(--superficie-tarjeta);
      border-radius: var(--radio-tarjeta);
      transition:
        background var(--duracion) var(--curva),
        transform var(--duracion) var(--curva);
    }
    .tarjeta:hover {
      background: var(--superficie-tarjeta-hover);
      transform: translateY(-2px);
    }
    .tarjeta:has(.enlace:focus-visible) {
      outline: 2px solid var(--foco);
      outline-offset: 2px;
    }
    .cuerpo {
      flex: 1;
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: var(--espacio-8);
      padding: 0 var(--espacio-4) var(--espacio-4);
    }
    .nombre {
      font-size: var(--texto-body);
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
      border-radius: var(--radio-tarjeta);
    }
    .acciones {
      margin-top: auto;
      width: 100%;
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: var(--espacio-8);
      padding-top: var(--espacio-4);
    }
    .cta {
      padding: 6px var(--espacio-12);
      white-space: nowrap;
      border-radius: var(--radio-pildora);
      background: var(--cta-fondo);
      color: var(--cta-texto);
      font-size: var(--texto-caption);
      transition: background var(--duracion-rapida) var(--curva);
    }
    .tarjeta:hover .cta {
      background: var(--cta-fondo-hover);
    }
    .comparar {
      position: relative;
      z-index: 1;
      padding: 5px var(--espacio-12);
      font-size: var(--texto-caption);
    }
  `,
})
export class TarjetaJuego {
  readonly juego = input.required<JuegoCatalogo>();
  readonly prioritaria = input(false);

  protected readonly comparar = inject(CompararStore);
  protected readonly enComparacion = computed(() => this.comparar.appids().includes(this.juego().appid));
  protected readonly metacritic = computed(() => textoMetacritic(this.juego().metacritic));
  protected readonly precio = computed(() => textoPrecio(this.juego()));
}
