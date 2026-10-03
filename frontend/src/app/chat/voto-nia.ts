import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  ElementRef,
  computed,
  effect,
  inject,
  input,
  signal,
  viewChild,
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
/** Lo que se dice al elegir un motivo: alguien lo va a leer. */
export const GRACIAS_POR_EL_MOTIVO = '¡Gracias! Atenderemos tus requerimientos.';

/** Cuánto se espera antes de mandar un cambio de motivo. Probar los cuatro chips son
 * cuatro peticiones que se pisan entre sí; con la espera, solo viaja el último. */
const ESPERA_MOTIVO_MS = 800;

/** 👍/👎 debajo de una respuesta de Nia. Es privado: nadie más ve el voto, y sirve para
 * comparar cómo contesta antes y después de cambiarle el prompt.
 *
 * El motivo solo se pide con 👎, porque con 👍 no hay nada que explicar, y es opcional:
 * obligarlo haría que la gente dejara de votar. */
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
        [disabled]="guardando()"
        (click)="votar(1)"
      >
        👍
      </button>
      <button
        type="button"
        class="pulgar"
        data-testid="voto-nia-abajo"
        [attr.aria-pressed]="voto() === -1"
        [attr.aria-label]="voto() === -1 ? 'Quitar tu voto en contra' : 'No me sirvió'"
        [disabled]="guardando()"
        (click)="votar(-1)"
      >
        👎
      </button>
      @if (aviso()) {
        <span class="meta aviso" role="status">{{ aviso() }}</span>
      }
    </div>

    @if (voto() === -1) {
      <div class="motivos" #panel data-testid="voto-nia-motivos">
        <span class="meta">¿Qué falló? (opcional)</span>
        @for (motivo of motivos; track motivo) {
          <button
            type="button"
            class="chip"
            data-testid="voto-nia-motivo"
            [attr.aria-pressed]="motivo === this.motivo()"
            [disabled]="guardando()"
            (click)="elegirMotivo(motivo)"
          >
            {{ motivo }}
          </button>
        }
        @if (motivo() === motivoLibre) {
          <div class="libre" data-testid="voto-nia-sugerencia">
            <label class="meta" [for]="idCampo">Cuéntanos qué mejorar</label>
            <textarea
              [id]="idCampo"
              rows="2"
              [maxLength]="maximo"
              [value]="borrador()"
              (input)="borrador.set($any($event.target).value)"
              data-testid="voto-nia-sugerencia-texto"
            ></textarea>
            <div class="pie-libre">
              <span class="meta">Se ve sin tu nombre en el buzón de sugerencias; no pongas datos personales.</span>
              <span class="meta mono">{{ borrador().length }}/{{ maximo }}</span>
              <button
                type="button"
                class="compacto"
                data-testid="voto-nia-sugerencia-enviar"
                [disabled]="guardando() || !borrador().trim() || borrador().trim() === enviada()"
                (click)="enviarSugerencia()"
              >
                Enviar sugerencia
              </button>
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
    .pulgar:hover:not([disabled]) {
      border-color: var(--neon);
    }
    .pulgar[aria-pressed='true'] {
      border-color: var(--neon);
      background: var(--acento-sistema);
    }
    .pulgar[disabled] {
      cursor: progress;
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
    .pie-libre .compacto {
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
  protected readonly motivo = signal<string | null>(null);
  /** Lo que se escribe en «otro motivo», y lo último que la API guardó. */
  protected readonly borrador = signal('');
  protected readonly enviada = signal<string | null>(null);
  protected readonly guardando = signal(false);
  private readonly error = signal('');

  /** Lo último que confirmó la API. Si una petición falla, la interfaz vuelve aquí en vez
   * de quedarse mostrando algo que no se guardó. */
  private guardado: { voto: VotoNiaValor | null; motivo: string | null } = { voto: null, motivo: null };
  private reloj?: ReturnType<typeof setTimeout>;

  private readonly panelMotivos = viewChild<ElementRef<HTMLElement>>('panel');

  protected readonly aviso = computed(
    () => this.error() || (this.motivo() ? GRACIAS_POR_EL_MOTIVO : this.voto() ? 'Gracias.' : ''),
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
    if (this.voto() === valor) {
      this.quitar();
      return;
    }
    this.voto.set(valor);
    if (valor === 1) {
      this.motivo.set(null);
    }
    this.mandar(valor, valor === -1 ? this.motivo() : null, 0);
  }

  /** Probar los cuatro chips son cuatro peticiones que se pisan: la interfaz marca el
   * elegido al instante y solo viaja el último, pasada la espera. */
  protected elegirMotivo(motivo: string): void {
    const elegido = this.motivo() === motivo ? null : motivo;
    this.motivo.set(elegido);
    this.mandar(-1, elegido, ESPERA_MOTIVO_MS);
  }

  private mandar(valor: VotoNiaValor, motivo: string | null, espera: number, sugerencia?: string): void {
    clearTimeout(this.reloj);
    this.error.set('');
    this.reloj = setTimeout(() => this.guardar(valor, motivo, sugerencia), espera);
  }

  /** El texto de «otro motivo» viaja con el 👎 y su motivo; la API le quita los datos personales. */
  protected enviarSugerencia(): void {
    const texto = this.borrador().trim().slice(0, MAXIMO_SUGERENCIA);
    if (texto) {
      this.mandar(-1, MOTIVO_LIBRE, 0, texto);
    }
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
        error: () => this.fallar(),
      });
  }

  private quitar(): void {
    clearTimeout(this.reloj);
    this.voto.set(null);
    this.motivo.set(null);
    this.guardando.set(true);
    this.error.set('');
    this.api.quitarVotoDeNia(this.idRespuesta(), this.usuario.id).subscribe({
      next: () => {
        this.actividad.respuestaVotada(this.idRespuesta(), false);
        this.confirmar(null, null);
      },
      error: () => this.fallar(),
    });
  }

  private confirmar(voto: VotoNiaValor | null, motivo: string | null): void {
    this.guardado = { voto, motivo };
    this.voto.set(voto);
    this.motivo.set(motivo);
    this.guardando.set(false);
  }

  /** Vuelve a lo último que la API confirmó: dejar marcados dos motivos porque uno falló
   * es peor que no haber marcado ninguno. */
  private fallar(): void {
    this.voto.set(this.guardado.voto);
    this.motivo.set(this.guardado.motivo);
    this.guardando.set(false);
    this.error.set('No se pudo guardar tu voto.');
  }
}
