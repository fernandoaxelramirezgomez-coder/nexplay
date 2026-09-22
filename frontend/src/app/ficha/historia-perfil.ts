import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { JuegoCatalogo, MotivoInsatisfaccion } from '../api/contrato';
import { NexplayApi } from '../api/nexplay-api';
import { AVISO_HISTORIA, historiaPerfil } from '../dominio/historia-perfil';
import { PerfilStore } from '../estado/perfil-store';
import { UsuarioStore } from '../estado/usuario-store';

/** Lo que Nia tiene que contar, con las mismas piezas que la versión por reglas. */
const PREGUNTA_A_NIA =
  'Con mi perfil declarado, cuéntame en un párrafo por qué este juego me tocaría a mí:' +
  ' si entra en mis géneros, si lo que más se menciona en las reseñas choca con mi tolerancia a la fricción,' +
  ' y qué significan mis horas por semana frente a las dos primeras horas. No me recomiendes comprarlo.';

/** Por qué este juego le tocaría a quien declaró el perfil. Sale de reglas —siempre, con
 * o sin clave de OpenAI— y un botón deja que Nia lo cuente con sus palabras. */
@Component({
  selector: 'app-historia-perfil',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <section class="historia" data-testid="historia-perfil">
      <h2 class="rotulo-seccion">Por qué te tocaría a ti</h2>

      @if (historia(); as segmentos) {
        <p class="lectura" data-testid="historia-texto">
          @for (segmento of segmentos; track $index) {
            @if (segmento.clave) {
              <strong>{{ segmento.texto }}</strong>
            } @else {
              {{ segmento.texto }}
            }
          }
        </p>

        @if (versionDeNia(); as texto) {
          <p class="lectura nia" data-testid="historia-nia">{{ texto }}</p>
          @if (avisoNia(); as aviso) {
            <p class="meta demo" data-testid="historia-nia-demo">{{ aviso }}</p>
          }
        }

        <div class="acciones">
          <button
            type="button"
            class="boton-fantasma"
            data-testid="historia-pedir-nia"
            [disabled]="esperando()"
            (click)="pedirANia()"
          >
            {{ esperando() ? 'Nia está escribiendo…' : versionDeNia() ? 'Que Nia lo cuente otra vez' : 'Que Nia lo cuente' }}
          </button>
          <span class="meta error" role="status" aria-live="polite">{{ error() }}</span>
        </div>

        <p class="meta aviso">{{ avisoFijo }}</p>
      } @else {
        <p class="lectura" data-testid="historia-sin-perfil">
          Todavía no sabemos cómo juegas. Con tu perfil, aquí aparece por qué este juego te tocaría a ti: tus
          géneros, tu tolerancia a la fricción y tus horas frente a las dos primeras.
        </p>
        <a class="boton-fantasma crear-perfil" routerLink="/perfil" data-testid="historia-crear-perfil">Crear tu perfil</a>
      }
    </section>
  `,
  styles: `
    .historia {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
    }
    p {
      margin: 0;
    }
    /* En una columna flex el enlace se estiraría a todo el ancho; va del tamaño de su texto. */
    .crear-perfil {
      align-self: flex-start;
    }
    /* Lo que escribe Nia se separa de lo que dicen las reglas con una franja neón:
       se ve de inmediato qué párrafo salió de un modelo. */
    .nia {
      padding-left: var(--espacio-16);
      border-left: 2px solid var(--neon);
    }
    .demo {
      margin: 0;
      line-height: var(--interlineado-largo);
    }
    .acciones {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--espacio-12);
    }
    .error:empty {
      display: none;
    }
    .aviso {
      max-width: var(--medida-lectura);
      line-height: var(--interlineado-largo);
    }
  `,
})
export class HistoriaPerfil {
  readonly juego = input.required<JuegoCatalogo>();
  readonly motivos = input<readonly MotivoInsatisfaccion[]>([]);

  private readonly api = inject(NexplayApi);
  private readonly perfil = inject(PerfilStore);
  private readonly usuario = inject(UsuarioStore);

  protected readonly avisoFijo = AVISO_HISTORIA;
  protected readonly esperando = signal(false);
  protected readonly error = signal('');
  protected readonly versionDeNia = signal('');
  protected readonly avisoNia = signal('');

  protected readonly historia = computed(() =>
    historiaPerfil(this.perfil.perfil(), this.juego(), this.motivos()),
  );

  protected pedirANia(): void {
    const perfil = this.perfil.perfil();
    if (!perfil || this.esperando()) {
      return;
    }

    this.esperando.set(true);
    this.error.set('');
    this.api
      .preguntarANia({
        usuario: this.usuario.id,
        appid: this.juego().appid,
        mensajes: [{ rol: 'usuario', contenido: PREGUNTA_A_NIA }],
        perfil,
      })
      .subscribe({
        next: (respuesta) => {
          this.versionDeNia.set(respuesta.respuesta);
          this.avisoNia.set(respuesta.modo === 'demostracion' ? (respuesta.aviso ?? 'Modo demostración.') : '');
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
