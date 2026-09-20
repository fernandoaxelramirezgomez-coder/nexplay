import { ChangeDetectionStrategy, Component, computed, inject, input, output, signal } from '@angular/core';
import { Router } from '@angular/router';

import { JuegoCatalogo } from '../api/contrato';
import { filtrarJuegos } from '../dominio/filtros';

const MAXIMO_SUGERENCIAS = 6;

/** Buscador protagonista del catálogo. Filtra los estantes al teclear y, además,
 * sugiere juegos concretos para saltar directo a su ficha. */
@Component({
  selector: 'app-buscador',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="buscador">
      <label class="solo-lector" for="buscador-catalogo">Buscar un juego por nombre</label>
      <input
        id="buscador-catalogo"
        type="search"
        role="combobox"
        autocomplete="off"
        aria-autocomplete="list"
        aria-controls="sugerencias-catalogo"
        [attr.aria-expanded]="abierto()"
        [attr.aria-activedescendant]="activo() >= 0 ? 'sugerencia-' + activo() : null"
        placeholder="Busca por nombre: Hollow Knight, Cyberpunk, Portal…"
        data-testid="filtro-texto"
        [value]="texto()"
        (input)="alTeclear($any($event.target).value)"
        (keydown)="alTecla($event)"
        (focus)="abierto.set(true)"
        (blur)="cerrarConRetraso()"
      />

      @if (abierto() && sugerencias().length) {
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
              <img [src]="juego.portada_url" alt="" width="64" height="30" loading="lazy" />
              <span class="nombre">{{ juego.nombre }}</span>
              <span class="punto" [attr.data-banda]="juego.banda_riesgo" aria-hidden="true"></span>
              <span class="solo-lector">riesgo general {{ juego.banda_riesgo }}</span>
            </li>
          }
        </ul>
      }
    </div>
  `,
  styles: `
    :host {
      display: block;
      width: min(680px, 100%);
    }
    .buscador {
      position: relative;
    }
    input {
      width: 100%;
      font: inherit;
      font-size: var(--texto-body);
      letter-spacing: inherit;
      color: var(--texto);
      background: var(--superficie-tarjeta);
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-pildora);
      padding: 16px var(--espacio-24);
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
    .sugerencias {
      position: absolute;
      z-index: 20;
      inset-inline: 0;
      top: calc(100% + var(--espacio-8));
      margin: 0;
      padding: var(--espacio-8);
      list-style: none;
      background: var(--superficie-tarjeta);
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-tarjeta);
      text-align: start;
    }
    .sugerencia {
      display: flex;
      align-items: center;
      gap: var(--espacio-12);
      padding: var(--espacio-8);
      border-radius: var(--radio-boton);
      cursor: pointer;
      min-height: 44px;
    }
    .sugerencia.activa {
      background: var(--superficie-tarjeta-hover);
    }
    .sugerencia img {
      border-radius: 6px;
      width: 64px;
      height: 30px;
      object-fit: cover;
    }
    .nombre {
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .punto {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      flex: none;
    }
    .punto[data-banda='bajo'] {
      background: var(--banda-bajo);
    }
    .punto[data-banda='medio'] {
      background: var(--banda-medio);
    }
    .punto[data-banda='alto'] {
      background: var(--banda-alto);
    }
  `,
})
export class Buscador {
  readonly juegos = input.required<JuegoCatalogo[]>();
  readonly texto = input('');
  readonly textoCambio = output<string>();

  private readonly router = inject(Router);

  protected readonly abierto = signal(false);
  protected readonly activo = signal(-1);

  protected readonly sugerencias = computed(() => {
    const texto = this.texto().trim();
    return texto ? filtrarJuegos(this.juegos(), { texto, genero: '' }).slice(0, MAXIMO_SUGERENCIAS) : [];
  });

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
    this.router.navigate(['/juego', juego.appid]);
  }

  protected cerrarConRetraso(): void {
    // Da tiempo a que un clic en una sugerencia se procese antes de cerrarla.
    setTimeout(() => this.abierto.set(false), 150);
  }
}
