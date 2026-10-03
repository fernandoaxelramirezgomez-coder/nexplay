import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  InjectionToken,
  computed,
  effect,
  inject,
  signal,
  viewChild,
} from '@angular/core';
import { NgTemplateOutlet } from '@angular/common';
import { Subscription, defer, retry, throwError, timeout, timer } from 'rxjs';

import { BuzonSugerencias, EstadoSistema } from '../api/contrato';
import { NexplayApi } from '../api/nexplay-api';
import { restablecerDatos } from '../dominio/datos-de-sesion';
import { ActividadStore } from '../estado/actividad-store';
import { HistorialStore } from '../estado/historial-store';
import { PerfilStore } from '../estado/perfil-store';

/** Render gratis duerme la API: la primera respuesta puede tardar casi un minuto. Antes de
 * los 3 s se dice «Conectando…»; después, «Despertando…», con reintentos cada 5 s y 20 s
 * por intento, hasta 90 s. Solo entonces «Sin conexión». */
export const ESPERA_DESPERTANDO_MS = 3_000;
export const TIEMPO_POR_INTENTO_MS = 20_000;
export const PAUSA_ENTRE_INTENTOS_MS = 5_000;
export const LIMITE_PARA_DESPERTAR_MS = 90_000;

/** Recargar la página tras restablecer vacía también lo que vive en memoria (la conversación
 * de Nia, los stores). En las pruebas se cambia por un espía. */
export const RECARGAR_PAGINA = new InjectionToken<() => void>('recargar la página', {
  providedIn: 'root',
  factory: () => () => location.reload(),
});

export type Conexion = 'conectando' | 'despertando' | 'conectado' | 'sin-conexion';

const FECHA = new Intl.DateTimeFormat('es-MX', { day: 'numeric', month: 'short' });

/** Administración: el estado del sistema y lo que hizo esta persona en este navegador, de un
 * vistazo. No está en el menú de las cinco vistas (la presentación se arma sobre ellas): se
 * llega con el escudo del pie del menú. Sin burbuja de Nia. /admin no tiene contraseña, así
 * que no muestra nada que no pueda ver cualquiera. */
@Component({
  selector: 'app-admin',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [NgTemplateOutlet],
  template: `
    <div class="admin" data-testid="admin">
      <header class="cabecera">
        <p class="sobrelinea mono">Administración</p>
        <h1>Estado del sistema</h1>
        <p class="entrada">
          Cómo está NexPlay ahora y qué hiciste en este navegador, de un vistazo. Lo de tu sesión se lee de este
          navegador y no sale de aquí.
        </p>
      </header>

      <section class="bloque" aria-labelledby="titulo-sistema">
        <h2 id="titulo-sistema" class="rotulo-seccion">Sistema</h2>
        <div class="rejilla" aria-live="polite">
          <article class="tarjeta" [attr.data-estado]="conexion() === 'sin-conexion' ? 'no-disponible' : 'ok'" data-testid="admin-backend">
            <p class="nombre">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <rect x="3" y="4" width="18" height="7" rx="2" /><rect x="3" y="13" width="18" height="7" rx="2" />
                <path d="M7 7.5h.01M7 16.5h.01" />
              </svg>
              Backend
              <span class="meta">API en Render</span>
            </p>
            <p class="estado" data-testid="admin-backend-estado">
              @switch (conexion()) {
                @case ('conectado') {
                  <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="m8 12 3 3 5-6" /></svg>
                  Conectado
                }
                @case ('sin-conexion') {
                  <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="m9 9 6 6M15 9l-6 6" /></svg>
                  Sin conexión
                }
                @case ('despertando') {
                  <svg class="girando" viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>
                  Despertando…
                }
                @default {
                  <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>
                  Conectando…
                }
              }
            </p>
            <p class="detalle meta">
              @switch (conexion()) {
                @case ('conectado') {
                  Respondió en {{ segundos() }} s.
                }
                @case ('despertando') {
                  Render gratis duerme la API cuando nadie la usa; despertar puede tardar hasta un minuto.
                }
                @case ('sin-conexion') {
                  No respondió en {{ limiteEnSegundos }} s.
                }
              }
            </p>
            @if (conexion() === 'sin-conexion') {
              <button type="button" class="compacto toque-amplio" data-testid="admin-reintentar" (click)="conectar()">
                Reintentar
              </button>
            }
          </article>

          <article class="tarjeta" [attr.data-estado]="estado() ? 'ok' : 'no-disponible'" data-testid="admin-openai">
            <p class="nombre">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 3v4M12 17v4M3 12h4M17 12h4M6.3 6.3l2.8 2.8M14.9 14.9l2.8 2.8M17.7 6.3l-2.8 2.8M9.1 14.9l-2.8 2.8" />
              </svg>
              OpenAI
              <span class="meta">Nia</span>
            </p>
            @if (estado(); as e) {
              <p class="estado">{{ e.nia_con_openai ? 'Configurado' : 'Modo demostración (reglas)' }}</p>
              <p class="detalle meta">
                {{ e.nia_con_openai ? 'Nia responde con IA y, lo que debe salir siempre igual, por reglas.' : 'Sin clave, Nia responde por reglas sobre los datos.' }}
              </p>
            } @else {
              <ng-container [ngTemplateOutlet]="noDisponible" />
            }
          </article>

          <article class="tarjeta" [attr.data-estado]="estado() ? 'ok' : 'no-disponible'" data-testid="admin-datos">
            <p class="nombre">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <ellipse cx="12" cy="5" rx="8" ry="3" /><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5" />
                <path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" />
              </svg>
              Datos
              <span class="meta">Release activo</span>
            </p>
            @if (estado(); as e) {
              <p class="estado mono">{{ e.datos_release ?? '—' }}</p>
              <p class="detalle meta">{{ e.juegos_catalogo }} juegos en el catálogo.</p>
            } @else {
              <ng-container [ngTemplateOutlet]="noDisponible" />
            }
          </article>

          <article class="tarjeta" [attr.data-estado]="estado() ? 'ok' : 'no-disponible'" data-testid="admin-modelo">
            <p class="nombre">
              <svg viewBox="0 0 24 24" aria-hidden="true">
                <rect x="6" y="6" width="12" height="12" rx="2" />
                <path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4" />
              </svg>
              Modelo activo
              <span class="meta">Riesgo y Nia</span>
            </p>
            @if (estado(); as e) {
              <p class="estado mono">{{ e.modelo_version }}</p>
              <p class="detalle meta">
                Entrenado con {{ e.modelo_juegos_entrenamiento ?? '—' }} juegos ({{ e.modelo_datos ?? '—' }}). Nia:
                <span class="mono">{{ e.modelo_nia ?? 'sin modelo de lenguaje' }}</span>.
              </p>
            } @else {
              <ng-container [ngTemplateOutlet]="noDisponible" />
            }
          </article>
        </div>
      </section>

      <section class="bloque" aria-labelledby="titulo-sesion">
        <h2 id="titulo-sesion" class="rotulo-seccion">Tu sesión en este navegador</h2>
        <div class="rejilla">
          @for (cifra of sesion(); track cifra.id) {
            <article class="tarjeta" [attr.data-estado]="cifra.valor === '—' ? 'no-disponible' : 'ok'" [attr.data-testid]="'admin-' + cifra.id">
              <p class="nombre">{{ cifra.nombre }}</p>
              <p class="estado cifra mono">{{ cifra.valor }}</p>
              @if (cifra.detalle) {
                <p class="detalle meta">{{ cifra.detalle }}</p>
              }
            </article>
          }
        </div>
      </section>

      <section class="bloque" aria-labelledby="titulo-buzon">
        <h2 id="titulo-buzon" class="rotulo-seccion">Buzón de sugerencias</h2>
        <p class="meta explica">Lo que la gente le dice a Nia con 👍 y 👎, de todos los visitantes y sin nombres.</p>
        @if (buzon(); as b) {
          <div class="buzon" data-testid="admin-buzon">
            <article class="tarjeta" data-estado="ok">
              <p class="nombre">Votos a Nia</p>
              <p class="estado cifra mono" data-testid="admin-buzon-votos">👍 {{ b.votos_a_favor }} · 👎 {{ b.votos_en_contra }}</p>
              <ul class="motivos" data-testid="admin-buzon-motivos">
                @for (m of b.por_motivo; track m.motivo) {
                  <li><span>{{ m.motivo }}</span><span class="mono">{{ m.cuantos }}</span></li>
                }
              </ul>
            </article>
            <article class="tarjeta ancha" data-estado="ok">
              <p class="nombre">Qué mejorar <span class="meta">«otro motivo», lo más reciente</span></p>
              @if (b.sugerencias.length) {
                <ul class="sugerencias" data-testid="admin-buzon-sugerencias">
                  @for (s of b.sugerencias; track $index) {
                    <li>
                      <p>{{ s.texto }}</p>
                      <p class="meta mono">{{ fecha(s.cuando) }}</p>
                    </li>
                  }
                </ul>
              } @else {
                <p class="estado">—</p>
                <p class="detalle meta">Todavía nadie escribió una sugerencia.</p>
              }
            </article>
          </div>
        } @else {
          <article class="tarjeta" data-estado="no-disponible" data-testid="admin-buzon-no-disponible">
            <ng-container [ngTemplateOutlet]="noDisponible" />
          </article>
        }
      </section>

      <section class="bloque" aria-labelledby="titulo-restablecer">
        <h2 id="titulo-restablecer" class="rotulo-seccion">Restablecer</h2>
        @if (!confirmando()) {
          <button type="button" class="boton-cta toque-amplio" data-testid="admin-restablecer" (click)="pedirConfirmacion()">
            Restablecer datos de esta sesión
          </button>
        } @else {
          <div class="confirmacion" role="alertdialog" aria-labelledby="titulo-confirmar" aria-describedby="texto-confirmar" data-testid="admin-confirmar">
            <p id="titulo-confirmar" class="estado">¿Borrar los datos de esta sesión?</p>
            <p id="texto-confirmar" class="lectura">
              Se borran de este navegador tu perfil, tu historial, tu lista de Comparar y lo que cuenta esta vista. No se
              puede deshacer. Los comentarios públicos y los votos que ya enviaste no se borran: siguen en NexPlay, y desde
              este navegador puedes seguir editándolos. Tus preferencias de tema y menú se quedan.
            </p>
            <div class="acciones">
              <button #cancelar type="button" class="boton-fantasma toque-amplio" data-testid="admin-cancelar" (click)="confirmando.set(false)">
                Cancelar
              </button>
              <button type="button" class="boton-cta toque-amplio" data-testid="admin-borrar" (click)="restablecer()">
                Sí, borrar mis datos
              </button>
            </div>
          </div>
        }
      </section>
    </div>

    <ng-template #noDisponible>
      <p class="estado">
        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M8 12h8" /></svg>
        No disponible
      </p>
      <p class="detalle meta">—</p>
    </ng-template>
  `,
  styles: `
    .admin {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-24);
    }
    .cabecera {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
    }
    .entrada {
      max-width: var(--medida-lectura);
      color: var(--texto-2);
    }
    .bloque {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
    }
    .rejilla {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: var(--espacio-16);
    }
    .buzon {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 2fr);
      gap: var(--espacio-16);
    }
    /* El glow va en el borde de la tarjeta, nunca en el texto. */
    .tarjeta {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-8);
      padding: var(--espacio-16);
      border: 1px solid color-mix(in srgb, var(--neon) 45%, var(--linea));
      border-radius: var(--radio-tarjeta);
      background: var(--superficie-tarjeta);
      box-shadow: var(--resplandor);
    }
    .tarjeta[data-estado='no-disponible'] {
      border-color: var(--linea);
      box-shadow: none;
    }
    .nombre {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--espacio-8);
      font-family: var(--fuente-display);
      font-size: var(--texto-subheading);
      font-weight: 700;
    }
    .nombre .meta {
      font-family: var(--fuente-texto);
      font-weight: 400;
    }
    .estado {
      display: flex;
      align-items: center;
      gap: var(--espacio-8);
      font-size: var(--texto-body);
      font-weight: 600;
      color: var(--neon);
    }
    .tarjeta[data-estado='no-disponible'] .estado {
      color: var(--texto-2);
    }
    .cifra {
      font-size: var(--texto-heading-sm);
      color: var(--texto);
    }
    .detalle {
      margin: 0;
    }
    svg {
      flex: none;
      width: 22px;
      height: 22px;
      fill: none;
      stroke: var(--neon);
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
      /* El glow de los íconos, del color de la vista. */
      filter: drop-shadow(0 0 4px rgb(var(--accion-canal) / 0.55));
    }
    .tarjeta[data-estado='no-disponible'] svg {
      stroke: var(--borde-control);
      filter: none;
    }
    .girando {
      animation: girar 2.4s linear infinite;
    }
    @keyframes girar {
      to {
        transform: rotate(360deg);
      }
    }
    @media (prefers-reduced-motion: reduce) {
      .girando {
        animation: none;
      }
    }
    .explica {
      margin-top: calc(-1 * var(--espacio-4));
    }
    .motivos,
    .sugerencias {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-8);
      margin: 0;
      padding: 0;
      list-style: none;
    }
    .motivos li {
      display: flex;
      justify-content: space-between;
      gap: var(--espacio-8);
      font-size: var(--texto-body-sm);
    }
    .sugerencias li {
      padding-bottom: var(--espacio-8);
      border-bottom: 1px solid var(--linea);
      overflow-wrap: anywhere;
    }
    .confirmacion {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
      padding: var(--espacio-16);
      border: 1px solid var(--neon);
      border-radius: var(--radio-tarjeta);
      background: var(--superficie-tarjeta);
      box-shadow: var(--resplandor);
    }
    .acciones {
      display: flex;
      flex-wrap: wrap;
      gap: var(--espacio-12);
    }
    .boton-cta,
    .boton-fantasma,
    .compacto {
      min-height: 44px;
      align-self: flex-start;
    }
    .boton-cta {
      box-shadow: var(--resplandor);
    }
    @media (max-width: 1100px) {
      .rejilla {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
    }
    @media (max-width: 640px) {
      .rejilla,
      .buzon {
        grid-template-columns: minmax(0, 1fr);
      }
    }
  `,
})
export class Admin {
  private readonly api = inject(NexplayApi);
  private readonly historial = inject(HistorialStore);
  private readonly perfil = inject(PerfilStore);
  private readonly actividad = inject(ActividadStore);
  private readonly recargar = inject(RECARGAR_PAGINA);

  protected readonly conexion = signal<Conexion>('conectando');
  protected readonly estado = signal<EstadoSistema | null>(null);
  protected readonly buzon = signal<BuzonSugerencias | null>(null);
  protected readonly confirmando = signal(false);
  private readonly milisegundos = signal(0);
  protected readonly segundos = computed(() => (this.milisegundos() / 1000).toFixed(1));
  protected readonly limiteEnSegundos = LIMITE_PARA_DESPERTAR_MS / 1000;

  private readonly botonCancelar = viewChild<ElementRef<HTMLButtonElement>>('cancelar');
  private suscripcion?: Subscription;
  private aviso?: ReturnType<typeof setTimeout>;

  /** Lo de la fila 2. «—» cuando no hay dato: 0 sería afirmar algo que no se midió. */
  protected readonly sesion = computed(() => {
    const entradas = this.historial.entradas();
    const actividad = this.actividad.actividad();
    const valores = this.perfil.valores();
    const cifra = (n: number | undefined) => (n ? String(n) : '—');
    const vistos = entradas.filter((e) => e.tipo === 'visto').length;
    const comparados = entradas.filter((e) => e.tipo === 'comparado').length;
    const valorados = actividad?.juegosValorados.length ?? 0;
    const votadas = actividad?.respuestasVotadas.length ?? 0;
    const comentarios = actividad?.comentarios ?? 0;
    return [
      { id: 'conversaciones', nombre: 'Conversaciones con Nia', valor: cifra(actividad?.conversacionesNia), detalle: '' },
      { id: 'mensajes', nombre: 'Mensajes a Nia', valor: cifra(actividad?.mensajesNia), detalle: '' },
      { id: 'juegos', nombre: 'Juegos consultados', valor: cifra(vistos), detalle: vistos ? 'Fichas distintas que abriste.' : '' },
      { id: 'comparaciones', nombre: 'Comparaciones', valor: cifra(comparados), detalle: '' },
      {
        id: 'perfil',
        nombre: 'Perfil',
        valor: this.perfil.hayPerfil() ? 'Completado' : 'Pendiente',
        detalle: this.perfil.hayPerfil()
          ? `${valores?.generos.length ?? 0} ${(valores?.generos.length ?? 0) === 1 ? 'género elegido' : 'géneros elegidos'}.`
          : 'Todavía no lo llenas.',
      },
      {
        id: 'valoraciones',
        nombre: 'Valoraciones y comentarios',
        valor: valorados + votadas + comentarios ? String(valorados + votadas + comentarios) : '—',
        detalle:
          valorados + votadas + comentarios
            ? `${valorados} juegos con estrellas · ${votadas} votos a Nia · ${comentarios} comentarios.`
            : '',
      },
    ];
  });

  constructor() {
    // Con la confirmación abierta, el foco va a «Cancelar»: lo seguro queda a un Enter.
    effect(() => this.botonCancelar()?.nativeElement.focus());
    inject(DestroyRef).onDestroy(() => {
      this.suscripcion?.unsubscribe();
      clearTimeout(this.aviso);
    });
    this.conectar();
  }

  /** Pide /estado; si tarda, avisa que Render está despertando y reintenta hasta el límite. */
  protected conectar(): void {
    this.suscripcion?.unsubscribe();
    clearTimeout(this.aviso);
    this.conexion.set('conectando');
    const inicio = Date.now();
    this.aviso = setTimeout(() => {
      if (this.conexion() === 'conectando') {
        this.conexion.set('despertando');
      }
    }, ESPERA_DESPERTANDO_MS);
    this.suscripcion = defer(() => this.api.estado())
      .pipe(
        timeout(TIEMPO_POR_INTENTO_MS),
        retry({
          delay: (error) => {
            this.conexion.set('despertando');
            return Date.now() - inicio + PAUSA_ENTRE_INTENTOS_MS < LIMITE_PARA_DESPERTAR_MS
              ? timer(PAUSA_ENTRE_INTENTOS_MS)
              : throwError(() => error);
          },
        }),
      )
      .subscribe({
        next: (estado) => {
          clearTimeout(this.aviso);
          this.milisegundos.set(Date.now() - inicio);
          this.estado.set(estado);
          this.conexion.set('conectado');
          this.api.buzonDeSugerencias().subscribe({
            next: (buzon) => this.buzon.set(buzon),
            error: () => this.buzon.set(null),
          });
        },
        error: () => {
          clearTimeout(this.aviso);
          this.estado.set(null);
          this.conexion.set('sin-conexion');
        },
      });
  }

  protected pedirConfirmacion(): void {
    this.confirmando.set(true);
  }

  protected restablecer(): void {
    restablecerDatos();
    this.recargar();
  }

  protected fecha(iso: string): string {
    const momento = new Date(iso);
    return Number.isNaN(momento.getTime()) ? '' : FECHA.format(momento);
  }
}
