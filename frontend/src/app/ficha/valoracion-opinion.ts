import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';

import { NexplayApi } from '../api/nexplay-api';
import { ResumenValoraciones } from '../api/contrato';
import { textoUtilidad } from '../dominio/utilidad';
import { UsuarioStore } from '../estado/usuario-store';
import { HiloComentarios } from './hilo-comentarios';

/** Voto sobre la segunda opinión: uno por persona y juego, y se puede cambiar. Debajo va
 * el hilo público de comentarios. */
@Component({
  selector: 'app-valoracion-opinion',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [HiloComentarios],
  template: `
    <section class="valoracion" data-testid="valoracion">
      <h3 class="titulo">¿Te sirvió esta segunda opinión?</h3>

      <div class="botones">
        <button
          type="button"
          class="voto"
          data-testid="valorar-util"
          aria-label="Sí, me sirvió"
          [attr.aria-pressed]="mia()?.util === true"
          [disabled]="guardando()"
          (click)="valorar(true)"
        >
          <span aria-hidden="true">👍</span>
        </button>
        <button
          type="button"
          class="voto"
          data-testid="valorar-no-util"
          aria-label="No me sirvió"
          [attr.aria-pressed]="mia()?.util === false"
          [disabled]="guardando()"
          (click)="valorar(false)"
        >
          <span aria-hidden="true">👎</span>
        </button>
        <span class="meta mono conteo" data-testid="valoracion-conteo">{{ conteo() }}</span>
        @if (mia()) {
          <button
            type="button"
            class="boton-fantasma quitar"
            data-testid="quitar-valoracion"
            [disabled]="guardando()"
            (click)="quitar()"
          >
            Quitar mi voto
          </button>
        }
      </div>

      <app-hilo-comentarios [appid]="appid()" />

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
    .botones {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--espacio-16);
    }
    /* Iconos: el texto completo va en aria-label, no en pantalla. La pila de fuentes
       de emoji es la del sistema; en Linux sin fuente de emoji se ven como cuadros. */
    .voto {
      width: 56px;
      height: 48px;
      display: grid;
      place-items: center;
      font-family: 'Apple Color Emoji', 'Segoe UI Emoji', 'Noto Color Emoji', 'Twemoji Mozilla', sans-serif;
      font-size: 24px;
      line-height: 1;
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-boton);
      background: transparent;
      cursor: pointer;
      transition:
        border-color var(--duracion-rapida) var(--curva),
        background var(--duracion-rapida) var(--curva);
    }
    .voto:hover:not([disabled]) {
      border-color: var(--texto);
    }
    .voto[aria-pressed='true'] {
      background: var(--acento-sistema);
      border-color: var(--texto);
    }
    .voto[disabled] {
      cursor: progress;
      opacity: 0.6;
    }
    .conteo {
      margin-inline-start: var(--espacio-8);
    }
    .quitar {
      margin-inline-start: auto;
      font-size: var(--texto-caption);
      padding: 4px var(--espacio-12);
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
    return resumen ? textoUtilidad(resumen.utiles, resumen.total) : '';
  });

  protected valorar(util: boolean): void {
    this.guardando.set(true);
    this.api.guardarValoracion(this.appid(), { usuario: this.usuario.id, util }).subscribe({
      next: (resumen) =>
        this.terminar(resumen, util ? 'Gracias, quedó marcada como útil.' : 'Gracias, quedó marcada como no útil.'),
      error: () => this.fallar(),
    });
  }

  protected quitar(): void {
    this.guardando.set(true);
    this.api.borrarValoracion(this.appid(), this.usuario.id).subscribe({
      next: (resumen) => this.terminar(resumen, 'Quitamos tu valoración.'),
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
