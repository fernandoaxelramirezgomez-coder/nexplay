import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  inject,
  signal,
} from '@angular/core';

import { SALUDO_CATALOGO } from '../dominio/textos-nia';

/** El saludo se escribe letra por letra: es lo que hace que se sienta alguien
 * escribiendo y no un cartel. Se corta en seco con prefers-reduced-motion. El texto vive
 * en dominio/textos-nia.ts, donde una prueba vigila que describa y no aconseje. */
const SALUDO = SALUDO_CATALOGO;
const MS_POR_LETRA = 22;

/** Nia del catálogo: el retrato de bienvenida, en el pie de la portada (app.html). La ficha tiene su
 * propia variante, que reacciona a la banda (ficha/nia-reaccion.ts); los assets de
 * cada una viven aparte en public/nia/. */
@Component({
  selector: 'app-nia-mascota',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="mascota" data-testid="nia-mascota">
      <img
        src="nia/catalogo.png"
        alt="Nia, la asistente de NexPlay"
        width="480"
        height="500"
        fetchpriority="high"
      />
      <p class="globo-nia globo" role="status" aria-live="polite" data-testid="nia-saludo">
        <span class="quien">Nia</span>
        <span class="texto">{{ visible() }}</span
        ><span class="cursor" [class.quieto]="termino()" aria-hidden="true">▋</span>
      </p>
    </div>
  `,
  styles: `
    .mascota {
      display: flex;
      align-items: center;
      gap: var(--espacio-24);
      max-width: var(--medida-lectura);
      text-align: start;
    }
    img {
      width: 148px;
      height: auto;
      flex: 0 0 auto;
      /* Respira como el logo, pero medio segundo más lenta para que no vayan a la par. */
      animation: flotar 6.5s var(--curva) infinite;
    }
    @keyframes flotar {
      0%,
      100% {
        transform: translateY(0) rotate(0deg);
        filter: drop-shadow(0 0 2px rgb(var(--neon-canal) / 0.2));
      }
      50% {
        transform: translateY(-6px) rotate(-1.2deg);
        filter: drop-shadow(0 0 calc(10px * var(--halo-radio)) rgb(var(--neon-canal) / calc(0.45 * var(--halo-alfa))));
      }
    }
    /* El globo es .globo-nia (base.css). Solo se reserva su alto final, para que la
       página no salte mientras el saludo se escribe letra por letra. */
    .globo {
      min-height: 6.5em;
    }
    .cursor {
      color: var(--neon);
      animation: parpadeo 1s steps(2, start) infinite;
    }
    .cursor.quieto {
      display: none;
    }
    @keyframes parpadeo {
      50% {
        opacity: 0;
      }
    }
    @media (max-width: 640px) {
      .mascota {
        flex-direction: column;
        text-align: center;
      }
      .globo::before {
        inset-inline-start: 50%;
        top: -7px;
        transform: translateX(-50%) rotate(135deg);
      }
    }
  `,
})
export class NiaMascota {
  private readonly destruir = inject(DestroyRef);

  private readonly letras = signal(0);
  protected readonly visible = computed(() => SALUDO.slice(0, this.letras()));
  protected readonly termino = computed(() => this.letras() >= SALUDO.length);

  constructor() {
    if (this.prefiereMenosMovimiento()) {
      this.letras.set(SALUDO.length);
      return;
    }

    const reloj = setInterval(() => {
      this.letras.update((n) => n + 1);
      if (this.letras() >= SALUDO.length) {
        clearInterval(reloj);
      }
    }, MS_POR_LETRA);
    this.destruir.onDestroy(() => clearInterval(reloj));
  }

  /** En un servidor o sin matchMedia no hay animación que evitar. */
  private prefiereMenosMovimiento(): boolean {
    return typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
  }
}
