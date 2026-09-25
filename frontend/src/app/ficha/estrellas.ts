import { ChangeDetectionStrategy, Component, ElementRef, computed, input, output, signal, viewChildren } from '@angular/core';

const ESTRELLAS = [1, 2, 3, 4, 5] as const;

/** Calificación de 1 a 5 estrellas, accesible con teclado.
 *
 * Es un radiogroup: una sola estrella entra en el orden de tabulación (la elegida, o la
 * primera si no hay), y las flechas se mueven entre 1 y 5 mostrando la vista previa.
 * Enter o Espacio confirman, porque cada estrella es un botón y los botones ya se activan
 * así; con el ratón, pasar por encima es la vista previa y el clic confirma. */
@Component({
  selector: 'app-estrellas',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      class="estrellas"
      role="radiogroup"
      aria-label="Califica esta segunda opinión"
      data-testid="estrellas"
      (mouseleave)="vista.set(null)"
      (focusout)="alSalir($event)"
      (keydown)="alTeclear($event)"
    >
      @for (n of estrellas; track n) {
        <button
          #estrella
          type="button"
          role="radio"
          class="estrella"
          [class.llena]="n <= llenas()"
          [class.previa]="vista() !== null && n <= vista()!"
          [attr.aria-checked]="valor() === n"
          [attr.aria-label]="'Calificar con ' + n + ' de 5 estrellas'"
          [attr.tabindex]="n === tabulable() ? 0 : -1"
          [attr.data-estrella]="n"
          [disabled]="deshabilitado()"
          (mouseenter)="vista.set(n)"
          (focus)="vista.set(n)"
          (click)="elegir.emit(n)"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d="M12 2.8l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 16.8l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z" />
          </svg>
        </button>
      }
    </div>
  `,
  styles: `
    .estrellas {
      display: inline-flex;
      gap: var(--espacio-4);
    }
    .estrella {
      display: grid;
      place-items: center;
      width: 44px;
      height: 44px;
      padding: 0;
      border: 0;
      border-radius: var(--radio-pildora);
      background: none;
      color: var(--borde-control);
      cursor: pointer;
      transition:
        color var(--duracion-rapida) var(--curva),
        transform var(--duracion-rapida) var(--curva),
        filter var(--duracion-rapida) var(--curva);
    }
    svg {
      width: 28px;
      height: 28px;
      fill: transparent;
      stroke: currentColor;
      stroke-width: 1.6;
      stroke-linejoin: round;
      transition: fill var(--duracion-rapida) var(--curva);
    }
    /* Elegidas: neón lleno, el mismo acento de todo lo que está activo en la app. */
    .llena {
      color: var(--neon);
    }
    .llena svg {
      fill: var(--neon);
    }
    /* Vista previa: crecen un poco y brillan; se nota que todavía no está confirmado. */
    .previa {
      color: var(--neon-hover);
      transform: scale(1.12);
      filter: drop-shadow(0 0 calc(6px * var(--halo-radio)) rgb(var(--neon-canal) / calc(0.55 * var(--halo-alfa))));
    }
    .previa svg {
      fill: var(--neon-hover);
    }
    .estrella[disabled] {
      cursor: progress;
      opacity: 0.6;
    }
    @media (prefers-reduced-motion: reduce) {
      .previa {
        transform: none;
      }
    }
  `,
})
export class Estrellas {
  /** La calificación confirmada, o null si todavía no hay. */
  readonly valor = input<number | null>(null);
  readonly deshabilitado = input(false);
  readonly elegir = output<number>();

  protected readonly estrellas = ESTRELLAS;
  /** La estrella que se previsualiza al pasar el ratón o al moverse con las flechas. */
  protected readonly vista = signal<number | null>(null);
  protected readonly llenas = computed(() => this.vista() ?? this.valor() ?? 0);
  /** Solo una estrella entra en el orden de tabulación: la elegida, o la primera. */
  protected readonly tabulable = computed(() => this.valor() ?? 1);

  private readonly botones = viewChildren<ElementRef<HTMLButtonElement>>('estrella');

  protected alTeclear(evento: KeyboardEvent): void {
    const actual = Number((evento.target as HTMLElement).dataset['estrella']);
    if (!actual) {
      return;
    }
    const destino: Record<string, number> = {
      ArrowRight: Math.min(5, actual + 1),
      ArrowUp: Math.min(5, actual + 1),
      ArrowLeft: Math.max(1, actual - 1),
      ArrowDown: Math.max(1, actual - 1),
      Home: 1,
      End: 5,
    };
    const siguiente = destino[evento.key];
    if (siguiente === undefined) {
      return;
    }
    evento.preventDefault();
    this.botones()[siguiente - 1]?.nativeElement.focus();
  }

  /** Al salir del grupo con el teclado se apaga la vista previa; moverse entre estrellas no. */
  protected alSalir(evento: FocusEvent): void {
    const adonde = evento.relatedTarget as Node | null;
    if (!adonde || !(evento.currentTarget as HTMLElement).contains(adonde)) {
      this.vista.set(null);
    }
  }
}
