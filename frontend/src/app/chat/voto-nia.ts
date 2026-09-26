import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';

import { NexplayApi } from '../api/nexplay-api';
import { VotoNiaValor } from '../api/contrato';
import { UsuarioStore } from '../estado/usuario-store';

/** Los mismos cuatro que acepta la API (MOTIVOS_VOTO_NIA en api/valoraciones.py): un
 * motivo fuera de la lista se guarda como ninguno, así que aquí no se inventan otros. */
export const MOTIVOS_VOTO = [
  'no respondió lo que pregunté',
  'dato incorrecto',
  'muy larga',
  'me recomendó algo',
] as const;

/** 👍/👎 debajo de una respuesta de Nia. Es privado: nadie más ve el voto, y sirve para
 * comparar cómo contesta antes y después de cambiarle el prompt.
 *
 * El motivo solo se pide con 👎, porque con 👍 no hay nada que explicar, y es opcional:
 * obligarlo haría que la gente dejara de votar. */
@Component({
  selector: 'app-voto-nia',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="voto" data-testid="voto-nia">
      <span class="meta pregunta">¿Te sirvió?</span>
      <button
        type="button"
        class="pulgar"
        data-testid="voto-nia-arriba"
        [attr.aria-pressed]="voto() === 1"
        [attr.aria-label]="voto() === 1 ? 'Quitar tu voto a favor' : 'Sí, me sirvió'"
        [disabled]="guardando()"
        (click)="votar(1)"
      >
        👍
      </button>
      <button
        type="button"
        class="pulgar"
        data-testid="voto-nia-abajo"
        [attr.aria-pressed]="voto() === -1"
        [attr.aria-label]="voto() === -1 ? 'Quitar tu voto en contra' : 'No me sirvió'"
        [disabled]="guardando()"
        (click)="votar(-1)"
      >
        👎
      </button>
      @if (aviso()) {
        <span class="meta aviso" role="status">{{ aviso() }}</span>
      }
    </div>

    @if (voto() === -1) {
      <div class="motivos" data-testid="voto-nia-motivos">
        <span class="meta">¿Qué falló? (opcional)</span>
        @for (motivo of motivos; track motivo) {
          <button
            type="button"
            class="chip"
            data-testid="voto-nia-motivo"
            [attr.aria-pressed]="motivo === this.motivo()"
            [disabled]="guardando()"
            (click)="elegirMotivo(motivo)"
          >
            {{ motivo }}
          </button>
        }
      </div>
    }
  `,
  styles: `
    .voto {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--espacio-8);
      margin-top: var(--espacio-4);
    }
    .pregunta {
      font-size: var(--texto-caption);
    }
    .pulgar {
      min-width: 32px;
      height: 28px;
      padding: 0 var(--espacio-8);
      border: 1px solid transparent;
      border-radius: var(--radio-pildora);
      background: transparent;
      font-size: 13px;
      line-height: 1;
      cursor: pointer;
      opacity: 0.55;
      transition:
        opacity var(--duracion-rapida) var(--curva),
        border-color var(--duracion-rapida) var(--curva);
    }
    .pulgar:hover:not([disabled]),
    .pulgar[aria-pressed='true'] {
      opacity: 1;
    }
    .pulgar[aria-pressed='true'] {
      border-color: var(--neon);
      background: var(--acento-sistema);
    }
    .pulgar:focus-visible {
      outline: 2px solid var(--foco);
      outline-offset: 2px;
    }
    .motivos {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--espacio-8);
      margin-top: var(--espacio-8);
    }
    .motivos .chip {
      padding: var(--espacio-4) var(--espacio-8);
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-pildora);
      background: var(--superficie-lienzo);
      font-family: var(--fuente-texto);
    }
    .motivos .chip::after {
      content: none;
    }
    .motivos .chip[aria-pressed='true'] {
      border-color: var(--neon);
      color: var(--texto);
    }
    .aviso {
      font-size: var(--texto-caption);
    }
  `,
})
export class VotoNia {
  /** El id que devolvió la API con la respuesta. */
  readonly idRespuesta = input.required<string>();

  private readonly api = inject(NexplayApi);
  private readonly usuario = inject(UsuarioStore);

  protected readonly motivos = MOTIVOS_VOTO;
  protected readonly voto = signal<VotoNiaValor | null>(null);
  protected readonly motivo = signal<string | null>(null);
  protected readonly guardando = signal(false);
  private readonly error = signal('');

  protected readonly aviso = computed(() => this.error() || (this.voto() ? 'Gracias.' : ''));

  /** El mismo pulgar dos veces quita el voto: es el gesto que ya hace el pulgar de los
   * comentarios, y sin él no habría forma de arrepentirse. */
  protected votar(valor: VotoNiaValor): void {
    if (this.guardando()) {
      return;
    }
    if (this.voto() === valor) {
      this.quitar();
      return;
    }
    this.guardar(valor, valor === -1 ? this.motivo() : null);
  }

  protected elegirMotivo(motivo: string): void {
    const elegido = this.motivo() === motivo ? null : motivo;
    this.guardar(-1, elegido);
  }

  private guardar(valor: VotoNiaValor, motivo: string | null): void {
    this.guardando.set(true);
    this.error.set('');
    this.api
      .votarRespuestaDeNia(this.idRespuesta(), {
        usuario: this.usuario.id,
        voto: valor,
        ...(motivo ? { motivo } : {}),
      })
      .subscribe({
        next: (respuesta) => {
          this.voto.set(respuesta.voto);
          this.motivo.set(respuesta.motivo);
          this.guardando.set(false);
        },
        error: () => this.fallar(),
      });
  }

  private quitar(): void {
    this.guardando.set(true);
    this.error.set('');
    this.api.quitarVotoDeNia(this.idRespuesta(), this.usuario.id).subscribe({
      next: () => {
        this.voto.set(null);
        this.motivo.set(null);
        this.guardando.set(false);
      },
      error: () => this.fallar(),
    });
  }

  private fallar(): void {
    this.guardando.set(false);
    this.error.set('No se pudo guardar tu voto.');
  }
}
