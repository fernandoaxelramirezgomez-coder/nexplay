import { HttpErrorResponse } from '@angular/common/http';
import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  computed,
  effect,
  inject,
  input,
  output,
  signal,
  untracked,
  viewChild,
} from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { JuegoCatalogo, MensajeChat, RespuestaNia } from '../api/contrato';
import { NexplayApi } from '../api/nexplay-api';
import { PildoraBanda } from '../compartido/pildora-banda';
import { Portada } from '../compartido/portada';
import { recortarHistorial, sugerenciasParaNia } from '../dominio/historial-nia';
import { criteriosDesde, sugerenciasPara } from '../dominio/sugerencias';
import {
  COMO_FILTRAR,
  EXPLICACION_SENAL,
  FICHAS_CATALOGO,
  FICHAS_JUEGO,
  FILTRAR_EL_CATALOGO,
  HABLAR_DE_UN_JUEGO,
  PIDE_JUEGO,
  SALUDO_CHAT_CATALOGO,
  saludoDeJuego,
  sinMarkdown,
} from '../dominio/textos-nia';
import { CatalogoStore } from '../estado/catalogo-store';
import { CompararStore, MAXIMO_COMPARAR } from '../estado/comparar-store';
import { HistorialStore } from '../estado/historial-store';
import { PanoramaStore } from '../estado/panorama-store';
import { PerfilStore } from '../estado/perfil-store';
import { UsuarioStore } from '../estado/usuario-store';
import { ElegirJuegoChat } from './elegir-juego-chat';
import { VotoNia } from './voto-nia';

const MAXIMO_TEXTO = 500;

/** Lo mismo que DIAS_DE_RETENCION_NIA en api/valoraciones.py. */
const DIAS_DE_RETENCION_NIA = 180;

/** Lo que acompaña a cada mensaje, por posición en el hilo. No va dentro del mensaje: los
 * mensajes se reenvían a la API tal cual y ahí solo caben rol y contenido. */
interface Extra {
  /** El id que la API le puso a la respuesta, para votarla. */
  id?: string;
  /** Los appids que puede pintar como tarjeta: la API ya los filtró. */
  juegos?: number[];
  /** Los appids que se pintan como «Sugerencia según tu perfil». */
  sugerencias?: number[];
  /** Nia pidió un juego: el mensaje trae el buscador hasta que se elige. */
  pideJuego?: boolean;
  resuelto?: boolean;
  /** Pidieron sugerencias sin perfil: el mensaje invita a crearlo. */
  pidePerfil?: boolean;
  /** La pregunta pedía comparar: si hay dos o más tarjetas, se ofrece abrirlas en Comparar. */
  comparar?: boolean;
  /** Ya había otros juegos en Comparar: el mensaje pregunta si reemplazarlos o agregar. */
  eligiendoComparar?: boolean;
  /** La pregunta no encajaba con el catálogo: solo ahí Nia dice sus avisos. */
  fueraDeTema?: boolean;
}

/** El chat de Nia, con un juego fijado o sobre el catálogo entero.
 *
 * Con `appid`, el backend le pasa los datos de ese juego; sin él, Nia usa sus herramientas
 * sobre el catálogo, y si la pregunta es de un juego lo pide con un buscador dentro del
 * chat. La conversación vive solo en pantalla; del lado del servidor queda anotada cada
 * pregunta con su respuesta, para poder votarlas. */
@Component({
  selector: 'app-nia',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [VotoNia, RouterLink, Portada, PildoraBanda, ElegirJuegoChat],
  // Nia lleva su violeta en cualquier vista donde aparezca (la ficha, la burbuja): el
  // botón principal y los compactos de adentro toman el color de acción de su vista.
  host: { 'data-vista': 'nia' },
  template: `
    <section class="seccion nia" data-testid="nia" [class.destacada]="muestraTitulo()" [class.alto]="llenaAlto()">
      @if (muestraTitulo()) {
        <header class="cabecera">
          <img class="avatar" src="nia/chat.png" alt="" width="200" height="233" data-testid="nia-avatar" />
          <h2 class="titulo">Pregúntale a Nia</h2>
        </header>
      }
      <!-- Todo lo que va entre la cabecera y el campo: en la columna de la ficha (alto) se
           desplaza como un solo bloque, y el campo con «Preguntar» se queda siempre abajo.
           Fuera de ahí no es una caja (display: contents). -->
      <!-- Qué es la señal, fijo arriba y fuera de lo que se desplaza: las respuestas ya no lo
           repiten. Va aquí y no en cada página para que salga igual en /nia, la ficha y la burbuja. -->
      <p class="senal meta" data-testid="nia-senal">{{ explicacionSenal }}</p>
      <div class="cuerpo-chat" #cuerpo>
      @if (muestraIntro()) {
        <p class="meta intro">Pregúntale por su riesgo, sus reseñas, la crítica o el precio.</p>
      }

      @if (fijadoEnElChat(); as juego) {
        <p class="hablando" data-testid="nia-hablando">
          Hablando de <strong>{{ juego.nombre }}</strong>
          <button type="button" class="boton-texto" data-testid="nia-hablando-cambiar" (click)="cambiarJuego()">
            Cambiar
          </button>
        </p>
      }

      <ol class="conversacion" #conversacion data-testid="conversacion">
        <li class="mensaje" data-rol="nia" data-testid="nia-bienvenida">
          <span class="quien meta mono">Nia</span>
          <p class="texto">{{ bienvenida() }}</p>
        </li>
        @for (mensaje of mensajes(); track $index) {
          @let extra = extras()[$index];
          <li
            class="mensaje"
            [class.pide-juego]="extra?.pideJuego"
            [attr.data-rol]="mensaje.rol"
            [attr.data-testid]="'mensaje-' + mensaje.rol"
          >
            <span class="quien meta mono">
              {{ mensaje.rol === 'usuario' ? 'Tú' : extra?.pideJuego ? 'Nia · necesito un juego' : 'Nia' }}
            </span>
            <p class="texto">{{ mensaje.contenido }}</p>
            @if (extra?.fueraDeTema && !extra?.pideJuego) {
              <p class="aviso-tema" data-testid="nia-aviso-tema">
                Solo hablo de los juegos del catálogo y no te digo si comprarlos o no. No escribas datos
                personales: tus preguntas se guardan {{ diasQueSeGuarda }} días.
              </p>
            }
            @if (extra?.pideJuego && !extra?.resuelto) {
              <app-elegir-juego-chat (elegido)="fijarJuego($event, $index)" />
            }
            @if (extra?.pidePerfil) {
              <a class="compacto invitar" data-tono="perfil" routerLink="/perfil" data-testid="nia-crear-perfil">
                Crear mi perfil →
              </a>
            }
            @if (extra?.juegos?.length) {
              <ul class="tarjetas" data-testid="nia-juegos">
                @for (juego of tarjetas(extra!.juegos!); track juego.appid) {
                  <li>
                    <a class="tarjeta" [routerLink]="['/juego', juego.appid]" data-testid="nia-tarjeta">
                      <app-portada class="mini" [src]="juego.portada_url" radio="6px" />
                      <span class="nombre">{{ juego.nombre }}</span>
                      <app-pildora-banda [banda]="juego.banda_riesgo" [compacta]="true" />
                    </a>
                  </li>
                }
              </ul>
              @if (extra?.comparar && extra!.juegos!.length >= 2) {
                @if (extra?.eligiendoComparar) {
                  <!-- Ya había otros juegos en Comparar: se pregunta antes de pisarlos. -->
                  <div class="elegir-comparar" data-testid="nia-comparar-elegir">
                    <span class="meta">Ya tienes {{ comparar.cantidad() }} en Comparar.</span>
                    <button
                      type="button"
                      class="compacto"
                      data-tono="comparar"
                      data-testid="nia-comparar-reemplazar"
                      (click)="irAComparar(extra!.juegos!)"
                    >
                      Reemplazarlos
                    </button>
                    <button
                      type="button"
                      class="compacto"
                      data-tono="comparar"
                      data-testid="nia-comparar-agregar"
                      (click)="irAComparar(juntos(extra!.juegos!))"
                    >
                      Agregar{{ caben(extra!.juegos!) }}
                    </button>
                  </div>
                } @else {
                  <button
                    type="button"
                    class="compacto invitar"
                    data-tono="comparar"
                    data-testid="nia-comparar"
                    (click)="verEnComparar(extra!.juegos!, $index)"
                  >
                    Verlos en Comparar →
                  </button>
                }
              }
            }
            @if (extra?.sugerencias?.length) {
              <ul class="sugeridos" data-testid="nia-sugerencias">
                @for (juego of tarjetas(extra!.sugerencias!); track juego.appid) {
                  <li>
                    <a class="sugerido" [routerLink]="['/juego', juego.appid]" data-testid="nia-sugerencia">
                      <app-portada class="portada" [src]="juego.portada_url" radio="8px" />
                      <span class="rotulo">Sugerencia según tu perfil</span>
                      <span class="nombre">{{ juego.nombre }}</span>
                      <app-pildora-banda [banda]="juego.banda_riesgo" [compacta]="true" />
                      @if (porQue()[juego.appid]; as razon) {
                        <span class="porque">{{ razon }}</span>
                      }
                    </a>
                  </li>
                }
              </ul>
            }
            @if (mensaje.rol === 'nia' && extra?.id; as idRespuesta) {
              <app-voto-nia [idRespuesta]="extra!.id!" />
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

      @if (pendientes().length) {
        <div class="sugerencias">
          @for (ficha of pendientes(); track ficha) {
            <button
              type="button"
              class="compacto"
              data-testid="sugerencia-nia"
              [disabled]="esperando()"
              (click)="tocarFicha(ficha)"
            >
              {{ ficha }}
            </button>
          }
        </div>
      }

      </div>

      <label class="escribir">
        <span class="solo-lector">Escribe tu pregunta para Nia</span>
        <textarea
          #campo
          id="nia-pregunta"
          rows="2"
          [attr.placeholder]="appidEfectivo() === null ? 'Pregúntale algo del catálogo…' : 'Pregúntale algo sobre este juego…'"
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
        @if (modo()) {
          <span class="modo" data-testid="nia-modo" [attr.data-modo]="modo()">
            {{ modo() === 'openai' ? 'Con IA' : modo() === 'reglas' ? 'Sin IA' : 'Sin IA · demostración' }}
          </span>
        }
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
    .senal {
      flex: none;
      margin: 0;
      font-size: var(--texto-caption);
      line-height: var(--interlineado-largo);
    }
    /* Con alto propio, la conversación es lo que crece y el campo queda al final. El
       host es flex column (chat/nia-pagina.ts), así que la sección llena lo que haya. */
    .nia.alto {
      flex: 1;
      min-height: 0;
    }
    .cuerpo-chat {
      display: contents;
    }
    /* En la columna de la ficha el alto es el de la pantalla: si no alcanza, el cuerpo se
       desplaza por dentro y el campo con «Preguntar» se queda a la vista. */
    .nia.alto .cuerpo-chat {
      display: flex;
      flex: 1;
      flex-direction: column;
      gap: var(--espacio-8);
      min-height: 0;
      overflow-y: auto;
    }
    .nia.alto .conversacion {
      max-height: none;
      overflow-y: visible;
    }
    .hablando {
      align-self: flex-start;
      display: flex;
      align-items: center;
      gap: var(--espacio-8);
      margin: 0;
      padding: 2px 4px 2px var(--espacio-12);
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-pildora);
      background: var(--superficie-lienzo);
      font-size: var(--texto-body-sm);
    }
    .conversacion {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
      max-height: min(72vh, 620px);
      overflow-y: auto;
    }
    /* Sus globos a la izquierda y los tuyos a la derecha, como en cualquier chat. */
    .mensaje {
      align-self: flex-start;
      max-width: 92%;
      box-sizing: border-box;
      background: var(--superficie-lienzo);
      border-radius: 4px var(--radio-tarjeta) var(--radio-tarjeta) var(--radio-tarjeta);
      padding: var(--espacio-8) var(--espacio-12) var(--espacio-12);
    }
    .mensaje[data-rol='usuario'] {
      align-self: flex-end;
      background: var(--acento-sistema);
      border-radius: var(--radio-tarjeta) 4px var(--radio-tarjeta) var(--radio-tarjeta);
    }
    /* Cuando Nia necesita un juego, su mensaje cambia de contorno: el azul de información,
       no los colores del riesgo ni su violeta, para que se lea como «me falta algo». */
    .mensaje.pide-juego {
      width: 92%;
      border: 2px dashed var(--info);
      background: color-mix(in srgb, var(--info) 8%, var(--superficie-lienzo));
    }
    .quien {
      display: block;
      margin-bottom: var(--espacio-4);
    }
    /* Letra de lectura: 17 px con aire, la respuesta es lo que se viene a leer. */
    .texto {
      margin: 0;
      font-size: 17px;
      line-height: 1.5;
      overflow-wrap: anywhere;
    }
    .invitar {
      display: inline-flex;
      margin-top: var(--espacio-8);
    }
    .elegir-comparar {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--espacio-8);
      margin-top: var(--espacio-8);
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
    /* Las sugerencias del perfil van aparte de las tarjetas de datos: rótulo propio, filo
       del rosa de Tu perfil y el riesgo de cada una al lado, también cuando es alto. */
    .sugeridos {
      list-style: none;
      margin: var(--espacio-8) 0 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: var(--espacio-8);
    }
    .sugerido {
      display: grid;
      grid-template-columns: 88px minmax(0, 1fr) auto;
      gap: 4px var(--espacio-12);
      align-items: center;
      padding: 10px;
      border: 1px solid color-mix(in srgb, var(--t-perfil) var(--mezcla-filo), var(--superficie));
      border-radius: var(--radio-boton);
      background: var(--superficie);
      color: inherit;
      text-decoration: none;
    }
    .sugerido .portada {
      grid-row: 1 / span 3;
      width: 88px;
    }
    .sugerido .rotulo {
      grid-column: 2 / span 2;
      justify-self: start;
      padding: 1px 10px;
      border: 1px solid color-mix(in srgb, var(--t-perfil) var(--mezcla-filo), var(--superficie));
      border-radius: var(--radio-pildora);
      font-size: var(--texto-caption);
    }
    .sugerido .nombre {
      font-weight: var(--peso-clave);
      font-size: 17px;
    }
    .sugerido .porque {
      grid-column: 2 / span 2;
      color: var(--texto-meta);
      font-size: var(--texto-caption);
    }
    .sugerencias {
      display: flex;
      flex-wrap: wrap;
      gap: var(--espacio-8);
    }
    /* El modo se ve siempre, no solo cuando responde por reglas: saber quién contesta es
       parte de la respuesta, y el punto verde tiene que decir que contestó una IA. */
    /* Con IA o sin ella, en una etiqueta junto al contador: no es un aviso, es de dónde
       sale la respuesta. */
    .modo {
      margin-left: auto;
      padding: 2px 10px;
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-pildora);
      color: var(--texto-meta);
      font-size: var(--texto-caption);
      white-space: nowrap;
    }
    /* Los avisos, solo cuando la pregunta se salió del tema: dentro del globo de Nia, con
       el azul de información y no con los colores del riesgo. */
    .aviso-tema {
      margin: var(--espacio-8) 0 0;
      padding: var(--espacio-8) var(--espacio-12);
      border-inline-start: 3px solid var(--info);
      border-radius: 0 8px 8px 0;
      background: color-mix(in srgb, var(--info) 10%, transparent);
      color: var(--texto);
      font-size: var(--texto-caption);
      line-height: var(--interlineado-largo);
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
    .escribir {
      display: flex;
      flex-direction: column;
    }
    textarea {
      font: inherit;
      font-size: 17px;
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
    /* Con wrap: en el teléfono la etiqueta del modo baja de renglón en vez de ensanchar
       el chat. */
    .acciones {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--espacio-8) var(--espacio-12);
    }
    .error:empty {
      display: none;
    }
    .error {
      margin: 0;
    }
    @media (max-width: 560px) {
      .mensaje {
        max-width: 100%;
      }
      .sugerido {
        grid-template-columns: 72px minmax(0, 1fr);
      }
      .sugerido .portada {
        width: 72px;
      }
      .sugerido .rotulo,
      .sugerido .porque {
        grid-column: 2;
      }
    }
  `,
})
export class Nia {
  /** El juego del que se habla, o null para hablar del catálogo entero. */
  readonly appid = input<number | null>(null);
  /** La burbuja flotante ya pone el rótulo en su cabecera: ahí sobra repetirlo. */
  readonly muestraTitulo = input(true);
  /** La línea de arriba del chat (la ficha la lleva; la página de Nia, no). */
  readonly muestraIntro = input(true);
  /** En su propia página el chat ocupa todo el panel: la conversación crece y el campo de
   * escribir se queda abajo, como en cualquier chat. */
  readonly llenaAlto = input(false);
  /** El primer mensaje y las fichas de arranque, si quien lo monta quiere otros (la
   * burbuja saluda distinto). */
  readonly saludo = input<string | null>(null);
  readonly fichas = input<readonly string[] | null>(null);

  /** Se eligió un juego desde el buscador del chat: quien lo monta puede reflejarlo. */
  readonly juegoFijado = output<JuegoCatalogo>();
  /** Nia está respondiendo: la página de Nia pone su mascota a pensar. */
  readonly pensando = output<boolean>();

  private readonly api = inject(NexplayApi);
  private readonly usuario = inject(UsuarioStore);
  private readonly perfil = inject(PerfilStore);
  private readonly catalogo = inject(CatalogoStore);
  private readonly panorama = inject(PanoramaStore);
  private readonly historial = inject(HistorialStore);
  protected readonly comparar = inject(CompararStore);
  private readonly router = inject(Router);
  private readonly conversacion = viewChild<ElementRef<HTMLElement>>('conversacion');
  private readonly cuerpo = viewChild<ElementRef<HTMLElement>>('cuerpo');
  private readonly campo = viewChild<ElementRef<HTMLTextAreaElement>>('campo');

  protected readonly maximo = MAXIMO_TEXTO;
  /** El mismo número que aplica api/valoraciones.py (DIAS_DE_RETENCION_NIA): si allá
   * cambia, aquí también, o el aviso miente. */
  protected readonly diasQueSeGuarda = DIAS_DE_RETENCION_NIA;
  protected readonly explicacionSenal = EXPLICACION_SENAL;

  /** El juego del que se habla: el de la entrada o el que se eligió dentro del chat. */
  readonly appidEfectivo = signal<number | null>(null);

  protected readonly texto = signal('');
  protected readonly esperando = signal(false);
  protected readonly error = signal('');
  protected readonly mensajes = signal<MensajeChat[]>([]);
  protected readonly extras = signal<Record<number, Extra>>({});
  /** '' hasta la primera respuesta: entonces se sabe si contestó el modelo o las reglas. */
  protected readonly modo = signal<'' | 'openai' | 'demostracion' | 'reglas'>('');
  /** Mientras espera, el texto cambia: a los cuatro segundos deja de ser "escribiendo". */
  protected readonly progreso = signal('Escribiendo…');
  private relojProgreso?: ReturnType<typeof setTimeout>;

  private readonly juegoEfectivo = computed(() => {
    const appid = this.appidEfectivo();
    return appid === null ? null : (this.catalogo.porAppid().get(appid) ?? null);
  });

  /** El juego elegido dentro del chat, cuando nadie más lo muestra (la burbuja). */
  protected readonly fijadoEnElChat = computed(() =>
    this.appid() === null ? this.juegoEfectivo() : null,
  );

  protected readonly bienvenida = computed(() => {
    const propio = this.saludo();
    if (propio) {
      return propio;
    }
    const juego = this.appid() === null ? null : this.juegoEfectivo();
    if (juego) {
      return saludoDeJuego(juego.nombre, juego.banda_riesgo);
    }
    return this.appid() === null ? SALUDO_CHAT_CATALOGO : '¡Hola! Soy Nia 👋 ¿Qué quieres saber de este juego?';
  });

  private readonly todasLasFichas = computed(() => {
    if (this.appidEfectivo() !== null) {
      return FICHAS_JUEGO;
    }
    return this.fichas() ?? FICHAS_CATALOGO;
  });

  /** Las fichas que todavía no se tocaron en esta conversación: una ya usada solo
   * repetiría la misma respuesta. Cuando no queda ninguna, la fila desaparece. */
  protected readonly pendientes = computed(() => {
    const preguntadas = new Set(
      this.mensajes()
        .filter((mensaje) => mensaje.rol === 'usuario')
        .map((mensaje) => mensaje.contenido.trim()),
    );
    return this.todasLasFichas().filter((ficha) => !preguntadas.has(ficha));
  });

  /** Las sugerencias que calculó el navegador con el perfil. Sin perfil guardado, ninguna. */
  private readonly calculadas = computed(() => {
    const valores = this.perfil.valores();
    if (!valores) {
      return [];
    }
    return sugerenciasPara(this.catalogo.juegos(), criteriosDesde(valores), this.panorama.porAppid()).sugerencias;
  });

  /** Lo que viaja a Nia de esas sugerencias: el appid y su porqué, contado en palabras. */
  private readonly sugerencias = computed(() => sugerenciasParaNia(this.calculadas()));

  /** El porqué de cada sugerencia, para su tarjeta: el texto de la tarjeta de Perfil. */
  protected readonly porQue = computed(() =>
    Object.fromEntries(
      this.calculadas()
        .slice(0, 6)
        .map((s) => [
          s.juego.appid,
          // "Coincide en Acción y Rol; el más específico…": en la tarjeta basta la coincidencia.
          s.razones
            .filter((razon) => razon.cumple)
            .slice(0, 2)
            .map((razon) => razon.texto.split(';')[0].replace(/\.$/, ''))
            .join(' · '),
        ]),
    ),
  );

  constructor() {
    effect(() => this.pensando.emit(this.esperando()));
    // Al cambiar el juego de la entrada, la conversación empieza de cero: el contexto es
    // otro. Si quien lo monta solo refleja el que se eligió dentro del chat, no se borra.
    effect(() => {
      const entrada = this.appid();
      if (entrada === untracked(this.appidEfectivo) && untracked(this.mensajes).length) {
        return;
      }
      untracked(() => {
        this.appidEfectivo.set(entrada);
        this.mensajes.set([]);
        this.extras.set({});
        this.modo.set('');
        this.error.set('');
      });
    });

    effect(() => {
      this.mensajes();
      this.esperando();
      const lista = this.conversacion()?.nativeElement;
      const cuerpo = this.cuerpo()?.nativeElement;
      if (lista) {
        // Tras pintar: si se ajusta antes, el último mensaje queda cortado. En la columna
        // de la ficha lo que se desplaza es el cuerpo entero, no solo la lista.
        requestAnimationFrame(() => {
          lista.scrollTop = lista.scrollHeight;
          if (cuerpo) {
            cuerpo.scrollTop = cuerpo.scrollHeight;
          }
        });
      }
    });
  }

  /** Del appid a la tarjeta, con el catálogo que ya tiene el navegador: del modelo solo
   * viaja el número. Un appid que no esté en el catálogo no se pinta. */
  protected tarjetas(appids: readonly number[]): JuegoCatalogo[] {
    const porAppid = this.catalogo.porAppid();
    return appids.map((appid) => porAppid.get(appid)).filter((juego): juego is JuegoCatalogo => !!juego);
  }

  /** Sin nada en Comparar (o con esos mismos juegos), abre la comparación; si había otros,
   * pregunta antes: «Verlos en Comparar» reemplazaba sin avisar una comparación de 4. */
  protected verEnComparar(appids: readonly number[], posicion: number): void {
    const actuales = this.comparar.appids();
    const nuevos = appids.slice(0, MAXIMO_COMPARAR);
    const mismos = actuales.length === nuevos.length && nuevos.every((appid) => actuales.includes(appid));
    if (!actuales.length || mismos) {
      this.irAComparar(nuevos);
      return;
    }
    this.extras.update((extras) => ({ ...extras, [posicion]: { ...extras[posicion], eligiendoComparar: true } }));
  }

  /** Los que ya estaban y los nuevos, sin repetir y hasta el máximo. */
  protected juntos(appids: readonly number[]): number[] {
    const actuales = this.comparar.appids();
    return [...actuales, ...appids.filter((appid) => !actuales.includes(appid))].slice(0, MAXIMO_COMPARAR);
  }

  /** «Agregar (caben 1)» cuando no entran todos. */
  protected caben(appids: readonly number[]): string {
    const actuales = this.comparar.appids();
    const faltan = appids.filter((appid) => !actuales.includes(appid)).length;
    const lugar = MAXIMO_COMPARAR - actuales.length;
    return faltan > lugar ? ` (caben ${lugar})` : '';
  }

  protected irAComparar(appids: readonly number[]): void {
    this.router.navigate(['/comparar'], { queryParams: { appids: appids.slice(0, MAXIMO_COMPARAR).join(',') } });
  }

  protected tocarFicha(ficha: string): void {
    if (ficha === HABLAR_DE_UN_JUEGO) {
      this.agregar({ rol: 'usuario', contenido: ficha });
      this.abrirBuscador();
      return;
    }
    if (ficha === FILTRAR_EL_CATALOGO) {
      this.agregar({ rol: 'usuario', contenido: ficha });
      this.ofrecerFiltros();
      return;
    }
    this.preguntar(ficha);
  }

  /** Nia pide el juego sin pasar por la API (la ficha «Hablar de un juego», o «Cambiar»). */
  abrirBuscador(): void {
    this.agregar({ rol: 'nia', contenido: PIDE_JUEGO }, { pideJuego: true });
  }

  /** Lo que ofrece el globito de Explorar: cómo pedirle filtros. */
  ofrecerFiltros(): void {
    this.agregar({ rol: 'nia', contenido: COMO_FILTRAR });
    this.campo()?.nativeElement.focus({ preventScroll: true });
  }

  protected cambiarJuego(): void {
    this.appidEfectivo.set(null);
    this.abrirBuscador();
  }

  protected fijarJuego(juego: JuegoCatalogo, posicion: number): void {
    this.appidEfectivo.set(juego.appid);
    this.extras.update((extras) => ({ ...extras, [posicion]: { ...extras[posicion], resuelto: true } }));
    this.juegoFijado.emit(juego);
    this.historial.registrar({ tipo: 'nia', appid: juego.appid, titulo: juego.nombre });
    // La pregunta que quedó pendiente se responde ya con el juego, sin que se repita. Si
    // no había (se tocó «Hablar de un juego»), Nia abre con la invitación de ese juego.
    const anteriores = this.mensajes().slice(0, posicion);
    const pendiente = [...anteriores].reverse().find((mensaje) => mensaje.rol === 'usuario');
    if (!pendiente || pendiente.contenido === HABLAR_DE_UN_JUEGO) {
      this.agregar({ rol: 'nia', contenido: saludoDeJuego(juego.nombre, juego.banda_riesgo) });
      return;
    }
    // Sola, con el juego elegido: con el hilo de antes («los 7 gratis…»), Nia volvía a
    // preguntar «¿de cuál de esos hablas?» en vez de contestar.
    this.consultar([pendiente], pendiente.contenido);
  }

  preguntar(pregunta: string): void {
    const contenido = pregunta.trim().slice(0, MAXIMO_TEXTO);
    if (!contenido || this.esperando()) {
      return;
    }
    this.agregar({ rol: 'usuario', contenido });
    this.texto.set('');
    // [value] solo escribe en el DOM cuando el valor cambia respecto al último que pintó.
    // Si se escribe y se envía antes de que Angular alcance a pintar lo escrito (pegar y
    // dar Enter, teclear rápido), lo último pintado sigue siendo '' y volver a '' "no
    // cambia nada": el contador marcaba 0 y el texto viejo se quedaba en el campo, y la
    // pregunta siguiente llegaba pegada a la anterior. Se vacía a mano.
    const campo = this.campo()?.nativeElement;
    if (campo) {
      campo.value = '';
    }
    this.consultar(this.mensajes(), contenido);
  }

  private agregar(mensaje: MensajeChat, extra?: Extra): void {
    const posicion = this.mensajes().length;
    this.mensajes.update((actuales) => [...actuales, mensaje]);
    if (extra) {
      this.extras.update((extras) => ({ ...extras, [posicion]: extra }));
    }
  }

  /** Manda el hilo (hasta la pregunta) y agrega la respuesta al final de la conversación. */
  private consultar(hilo: MensajeChat[], pregunta: string): void {
    const appid = this.appidEfectivo();
    // Sin juego no hay ficha que recordar: el historial guarda juegos, no conversaciones.
    if (appid !== null) {
      this.historial.registrar({
        tipo: 'nia',
        appid,
        titulo: this.catalogo.porAppid().get(appid)?.nombre ?? `Juego ${appid}`,
      });
    }
    this.error.set('');
    this.esperando.set(true);
    this.progreso.set('Escribiendo…');
    clearTimeout(this.relojProgreso);
    this.relojProgreso = setTimeout(
      () => this.progreso.set(appid === null ? 'Buscando en el catálogo…' : 'Sigue leyendo los datos del juego…'),
      4000,
    );

    const sugerencias = this.sugerencias();
    // Del formulario solo viajan los géneros: con ellos Nia dice cuáles coinciden.
    const generos = this.perfil.valores()?.generos ?? [];
    this.api
      .preguntarANia({
        usuario: this.usuario.id,
        ...(appid !== null ? { appid } : {}),
        mensajes: recortarHistorial(hilo),
        ...(sugerencias.length ? { sugerencias } : {}),
        ...(generos.length ? { generos } : {}),
      })
      .subscribe({
        next: (respuesta) => this.recibir(respuesta, pregunta),
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

  private recibir(respuesta: RespuestaNia, pregunta: string): void {
    this.agregar(
      { rol: 'nia', contenido: sinMarkdown(respuesta.respuesta) },
      {
        id: respuesta.id,
        juegos: respuesta.juegos,
        sugerencias: respuesta.sugerencias ?? [],
        pideJuego: respuesta.pide_juego ?? false,
        pidePerfil: respuesta.pide_perfil ?? false,
        comparar: /compar|\bvs\b|diferencia/i.test(pregunta),
        fueraDeTema: respuesta.fuera_de_tema ?? false,
      },
    );
    this.modo.set(respuesta.modo);
    this.esperando.set(false);
    clearTimeout(this.relojProgreso);
  }
}
