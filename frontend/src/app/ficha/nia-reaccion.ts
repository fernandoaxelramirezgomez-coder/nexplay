import { ChangeDetectionStrategy, Component, computed, input, linkedSignal } from '@angular/core';

import { NivelRiesgo } from '../api/contrato';
import { reaccionPara } from '../dominio/reaccion-nia';

/** Nia reacciona a la banda de riesgo del juego. Es apoyo visual: el resultado lo dicen
 * el veredicto y la segunda opinión, y este bloque solo lo refuerza de un vistazo.
 *
 * Toda la decisión vive en dominio/reaccion-nia.ts; aquí solo se pinta. Si el PNG no
 * carga, la imagen se quita y el globo se queda: el mensaje no depende del dibujo. */
@Component({
  selector: 'app-nia-reaccion',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <figure
      class="reaccion"
      data-testid="nia-reaccion"
      [attr.data-banda]="nivel()"
      [attr.data-emocion]="reaccion().emocion"
    >
      @if (!imagenCaida()) {
        <img
          [src]="reaccion().imagen"
          [alt]="reaccion().descripcion"
          width="226"
          height="220"
          data-testid="nia-reaccion-imagen"
          (error)="imagenCaida.set(true)"
        />
      }
      <figcaption class="globo" data-testid="nia-reaccion-texto">
        <span class="quien mono">Nia</span>
        {{ reaccion().texto }}
      </figcaption>
    </figure>
  `,
  styles: `
    .reaccion {
      margin: var(--espacio-16) 0 0;
      display: flex;
      align-items: center;
      gap: var(--espacio-16);
      max-width: var(--medida-lectura);
    }
    img {
      width: 96px;
      height: auto;
      flex: 0 0 auto;
      /* El halo toma el color de la banda: la misma señal que la franja del veredicto. */
      --halo: var(--banda-medio);
    }
    [data-banda='bajo'] img {
      --halo: var(--banda-bajo);
    }
    [data-banda='alto'] img {
      --halo: var(--banda-alto);
    }

    /* Tranquila: flota y respira. Es la que más se mueve, y aun así poco. */
    [data-emocion='tranquila'] img {
      animation: flotar 5s var(--curva) infinite;
    }
    @keyframes flotar {
      0%,
      100% {
        transform: translateY(0);
        filter: drop-shadow(0 0 3px color-mix(in srgb, var(--halo) 30%, transparent));
      }
      50% {
        transform: translateY(-4px);
        filter: drop-shadow(0 0 9px color-mix(in srgb, var(--halo) 55%, transparent));
      }
    }

    /* Pensativa: no flota; inclina la cabeza, despacio. */
    [data-emocion='pensativa'] img {
      transform-origin: 50% 90%;
      animation: inclinar 7s ease-in-out infinite;
      filter: drop-shadow(0 0 6px color-mix(in srgb, var(--halo) 40%, transparent));
    }
    @keyframes inclinar {
      0%,
      100% {
        transform: rotate(-1.5deg);
      }
      50% {
        transform: rotate(1.5deg);
      }
    }

    /* Cautelosa: no se mueve. Solo el halo late, tenue y lento: es la que menos llama
       la atención, porque lo que importa en esa banda son los motivos, no Nia. */
    [data-emocion='cautelosa'] img {
      animation: vigilar 8s ease-in-out infinite;
    }
    @keyframes vigilar {
      0%,
      100% {
        filter: drop-shadow(0 0 2px color-mix(in srgb, var(--halo) 25%, transparent));
      }
      50% {
        filter: drop-shadow(0 0 7px color-mix(in srgb, var(--halo) 45%, transparent));
      }
    }

    .globo {
      position: relative;
      margin: 0;
      padding: var(--espacio-12) var(--espacio-16);
      border: 1px solid var(--linea);
      border-radius: var(--radio-tarjeta);
      background: var(--superficie-tarjeta);
      font-size: var(--texto-body-sm);
      line-height: var(--interlineado-largo);
    }
    /* El acento de la banda alta: un filo del color de la banda, fijo. */
    [data-banda='alto'] .globo {
      border-inline-start: 3px solid var(--banda-alto);
    }
    .globo::before {
      content: '';
      position: absolute;
      inset-inline-start: -7px;
      top: 50%;
      width: 12px;
      height: 12px;
      transform: translateY(-50%) rotate(45deg);
      border-inline-start: 1px solid var(--linea);
      border-block-end: 1px solid var(--linea);
      background: var(--superficie-tarjeta);
    }
    [data-banda='alto'] .globo::before {
      inset-inline-start: -9px;
    }
    .quien {
      display: block;
      margin-bottom: var(--espacio-4);
      color: var(--texto-meta);
      font-size: var(--texto-caption);
    }

    /* Con menos movimiento pedido, la imagen queda quieta en su pose. */
    @media (prefers-reduced-motion: reduce) {
      img {
        animation: none !important;
        transform: none !important;
      }
    }
    @media (max-width: 520px) {
      .reaccion {
        flex-direction: column;
        align-items: flex-start;
      }
      .globo::before {
        inset-inline-start: 32px;
        top: -7px;
        transform: rotate(135deg);
      }
    }
  `,
})
export class NiaReaccion {
  readonly nivel = input.required<NivelRiesgo>();

  protected readonly reaccion = computed(() => reaccionPara(this.nivel()));
  /** Se reinicia si cambia la banda: otra imagen, otra oportunidad de cargar. */
  protected readonly imagenCaida = linkedSignal({ source: this.nivel, computation: () => false });
}
