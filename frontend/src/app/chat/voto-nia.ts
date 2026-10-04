import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  Injector,
  afterNextRender,
  computed,
  effect,
  inject,
  input,
  signal,
  viewChild,
  viewChildren,
} from '@angular/core';

import { NexplayApi } from '../api/nexplay-api';
import { VotoNiaValor } from '../api/contrato';
import { ActividadStore } from '../estado/actividad-store';
import { UsuarioStore } from '../estado/usuario-store';

/** Los mismos cinco que acepta la API (MOTIVOS_VOTO_NIA en api/valoraciones.py): un
 * motivo fuera de la lista se guarda como ninguno, así que aquí no se inventan otros. */
export const MOTIVOS_VOTO = [
  'no respondió lo que pregunté',
  'dato incorrecto',
  'muy larga',
  'me recomendó algo',
  'otro motivo',
] as const;
/** El único motivo que abre un texto: qué mejorar, para el buzón de sugerencias de /admin. */
export const MOTIVO_LIBRE = 'otro motivo';
export const MAXIMO_SUGERENCIA = 280;
/** Lo que se dice al elegir un motivo. Agradece sin prometer: nadie se compromete a cambiar
 * algo por un voto. */
export const GRACIAS_POR_EL_MOTIVO = '¡Gracias por avisarnos!';

/** Cuánto se espera antes de mandar un cambio de motivo. «Cambiar» y otro chip, varias veces
 * seguidas, son peticiones que se pisan entre sí; con la espera, solo viaja la última. */
const ESPERA_MOTIVO_MS = 800;

/** Lo invisible al inicio del campo: saltos de línea, espacios, caracteres de ancho cero y el
 * marcador de objeto que dejan algunos teclados. En iPhone el campo abría con uno de esos y el
 * contador decía 1/280 con el campo vacío; no cuenta ni viaja. */
const INVISIBLE_AL_INICIO = /^[\s\u200B-\u200D\u2060\uFFFC]+/;

/** A dónde va el foco cuando el panel cambia y el botón que lo tenía desaparece. */
type DestinoDelFoco = 'cambiar' | 'abajo' | 'marcado' | 'campo';

/** 👍/👎 debajo de una respuesta de Nia. Es privado: nadie más ve el voto, y sirve para
 * comparar cómo contesta antes y después de cambiarle el prompt.
 *
 * El motivo solo se pide con 👎, porque con 👍 no hay nada que explicar, y es opcional:
 * obligarlo haría que la gente dejara de votar. El chat es chico, así que el panel de
 * motivos no se queda abierto: al elegir uno se pliega a «¡Gracias por avisarnos! ·
 * Cambiar», y si la persona sigue escribiendo sin elegir, se cierra. */
@Component({
  selector: 'app-voto-nia',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="voto" data-testid="voto-nia">
      <span class="meta pregunta">¿Te sirvió?</span>
      <button
        type="button"
        class="pulgar"
        data-testid="voto-nia-arriba"
        [attr.aria-pressed]="voto() === 1"
        [attr.aria-label]="voto() === 1 ? 'Quitar tu voto a favor' : 'Sí, me sirvió'"
        [attr.aria-disabled]="guardando() || null"
        (click)="votar(1)"
      >
        👍
      </button>
      <button
        #abajo
        type="button"
        class="pulgar"
        data-testid="voto-nia-abajo"
        [attr.aria-pressed]="voto() === -1"
        [attr.aria-label]="voto() === -1 ? 'Quitar tu voto en contra' : 'No me sirvió'"
        [attr.aria-disabled]="guardando() || null"
        (click)="votar(-1)"
      >
        👎
      </button>
      @if (aviso()) {
        <span class="meta aviso" role="status">{{ aviso() }}</span>
      }
      @if (plegado()) {
        <span class="meta" aria-hidden="true">·</span>
        <button
          #cambiar
          type="button"
          class="boton-texto cambiar"
          data-testid="voto-nia-cambiar"
          [attr.aria-label]="'Cambiar el motivo: ' + motivo()"
          (click)="reabrir()"
        >
          Cambiar
        </button>
      }
    </div>

    @if (voto() === -1 && abierto()) {
      <div class="motivos" #panel role="group" aria-label="¿Qué falló?" data-testid="voto-nia-motivos">
        <span class="meta">¿Qué falló? (opcional)</span>
        @for (motivo of motivos; track motivo) {
          <button
            #chip
            type="button"
            class="chip"
            data-testid="voto-nia-motivo"
            [attr.aria-pressed]="motivo === marcado()"
            [attr.aria-disabled]="guardando() || null"
            (click)="elegirMotivo(motivo)"
          >
            {{ motivo }}
          </button>
        }
        @if (escribiendo()) {
          <div class="libre" data-testid="voto-nia-sugerencia">
            <label class="meta" [for]="idCampo">Cuéntanos qué mejorar</label>
            <textarea
              #campo
              [id]="idCampo"
              rows="2"
              [maxLength]="maximo"
              [value]="borrador()"
              (input)="alEscribir($event)"
              (keydown.escape)="$event.stopPropagation(); cancelarSugerencia()"
              data-testid="voto-nia-sugerencia-texto"
            ></textarea>
            <div class="pie-libre">
              <span class="meta">Se ve sin tu nombre en el buzón de sugerencias; no pongas datos personales.</span>
              <span class="meta mono">{{ borrador().length }}/{{ maximo }}</span>
              <span class="botones-libre" #botonesLibre>
                <button
                  type="button"
                  class="boton-texto"
                  data-testid="voto-nia-sugerencia-cancelar"
                  (click)="cancelarSugerencia()"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  class="compacto"
                  data-testid="voto-nia-sugerencia-enviar"
                  [attr.aria-disabled]="guardando() || null"
                  (click)="enviarSugerencia()"
                >
                  Enviar sugerencia
                </button>
              </span>
            </div>
          </div>
        }
      </div>
    }
  `,
  styles: `
    .voto {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--espacio-8);
      margin-top: var(--espacio-4);
    }
    .pregunta {
      font-size: var(--texto-caption);
    }
    .pulgar {
      min-width: 40px;
      height: 32px;
      padding: 0 var(--espacio-8);
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-pildora);
      background: var(--superficie-lienzo);
      font-size: 16px;
      line-height: 1;
      cursor: pointer;
      transition:
        border-color var(--duracion-rapida) var(--curva),
        background var(--duracion-rapida) var(--curva);
    }
    .pulgar:hover:not([aria-disabled='true']) {
      border-color: var(--neon);
    }
    .pulgar[aria-pressed='true'] {
      border-color: var(--neon);
      background: var(--acento-sistema);
    }
    /* Ocupado con aria-disabled y no con disabled: un botón deshabilitado suelta el foco, y
       quien vota con el teclado se quedaba sin saber dónde estaba. */
    .pulgar[aria-disabled='true'],
    .motivos .chip[aria-disabled='true'],
    .libre .compacto[aria-disabled='true'] {
      cursor: progress;
    }
    .cambiar {
      min-height: 32px;
      font-size: var(--texto-caption);
    }
    .pulgar:focus-visible {
      outline: 2px solid var(--foco);
      outline-offset: 2px;
    }
    .motivos {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--espacio-8);
      margin-top: var(--espacio-8);
    }
    .motivos .chip {
      padding: var(--espacio-4) var(--espacio-8);
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-pildora);
      background: var(--superficie-lienzo);
      font-family: var(--fuente-texto);
    }
    .motivos .chip::after {
      content: none;
    }
    .motivos .chip[aria-pressed='true'] {
      border-color: var(--neon);
      color: var(--texto);
    }
    .aviso {
      font-size: var(--texto-caption);
    }
    .libre {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-4);
      flex-basis: 100%;
    }
    /* El mismo campo que el de los comentarios de la ficha. */
    .libre textarea {
      width: 100%;
      font: inherit;
      letter-spacing: inherit;
      color: var(--texto);
      background: var(--superficie-lienzo);
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-tarjeta);
      padding: var(--espacio-8) var(--espacio-12);
      resize: vertical;
      transition: border-color var(--duracion-rapida) var(--curva);
    }
    .libre textarea:focus-visible {
      outline: 2px solid var(--foco);
      outline-offset: 2px;
      border-color: var(--neon);
    }
    .pie-libre {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--espacio-8);
    }
    .botones-libre {
      display: inline-flex;
      align-items: center;
      gap: var(--espacio-16);
      margin-left: auto;
    }
  `,
})
export class VotoNia {
  /** El id que devolvió la API con la respuesta. */
  readonly idRespuesta = input.required<string>();

  private readonly api = inject(NexplayApi);
  private readonly usuario = inject(UsuarioStore);
  private readonly actividad = inject(ActividadStore);

  protected readonly motivos = MOTIVOS_VOTO;
  protected readonly motivoLibre = MOTIVO_LIBRE;
  protected get idCampo(): string {
    return `sugerencia-${this.idRespuesta()}`;
  }
  protected readonly maximo = MAXIMO_SUGERENCIA;
  protected readonly voto = signal<VotoNiaValor | null>(null);
  /** El motivo registrado (o por registrar, durante la espera). «otro motivo» solo llega
   * aquí al enviar su texto: abrir el campo todavía no registra nada. */
  protected readonly motivo = signal<string | null>(null);
  /** Los chips a la vista. Con un motivo ya elegido, cerrado es la línea «Cambiar». */
  protected readonly abierto = signal(false);
  /** El campo de «otro motivo» abierto. */
  protected readonly escribiendo = signal(false);
  /** Lo que se escribe en «otro motivo», y lo último que la API guardó. */
  protected readonly borrador = signal('');
  protected readonly enviada = signal<string | null>(null);
  protected readonly guardando = signal(false);
  private readonly error = signal('');

  /** El chip que se ve marcado: el del campo abierto, o el registrado. */
  protected readonly marcado = computed(() => (this.escribiendo() ? MOTIVO_LIBRE : this.motivo()));
  /** 👎 con motivo y los chips cerrados: la línea corta. */
  protected readonly plegado = computed(
    () => this.voto() === -1 && !!this.motivo() && !this.abierto() && !this.error(),
  );

  /** Lo último que confirmó la API. Si una petición falla, la interfaz vuelve aquí en vez
   * de quedarse mostrando algo que no se guardó. */
  private guardado: { voto: VotoNiaValor | null; motivo: string | null } = { voto: null, motivo: null };
  private reloj?: ReturnType<typeof setTimeout>;

  private readonly panelMotivos = viewChild<ElementRef<HTMLElement>>('panel');
  private readonly botonCambiar = viewChild<ElementRef<HTMLButtonElement>>('cambiar');
  private readonly botonAbajo = viewChild<ElementRef<HTMLButtonElement>>('abajo');
  private readonly chips = viewChildren<ElementRef<HTMLButtonElement>>('chip');
  private readonly campo = viewChild<ElementRef<HTMLTextAreaElement>>('campo');
  private readonly botonesLibre = viewChild<ElementRef<HTMLElement>>('botonesLibre');
  private readonly anfitrion = inject<ElementRef<HTMLElement>>(ElementRef);
  private readonly inyector = inject(Injector);

  protected readonly aviso = computed(
    () =>
      this.error() || (this.voto() === -1 && this.motivo() ? GRACIAS_POR_EL_MOTIVO : this.voto() ? 'Gracias.' : ''),
  );

  constructor() {
    // Al abrirse, los chips quedaban bajo el borde del hilo y nadie los veía.
    effect(() => {
      const panel = this.panelMotivos()?.nativeElement;
      if (panel) {
        // Tras pintar, y con ?. porque el DOM de las pruebas no implementa scrollIntoView.
        requestAnimationFrame(() => panel.scrollIntoView?.({ block: 'nearest', behavior: 'smooth' }));
      }
    });
    inject(DestroyRef).onDestroy(() => clearTimeout(this.reloj));
  }

  /** El mismo pulgar dos veces quita el voto: es el gesto que ya hace el pulgar de los
   * comentarios, y sin él no habría forma de arrepentirse. */
  protected votar(valor: VotoNiaValor): void {
    if (this.guardando()) {
      return;
    }
    if (this.voto() === valor) {
      this.quitar();
      return;
    }
    this.voto.set(valor);
    if (valor === 1) {
      this.motivo.set(null);
    }
    this.abierto.set(valor === -1);
    this.escribiendo.set(false);
    this.mandar(valor, valor === -1 ? this.motivo() : null, 0);
  }

  /** Un chip registra su motivo y pliega el panel; el que ya estaba marcado se quita, que es
   * lo que promete aria-pressed. «otro motivo» solo abre el campo: se registra al enviarlo. */
  protected elegirMotivo(motivo: string): void {
    if (this.guardando()) {
      return;
    }
    if (motivo === MOTIVO_LIBRE) {
      if (this.escribiendo()) {
        this.cancelarSugerencia();
      } else {
        this.escribiendo.set(true);
        this.enfocar('campo');
        this.mostrarElCampo();
      }
      return;
    }
    const elegido = this.marcado() === motivo ? null : motivo;
    this.escribiendo.set(false);
    this.motivo.set(elegido);
    this.abierto.set(false);
    this.enfocar(elegido ? 'cambiar' : 'abajo');
    this.mandar(-1, elegido, ESPERA_MOTIVO_MS);
  }

  /** «Cambiar»: los chips otra vez, con el motivo actual marcado. Si fue «otro motivo», su
   * campo muestra lo que la API guardó, ya sin datos personales. */
  protected reabrir(): void {
    if (this.motivo() === MOTIVO_LIBRE) {
      this.borrador.set(this.enviada() ?? this.borrador());
    }
    this.escribiendo.set(this.motivo() === MOTIVO_LIBRE);
    this.abierto.set(true);
    this.enfocar('marcado');
    if (this.escribiendo()) {
      this.mostrarElCampo();
    }
  }

  /** Lo que se escribe en «otro motivo», sin lo invisible del inicio: también se quita del
   * campo, para que lo que se ve y el contador digan lo mismo. */
  protected alEscribir(evento: Event): void {
    const campo = evento.target as HTMLTextAreaElement;
    const limpio = campo.value.replace(INVISIBLE_AL_INICIO, '');
    if (limpio !== campo.value) {
      campo.value = limpio;
    }
    this.borrador.set(limpio);
  }

  /** Cancelar, Escape o enviar vacío: se cierra sin registrar nada y queda lo de antes. */
  protected cancelarSugerencia(): void {
    this.escribiendo.set(false);
    this.borrador.set(this.enviada() ?? '');
    this.abierto.set(false);
    this.enfocar(this.motivo() ? 'cambiar' : 'abajo');
  }

  /** La persona siguió escribiendo en el chat sin elegir: el motivo es opcional, así que el
   * panel se cierra. Lo ya escrito en «otro motivo» no se tira. */
  plegar(): void {
    if (!this.abierto() || (this.escribiendo() && this.borrador().trim())) {
      return;
    }
    this.escribiendo.set(false);
    this.abierto.set(false);
  }

  private mandar(valor: VotoNiaValor, motivo: string | null, espera: number, sugerencia?: string): void {
    clearTimeout(this.reloj);
    this.error.set('');
    this.reloj = setTimeout(() => this.guardar(valor, motivo, sugerencia), espera);
  }

  /** El texto de «otro motivo» viaja con el 👎 y su motivo; la API le quita los datos personales. */
  protected enviarSugerencia(): void {
    if (this.guardando()) {
      return;
    }
    const texto = this.borrador().trim().slice(0, MAXIMO_SUGERENCIA);
    if (!texto) {
      this.cancelarSugerencia();
      return;
    }
    this.escribiendo.set(false);
    this.motivo.set(MOTIVO_LIBRE);
    this.abierto.set(false);
    this.enfocar('cambiar');
    if (texto !== this.enviada() || this.guardado.motivo !== MOTIVO_LIBRE) {
      this.mandar(-1, MOTIVO_LIBRE, 0, texto);
    }
  }

  /** Mueve el foco cuando el botón que lo tenía desaparece al plegar o abrir el panel. Solo si
   * el foco estaba aquí (o se perdió con el botón): si la persona ya está escribiendo en el
   * chat, no se lo quita. */
  private enfocar(destino: DestinoDelFoco): void {
    afterNextRender(
      () => {
        const activo = document.activeElement;
        if (activo && activo !== document.body && !this.anfitrion.nativeElement.contains(activo)) {
          return;
        }
        const chips = this.chips();
        const elemento =
          destino === 'cambiar'
            ? this.botonCambiar()
            : destino === 'abajo'
              ? this.botonAbajo()
              : destino === 'campo'
                ? this.campo()
                : (chips[MOTIVOS_VOTO.indexOf(this.marcado() as (typeof MOTIVOS_VOTO)[number])] ?? chips[0]);
        elemento?.nativeElement.focus();
      },
      { injector: this.inyector },
    );
  }

  /** Al abrirse «otro motivo», el panel crece y sus botones quedaban bajo el borde del hilo: en
   * el teléfono, «Cancelar» y «Enviar sugerencia» no se veían. El foco solo trae el campo; esto
   * trae también los botones, después de enfocar. Con ?. porque el DOM de las pruebas no lo tiene. */
  private mostrarElCampo(): void {
    afterNextRender(() => this.botonesLibre()?.nativeElement.scrollIntoView?.({ block: 'nearest' }), {
      injector: this.inyector,
    });
  }

  private guardar(valor: VotoNiaValor, motivo: string | null, sugerencia?: string): void {
    this.guardando.set(true);
    this.api
      .votarRespuestaDeNia(this.idRespuesta(), {
        usuario: this.usuario.id,
        voto: valor,
        ...(motivo ? { motivo } : {}),
        ...(sugerencia ? { sugerencia } : {}),
      })
      .subscribe({
        next: (respuesta) => {
          this.actividad.respuestaVotada(this.idRespuesta(), true);
          this.enviada.set(respuesta.sugerencia ?? null);
          this.confirmar(respuesta.voto, respuesta.motivo);
        },
        error: () => this.fallar(!!sugerencia),
      });
  }

  private quitar(): void {
    clearTimeout(this.reloj);
    this.voto.set(null);
    this.motivo.set(null);
    this.abierto.set(false);
    this.escribiendo.set(false);
    this.guardando.set(true);
    this.error.set('');
    this.api.quitarVotoDeNia(this.idRespuesta(), this.usuario.id).subscribe({
      next: () => {
        this.actividad.respuestaVotada(this.idRespuesta(), false);
        this.confirmar(null, null);
      },
      error: () => this.fallar(false),
    });
  }

  private confirmar(voto: VotoNiaValor | null, motivo: string | null): void {
    this.guardado = { voto, motivo };
    this.voto.set(voto);
    this.motivo.set(motivo);
    this.guardando.set(false);
  }

  /** Vuelve a lo último que la API confirmó: dejar marcados dos motivos porque uno falló
   * es peor que no haber marcado ninguno. Con 👎, los chips se abren para reintentar, y una
   * sugerencia que no se guardó sigue en su campo. */
  private fallar(conSugerencia: boolean): void {
    const abajo = this.guardado.voto === -1;
    this.voto.set(this.guardado.voto);
    this.motivo.set(this.guardado.motivo);
    this.abierto.set(abajo);
    this.escribiendo.set(abajo && conSugerencia);
    this.guardando.set(false);
    this.error.set('No se pudo guardar tu voto.');
    if (abajo) {
      this.enfocar(conSugerencia ? 'campo' : 'marcado');
      if (conSugerencia) {
        this.mostrarElCampo();
      }
    }
  }
}
