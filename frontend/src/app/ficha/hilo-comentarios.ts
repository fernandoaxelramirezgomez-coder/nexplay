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

/** Hilo público de comentarios sobre la segunda opinión: se agregan al final y no se
 * editan ni se borran desde la app. Angular escapa el texto al interpolarlo, así que un
 * comentario con HTML se ve como texto. */
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
          @for (comentario of comentarios(); track comentario.creado + comentario.texto) {
            <li class="burbuja" data-testid="comentario">
              <p class="autor meta mono">Anónimo · {{ cuando(comentario.creado) }}</p>
              <p class="texto">{{ comentario.texto }}</p>
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
      max-height: 320px;
      overflow-y: auto;
    }
    .burbuja {
      background: var(--superficie-lienzo);
      border-radius: var(--radio-tarjeta);
      padding: var(--espacio-12);
      max-width: var(--medida-lectura);
    }
    .autor {
      margin: 0 0 var(--espacio-4);
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
    .acciones {
      display: flex;
      align-items: center;
      gap: var(--espacio-12);
    }
    .boton-cta[disabled] {
      opacity: 0.6;
      cursor: not-allowed;
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
  protected readonly cuando = hace;

  protected readonly recurso = rxResource({
    params: () => this.appid(),
    stream: ({ params }) => this.api.comentarios(params),
    defaultValue: [] as Comentario[],
  });

  protected readonly comentarios = computed(() => this.recurso.value());

  constructor() {
    // El más nuevo va al final: al llegar uno, se muestra sin tener que bajar a mano.
    effect(() => {
      this.comentarios();
      const lista = this.lista()?.nativeElement;
      if (lista) {
        // Tras pintar: si se ajusta antes, el último mensaje queda cortado.
        requestAnimationFrame(() => (lista.scrollTop = lista.scrollHeight));
      }
    });
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
        this.aviso.set(
          error.status === 429
            ? (error.error?.detail ?? 'Estás comentando muy seguido. Espera un momento.')
            : 'No se pudo enviar el comentario. Revisa que la API esté corriendo.',
        );
      },
    });
  }
}
