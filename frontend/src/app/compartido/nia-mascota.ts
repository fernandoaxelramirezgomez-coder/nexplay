import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  inject,
  signal,
} from '@angular/core';

/** El saludo se escribe letra por letra: es lo que hace que se sienta alguien
 * escribiendo y no un cartel. Se corta en seco con prefers-reduced-motion. */
const SALUDO =
  '¡Hola! Soy Nia. Te muestro qué tan seguido un juego deja señales de arrepentimiento temprano' +
  ' en sus primeras dos horas. Busca uno aquí arriba y te cuento lo que dicen sus reseñas.';
const MS_POR_LETRA = 22;

/** Nia del catálogo: el retrato de bienvenida, solo en el inicio. La ficha tiene su
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
      <p class="globo" role="status" aria-live="polite" data-testid="nia-saludo">
        <span class="texto">{{ visible() }}</span
        ><span class="cursor" [class.quieto]="termino()" aria-hidden="true">▋</span>
      </p>
    </div>
  `,
  styles: `
    .mascota {
      display: flex;
      align-items: center;
      gap: var(--espacio-16);
      max-width: var(--medida-lectura);
      text-align: start;
    }
    img {
      width: 132px;
      height: auto;
      flex: 0 0 auto;
      /* Respira como el logo, pero medio segundo más lenta para que no vayan a la par. */
      animation: flotar 6.5s var(--curva) infinite;
    }
    @keyframes flotar {
      0%,
      100% {
        transform: translateY(0) rotate(0deg);
        filter: drop-shadow(0 0 2px rgba(34, 224, 255, 0.2));
      }
      50% {
        transform: translateY(-6px) rotate(-1.2deg);
        filter: drop-shadow(0 0 10px rgba(34, 224, 255, 0.45));
      }
    }
    /* El globo sale del lado de Nia: la punta lo ata a ella. */
    .globo {
      position: relative;
      margin: 0;
      padding: var(--espacio-12) var(--espacio-16);
      border: 1px solid var(--linea);
      border-radius: var(--radio-tarjeta);
      background: var(--superficie-tarjeta);
      font-size: var(--texto-body-sm);
      line-height: var(--interlineado-largo);
      min-height: 5.5em;
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
