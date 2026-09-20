import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  computed,
  effect,
  inject,
  input,
  signal,
  viewChild,
} from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { HttpErrorResponse } from '@angular/common/http';

import { Comentario } from '../api/contrato';
import { NexplayApi } from '../api/nexplay-api';
import { hace } from '../dominio/tiempo';
import { UsuarioStore } from '../estado/usuario-store';

const MAXIMO_TEXTO = 500;

/** Hilo público de comentarios sobre la segunda opinión. Cada quien edita y elimina los
 * suyos —la API es la que decide de quién es cada uno— y cualquiera puede darle un
 * pulgar arriba. Angular escapa el texto al interpolarlo, así que un comentario con HTML
 * se ve como texto, también después de editarlo. */
@Component({
  selector: 'app-hilo-comentarios',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="hilo" data-testid="hilo-comentarios">
      <h3 class="titulo">Lo que dicen otras personas</h3>
      <p class="meta aviso-publico" data-testid="aviso-publico">
        Los comentarios son públicos y anónimos: cualquiera puede verlos. No compartas datos personales.
      </p>

      @if (recurso.error()) {
        <p class="meta">No se pudieron cargar los comentarios.</p>
      } @else if (recurso.isLoading()) {
        <p class="meta">Cargando comentarios…</p>
      } @else if (comentarios().length) {
        <ol class="burbujas" #lista data-testid="lista-comentarios">
          @for (comentario of comentarios(); track comentario.id) {
            <li class="burbuja" data-testid="comentario" [attr.data-id]="comentario.id">
              <p class="autor meta mono">
                <span>Anónimo · {{ cuando(comentario) }}</span>
                @if (comentario.editado) {
                  <span data-testid="comentario-editado">(editado)</span>
                }
                @if (comentario.es_mio) {
                  <button
                    type="button"
                    class="enlace"
                    data-testid="comentario-editar"
                    [disabled]="ocupado() === comentario.id"
                    (click)="abrirEdicion(comentario)"
                  >
                    Editar
                  </button>
                  <button
                    type="button"
                    class="enlace"
                    data-testid="comentario-eliminar"
                    [disabled]="ocupado() === comentario.id"
                    (click)="pedirConfirmacion(comentario.id)"
                  >
                    Eliminar
                  </button>
                }
              </p>

              @if (editando() === comentario.id) {
                <label class="escribir">
                  <span class="solo-lector">Edita tu comentario</span>
                  <textarea
                    rows="2"
                    [attr.maxlength]="maximo"
                    data-testid="comentario-editor"
                    [value]="borrador()"
                    [disabled]="ocupado() === comentario.id"
                    (input)="borrador.set($any($event.target).value)"
                  ></textarea>
                </label>
                <div class="acciones">
                  <button
                    type="button"
                    class="boton-cta"
                    data-testid="comentario-guardar-edicion"
                    [disabled]="ocupado() === comentario.id || !borrador().trim()"
                    (click)="guardarEdicion(comentario.id)"
                  >
                    Guardar
                  </button>
                  <button type="button" class="boton-fantasma" data-testid="comentario-cancelar-edicion" (click)="cancelar()">
                    Cancelar
                  </button>
                  <span class="meta mono">{{ borrador().length }}/{{ maximo }}</span>
                </div>
              } @else {
                <p class="texto">{{ comentario.texto }}</p>
              }

              @if (confirmando() === comentario.id) {
                <div class="acciones confirmar" data-testid="comentario-confirmar">
                  <span class="meta">¿Eliminar este comentario?</span>
                  <button
                    type="button"
                    class="boton-cta"
                    data-testid="comentario-confirmar-eliminar"
                    [disabled]="ocupado() === comentario.id"
                    (click)="eliminar(comentario.id)"
                  >
                    Sí, eliminar
                  </button>
                  <button type="button" class="boton-fantasma" data-testid="comentario-cancelar-eliminar" (click)="cancelar()">
                    Cancelar
                  </button>
                </div>
              }

              <button
                type="button"
                class="reaccion"
                data-testid="comentario-reaccion"
                [attr.aria-label]="comentario.reaccione_mia ? 'Quitar mi pulgar arriba' : 'Dar un pulgar arriba'"
                [attr.aria-pressed]="comentario.reaccione_mia"
                [disabled]="ocupado() === comentario.id"
                (click)="reaccionar(comentario.id)"
              >
                <span aria-hidden="true">👍</span>
                <span class="mono" data-testid="comentario-reacciones">{{ comentario.reacciones }}</span>
              </button>
            </li>
          }
        </ol>
      } @else {
        <p class="meta" data-testid="hilo-vacio">Todavía no hay comentarios. El tuyo sería el primero.</p>
      }

      <label class="escribir">
        <span class="solo-lector">Escribe un comentario público</span>
        <textarea
          rows="2"
          placeholder="Escribe un comentario público…"
          [attr.maxlength]="maximo"
          data-testid="comentario-nuevo"
          [value]="texto()"
          [disabled]="enviando()"
          (input)="texto.set($any($event.target).value)"
        ></textarea>
      </label>
      <div class="acciones">
        <button
          type="button"
          class="boton-cta"
          data-testid="enviar-comentario"
          [disabled]="enviando() || !texto().trim()"
          (click)="enviar()"
        >
          {{ enviando() ? 'Enviando…' : 'Enviar' }}
        </button>
        <span class="meta mono">{{ texto().length }}/{{ maximo }}</span>
      </div>

      <p class="meta aviso" role="status" aria-live="polite">{{ aviso() }}</p>
    </section>
  `,
  styles: `
    .hilo {
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
    .aviso-publico {
      margin: 0;
      max-width: var(--medida-lectura);
      line-height: var(--interlineado-largo);
    }
    .burbujas {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: var(--espacio-8);
      max-height: 360px;
      overflow-y: auto;
    }
    .burbuja {
      background: var(--superficie-lienzo);
      border-radius: var(--radio-tarjeta);
      padding: var(--espacio-12);
      max-width: var(--medida-lectura);
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: var(--espacio-8);
    }
    .autor {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--espacio-8);
      margin: 0;
    }
    /* Acción secundaria dentro del texto: pesa menos que un botón con borde. */
    .enlace {
      border: 0;
      background: none;
      padding: 0;
      font: inherit;
      letter-spacing: inherit;
      color: var(--texto-meta);
      text-decoration: underline;
      text-underline-offset: 3px;
      cursor: pointer;
    }
    .enlace:hover:not([disabled]) {
      color: var(--texto);
    }
    .texto {
      margin: 0;
      font-size: var(--texto-body-sm);
      line-height: var(--interlineado-largo);
      overflow-wrap: anywhere;
    }
    .escribir {
      display: flex;
      flex-direction: column;
      align-self: stretch;
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
    .burbuja textarea {
      background: var(--superficie-tarjeta);
    }
    textarea:hover,
    textarea:focus {
      border-color: var(--texto);
    }
    .acciones {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--espacio-12);
    }
    .confirmar {
      gap: var(--espacio-8);
    }
    .boton-cta[disabled] {
      opacity: 0.6;
      cursor: not-allowed;
    }
    /* Mismo lenguaje que el voto de la segunda opinión: borde discreto, relleno índigo
       cuando está activo. La pila de emoji es la del sistema. */
    .reaccion {
      display: inline-flex;
      align-items: center;
      gap: var(--espacio-8);
      padding: 4px var(--espacio-12);
      font-family: 'Apple Color Emoji', 'Segoe UI Emoji', 'Noto Color Emoji', 'Twemoji Mozilla', sans-serif;
      font-size: var(--texto-caption);
      line-height: 1.6;
      color: var(--texto);
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-pildora);
      background: transparent;
      cursor: pointer;
      transition:
        border-color var(--duracion-rapida) var(--curva),
        background var(--duracion-rapida) var(--curva);
    }
    .reaccion:hover:not([disabled]) {
      border-color: var(--texto);
    }
    .reaccion[aria-pressed='true'] {
      background: var(--acento-sistema);
      border-color: var(--texto);
    }
    .reaccion[disabled] {
      cursor: progress;
      opacity: 0.6;
    }
    .aviso:empty {
      display: none;
    }
    .aviso {
      margin: 0;
    }
  `,
})
export class HiloComentarios {
  readonly appid = input.required<number>();

  private readonly api = inject(NexplayApi);
  private readonly usuario = inject(UsuarioStore);
  private readonly lista = viewChild<ElementRef<HTMLElement>>('lista');

  protected readonly maximo = MAXIMO_TEXTO;
  protected readonly texto = signal('');
  protected readonly enviando = signal(false);
  protected readonly aviso = signal('');
  /** Ids del comentario que se está editando, del que pide confirmación y del que espera
   * respuesta de la API: solo uno a la vez de cada cosa. */
  protected readonly editando = signal<number | null>(null);
  protected readonly confirmando = signal<number | null>(null);
  protected readonly ocupado = signal<number | null>(null);
  protected readonly borrador = signal('');

  private largoPrevio = 0;

  protected readonly recurso = rxResource({
    params: () => this.appid(),
    stream: ({ params }) => this.api.comentarios(params, this.usuario.id),
    defaultValue: [] as Comentario[],
  });

  protected readonly comentarios = computed(() => this.recurso.value());

  constructor() {
    // Al llegar uno nuevo, el hilo baja solo. Editar o reaccionar no mueve el scroll.
    effect(() => {
      const largo = this.comentarios().length;
      const lista = this.lista()?.nativeElement;
      if (lista && largo > this.largoPrevio) {
        // Tras pintar: si se ajusta antes, el último mensaje queda cortado.
        requestAnimationFrame(() => (lista.scrollTop = lista.scrollHeight));
      }
      this.largoPrevio = largo;
    });
  }

  /** La fecha que se muestra es la del último cambio, si lo hubo. */
  protected cuando(comentario: Comentario): string {
    return hace(comentario.actualizado ?? comentario.creado);
  }

  protected abrirEdicion(comentario: Comentario): void {
    this.confirmando.set(null);
    this.aviso.set('');
    this.editando.set(comentario.id);
    this.borrador.set(comentario.texto);
  }

  protected pedirConfirmacion(id: number): void {
    this.editando.set(null);
    this.aviso.set('');
    this.confirmando.set(id);
  }

  protected cancelar(): void {
    this.editando.set(null);
    this.confirmando.set(null);
    this.borrador.set('');
  }

  protected enviar(): void {
    const texto = this.texto().trim();
    if (!texto || this.enviando()) {
      return;
    }

    this.enviando.set(true);
    this.aviso.set('');
    this.api.comentar(this.appid(), { usuario: this.usuario.id, texto }).subscribe({
      next: (hilo) => {
        this.recurso.set(hilo);
        this.texto.set('');
        this.enviando.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.enviando.set(false);
        this.aviso.set(this.mensajeDeError(error, 'No se pudo enviar el comentario.'));
      },
    });
  }

  protected guardarEdicion(id: number): void {
    const texto = this.borrador().trim();
    if (!texto || this.ocupado() !== null) {
      return;
    }

    this.ocupado.set(id);
    this.aviso.set('');
    this.api.editarComentario(this.appid(), id, { usuario: this.usuario.id, texto }).subscribe({
      next: (hilo) => {
        this.recurso.set(hilo);
        this.ocupado.set(null);
        this.cancelar();
        this.aviso.set('Comentario actualizado.');
      },
      error: (error: HttpErrorResponse) => {
        this.ocupado.set(null);
        this.aviso.set(this.mensajeDeError(error, 'No se pudo editar el comentario.'));
      },
    });
  }

  protected eliminar(id: number): void {
    if (this.ocupado() !== null) {
      return;
    }

    this.ocupado.set(id);
    this.aviso.set('');
    this.api.borrarComentario(this.appid(), id, this.usuario.id).subscribe({
      next: (hilo) => {
        this.recurso.set(hilo);
        this.largoPrevio = hilo.length;
        this.ocupado.set(null);
        this.cancelar();
        this.aviso.set('Comentario eliminado.');
      },
      error: (error: HttpErrorResponse) => {
        this.ocupado.set(null);
        this.aviso.set(this.mensajeDeError(error, 'No se pudo eliminar el comentario.'));
      },
    });
  }

  protected reaccionar(id: number): void {
    if (this.ocupado() !== null) {
      return;
    }

    this.ocupado.set(id);
    this.aviso.set('');
    this.api.reaccionar(this.appid(), id, this.usuario.id).subscribe({
      next: (reaccion) => {
        this.recurso.update((hilo) =>
          hilo.map((comentario) =>
            comentario.id === id
              ? { ...comentario, reacciones: reaccion.reacciones, reaccione_mia: reaccion.reaccione_mia }
              : comentario,
          ),
        );
        this.ocupado.set(null);
      },
      error: (error: HttpErrorResponse) => {
        this.ocupado.set(null);
        this.aviso.set(this.mensajeDeError(error, 'No se pudo registrar tu reacción.'));
      },
    });
  }

  /** El 403 y el 429 traen explicación de la API; el resto es la API caída. */
  private mensajeDeError(error: HttpErrorResponse, generico: string): string {
    if (error.status === 403) {
      return 'Ese comentario es de otra persona.';
    }
    if (error.status === 429) {
      return error.error?.detail ?? 'Vas muy seguido. Espera un momento.';
    }
    return `${generico} Revisa que la API esté corriendo.`;
  }
}
