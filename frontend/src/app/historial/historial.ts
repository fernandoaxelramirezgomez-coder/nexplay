import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { PildoraBanda } from '../compartido/pildora-banda';
import { hace } from '../dominio/tiempo';
import { EntradaHistorial, HistorialStore, MAXIMO_HISTORIAL, TipoEntrada } from '../estado/historial-store';

const ROTULO: Record<TipoEntrada, string> = {
  visto: 'Ficha abierta',
  comparado: 'Comparación',
  nia: 'Pregunta a Nia',
  perfil: 'Perfil',
};

@Component({
  selector: 'app-historial',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, PildoraBanda],
  template: `
    <div class="historial" data-testid="historial">
      <header class="cabecera">
        <h1>Tu historial</h1>
        <p class="lectura entrada">
          Las fichas que abriste, lo que comparaste y lo que le preguntaste a Nia.
          <strong>Vive solo en este navegador</strong>: no viaja a ningún servidor y nadie más lo ve.
          Se guardan las últimas {{ maximo }} cosas.
        </p>
      </header>

      @if (historial.hayHistorial()) {
        <ol class="lista" data-testid="historial-lista">
          @for (entrada of entradas(); track $index) {
            <li class="entrada-historial" [attr.data-tipo]="entrada.tipo" data-testid="historial-entrada">
              <span class="rotulo mono">{{ rotulo(entrada.tipo) }}</span>
              @if (entrada.appid) {
                <a class="titulo" [routerLink]="['/juego', entrada.appid]">{{ entrada.titulo }}</a>
              } @else {
                <span class="titulo">{{ entrada.titulo }}</span>
              }
              @if (entrada.banda) {
                <app-pildora-banda [banda]="entrada.banda" />
              }
              <span class="cuando meta mono">{{ cuando(entrada) }}</span>
            </li>
          }
        </ol>

        <div class="acciones">
          @if (confirmando()) {
            <p class="meta" role="status">¿Seguro? Esto no se puede deshacer.</p>
            <button type="button" class="boton-cta" data-testid="historial-confirmar" (click)="borrar()">
              Sí, borrar
            </button>
            <button type="button" class="boton-fantasma" (click)="confirmando.set(false)">Cancelar</button>
          } @else {
            <button type="button" class="boton-fantasma" data-testid="historial-borrar" (click)="confirmando.set(true)">
              Borrar el historial
            </button>
          }
        </div>
      } @else {
        <p class="lectura vacio" data-testid="historial-vacio">
          Todavía no hay nada. Abre la ficha de un juego y regresa aquí.
          <a class="boton-texto" routerLink="/explorar">Ir al catálogo →</a>
        </p>
      }
    </div>
  `,
  styles: `
    .historial {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-24);
    }
    .cabecera {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
    }
    .lista {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
    }
    .entrada-historial {
      display: flex;
      align-items: center;
      gap: var(--espacio-12);
      flex-wrap: wrap;
      padding: var(--espacio-12) 0;
      border-top: var(--filete);
    }
    .rotulo {
      min-width: 13ch;
      color: var(--texto-meta);
      font-size: var(--texto-caption);
    }
    .titulo {
      color: var(--texto);
      text-decoration: none;
    }
    a.titulo:hover {
      color: var(--neon);
      text-decoration: underline;
      text-underline-offset: 4px;
    }
    .cuando {
      margin-inline-start: auto;
    }
    .acciones {
      display: flex;
      align-items: center;
      gap: var(--espacio-12);
      flex-wrap: wrap;
    }
    .vacio {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: var(--espacio-8);
    }
  `,
})
export class Historial {
  protected readonly historial = inject(HistorialStore);
  protected readonly maximo = MAXIMO_HISTORIAL;
  protected readonly confirmando = signal(false);

  protected readonly entradas = computed(() => this.historial.entradas());

  protected rotulo(tipo: TipoEntrada): string {
    return ROTULO[tipo];
  }

  protected cuando(entrada: EntradaHistorial): string {
    return hace(entrada.cuando);
  }

  protected borrar(): void {
    this.historial.borrar();
    this.confirmando.set(false);
  }
}
