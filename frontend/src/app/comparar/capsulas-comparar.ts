import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';

import { JuegoCatalogo } from '../api/contrato';
import { Buscador } from '../catalogo/buscador';
import { Portada } from '../compartido/portada';
import { CatalogoStore } from '../estado/catalogo-store';
import { CompararStore, MAXIMO_COMPARAR } from '../estado/comparar-store';

/** Los juegos elegidos, como cápsulas, y una para agregar otro sin ir al catálogo y
 * volver. Antes había que salir a Explorar, buscar la tarjeta y regresar. */
@Component({
  selector: 'app-capsulas-comparar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Portada, Buscador],
  template: `
    <div class="caja" data-testid="capsulas-comparar">
      <div class="capsulas">
      @for (juego of juegos(); track juego.appid) {
        <span class="capsula" [attr.data-appid]="juego.appid">
          <app-portada class="miniatura" [src]="juego.portada_url" />
          <span class="nombre">{{ juego.nombre }}</span>
          <button
            type="button"
            class="quitar toque-amplio"
            data-testid="quitar-comparar"
            [attr.aria-label]="'Quitar de la comparación: ' + juego.nombre"
            (click)="comparar.quitar(juego.appid)"
          >
            ×
          </button>
        </span>
      }

      @if (!lleno()) {
        <button
          type="button"
          class="capsula vacia"
          data-testid="abrir-agregar"
          [attr.aria-expanded]="abierto()"
          (click)="alternar()"
        >
          + Agregar juego
        </button>
      } @else {
        <p class="meta lleno" data-testid="capsulas-lleno">
          Ya hay {{ maximo }} juegos, el máximo. Quita uno para agregar otro.
        </p>
      }
      </div>

      @if (abierto() && !lleno()) {
        <div class="panel">
          <app-buscador
            [juegos]="catalogo.juegos()"
            [texto]="texto()"
            [excluir]="comparar.appids()"
            [autoFoco]="true"
            etiqueta=""
            modo="elegir"
            (textoCambio)="texto.set($event)"
            (elegido)="agregar($event)"
          />
        </div>
      }
    </div>
  `,
  styles: `
    .caja {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-8);
    }
    .capsulas {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--espacio-12);
    }
    .capsula {
      display: flex;
      align-items: center;
      gap: var(--espacio-8);
      max-width: 320px;
      padding: var(--espacio-4) var(--espacio-8) var(--espacio-4) var(--espacio-4);
      border: 1px solid var(--linea);
      border-radius: var(--radio-pildora);
      background: var(--superficie-tarjeta);
      font-size: var(--texto-body-sm);
    }
    .miniatura {
      width: 64px;
      flex: none;
    }
    .nombre {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .quitar {
      position: relative;
      display: grid;
      place-items: center;
      width: 24px;
      height: 24px;
      flex: none;
      padding: 0;
      border: 0;
      border-radius: 50%;
      background: none;
      color: var(--texto-meta);
      font-size: 20px;
      line-height: 1;
      cursor: pointer;
    }
    .quitar:hover {
      color: var(--banda-alto-texto);
    }
    .vacia {
      border-style: dashed;
      border-color: var(--borde-control);
      background: none;
      color: var(--texto-meta);
      min-height: 44px;
      padding-inline: var(--espacio-16);
      cursor: pointer;
    }
    .vacia:hover {
      border-color: var(--neon);
      color: var(--texto);
    }
    /* El buscador trae su propio panel para los resultados; este es el que sostiene el
       campo, para que no quede flotando encima de la tabla. */
    /* En el flujo y no flotando: así empuja la tabla hacia abajo en vez de taparle el
       encabezado, y cabe el placeholder entero. */
    .panel {
      width: min(460px, 100%);
      padding: var(--espacio-8);
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-burbuja);
      background: var(--superficie-tarjeta);
    }
    .lleno {
      margin: 0;
    }
  `,
})
export class CapsulasComparar {
  protected readonly catalogo = inject(CatalogoStore);
  protected readonly comparar = inject(CompararStore);

  protected readonly maximo = MAXIMO_COMPARAR;
  protected readonly abierto = signal(false);
  protected readonly texto = signal('');

  protected readonly juegos = computed(() => {
    const porAppid = this.catalogo.porAppid();
    return this.comparar
      .appids()
      .map((appid) => porAppid.get(appid))
      .filter((juego) => juego !== undefined);
  });

  protected readonly lleno = computed(() => this.comparar.cantidad() >= MAXIMO_COMPARAR);

  protected alternar(): void {
    this.abierto.update((abierto) => !abierto);
    this.texto.set('');
  }

  protected cerrar(): void {
    this.abierto.set(false);
  }

  protected agregar(juego: JuegoCatalogo): void {
    this.comparar.alternar(juego.appid);
    this.texto.set('');
    this.abierto.set(false);
  }
}
