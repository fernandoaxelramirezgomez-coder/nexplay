import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { JuegoCatalogo, MotivoInsatisfaccion } from '../api/contrato';
import { AVISO_HISTORIA, historiaPerfil } from '../dominio/historia-perfil';
import { lineaPlataforma, respuestasPerfil } from '../dominio/opciones-perfil';
import { PerfilStore } from '../estado/perfil-store';

/** Por qué este juego le tocaría a quien declaró el perfil, con reglas sobre los datos
 * declarados. Es el bloque destacado de la ficha: lo declarado en chips, tres líneas con
 * su icono y la etiqueta que lo separa del riesgo. Aquí no se habla con Nia: en la ficha
 * hay una sola entrada al chat, que es su tarjeta en la columna de al lado. */
@Component({
  selector: 'app-historia-perfil',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <section class="bloque destacado historia" data-seccion="perfil" data-testid="historia-perfil">
      <header class="bloque-cabecera">
        <span class="insignia" aria-hidden="true">
          <svg viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" /><circle cx="12" cy="10" r="3.4" /><path d="M6.2 19.2a6 6 0 0 1 11.6 0" />
          </svg>
        </span>
        <h2 class="bloque-titulo">Por qué te tocaría a ti</h2>
        <p class="bloque-sub">
          {{ historia() ? 'Cómo encaja este juego con lo que declaraste.' : 'Aparece cuando nos cuentas cómo juegas.' }}
        </p>
        @if (historia()) {
          <span class="afinidad" data-testid="historia-etiqueta">Afinidad · no cambia el riesgo</span>
        }
      </header>

      @if (historia(); as lineas) {
        <ul class="respuestas" aria-label="Lo que declaraste en tu perfil" data-testid="historia-respuestas">
          @for (respuesta of respuestas(); track $index) {
            <li>
              @if (respuesta.pregunta) {
                <span class="pregunta">{{ respuesta.pregunta }}:</span>
              }
              {{ respuesta.texto }}
            </li>
          }
        </ul>

        <!-- Cada línea en una sola línea de plantilla a propósito: los saltos entre
             bloques se volverían espacios dentro del texto. -->
        <ul class="lineas" data-testid="historia-texto">
          @for (linea of lineas; track linea.tipo) {
            <li class="linea" [attr.data-tipo]="linea.tipo">
              <span class="icono" aria-hidden="true">
                @switch (linea.tipo) {
                  @case ('generos') {
                    <svg viewBox="0 0 24 24"><path d="M20 6 9 17l-5-5" /></svg>
                  }
                  @case ('tiempo') {
                    <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>
                  }
                  @case ('compra') {
                    <svg viewBox="0 0 24 24">
                      <circle cx="12" cy="12" r="9" />
                      <path d="M15 9.2A3 3 0 0 0 12.2 8H11a2 2 0 0 0 0 4h2a2 2 0 0 1 0 4h-1.2A3 3 0 0 1 9 14.8M12 6v2m0 8v2" />
                    </svg>
                  }
                }
              </span>
              <span>@for (segmento of linea.segmentos; track $index) {@if (segmento.clave) {<strong class="clave">{{ segmento.texto }}</strong>} @else {<ng-container>{{ segmento.texto }}</ng-container>}}</span>
            </li>
          }
          <!-- La plataforma se arma aquí con todas las marcadas: la API recibe una sola. -->
          @if (plataforma(); as linea) {
            <li class="linea" data-tipo="plataforma" data-testid="historia-plataforma">
              <span class="icono" aria-hidden="true">
                <svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="12" rx="2" /><path d="M8 20h8M12 16v4" /></svg>
              </span>
              <span>{{ linea }}</span>
            </li>
          }
        </ul>

        <p class="meta aviso">{{ avisoFijo }}</p>
        <a class="boton-texto" routerLink="/perfil" data-testid="historia-editar-perfil">Editar tu perfil</a>
      } @else {
        <p class="lectura" data-testid="historia-sin-perfil">
          Con tu perfil, aquí ves si el juego entra en tus géneros, en cuántas sesiones llegarías a las dos
          horas del reembolso y cuánto pesa la compra en tu año.
        </p>
        <a class="tarjeta-accion crear-perfil" data-tono="perfil" routerLink="/perfil" data-testid="historia-crear-perfil">
          <span class="insignia" aria-hidden="true">
            <svg viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10" /><circle cx="12" cy="10" r="3.4" /><path d="M6.2 19.2a6 6 0 0 1 11.6 0" />
            </svg>
          </span>
          <span class="titulo">Crear tu perfil</span>
          <span class="sub">Cuéntanos cómo juegas · 1 minuto</span>
          <span class="chevron" aria-hidden="true">›</span>
        </a>
      }
    </section>
  `,
  styles: `
    p {
      margin: 0;
    }
    .afinidad {
      grid-column: 3;
      grid-row: 1 / span 2;
      align-self: start;
      padding: 4px var(--espacio-12);
      border: 1px solid color-mix(in srgb, var(--tono) var(--mezcla-filo), var(--superficie));
      border-radius: var(--radio-pildora);
      color: var(--texto);
      font-size: var(--texto-caption);
      white-space: nowrap;
    }
    .respuestas {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-wrap: wrap;
      gap: var(--espacio-8);
    }
    .respuestas li {
      padding: 6px var(--espacio-12);
      border: 1px solid color-mix(in srgb, var(--tono) var(--mezcla-filo), var(--superficie));
      border-radius: var(--radio-pildora);
      background: var(--superficie-2);
      font-size: var(--texto-caption);
    }
    .pregunta {
      color: var(--texto-meta);
    }
    /* Tres líneas cortas, cada una con su icono: una por pregunta del formulario. */
    .lineas {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
    }
    .linea {
      display: grid;
      grid-template-columns: 32px minmax(0, 1fr);
      align-items: center;
      gap: var(--espacio-12);
      font-size: var(--texto-body);
      line-height: 1.4;
    }
    .icono {
      display: grid;
      place-items: center;
      width: 32px;
      height: 32px;
      border-radius: 10px;
      color: var(--tono);
      background: rgb(var(--tono-canal) / 0.14);
    }
    .icono svg {
      width: 18px;
      height: 18px;
      fill: none;
      stroke: currentColor;
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    /* La palabra clave, subrayada con el color del bloque; las letras conservan el color de
       texto, que es el que pasa contraste. */
    .clave {
      color: var(--texto);
      text-decoration: underline;
      text-decoration-color: var(--tono);
      text-decoration-thickness: 3px;
      text-underline-offset: 5px;
    }
    .aviso {
      max-width: var(--medida-lectura);
      line-height: var(--interlineado-largo);
    }
    @media (max-width: 640px) {
      .afinidad {
        grid-column: 1 / -1;
        grid-row: auto;
        justify-self: start;
        margin-top: var(--espacio-8);
      }
      .linea {
        font-size: 18px;
      }
    }
  `,
})
export class HistoriaPerfil {
  readonly juego = input.required<JuegoCatalogo>();
  readonly motivos = input<readonly MotivoInsatisfaccion[]>([]);

  private readonly perfil = inject(PerfilStore);

  protected readonly avisoFijo = AVISO_HISTORIA;

  protected readonly historia = computed(() =>
    historiaPerfil(this.perfil.perfil(), this.juego(), this.motivos()),
  );

  protected readonly plataforma = computed(() => lineaPlataforma(this.perfil.valores()?.plataformas ?? []));

  protected readonly respuestas = computed(() => {
    const valores = this.perfil.valores();
    return valores ? respuestasPerfil(valores) : [];
  });
}
