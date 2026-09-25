import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { JuegoCatalogo, MotivoInsatisfaccion } from '../api/contrato';
import { NexplayApi } from '../api/nexplay-api';
import { AVISO_HISTORIA, historiaPerfil, partirDatos } from '../dominio/historia-perfil';
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

      @if (historiaConDatos(); as segmentos) {
        <!-- En una sola línea a propósito: los saltos entre bloques se volverían espacios
             dentro del párrafo. Los espacios de verdad ya vienen en cada segmento. -->
        <p class="lectura parrafo" data-testid="historia-texto">@for (segmento of segmentos; track $index) {@if (segmento.clave) {<strong class="clave">{{ segmento.texto }}</strong>} @else {@for (trozo of segmento.trozos; track $index) {@if (trozo.dato) {<span class="dato">{{ trozo.texto }}</span>} @else {<ng-container>{{ trozo.texto }}</ng-container>}}}}</p>

        @if (versionDeNia(); as texto) {
          <p class="lectura nia" data-testid="historia-nia">{{ texto }}</p>
          @if (avisoNia(); as aviso) {
            <p class="meta demo" data-testid="historia-nia-demo">{{ aviso }}</p>
          }
        }

        <!-- Mini Nia decorativa: acompaña al botón que le pide contarlo, no dice nada. -->
        <div class="con-nia" data-testid="historia-con-nia">
          <img
            class="mini-nia"
            src="nia/historia.png"
            alt=""
            aria-hidden="true"
            width="210"
            height="235"
            loading="lazy"
            data-testid="historia-mini-nia"
          />
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
    /* El párrafo por reglas es lo que se lee de esta sección: Inter un paso más grande que
       la lectura normal y con más aire entre líneas. */
    .parrafo {
      font-family: var(--fuente-texto);
      font-size: calc(var(--texto-body) + 2px);
      line-height: 1.7;
    }
    /* Las cifras (porcentajes, horas, días) van en la mono, como los datos del resto de
       la app; un poco más chicas para que igualen la altura de la x de Inter. */
    .dato {
      font-family: var(--fuente-mono);
      font-size: 0.9em;
      letter-spacing: 0;
      white-space: nowrap;
    }
    /* La palabra clave lleva un subrayado cian que brilla hacia abajo. El brillo es del
       subrayado: las letras conservan el color de texto, sin sombra, y el contraste AA. */
    .clave {
      color: var(--texto);
      padding-bottom: 3px;
      background-image:
        linear-gradient(var(--neon), var(--neon)),
        linear-gradient(to top, rgb(var(--neon-canal) / 0.3), rgb(var(--neon-canal) / 0));
      background-size:
        100% 2px,
        100% 9px;
      background-position:
        0 100%,
        0 100%;
      background-repeat: no-repeat;
      -webkit-box-decoration-break: clone;
      box-decoration-break: clone;
    }
    .con-nia {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--espacio-8);
      margin-top: var(--espacio-8);
    }
    /* Nia con el foco encendido (Idea, de la hoja v2): la idea de contarlo con sus palabras. */
    .mini-nia {
      width: 84px;
      height: auto;
      filter: drop-shadow(0 0 calc(6px * var(--halo-radio)) rgb(var(--neon-canal) / calc(0.3 * var(--halo-alfa))));
    }
    .acciones {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: center;
      gap: var(--espacio-12);
    }
    @media (max-width: 640px) {
      .parrafo {
        font-size: var(--texto-body);
        line-height: 1.65;
      }
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

  /** La historia con las cifras separadas, para pintarlas en la mono. */
  protected readonly historiaConDatos = computed(() =>
    this.historia()?.map((segmento) => ({ ...segmento, trozos: partirDatos(segmento.texto) })),
  );

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
