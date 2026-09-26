import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { of } from 'rxjs';

import { JuegoCatalogo } from '../api/contrato';
import { NexplayApi } from '../api/nexplay-api';
import { advertenciaNexplay, advertenciaSinCritica, sentimientoSteam } from '../dominio/critica';
import { PanoramaStore } from '../estado/panorama-store';
import { UsuarioStore } from '../estado/usuario-store';

/** «Crítica y público»: qué dicen de un juego, además del riesgo. Con Metacritic, su nota
 * y la de Steam; sin Metacritic, lo dice y da el sentimiento de las reseñas de Steam con la
 * advertencia de dónde viene. Con `conNexplay`, lo que se dice en NexPlay, con la misma
 * advertencia.
 *
 * Nada de esto entra al modelo. El porcentaje de Steam va en el azul de la opinión y
 * nunca en los colores del riesgo: un 94 % en verde se leería como «riesgo bajo». */
@Component({
  selector: 'app-critica-publico',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section
      class="critica"
      [class.bloque]="!incrustado()"
      [class.incrustado]="incrustado()"
      [class.angosto]="angosto()"
      data-seccion="opinion"
      data-testid="critica-publico"
    >
      @if (incrustado()) {
        <h3 class="titulo-incrustado">Crítica y público</h3>
      } @else {
      <header class="bloque-cabecera">
        <span class="insignia" aria-hidden="true">
          <svg viewBox="0 0 24 24">
            <path d="M17 20v-2a4 4 0 0 0-4-4H7a4 4 0 0 0-4 4v2" /><circle cx="10" cy="7" r="4" />
            <path d="M21 20v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8" />
          </svg>
        </span>
        <h3 class="bloque-titulo">Crítica y público</h3>
        <p class="bloque-sub">Qué dicen de él, además del riesgo.</p>
      </header>
      }

      @if (juego().metacritic !== null) {
        <p class="metacritic" data-testid="critica-metacritic">
          Metacritic {{ juego().metacritic }}
          <small>
            Crítica especializada.
            @if (promedio() !== null) {
              El promedio del catálogo es {{ promedio()!.toFixed(1) }}.
            }
          </small>
        </p>
      }

      @if (steam(); as s) {
        <div class="sentimiento" data-testid="critica-steam">
          <p class="cifra">
            <strong data-testid="critica-porcentaje">{{ s.porcentaje }} %</strong>
            <span>de reseñas positivas en Steam@if (s.etiqueta) {<ng-container> · {{ s.etiqueta }}</ng-container>}</span>
          </p>
          <span class="barra" aria-hidden="true"><span [style.width.%]="s.porcentaje"></span></span>
        </div>
        @if (juego().metacritic === null) {
          <p class="advertencia" data-testid="critica-advertencia">{{ advertenciaSteam() }}</p>
        } @else {
          <p class="meta">De {{ totalSteam() }} reseñas de jugadores en Steam.</p>
        }
      } @else if (juego().metacritic === null) {
        <p class="meta">Sin crítica especializada ni resumen de Steam para este juego.</p>
      }

      @if (conNexplay() && hayNexplay()) {
        <div class="nexplay" data-testid="critica-nexplay">
          <p class="titulo-nexplay">En NexPlay</p>
          <p class="resumen mono">{{ resumenNexplay() }}</p>
          @if (ultimoComentario(); as comentario) {
            <blockquote class="comentario">«{{ comentario }}»</blockquote>
          }
          <p class="advertencia">{{ advertenciaNexplay() }}</p>
        </div>
      }
    </section>
  `,
  styles: `
    .critica {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
    }
    /* Dentro de la ficha técnica: sin caja propia, bajo un filete y con un título chico. */
    .incrustado {
      padding-top: var(--espacio-16);
      border-top: 1px solid var(--borde);
    }
    .titulo-incrustado {
      margin: 0;
      color: var(--info);
      font-family: var(--fuente-display);
      font-size: 17px;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }
    /* En una columna de Comparar: menos relleno y sin icono, o el título se parte. */
    .angosto {
      padding: var(--espacio-16) 14px 18px;
    }
    .angosto .bloque-cabecera {
      grid-template-columns: minmax(0, 1fr);
    }
    .angosto .insignia {
      display: none;
    }
    .angosto .bloque-titulo {
      font-size: 17px;
      letter-spacing: 0.04em;
    }
    .angosto .bloque-sub {
      grid-column: 1;
    }
    p {
      margin: 0;
    }
    .metacritic {
      font-family: var(--fuente-mono);
      font-size: 18px;
    }
    .metacritic small {
      display: block;
      margin-top: var(--espacio-4);
      color: var(--texto-meta);
      font-family: var(--fuente-texto);
      font-size: var(--texto-caption);
      line-height: 1.4;
    }
    .sentimiento {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-8);
    }
    .cifra {
      display: flex;
      flex-wrap: wrap;
      align-items: baseline;
      gap: var(--espacio-4) var(--espacio-8);
      line-height: 1.35;
    }
    .cifra strong {
      font-family: var(--fuente-mono);
      font-size: 26px;
    }
    .barra {
      display: block;
      height: 10px;
      border-radius: var(--radio-pildora);
      background: var(--superficie-2);
      overflow: hidden;
    }
    .barra span {
      display: block;
      height: 100%;
      border-radius: var(--radio-pildora);
      background: var(--info);
    }
    .advertencia {
      padding: var(--espacio-8) var(--espacio-12);
      border: 1px dashed var(--borde-control);
      border-radius: 12px;
      background: var(--superficie-2);
      line-height: 1.4;
    }
    .nexplay {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-8);
      padding-top: var(--espacio-12);
      border-top: 1px solid var(--borde);
    }
    .titulo-nexplay {
      font-weight: var(--peso-clave);
    }
    .comentario {
      margin: 0;
      padding: var(--espacio-8) var(--espacio-12);
      border-radius: 12px;
      background: var(--superficie-lienzo);
      line-height: 1.45;
    }
  `,
})
export class CriticaPublico {
  readonly juego = input.required<JuegoCatalogo>();
  readonly promedio = input<number | null>(null);
  readonly conNexplay = input(false);
  readonly angosto = input(false);
  /** Dentro de otra tarjeta (la ficha técnica): sin caja ni icono propios. */
  readonly incrustado = input(false);

  private readonly panorama = inject(PanoramaStore);
  private readonly api = inject(NexplayApi);
  private readonly usuario = inject(UsuarioStore);

  protected readonly steam = computed(() => sentimientoSteam(this.panorama.porAppid().get(this.juego().appid)));
  protected readonly totalSteam = computed(() => new Intl.NumberFormat('es-MX').format(this.steam()?.total ?? 0));
  protected readonly advertenciaSteam = computed(() => advertenciaSinCritica(this.steam()?.total ?? 0));

  private readonly valoraciones = rxResource({
    params: () => (this.conNexplay() ? this.juego().appid : undefined),
    stream: ({ params }) => this.api.valoraciones(params, this.usuario.id),
  });
  private readonly comentarios = rxResource({
    params: () => (this.conNexplay() ? this.juego().appid : undefined),
    stream: ({ params }) => (params ? this.api.comentarios(params, this.usuario.id) : of([])),
  });

  private readonly totalValoraciones = computed(() =>
    this.valoraciones.hasValue() ? (this.valoraciones.value()?.total ?? 0) : 0,
  );
  private readonly lista = computed(() => (this.comentarios.hasValue() ? (this.comentarios.value() ?? []) : []));

  protected readonly hayNexplay = computed(() => this.totalValoraciones() > 0 || this.lista().length > 0);

  protected readonly resumenNexplay = computed(() => {
    const partes: string[] = [];
    const promedio = this.valoraciones.hasValue() ? this.valoraciones.value()?.promedio : null;
    const total = this.totalValoraciones();
    if (total) {
      partes.push(`${promedio?.toFixed(1)} ★ · ${total} ${total === 1 ? 'valoración' : 'valoraciones'}`);
    }
    const comentarios = this.lista().length;
    if (comentarios) {
      partes.push(`${comentarios} ${comentarios === 1 ? 'comentario' : 'comentarios'}`);
    }
    return partes.join(' · ');
  });

  /** El más reciente: el hilo llega del más viejo al más nuevo. */
  protected readonly ultimoComentario = computed(() => {
    const lista = this.lista();
    const texto = lista.length ? lista[lista.length - 1].texto : '';
    return texto.length > 140 ? `${texto.slice(0, 137)}…` : texto;
  });

  protected readonly advertenciaNexplay = computed(() => advertenciaNexplay(this.totalValoraciones(), this.lista().length));
}
