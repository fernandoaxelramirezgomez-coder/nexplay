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

import { JuegoCatalogo, MensajeChat } from '../api/contrato';
import { NexplayApi } from '../api/nexplay-api';
import { RouterLink } from '@angular/router';

import { PildoraBanda } from '../compartido/pildora-banda';
import { Portada } from '../compartido/portada';
import { VotoNia } from './voto-nia';
import { sinMarkdown } from '../dominio/textos-nia';
import { CatalogoStore } from '../estado/catalogo-store';
import { HistorialStore } from '../estado/historial-store';
import { PerfilStore } from '../estado/perfil-store';
import { UsuarioStore } from '../estado/usuario-store';

const MAXIMO_TEXTO = 500;
/** La API acepta 10 mensajes; se manda la cola más reciente. */
const MAXIMO_MENSAJES = 10;

/** Lo mismo que DIAS_DE_RETENCION_NIA en api/valoraciones.py. */
const DIAS_DE_RETENCION_NIA = 180;

const SUGERENCIAS_JUEGO = ['¿Por qué tiene esa banda?', '¿Cuánto cuesta?', '¿Qué dice la crítica?'];

/** Sin juego elegido, las preguntas de arranque son del catálogo entero. */
const SUGERENCIAS_CATALOGO = [
  '¿Qué juegos de acción tienen riesgo bajo?',
  '¿Hay algo gratis?',
  '¿De dónde salen los datos?',
];

/** Lo primero que se ve cuando la conversación está vacía: antes había un hueco. */
/** No repite el rótulo de arriba ("Pregúntale a Nia"): dice qué sabe contestar, que es
 * lo que el rótulo no dice. */
const BIENVENIDA_CHAT =
  'Puedo contarte por qué quedó en esa banda, qué motivos aparecen en las reseñas, qué ' +
  'dijo la crítica y cuánto cuesta. Lo que no hago es decirte si comprarlo.';

const BIENVENIDA_CATALOGO =
  'Puedo filtrar los juegos del catálogo por género, banda de riesgo y precio, leer la ' +
  'ficha de cualquiera y contarte de dónde salen los datos. Lo que no hago es elegir por ti.';

/** El chat de Nia, con un juego fijado o sobre el catálogo entero.
 *
 * Con `appid`, el backend le pasa los datos de ese juego; sin él, Nia usa sus herramientas
 * sobre el catálogo. La conversación vive solo en pantalla y no se guarda; lo que sí queda
 * anotado del lado del servidor es cada pregunta y su respuesta, para poder votarlas. */
@Component({
  selector: 'app-nia',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [VotoNia, RouterLink, Portada, PildoraBanda],
  template: `
    <section class="seccion nia" data-testid="nia" [class.destacada]="muestraTitulo()" [class.alto]="llenaAlto()">
      @if (muestraTitulo()) {
        <header class="cabecera">
          <img class="avatar" src="nia/chat.png" alt="" width="200" height="233" data-testid="nia-avatar" />
          <h2 class="titulo">Pregúntale a Nia</h2>
        </header>
      }
      @if (muestraIntro()) {
        <p class="meta intro">
          Responde con los datos de este juego: su banda, los motivos de las reseñas, la crítica y el precio. No
          recomienda comprar ni no comprar.
        </p>
      }

      @if (!mensajes().length) {
        <p class="globo-nia bienvenida" data-testid="nia-bienvenida">
          <span class="quien">Nia</span>
          {{ bienvenida() }}
        </p>
      }

      @if (mensajes().length) {
        <ol class="conversacion" #conversacion data-testid="conversacion">
          @for (mensaje of mensajes(); track $index) {
            <li class="mensaje" [attr.data-rol]="mensaje.rol" [attr.data-testid]="'mensaje-' + mensaje.rol">
              <span class="quien meta mono">{{ mensaje.rol === 'usuario' ? 'Tú' : 'Nia' }}</span>
              @if (pasosPorMensaje()[$index]; as pasos) {
                <p class="pasos meta" data-testid="nia-pasos">{{ pasos.join(' · ') }}</p>
              }
              <p class="texto">{{ mensaje.contenido }}</p>
              @if (juegosPorMensaje()[$index]; as appids) {
                <ul class="tarjetas" data-testid="nia-juegos">
                  @for (juego of tarjetas(appids); track juego.appid) {
                    <li>
                      <a class="tarjeta" [routerLink]="['/juego', juego.appid]" data-testid="nia-tarjeta">
                        <app-portada class="mini" [src]="juego.portada_url" radio="6px" />
                        <span class="nombre">{{ juego.nombre }}</span>
                        <app-pildora-banda [banda]="juego.banda_riesgo" [compacta]="true" />
                      </a>
                    </li>
                  }
                </ul>
              }
              @if (mensaje.rol === 'nia' && idPorMensaje()[$index]; as idRespuesta) {
                <app-voto-nia [idRespuesta]="idRespuesta" />
              }
            </li>
          }
          @if (esperando()) {
            <li class="mensaje" data-rol="nia">
              <span class="quien meta mono">Nia</span>
              <p class="texto meta" data-testid="nia-escribiendo">
                <span class="puntos" aria-hidden="true"><span></span><span></span><span></span></span>
                {{ progreso() }}
              </p>
            </li>
          }
        </ol>
      }

      @if (pendientes().length) {
        <div class="sugerencias">
          @for (sugerencia of pendientes(); track sugerencia) {
            <button
              type="button"
              class="chip"
              data-testid="sugerencia-nia"
              [disabled]="esperando()"
              (click)="preguntar(sugerencia)"
            >
              {{ sugerencia }}
            </button>
          }
        </div>
      }

      <p class="modo meta" data-testid="nia-modo" [attr.data-modo]="modo()">
        <span class="punto" aria-hidden="true"></span>
        @if (modo() === 'demostracion') {
          Modo demostración: respuestas automáticas sin IA.
        } @else if (modo() === 'openai') {
          Respuesta generada con IA a partir de los datos de este juego.
        } @else {
          Nia responde solo con los datos de este juego.
        }
      </p>

      <p class="meta privacidad" data-testid="nia-privacidad">
        No escribas datos personales: se guardan tu pregunta y la respuesta durante
        {{ diasQueSeGuarda }} días, para poder revisar los votos.
      </p>

      <label class="escribir">
        <span class="solo-lector">Escribe tu pregunta para Nia</span>
        <textarea
          id="nia-pregunta"
          rows="2"
          [attr.placeholder]="appid() === null ? 'Pregúntale algo del catálogo…' : 'Pregúntale algo sobre este juego…'"
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
      gap: var(--espacio-8);
    }
    /* En la ficha el chat es una pieza de interfaz, no texto largo: lleva superficie y un
       filo neón con brillo, más marcado que el resto de la ficha, que va sin caja. Dentro
       de la burbuja flotante no, porque ahí el panel ya es la superficie. */
    .destacada {
      padding: var(--espacio-16);
      border: 1px solid color-mix(in srgb, var(--neon) 55%, var(--linea));
      border-radius: var(--radio-tarjeta);
      background: var(--superficie-tarjeta);
      box-shadow:
        0 0 0 1px rgb(var(--neon-canal) / 0.1),
        0 0 calc(24px * var(--halo-radio)) rgb(var(--neon-canal) / calc(0.16 * var(--halo-alfa)));
    }
    .cabecera {
      display: flex;
      align-items: center;
      gap: var(--espacio-12);
    }
    /* Nia saludando (Wave, de la hoja v2), la misma cara que la burbuja del chat. */
    .avatar {
      width: 40px;
      height: 40px;
      padding: 4px 4px 0;
      object-fit: contain;
      object-position: center bottom;
      border-radius: 50%;
      background: var(--superficie-lienzo);
      box-shadow:
        0 0 0 1px var(--neon),
        0 0 calc(10px * var(--halo-radio)) rgb(var(--neon-canal) / calc(0.4 * var(--halo-alfa)));
    }
    .titulo {
      margin: 0;
      font-size: var(--texto-body-sm);
    }
    /* El chat es para leer la respuesta, no la introducción: lo de alrededor va compacto
       y el alto que se gana se lo queda la conversación. */
    .intro {
      margin: 0;
      font-size: var(--texto-caption);
      line-height: var(--interlineado-largo);
    }
    .bienvenida {
      margin: 0;
    }
    /* Con alto propio, la conversación es lo que crece y el campo queda al final. El
       host es flex column (chat/nia-pagina.ts), así que la sección llena lo que haya. */
    .nia.alto {
      flex: 1;
      min-height: 0;
    }
    .nia.alto .conversacion {
      flex: 1;
      max-height: none;
    }
    .nia.alto .escribir {
      margin-top: auto;
    }
    .conversacion {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: var(--espacio-8);
      max-height: min(72vh, 620px);
      overflow-y: auto;
    }
    .mensaje {
      background: var(--superficie-lienzo);
      border-radius: var(--radio-tarjeta);
      padding: var(--espacio-8) var(--espacio-12);
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
    /* Lo que consultó antes de responder. Va arriba, en letra de dato: es el rastro de
       de dónde salió lo que dice, no parte de la respuesta. */
    .pasos {
      margin: 0 0 var(--espacio-4);
      font-size: var(--texto-caption);
    }
    /* Los juegos que nombra, como tarjeta: el appid lo devolvió una herramienta y la
       portada sale del catálogo del navegador, nunca de lo que diga el modelo. */
    .tarjetas {
      list-style: none;
      margin: var(--espacio-8) 0 0;
      padding: 0;
      display: flex;
      flex-wrap: wrap;
      gap: var(--espacio-8);
    }
    .tarjeta {
      display: flex;
      align-items: center;
      gap: var(--espacio-8);
      padding: var(--espacio-4) var(--espacio-8) var(--espacio-4) var(--espacio-4);
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-pildora);
      color: inherit;
      text-decoration: none;
      font-size: var(--texto-caption);
      transition: border-color var(--duracion-rapida) var(--curva);
    }
    .tarjeta:hover {
      border-color: var(--neon);
    }
    .tarjeta .mini {
      width: 46px;
      flex: none;
    }
    .sugerencias {
      display: flex;
      flex-wrap: wrap;
      gap: var(--espacio-8);
    }
    /* Aquí los chips se pulsan para preguntar: llevan filo y superficie para que se lean
       como botones y no como el texto de al lado. */
    .sugerencias .chip {
      padding: var(--espacio-8) var(--espacio-12);
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-pildora);
      background: var(--superficie-lienzo);
      font-family: var(--fuente-texto);
    }
    .sugerencias .chip:hover:not([disabled]) {
      border-color: var(--neon);
      color: var(--texto);
    }
    .sugerencias .chip::after {
      content: none;
    }
    .sugerencias .chip[disabled] {
      opacity: 0.55;
      cursor: not-allowed;
    }
    /* El modo se ve siempre, no solo cuando responde por reglas: saber quién contesta es
       parte de la respuesta, y el punto verde tiene que decir que contestó una IA. */
    .modo {
      display: flex;
      align-items: baseline;
      gap: var(--espacio-8);
      margin: 0;
      line-height: var(--interlineado-largo);
    }
    .modo .punto {
      width: 8px;
      height: 8px;
      flex: none;
      border-radius: 50%;
      background: var(--borde-control);
    }
    .modo[data-modo='openai'] .punto {
      background: var(--banda-bajo);
    }
    .modo[data-modo='demostracion'] .punto {
      background: var(--banda-medio);
    }
    /* Tres puntos que laten mientras Nia responde. La regla global de
       prefers-reduced-motion los deja quietos. */
    .puntos {
      display: inline-flex;
      gap: 3px;
    }
    .puntos span {
      width: 5px;
      height: 5px;
      border-radius: 50%;
      background: var(--texto-meta);
      animation: latir 1.2s ease-in-out infinite;
    }
    .puntos span:nth-child(2) {
      animation-delay: 0.15s;
    }
    .puntos span:nth-child(3) {
      animation-delay: 0.3s;
    }
    @keyframes latir {
      0%,
      100% {
        opacity: 0.3;
      }
      50% {
        opacity: 1;
      }
    }
    .privacidad {
      margin: 0;
      font-size: var(--texto-caption);
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
      border-color: var(--neon);
    }
    .acciones {
      display: flex;
      align-items: center;
      gap: var(--espacio-12);
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
  /** El juego del que se habla, o null para hablar del catálogo entero. */
  readonly appid = input<number | null>(null);
  /** La burbuja flotante ya pone el rótulo en su cabecera: ahí sobra repetirlo. */
  readonly muestraTitulo = input(true);
  /** La página de Nia ya explica arriba con qué responde: repetirlo aquí es la misma
   * frase dos veces, una debajo de la otra. */
  readonly muestraIntro = input(true);
  /** En su propia página el chat ocupa todo el panel: la conversación crece y el campo de
   * escribir se queda abajo, como en cualquier chat. */
  readonly llenaAlto = input(false);

  private readonly api = inject(NexplayApi);
  private readonly usuario = inject(UsuarioStore);
  private readonly perfil = inject(PerfilStore);
  private readonly catalogo = inject(CatalogoStore);
  private readonly historial = inject(HistorialStore);
  private readonly conversacion = viewChild<ElementRef<HTMLElement>>('conversacion');

  protected readonly maximo = MAXIMO_TEXTO;
  protected readonly sugerencias = computed(() => (this.appid() === null ? SUGERENCIAS_CATALOGO : SUGERENCIAS_JUEGO));
  protected readonly bienvenida = computed(() =>
    this.appid() === null ? BIENVENIDA_CATALOGO : BIENVENIDA_CHAT,
  );
  /** El mismo número que aplica api/valoraciones.py (DIAS_DE_RETENCION_NIA): si allá
   * cambia, aquí también, o el aviso miente. */
  protected readonly diasQueSeGuarda = DIAS_DE_RETENCION_NIA;
  /** Las que todavía no se preguntaron en esta conversación: una sugerencia ya usada solo
   * repetiría la misma respuesta. Cuando no queda ninguna, la fila desaparece. */
  protected readonly pendientes = computed(() => {
    const preguntadas = new Set(
      this.mensajes()
        .filter((mensaje) => mensaje.rol === 'usuario')
        .map((mensaje) => mensaje.contenido.trim()),
    );
    return this.sugerencias().filter((sugerencia) => !preguntadas.has(sugerencia));
  });
  protected readonly texto = signal('');
  protected readonly esperando = signal(false);
  protected readonly error = signal('');
  protected readonly mensajes = signal<MensajeChat[]>([]);
  /** El id que la API le puso a cada respuesta, por posición en el hilo. No va dentro del
   * mensaje: los mensajes se reenvían a la API tal cual y ahí solo caben rol y contenido. */
  protected readonly idPorMensaje = signal<Record<number, string>>({});
  /** Lo que consultó antes de responder, por posición. */
  protected readonly pasosPorMensaje = signal<Record<number, string[]>>({});
  /** Los appids que la respuesta puede pintar como tarjeta, por posición. La API ya los
   * filtró: solo pasan los que una herramienta devolvió en ese turno. */
  protected readonly juegosPorMensaje = signal<Record<number, number[]>>({});
  /** '' hasta la primera respuesta: entonces se sabe si contestó el modelo o las reglas. */
  protected readonly modo = signal<'' | 'openai' | 'demostracion'>('');
  /** Mientras espera, el texto cambia: a los cuatro segundos deja de ser "escribiendo". */
  protected readonly progreso = signal('Escribiendo…');
  private relojProgreso?: ReturnType<typeof setTimeout>;

  constructor() {
    // Al cambiar de juego, la conversación empieza de cero: el contexto es otro.
    effect(() => {
      this.appid();
      this.mensajes.set([]);
      this.idPorMensaje.set({});
      this.pasosPorMensaje.set({});
      this.juegosPorMensaje.set({});
      this.modo.set('');
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

  /** Del appid a la tarjeta, con el catálogo que ya tiene el navegador: del modelo solo
   * viaja el número. Un appid que no esté en el catálogo no se pinta. */
  protected tarjetas(appids: readonly number[]): JuegoCatalogo[] {
    const porAppid = this.catalogo.porAppid();
    return appids.map((appid) => porAppid.get(appid)).filter((juego): juego is JuegoCatalogo => !!juego);
  }

  protected preguntar(pregunta: string): void {
    const contenido = pregunta.trim().slice(0, MAXIMO_TEXTO);
    if (!contenido || this.esperando()) {
      return;
    }

    const mensajes = [...this.mensajes(), { rol: 'usuario' as const, contenido }];
    this.mensajes.set(mensajes);
    const appid = this.appid();
    // Sin juego no hay ficha que recordar: el historial guarda juegos, no conversaciones.
    if (appid !== null) {
      this.historial.registrar({
        tipo: 'nia',
        appid,
        titulo: this.catalogo.porAppid().get(appid)?.nombre ?? `Juego ${appid}`,
      });
    }
    this.texto.set('');
    this.error.set('');
    this.esperando.set(true);
    this.progreso.set('Escribiendo…');
    clearTimeout(this.relojProgreso);
    this.relojProgreso = setTimeout(
      () => this.progreso.set(appid === null ? 'Buscando en el catálogo…' : 'Sigue leyendo los datos del juego…'),
      4000,
    );

    this.api
      .preguntarANia({
        usuario: this.usuario.id,
        ...(appid !== null ? { appid } : {}),
        mensajes: mensajes.slice(-MAXIMO_MENSAJES),
        ...(this.perfil.perfil() ? { perfil: this.perfil.perfil()! } : {}),
      })
      .subscribe({
        next: (respuesta) => {
          const posicion = this.mensajes().length;
          this.idPorMensaje.update((ids) => ({ ...ids, [posicion]: respuesta.id }));
          if (respuesta.pasos.length) {
            this.pasosPorMensaje.update((pasos) => ({ ...pasos, [posicion]: respuesta.pasos }));
          }
          if (respuesta.juegos.length) {
            this.juegosPorMensaje.update((juegos) => ({ ...juegos, [posicion]: respuesta.juegos }));
          }
          this.mensajes.update((actuales) => [
            ...actuales,
            { rol: 'nia', contenido: sinMarkdown(respuesta.respuesta) },
          ]);
          this.modo.set(respuesta.modo);
          this.esperando.set(false);
          clearTimeout(this.relojProgreso);
        },
        error: (error: HttpErrorResponse) => {
          this.esperando.set(false);
          clearTimeout(this.relojProgreso);
          this.error.set(
            error.status === 429
              ? (error.error?.detail ?? 'Nia está recibiendo muchas preguntas. Espera un momento.')
              : 'No se pudo preguntar a Nia. Revisa que la API esté corriendo.',
          );
        },
      });
  }
}
