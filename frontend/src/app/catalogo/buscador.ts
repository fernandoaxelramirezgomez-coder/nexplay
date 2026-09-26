import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  afterNextRender,
  computed,
  inject,
  input,
  output,
  signal,
  viewChild,
} from '@angular/core';
import { Router } from '@angular/router';

import { JuegoCatalogo } from '../api/contrato';
import { PildoraBanda } from '../compartido/pildora-banda';
import { filtrarJuegos } from '../dominio/filtros';
import { textoMetacritic, textoPrecio } from '../dominio/formato';

const MAXIMO_SUGERENCIAS = 6;

/** Si la coincidencia encontrada arranca palabra. */
function empiezaPalabra({ juego, desde }: { juego: JuegoCatalogo; desde: number }): boolean {
  return desde === 0 || (desde > 0 && !/[\p{L}\p{N}]/u.test(juego.nombre[desde - 1]));
}

/** Dónde empieza lo buscado dentro del nombre: primero al principio de una palabra y, si
 * ahí no está, en cualquier sitio. -1 si no aparece. */
function posicionDeLaCoincidencia(nombre: string, buscado: string): number {
  if (!buscado) {
    return -1;
  }
  const texto = nombre.toLowerCase();
  const aguja = buscado.toLowerCase();
  for (let i = texto.indexOf(aguja); i >= 0; i = texto.indexOf(aguja, i + 1)) {
    if (i === 0 || !/[\p{L}\p{N}]/u.test(texto[i - 1])) {
      return i;
    }
  }
  return texto.indexOf(aguja);
}

/** El buscador del inicio: sugiere juegos concretos para saltar a su ficha, con la banda,
 * el precio y la nota a la vista. En Explorar va sin panel ([sugerir]="false"): allá la
 * cuadrícula ya filtra al teclear y el desplegable sería la misma búsqueda dos veces. */
@Component({
  selector: 'app-buscador',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [PildoraBanda],
  template: `
    <div class="buscador">
      @if (etiqueta()) {
        <label for="buscador-catalogo">{{ etiqueta() }}</label>
      } @else {
        <label class="solo-lector" for="buscador-catalogo">Busca un juego del catálogo</label>
      }
      <div class="campo">
        <svg aria-hidden="true" viewBox="0 0 24 24">
          <circle cx="11" cy="11" r="6" />
          <path d="m16 16 4 4" />
        </svg>
        <input
          id="buscador-catalogo"
          type="search"
          role="combobox"
          autocomplete="off"
          aria-autocomplete="list"
          aria-controls="sugerencias-catalogo"
          [attr.aria-expanded]="abierto()"
          [attr.aria-activedescendant]="activo() >= 0 ? 'sugerencia-' + activo() : null"
          #campo
          placeholder="Hollow Knight, Cyberpunk, Portal…"
          data-testid="filtro-texto"
          [value]="texto()"
          (input)="alTeclear($any($event.target).value)"
          (keydown)="alTecla($event)"
          (focus)="abierto.set(true)"
          (blur)="cerrarConRetraso()"
        />
      </div>

      @if (sugerir() && abierto() && texto().trim()) {
        <div class="panel" data-testid="buscador-panel">
          @if (sugerencias().length) {
            <ul class="sugerencias" id="sugerencias-catalogo" role="listbox" data-testid="sugerencias">
              @for (juego of sugerencias(); track juego.appid; let i = $index) {
                <li
                  class="sugerencia"
                  role="option"
                  [id]="'sugerencia-' + i"
                  [class.activa]="i === activo()"
                  [attr.aria-selected]="i === activo()"
                  (mousedown)="abrir(juego)"
                  (mouseenter)="activo.set(i)"
                >
                  <img [src]="juego.portada_url" alt="" width="92" height="43" loading="lazy" />
                  <span class="datos">
                    <!-- En una sola línea a propósito: un salto entre los trozos se
                         convierte en un espacio y parte el nombre ("Grand The ft Auto"). -->
                    <span class="nombre">@for (trozo of partes(juego.nombre); track $index) {@if (trozo.coincide) {<strong>{{ trozo.texto }}</strong>} @else {<ng-container>{{ trozo.texto }}</ng-container>}}</span>
                    <span class="linea">
                      <app-pildora-banda [banda]="juego.banda_riesgo" [compacta]="true" />
                      <span class="meta mono">{{ precio(juego) }} · {{ critica(juego.metacritic) }}</span>
                    </span>
                  </span>
                </li>
              }
            </ul>
            <!-- Solo cuando el panel sirve para navegar: eligiendo un juego para comparar
                 o para el chat, mandar a Explorar es sacar a la persona de lo que hacía. -->
            @if (modo() === 'ficha') {
              <button type="button" class="pie" data-testid="buscador-ver-todos" (mousedown)="verTodos()">
                {{ coincidencias().length === 1 ? 'Ver el resultado en Explorar →' : 'Ver los ' + coincidencias().length + ' resultados en Explorar →' }}
              </button>
            }
          } @else {
            <p class="vacio meta" role="status" data-testid="buscador-vacio">
              «{{ texto().trim() }}» no está en el catálogo de {{ juegos().length }} juegos de Steam.
            </p>
          }
        </div>
      }
    </div>
  `,
  styles: `
    :host {
      display: block;
      width: 100%;
      max-width: 680px;
    }
    .buscador {
      position: relative;
    }
    label {
      display: block;
      margin: 0 0 var(--espacio-8);
      color: var(--texto);
      font-size: var(--texto-body-sm);
      font-weight: var(--peso-clave);
    }
    .campo {
      position: relative;
    }
    .campo svg {
      position: absolute;
      z-index: 1;
      top: 50%;
      left: var(--espacio-24);
      width: 19px;
      height: 19px;
      fill: none;
      stroke: var(--neon);
      stroke-linecap: round;
      stroke-width: 1.8;
      transform: translateY(-50%);
      pointer-events: none;
    }
    input {
      width: 100%;
      font: inherit;
      font-size: var(--texto-body);
      letter-spacing: inherit;
      color: var(--texto);
      background: var(--superficie-tarjeta);
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-boton);
      padding: 16px var(--espacio-24) 16px 50px;
      transition: border-color var(--duracion-rapida) var(--curva);
    }
    input::placeholder {
      color: var(--texto-meta);
      font-size: var(--texto-body-sm);
    }
    input:hover,
    input:focus {
      border-color: var(--neon);
    }
    /* El panel flota sobre el contenido y es más ancho que el campo: así no empuja la
       fila de chips ni se queda estrecho cuando el nombre es largo. */
    .panel {
      position: absolute;
      z-index: 20;
      inset-inline-start: 0;
      min-width: 100%;
      width: max(100%, 520px);
      top: calc(100% + var(--espacio-8));
      padding: var(--espacio-8);
      background: var(--superficie-tarjeta);
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-burbuja);
      box-shadow: var(--sombra-suave);
      text-align: start;
    }
    .sugerencias {
      margin: 0;
      padding: 0;
      list-style: none;
    }
    .sugerencia {
      display: flex;
      align-items: center;
      gap: var(--espacio-12);
      min-height: 56px;
      padding: var(--espacio-8);
      border-radius: var(--radio-boton);
      cursor: pointer;
    }
    .sugerencia.activa {
      background: var(--superficie-tarjeta-hover);
    }
    .sugerencia img {
      width: 92px;
      height: 43px;
      flex: none;
      border-radius: 6px;
      object-fit: cover;
    }
    .datos {
      display: flex;
      flex-direction: column;
      gap: 2px;
      min-width: 0;
    }
    .nombre {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-size: var(--texto-body-sm);
    }
    .nombre strong {
      color: var(--neon);
    }
    .linea {
      display: flex;
      align-items: center;
      gap: var(--espacio-8);
      flex-wrap: wrap;
    }
    .pie {
      display: block;
      width: 100%;
      margin-top: var(--espacio-4);
      padding: var(--espacio-12) var(--espacio-8);
      border: 0;
      border-top: var(--filete);
      background: none;
      color: var(--neon);
      font-size: var(--texto-caption);
      text-align: start;
      cursor: pointer;
    }
    .pie:hover {
      text-decoration: underline;
      text-underline-offset: 4px;
    }
    .vacio {
      margin: 0;
      padding: var(--espacio-12) var(--espacio-8);
      line-height: var(--interlineado-largo);
    }
  `,
})
export class Buscador {
  private readonly campo = viewChild<ElementRef<HTMLInputElement>>('campo');

  readonly juegos = input.required<JuegoCatalogo[]>();
  readonly texto = input('');
  /** En Explorar la cuadrícula ya filtra al teclear: ahí el panel sería la misma búsqueda
   * dos veces, una encima de la otra. */
  readonly sugerir = input(true);
  /** 'ficha' abre el juego elegido; 'elegir' solo lo anuncia y deja decidir a quien lo usa
   * (comparar lo agrega a la bandeja en vez de navegar). */
  readonly modo = input<'ficha' | 'elegir'>('ficha');
  /** Appids que no tiene sentido ofrecer, como los que ya están en la comparación. */
  readonly excluir = input<readonly number[]>([]);
  /** El campo toma el foco al aparecer: en un panel que se abre, escribir es lo siguiente. */
  readonly autoFoco = input(false);
  /** Vacía, la etiqueta se queda solo para el lector de pantalla: dentro de un panel que
   * ya se llama "Agregar juego", preguntar otra vez sobra. */
  readonly etiqueta = input('¿Qué juego estás pensando comprar?');
  readonly textoCambio = output<string>();
  readonly elegido = output<JuegoCatalogo>();

  private readonly router = inject(Router);

  private readonly _abierto = signal(false);
  protected readonly abierto = this._abierto;
  /** Público a propósito: el inicio lo lee con una referencia de plantilla para dejar
   * quieto el carrusel mientras el panel está encima. */
  readonly panelDesplegado = computed(() => this.sugerir() && this.abierto() && !!this.texto().trim());
  protected readonly activo = signal(-1);

  /** Todo lo que coincide; el panel muestra las primeras y el pie dice cuántas hay. */
  protected readonly coincidencias = computed(() => {
    const texto = this.texto().trim();
    const fuera = new Set(this.excluir());
    if (!texto) {
      return [];
    }
    // Buscando "the", primero "The Sims" y después "Together": el que empieza palabra es
    // casi siempre el que se está buscando.
    return filtrarJuegos(this.juegos(), { texto, genero: '' })
      .filter((juego) => !fuera.has(juego.appid))
      .map((juego) => ({ juego, desde: posicionDeLaCoincidencia(juego.nombre, texto) }))
      .sort((a, b) => Number(!empiezaPalabra(a)) - Number(!empiezaPalabra(b)) || a.desde - b.desde)
      .map(({ juego }) => juego);
  });

  protected readonly sugerencias = computed(() => this.coincidencias().slice(0, MAXIMO_SUGERENCIAS));

  protected readonly precio = textoPrecio;
  protected readonly critica = textoMetacritic;

  /** El nombre partido para resaltar lo que se tecleó, sin tocar el original. Se prefiere
   * la coincidencia que empieza palabra: buscando "the", lo que se espera resaltado es
   * "The Sims", no las tres letras de en medio de "Together". */
  protected partes(nombre: string): { texto: string; coincide: boolean }[] {
    const buscado = this.texto().trim();
    const desde = posicionDeLaCoincidencia(nombre, buscado);
    if (!buscado || desde < 0) {
      return [{ texto: nombre, coincide: false }];
    }
    return [
      { texto: nombre.slice(0, desde), coincide: false },
      { texto: nombre.slice(desde, desde + buscado.length), coincide: true },
      { texto: nombre.slice(desde + buscado.length), coincide: false },
    ].filter((trozo) => trozo.texto);
  }

  constructor() {
    afterNextRender(() => {
      if (this.autoFoco()) {
        this.campo()?.nativeElement.focus();
      }
    });
  }

  protected verTodos(): void {
    this.abierto.set(false);
    this.router.navigate(['/explorar'], { queryParams: { q: this.texto().trim() } });
  }

  protected alTeclear(valor: string): void {
    this.abierto.set(true);
    this.activo.set(-1);
    this.textoCambio.emit(valor);
  }

  protected alTecla(evento: KeyboardEvent): void {
    const total = this.sugerencias().length;
    if (evento.key === 'Escape') {
      this.abierto.set(false);
      return;
    }
    if (!total) {
      return;
    }
    if (evento.key === 'ArrowDown') {
      evento.preventDefault();
      this.abierto.set(true);
      this.activo.set(this.activo() + 1 >= total ? 0 : this.activo() + 1);
      return;
    }
    if (evento.key === 'ArrowUp') {
      evento.preventDefault();
      this.abierto.set(true);
      this.activo.set(this.activo() <= 0 ? total - 1 : this.activo() - 1);
      return;
    }
    if (evento.key === 'Enter' && this.activo() >= 0) {
      evento.preventDefault();
      this.abrir(this.sugerencias()[this.activo()]);
    }
  }

  protected abrir(juego: JuegoCatalogo): void {
    this.abierto.set(false);
    if (this.modo() === 'elegir') {
      this.elegido.emit(juego);
      return;
    }
    this.router.navigate(['/juego', juego.appid]);
  }

  protected cerrarConRetraso(): void {
    // Da tiempo a que un clic en una sugerencia se procese antes de cerrarla.
    setTimeout(() => this.abierto.set(false), 150);
  }
}
