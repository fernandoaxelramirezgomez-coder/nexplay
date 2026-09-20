import { ChangeDetectionStrategy, Component, computed, inject, input, linkedSignal, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';

import { NexplayApi } from '../api/nexplay-api';
import { ResumenValoraciones } from '../api/contrato';
import { textoUtilidad } from '../dominio/utilidad';
import { UsuarioStore } from '../estado/usuario-store';

const MAXIMO_COMENTARIO = 500;

/** Valoración de la segunda opinión: el conteo de "útil" es público y el comentario es
 * privado (la API solo lo devuelve a quien lo escribió). */
@Component({
  selector: 'app-valoracion-opinion',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="valoracion" data-testid="valoracion">
      <h3 class="titulo">¿Te sirvió esta segunda opinión?</h3>

      <div class="botones">
        <button
          type="button"
          class="boton-fantasma"
          data-testid="valorar-util"
          [attr.aria-pressed]="mia()?.util === true"
          [disabled]="guardando()"
          (click)="valorar(true)"
        >
          Sí, me sirvió
        </button>
        <button
          type="button"
          class="boton-fantasma"
          data-testid="valorar-no-util"
          [attr.aria-pressed]="mia()?.util === false"
          [disabled]="guardando()"
          (click)="valorar(false)"
        >
          No me sirvió
        </button>
        <span class="meta mono" data-testid="valoracion-conteo">{{ conteo() }}</span>
      </div>

      @if (mia()) {
        <label class="comentario">
          <span class="meta">Tu comentario (opcional). Solo tú lo ves.</span>
          <textarea
            rows="3"
            [attr.maxlength]="maximo"
            data-testid="valoracion-comentario"
            [value]="comentario()"
            (input)="comentario.set($any($event.target).value)"
          ></textarea>
          <span class="meta mono contador">{{ comentario().length }}/{{ maximo }}</span>
        </label>

        <div class="acciones">
          <button
            type="button"
            class="boton-fantasma"
            data-testid="guardar-comentario"
            [disabled]="guardando() || !comentarioCambio()"
            (click)="guardarComentario()"
          >
            Guardar comentario
          </button>
          @if (mia()?.comentario) {
            <button type="button" class="boton-fantasma" data-testid="borrar-comentario" [disabled]="guardando()" (click)="borrarComentario()">
              Borrar comentario
            </button>
          }
          <button type="button" class="boton-fantasma" data-testid="quitar-valoracion" [disabled]="guardando()" (click)="quitar()">
            Quitar mi valoración
          </button>
        </div>
      }

      <p class="meta aviso" role="status" aria-live="polite">{{ aviso() }}</p>
    </section>
  `,
  styles: `
    .valoracion {
      border-top: 1px solid var(--linea);
      margin-top: var(--espacio-16);
      padding-top: var(--espacio-16);
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
    }
    .titulo {
      font-size: var(--texto-body-sm);
    }
    .botones,
    .acciones {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--espacio-8);
    }
    .comentario {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-4);
      max-width: var(--medida-lectura);
    }
    textarea {
      font: inherit;
      letter-spacing: inherit;
      color: var(--texto);
      background: var(--superficie-lienzo);
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-tarjeta);
      padding: var(--espacio-12);
      resize: vertical;
      transition: border-color var(--duracion-rapida) var(--curva);
    }
    textarea:hover,
    textarea:focus {
      border-color: var(--texto);
    }
    .contador {
      align-self: flex-end;
    }
    .aviso:empty {
      display: none;
    }
    .aviso {
      margin: 0;
    }
  `,
})
export class ValoracionOpinion {
  readonly appid = input.required<number>();

  private readonly api = inject(NexplayApi);
  private readonly usuario = inject(UsuarioStore);

  protected readonly maximo = MAXIMO_COMENTARIO;
  protected readonly guardando = signal(false);
  protected readonly aviso = signal('');

  private readonly recurso = rxResource({
    params: () => this.appid(),
    stream: ({ params }) => this.api.valoraciones(params, this.usuario.id),
  });

  protected readonly mia = computed(() => this.recurso.value()?.mia ?? null);
  protected readonly conteo = computed(() => {
    const resumen = this.recurso.value();
    return resumen ? textoUtilidad(resumen.utiles, resumen.total) : '';
  });

  /** Arranca con lo guardado y se reinicia al cambiar de juego o al llegar otra respuesta. */
  protected readonly comentario = linkedSignal<ResumenValoraciones | undefined, string>({
    source: this.recurso.value,
    computation: (resumen) => resumen?.mia?.comentario ?? '',
  });

  protected readonly comentarioCambio = computed(
    () => this.comentario().trim() !== (this.mia()?.comentario ?? ''),
  );

  protected valorar(util: boolean): void {
    this.enviar({ util, comentario: this.comentario().trim() || null }, util ? 'Gracias, quedó marcada como útil.' : 'Gracias, quedó marcada como no útil.');
  }

  protected guardarComentario(): void {
    const util = this.mia()?.util;
    if (util === undefined) {
      return;
    }
    this.enviar({ util, comentario: this.comentario().trim() || null }, 'Comentario guardado.');
  }

  protected borrarComentario(): void {
    const util = this.mia()?.util;
    if (util === undefined) {
      return;
    }
    this.enviar({ util, comentario: null }, 'Comentario borrado; tu valoración sigue ahí.');
  }

  protected quitar(): void {
    this.guardando.set(true);
    this.api.borrarValoracion(this.appid(), this.usuario.id).subscribe({
      next: (resumen) => this.terminar(resumen, 'Quitamos tu valoración.'),
      error: () => this.fallar(),
    });
  }

  private enviar(cambios: { util: boolean; comentario: string | null }, aviso: string): void {
    this.guardando.set(true);
    this.api.guardarValoracion(this.appid(), { usuario: this.usuario.id, ...cambios }).subscribe({
      next: (resumen) => this.terminar(resumen, aviso),
      error: () => this.fallar(),
    });
  }

  private terminar(resumen: ResumenValoraciones, aviso: string): void {
    this.recurso.set(resumen);
    this.guardando.set(false);
    this.aviso.set(aviso);
  }

  private fallar(): void {
    this.guardando.set(false);
    this.aviso.set('No se pudo guardar. Revisa que la API esté corriendo e inténtalo de nuevo.');
  }
}
