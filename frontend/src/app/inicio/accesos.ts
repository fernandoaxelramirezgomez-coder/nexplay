import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';

import { CatalogoStore } from '../estado/catalogo-store';

type Icono = 'explorar' | 'comparar' | 'nia' | 'panorama';

interface Acceso {
  ruta: string;
  /** El color de la vista a la que lleva: el mismo del menú y de su fondo. */
  tono: Icono;
  titulo: string;
  texto: string;
}

/** Los cuatro accesos del inicio: tarjetas anchas, cada una con el color de su vista y
 * una línea que dice qué hay ahí. */
@Component({
  selector: 'app-accesos',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <section class="accesos" aria-labelledby="titulo-accesos" data-testid="inicio-accesos">
      <h2 class="rotulo-seccion" id="titulo-accesos">Qué puedes hacer aquí</h2>
      <ul class="rejilla">
        @for (acceso of accesos(); track acceso.ruta) {
          <li>
            <a
              class="tarjeta-accion"
              [attr.data-tono]="acceso.tono"
              [routerLink]="acceso.ruta"
              [attr.data-testid]="'acceso-' + acceso.ruta.slice(1)"
            >
              <span class="insignia" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  @switch (acceso.tono) {
                    @case ('explorar') {
                      <circle cx="12" cy="12" r="10" />
                      <path d="m16.24 7.76-2.12 6.36-6.36 2.12 2.12-6.36z" />
                    }
                    @case ('comparar') {
                      <rect x="3" y="3" width="18" height="18" rx="2" /><path d="M12 3v18" />
                    }
                    @case ('nia') {
                      <path d="M20 14.5a3 3 0 0 1-3 3H9l-4 3v-3a3 3 0 0 1-1-2.2V8a3 3 0 0 1 3-3h10a3 3 0 0 1 3 3z" />
                    }
                    @case ('panorama') {
                      <path d="M4 19V5" /><path d="M4 19h16" /><path d="M8 19v-6m4 6V8m4 11v-4" />
                    }
                  }
                </svg>
              </span>
              <span class="titulo">{{ acceso.titulo }}</span>
              <span class="sub">{{ acceso.texto }}</span>
              <span class="chevron" aria-hidden="true">›</span>
            </a>
          </li>
        }
      </ul>
    </section>
  `,
  styles: `
    .accesos {
      padding-top: var(--espacio-24);
      border-top: var(--filete);
    }
    .rejilla {
      list-style: none;
      margin: var(--espacio-16) 0 0;
      padding: 0;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: var(--espacio-12);
    }
    .rejilla li,
    .tarjeta-accion {
      height: 100%;
    }
    @media (max-width: 760px) {
      .rejilla {
        grid-template-columns: 1fr;
      }
    }
  `,
})
export class Accesos {
  private readonly catalogo = inject(CatalogoStore);

  protected readonly accesos = computed<readonly Acceso[]>(() => {
    const cuantos = this.catalogo.juegos().length;
    return [
      {
        ruta: '/explorar',
        tono: 'explorar',
        titulo: 'Explorar',
        texto: `${cuantos ? `Los ${cuantos} juegos` : 'El catálogo'}, por nivel de riesgo`,
      },
      { ruta: '/comparar', tono: 'comparar', titulo: 'Comparar', texto: 'Hasta cuatro juegos lado a lado' },
      { ruta: '/nia', tono: 'nia', titulo: 'Preguntar a Nia', texto: 'Tu asistente del catálogo' },
      { ruta: '/panorama', tono: 'panorama', titulo: 'Panorama', texto: 'Los datos del catálogo en gráficas' },
    ];
  });
}
