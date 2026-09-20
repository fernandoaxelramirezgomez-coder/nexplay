import { HttpErrorResponse } from '@angular/common/http';
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

import { MensajeChat } from '../api/contrato';
import { NexplayApi } from '../api/nexplay-api';
import { PerfilStore } from '../estado/perfil-store';
import { UsuarioStore } from '../estado/usuario-store';

const MAXIMO_TEXTO = 500;
/** La API acepta 10 mensajes; se manda la cola más reciente. */
const MAXIMO_MENSAJES = 10;

const SUGERENCIAS = ['¿Por qué tiene esa banda?', '¿Cuánto cuesta?', '¿Qué dice la crítica?'];

/** Chat de la ficha. El backend le pasa a Nia los datos reales de este juego; la
 * conversación vive solo en pantalla y no se guarda. */
@Component({
  selector: 'app-nia',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="tarjeta nia" data-testid="nia">
      <h2>Pregúntale a Nia</h2>
      <p class="meta intro">
        Responde con los datos de este juego: su banda, los motivos de las reseñas, la crítica y el precio. No
        recomienda comprar ni no comprar.
      </p>

      @if (mensajes().length) {
        <ol class="conversacion" #conversacion data-testid="conversacion">
          @for (mensaje of mensajes(); track $index) {
            <li class="mensaje" [attr.data-rol]="mensaje.rol" [attr.data-testid]="'mensaje-' + mensaje.rol">
              <span class="quien meta mono">{{ mensaje.rol === 'usuario' ? 'Tú' : 'Nia' }}</span>
              <p class="texto">{{ mensaje.contenido }}</p>
            </li>
          }
          @if (esperando()) {
            <li class="mensaje" data-rol="nia">
              <span class="quien meta mono">Nia</span>
              <p class="texto meta" data-testid="nia-escribiendo">Escribiendo…</p>
            </li>
          }
        </ol>
      } @else {
        <div class="sugerencias">
          @for (sugerencia of sugerencias; track sugerencia) {
            <button type="button" class="chip" data-testid="sugerencia-nia" (click)="preguntar(sugerencia)">
              {{ sugerencia }}
            </button>
          }
        </div>
      }

      @if (modoDemostracion()) {
        <p class="aviso-demo meta" data-testid="nia-modo-demo">{{ avisoModo() }}</p>
      }

      <label class="escribir">
        <span class="solo-lector">Escribe tu pregunta para Nia</span>
        <textarea
          rows="2"
          placeholder="Pregúntale algo sobre este juego…"
          [attr.maxlength]="maximo"
          data-testid="nia-pregunta"
          [value]="texto()"
          [disabled]="esperando()"
          (input)="texto.set($any($event.target).value)"
          (keydown.enter)="$event.preventDefault(); preguntar(texto())"
        ></textarea>
      </label>
      <div class="acciones">
        <button
          type="button"
          class="boton-cta"
          data-testid="nia-enviar"
          [disabled]="esperando() || !texto().trim()"
          (click)="preguntar(texto())"
        >
          {{ esperando() ? 'Preguntando…' : 'Preguntar' }}
        </button>
        <span class="meta mono">{{ texto().length }}/{{ maximo }}</span>
      </div>

      <p class="meta error" role="status" aria-live="polite">{{ error() }}</p>
    </section>
  `,
  styles: `
    .nia {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
    }
    h2 {
      font-size: var(--texto-subheading);
    }
    .intro {
      margin: 0;
      line-height: var(--interlineado-largo);
    }
    .conversacion {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: var(--espacio-8);
      max-height: 320px;
      overflow-y: auto;
    }
    .mensaje {
      background: var(--superficie-lienzo);
      border-radius: var(--radio-tarjeta);
      padding: var(--espacio-12);
    }
    .mensaje[data-rol='usuario'] {
      background: var(--acento-sistema);
    }
    .quien {
      display: block;
      margin-bottom: var(--espacio-4);
    }
    .texto {
      margin: 0;
      font-size: var(--texto-body-sm);
      line-height: var(--interlineado-largo);
      overflow-wrap: anywhere;
    }
    .sugerencias {
      display: flex;
      flex-wrap: wrap;
      gap: var(--espacio-8);
    }
    .aviso-demo {
      margin: 0;
      padding: var(--espacio-8) var(--espacio-12);
      border: 1px dashed var(--borde-control);
      border-radius: var(--radio-tarjeta);
      line-height: var(--interlineado-largo);
    }
    .escribir {
      display: flex;
      flex-direction: column;
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
    .error:empty {
      display: none;
    }
    .error {
      margin: 0;
    }
  `,
})
export class Nia {
  readonly appid = input.required<number>();

  private readonly api = inject(NexplayApi);
  private readonly usuario = inject(UsuarioStore);
  private readonly perfil = inject(PerfilStore);
  private readonly conversacion = viewChild<ElementRef<HTMLElement>>('conversacion');

  protected readonly maximo = MAXIMO_TEXTO;
  protected readonly sugerencias = SUGERENCIAS;
  protected readonly texto = signal('');
  protected readonly esperando = signal(false);
  protected readonly error = signal('');
  protected readonly mensajes = signal<MensajeChat[]>([]);
  protected readonly avisoModo = signal('');
  protected readonly modoDemostracion = computed(() => !!this.avisoModo());

  constructor() {
    // Al cambiar de juego, la conversación empieza de cero: el contexto es otro.
    effect(() => {
      this.appid();
      this.mensajes.set([]);
      this.avisoModo.set('');
      this.error.set('');
    });

    effect(() => {
      this.mensajes();
      this.esperando();
      const lista = this.conversacion()?.nativeElement;
      if (lista) {
        // Tras pintar: si se ajusta antes, el último mensaje queda cortado.
        requestAnimationFrame(() => (lista.scrollTop = lista.scrollHeight));
      }
    });
  }

  protected preguntar(pregunta: string): void {
    const contenido = pregunta.trim().slice(0, MAXIMO_TEXTO);
    if (!contenido || this.esperando()) {
      return;
    }

    const mensajes = [...this.mensajes(), { rol: 'usuario' as const, contenido }];
    this.mensajes.set(mensajes);
    this.texto.set('');
    this.error.set('');
    this.esperando.set(true);

    this.api
      .preguntarANia({
        usuario: this.usuario.id,
        appid: this.appid(),
        mensajes: mensajes.slice(-MAXIMO_MENSAJES),
        ...(this.perfil.perfil() ? { perfil: this.perfil.perfil()! } : {}),
      })
      .subscribe({
        next: (respuesta) => {
          this.mensajes.update((actuales) => [...actuales, { rol: 'nia', contenido: respuesta.respuesta }]);
          this.avisoModo.set(respuesta.modo === 'demostracion' ? (respuesta.aviso ?? 'Modo demostración.') : '');
          this.esperando.set(false);
        },
        error: (error: HttpErrorResponse) => {
          this.esperando.set(false);
          this.error.set(
            error.status === 429
              ? (error.error?.detail ?? 'Nia está recibiendo muchas preguntas. Espera un momento.')
              : 'No se pudo preguntar a Nia. Revisa que la API esté corriendo.',
          );
        },
      });
  }
}
