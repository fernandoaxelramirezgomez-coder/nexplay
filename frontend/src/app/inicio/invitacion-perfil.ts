import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { PerfilStore } from '../estado/perfil-store';

const CLAVE = 'nexplay.invitacion-perfil.v1';

function descartadaAntes(): boolean {
  try {
    return localStorage.getItem(CLAVE) === 'descartada';
  } catch {
    return false;
  }
}

/** La invitación a crear el perfil, en el inicio: mientras no haya perfil y hasta que se
 * pulse «Ahora no», que se recuerda y no vuelve. Es una acción secundaria —compacto, no
 * botón principal—: la principal del inicio sigue siendo buscar. */
@Component({
  selector: 'app-invitacion-perfil',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    @if (visible()) {
      <aside class="invitacion" aria-labelledby="titulo-invitacion" data-testid="invitacion-perfil">
        <span class="insignia" aria-hidden="true">
          <svg viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" /><circle cx="12" cy="10" r="3.4" /><path d="M6.2 19.2a6 6 0 0 1 11.6 0" />
          </svg>
        </span>
        <h2 class="titulo" id="titulo-invitacion">Cuéntanos cómo juegas</h2>
        <p class="sub">1 minuto · Verás si cada juego encaja contigo y sugerencias a tu medida.</p>
        <div class="acciones">
          <a class="compacto" data-tono="perfil" routerLink="/perfil" data-testid="invitacion-crear">Crear mi perfil →</a>
          <button type="button" class="boton-texto" data-testid="invitacion-ahora-no" (click)="descartar()">Ahora no</button>
        </div>
      </aside>
    }
  `,
  styles: `
    .invitacion {
      display: grid;
      grid-template-columns: 52px minmax(0, 1fr) auto;
      align-items: center;
      gap: var(--espacio-4) var(--espacio-16);
      padding: 18px 20px;
      border: 1px solid color-mix(in srgb, var(--t-perfil) var(--mezcla-filo), var(--superficie));
      border-radius: var(--radio-tarjeta);
      background:
        linear-gradient(90deg, rgb(var(--canal-perfil) / 0.14), transparent 65%),
        var(--superficie);
      box-shadow: 0 0 30px rgb(var(--canal-perfil) / 0.16);
    }
    .insignia {
      grid-row: 1 / span 2;
      display: grid;
      place-items: center;
      width: 52px;
      height: 52px;
      border-radius: 14px;
      color: var(--t-perfil);
      background: rgb(var(--canal-perfil) / 0.14);
    }
    .insignia svg {
      width: 26px;
      height: 26px;
      fill: none;
      stroke: currentColor;
      stroke-width: 2;
      stroke-linecap: round;
    }
    .titulo {
      margin: 0;
      color: var(--t-perfil);
      font-family: var(--fuente-display);
      font-size: 22px;
      font-weight: 700;
      letter-spacing: 0.06em;
      text-transform: uppercase;
    }
    .sub {
      grid-column: 2;
      margin: 0;
      color: var(--texto-meta);
      line-height: 1.4;
    }
    .acciones {
      grid-column: 3;
      grid-row: 1 / span 2;
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: var(--espacio-12);
    }
    @media (max-width: 760px) {
      .invitacion {
        grid-template-columns: 44px minmax(0, 1fr);
        padding: var(--espacio-16);
      }
      .insignia {
        width: 44px;
        height: 44px;
      }
      .titulo {
        font-size: 20px;
        letter-spacing: 0.03em;
      }
      .acciones {
        grid-column: 1 / -1;
        grid-row: auto;
        margin-top: var(--espacio-8);
      }
    }
  `,
})
export class InvitacionPerfil {
  private readonly perfil = inject(PerfilStore);
  private readonly descartada = signal(descartadaAntes());

  protected readonly visible = computed(() => !this.perfil.hayPerfil() && !this.descartada());

  protected descartar(): void {
    this.descartada.set(true);
    try {
      localStorage.setItem(CLAVE, 'descartada');
    } catch {
      // Sin almacenamiento, «Ahora no» dura lo que dure la pestaña.
    }
  }
}
