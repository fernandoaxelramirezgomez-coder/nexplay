import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';

import { NexplayApi } from '../api/nexplay-api';
import { ResumenValoraciones } from '../api/contrato';
import { textoCalificacion } from '../dominio/calificacion';
import { UsuarioStore } from '../estado/usuario-store';
import { Estrellas } from './estrellas';
import { HiloComentarios } from './hilo-comentarios';

/** Calificación de 1 a 5 estrellas sobre la segunda opinión: una por persona y juego, y
 * se puede cambiar o quitar. Debajo va el hilo público de comentarios. */
@Component({
  selector: 'app-valoracion-opinion',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [HiloComentarios, Estrellas],
  template: `
    <section class="valoracion" data-testid="valoracion">
      <h3 class="titulo">¿Te sirvió esta segunda opinión?</h3>

      <div class="botones">
        <app-estrellas [valor]="mia()" [deshabilitado]="guardando()" (elegir)="valorar($event)" />
        <span class="meta mono conteo" data-testid="valoracion-conteo">{{ conteo() }}</span>
        @if (mia()) {
          <button
            type="button"
            class="boton-texto quitar"
            data-testid="quitar-valoracion"
            [disabled]="guardando()"
            (click)="quitar()"
          >
            Quitar mi valoración
          </button>
        }
      </div>

      <app-hilo-comentarios [appid]="appid()" />

      <p class="meta aviso" role="status" aria-live="polite">{{ aviso() }}</p>
    </section>
  `,
  styles: `
    .valoracion {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
    }
    .titulo {
      font-size: var(--texto-body-sm);
    }
    .botones {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--espacio-16);
    }
    .conteo {
      margin-inline-start: var(--espacio-8);
    }
    .quitar {
      margin-inline-start: auto;
      font-size: var(--texto-caption);
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

  protected readonly guardando = signal(false);
  protected readonly aviso = signal('');

  private readonly recurso = rxResource({
    params: () => this.appid(),
    stream: ({ params }) => this.api.valoraciones(params, this.usuario.id),
  });

  protected readonly mia = computed(() => this.recurso.value()?.mia ?? null);
  protected readonly conteo = computed(() => {
    const resumen = this.recurso.value();
    return resumen ? textoCalificacion(resumen.promedio, resumen.total) : '';
  });

  protected valorar(calificacion: number): void {
    this.guardando.set(true);
    this.api.guardarValoracion(this.appid(), { usuario: this.usuario.id, calificacion }).subscribe({
      next: (resumen) =>
        this.terminar(resumen, `Gracias, quedó calificada con ${calificacion} de 5 estrellas.`),
      error: () => this.fallar(),
    });
  }

  protected quitar(): void {
    this.guardando.set(true);
    this.api.borrarValoracion(this.appid(), this.usuario.id).subscribe({
      next: (resumen) => this.terminar(resumen, 'Quitamos tu calificación.'),
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
