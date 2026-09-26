import { ChangeDetectionStrategy, Component, computed, inject, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { JuegoCatalogo, MotivoInsatisfaccion } from '../api/contrato';
import { AVISO_HISTORIA, historiaPerfil } from '../dominio/historia-perfil';
import { PerfilStore } from '../estado/perfil-store';

/** Por qué este juego le tocaría a quien declaró el perfil, con reglas sobre los datos
 * declarados. Aquí no se habla con Nia: en la ficha hay una sola entrada al chat, que es
 * su tarjeta en la columna de al lado. */
@Component({
  selector: 'app-historia-perfil',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <section class="historia" data-testid="historia-perfil">
      <h2 class="rotulo-seccion">Por qué te tocaría a ti</h2>

      @if (historia(); as segmentos) {
        <!-- Cada línea en una sola línea de plantilla a propósito: los saltos entre
             bloques se volverían espacios dentro del texto. -->
        <ul class="lineas" data-testid="historia-texto">
          @for (linea of segmentos; track $index) {
            <li class="linea lectura">@for (segmento of linea; track $index) {@if (segmento.clave) {<strong class="clave">{{ segmento.texto }}</strong>} @else {<ng-container>{{ segmento.texto }}</ng-container>}}</li>
          }
        </ul>

        <p class="meta aviso">{{ avisoFijo }}</p>
      } @else {
        <p class="lectura" data-testid="historia-sin-perfil">
          Todavía no sabemos cómo juegas. Con tu perfil, aquí aparece por qué este juego te tocaría a ti: tus
          géneros, tu tolerancia a la fricción y tus horas frente a las dos primeras.
        </p>
        <a class="boton-fantasma crear-perfil" routerLink="/perfil" data-testid="historia-crear-perfil">Crear tu perfil</a>
      }
    </section>
  `,
  styles: `
    .historia {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-12);
    }
    p {
      margin: 0;
    }
    /* En una columna flex el enlace se estiraría a todo el ancho; va del tamaño de su texto. */
    .crear-perfil {
      align-self: flex-start;
    }
    /* Tres líneas cortas, cada una con su viñeta: una por pregunta del formulario. */
    .lineas {
      list-style: none;
      margin: 0;
      padding: 0;
      display: flex;
      flex-direction: column;
      gap: var(--espacio-8);
    }
    .linea {
      position: relative;
      padding-inline-start: var(--espacio-16);
      line-height: var(--interlineado-largo);
    }
    .linea::before {
      content: '';
      position: absolute;
      inset-inline-start: 0;
      top: 0.7em;
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--borde-control);
    }
    /* La palabra clave lleva un subrayado cian que brilla hacia abajo. El brillo es del
       subrayado: las letras conservan el color de texto, sin sombra, y el contraste AA. */
    .clave {
      color: var(--texto);
      padding-bottom: 3px;
      background-image:
        linear-gradient(var(--neon), var(--neon)),
        linear-gradient(to top, rgb(var(--neon-canal) / 0.3), rgb(var(--neon-canal) / 0));
      background-size:
        100% 2px,
        100% 9px;
      background-position:
        0 100%,
        0 100%;
      background-repeat: no-repeat;
      -webkit-box-decoration-break: clone;
      box-decoration-break: clone;
    }
    .aviso {
      max-width: var(--medida-lectura);
      line-height: var(--interlineado-largo);
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
}
