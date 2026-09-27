import { ChangeDetectionStrategy, Component, ElementRef, computed, inject, viewChild } from '@angular/core';
import { RouterLink } from '@angular/router';

import { DIFERENCIA, HERRAMIENTAS, destacadaDelInicio } from '../dominio/herramientas-inicio';
import { CatalogoStore } from '../estado/catalogo-store';

/** «¿Por qué elegir NexPlay?»: lo que nos diferencia (las primeras dos horas) en una
 * tarjeta destacada que lleva a Explorar, y las cuatro herramientas, cada una con el
 * icono y el color de su vista en el menú. La separa del encabezado una nave que apunta
 * hacia abajo y, al tocarla, baja hasta aquí. */
@Component({
  selector: 'app-por-que-elegir',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <div class="separador">
      <button
        type="button"
        class="nave"
        aria-label="Bajar a «¿Por qué elegir NexPlay?»"
        data-testid="por-que-nave"
        (click)="bajar()"
      >
        <span class="emoji" aria-hidden="true">🚀</span>
      </button>
    </div>
    <section class="por-que" #seccion aria-labelledby="titulo-por-que" data-testid="inicio-por-que">
      <h2 id="titulo-por-que" tabindex="-1" #titulo>¿Por qué elegir NexPlay?</h2>
      <p class="diferencia">{{ diferencia }}</p>
      <div class="rejilla">
        <article class="destacada" data-tono="inicio" data-testid="por-que-destacada">
          <span class="insignia" aria-hidden="true">
            <svg viewBox="0 0 24 24"><circle cx="12" cy="13" r="8" /><path d="M12 9v4l2.5 2.5M9 2h6" /></svg>
          </span>
          <h3>{{ destacada().titulo }}</h3>
          <p class="texto">{{ destacada().texto }}</p>
          <p class="aclaracion">{{ destacada().aclaracion }}</p>
          <a class="compacto" data-tono="inicio" routerLink="/explorar" data-testid="por-que-explorar"
            >{{ destacada().accion }} <span aria-hidden="true">→</span></a
          >
        </article>
        @for (herramienta of herramientas; track herramienta.id) {
          <a
            class="herramienta"
            [routerLink]="herramienta.ruta"
            [attr.data-tono]="herramienta.tono"
            [attr.data-herramienta]="herramienta.id"
            data-testid="herramienta-inicio"
          >
            <span class="insignia" aria-hidden="true">
              <svg viewBox="0 0 24 24">
                @switch (herramienta.id) {
                  @case ('motivos') {
                    <path d="M4 18V9m8 9V5m8 13v-6" />
                  }
                  @case ('nia') {
                    <path d="M20 14.5a3 3 0 0 1-3 3H9l-4 3v-3a3 3 0 0 1-1-2.2V8a3 3 0 0 1 3-3h10a3 3 0 0 1 3 3z" />
                  }
                  @case ('comparar') {
                    <rect x="3" y="3" width="18" height="18" rx="2" /><path d="M12 3v18" />
                  }
                  @case ('perfil') {
                    <circle cx="12" cy="12" r="10" /><circle cx="12" cy="10" r="3.4" />
                    <path d="M6.2 19.2a6 6 0 0 1 11.6 0" />
                  }
                }
              </svg>
            </span>
            <h3>{{ herramienta.titulo }} <span class="flecha" aria-hidden="true">→</span></h3>
            <p>{{ herramienta.linea }}</p>
          </a>
        }
      </div>
    </section>
  `,
  styles: `
    :host {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-24);
    }
    /* La nave en medio de una línea que se desvanece a los lados: separa la sección del
       encabezado y avisa que hay más abajo. */
    .separador {
      display: flex;
      align-items: center;
      gap: var(--espacio-16);
      margin-top: var(--espacio-24);
    }
    .separador::before,
    .separador::after {
      content: '';
      flex: 1;
      height: 1px;
    }
    .separador::before {
      background: linear-gradient(to right, transparent, var(--linea));
    }
    .separador::after {
      background: linear-gradient(to left, transparent, var(--linea));
    }
    .nave {
      display: grid;
      place-items: center;
      width: 64px;
      height: 64px;
      padding: 0;
      border: 1px solid color-mix(in srgb, var(--neon) 45%, var(--linea));
      border-radius: 50%;
      background: var(--superficie);
      cursor: pointer;
      box-shadow: 0 0 24px rgb(var(--accion-canal) / 0.18);
      animation: flotar 2.4s var(--curva) infinite;
      transition:
        border-color var(--duracion-rapida) var(--curva),
        box-shadow var(--duracion-rapida) var(--curva);
    }
    .nave:hover,
    .nave:focus-visible {
      animation-play-state: paused;
    }
    .nave:hover {
      border-color: var(--neon);
      box-shadow: 0 0 32px rgb(var(--accion-canal) / 0.35);
    }
    .nave:focus-visible {
      outline: 2px solid var(--foco);
      outline-offset: 3px;
    }
    /* El cohete del emoji mira arriba a la derecha: girado 135° apunta hacia abajo. */
    .emoji {
      display: block;
      font-size: 32px;
      line-height: 1;
      transform: rotate(135deg);
    }
    /* Baja y sube sin parar, como invitando a seguir hacia abajo. Se detiene con el cursor
       encima o con el foco, y con movimiento reducido la regla global ni lo mueve. */
    @keyframes flotar {
      0%,
      100% {
        transform: translateY(0);
      }
      50% {
        transform: translateY(6px);
      }
    }
    .por-que {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-16);
      scroll-margin-top: var(--espacio-24);
    }
    h2 {
      text-align: center;
      font-size: clamp(var(--texto-subheading), 2.4vw, var(--texto-heading-sm));
    }
    h2:focus {
      outline: none;
    }
    .diferencia {
      max-width: 62ch;
      margin-inline: auto;
      margin-bottom: var(--espacio-8);
      color: var(--texto-meta);
      font-size: 19px;
      line-height: 1.45;
      text-align: center;
    }
    /* A lo ancho, la destacada a la izquierda en dos filas y las cuatro a la derecha. */
    .rejilla {
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) repeat(2, minmax(0, 1fr));
      gap: var(--espacio-16);
    }
    .insignia {
      display: grid;
      place-items: center;
      width: 44px;
      height: 44px;
      border-radius: 12px;
      color: var(--tono);
      background: rgb(var(--tono-canal) / 0.14);
    }
    .insignia svg {
      width: 22px;
      height: 22px;
      fill: none;
      stroke: currentColor;
      stroke-width: 2;
      stroke-linecap: round;
      stroke-linejoin: round;
    }
    /* Lo que nadie más mide, con la única acción principal del Inicio. */
    .destacada {
      grid-row: 1 / span 2;
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 14px;
      padding: var(--espacio-24);
      border: 1px solid color-mix(in srgb, var(--tono) var(--mezcla-filo), var(--superficie));
      border-radius: 20px;
      background:
        radial-gradient(ellipse 80% 70% at 0% 0%, rgb(var(--tono-canal) / 0.16), transparent 70%),
        var(--superficie);
      box-shadow: 0 24px 60px rgb(0 0 0 / 0.25);
    }
    :host-context([data-tema='claro']) .destacada {
      box-shadow: 0 18px 44px rgb(11 15 31 / 0.1);
    }
    .destacada .insignia {
      width: 56px;
      height: 56px;
      border-radius: 16px;
    }
    .destacada .insignia svg {
      width: 28px;
      height: 28px;
    }
    .destacada h3 {
      font-size: 24px;
      font-weight: 700;
      line-height: 1.2;
    }
    .texto {
      font-size: 18px;
      line-height: 1.45;
    }
    .aclaracion {
      color: var(--texto-meta);
      font-size: var(--texto-body-sm);
      line-height: 1.45;
    }
    .destacada .compacto {
      margin-top: auto;
    }
    /* Cada herramienta es un enlace entero, con el filete, el icono y el color de su
       vista, como los pasos de Cómo funciona. */
    .herramienta {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-8);
      padding: 18px;
      border: 1px solid var(--borde);
      border-radius: var(--radio-tarjeta);
      background: var(--superficie);
      color: var(--texto);
      text-decoration: none;
      box-shadow: inset 0 3px 0 var(--tono);
      transition:
        border-color var(--duracion) var(--curva),
        transform var(--duracion) var(--curva);
    }
    .herramienta:hover {
      border-color: var(--tono);
      transform: translateY(-2px);
    }
    .herramienta:focus-visible {
      outline: 2px solid var(--foco);
      outline-offset: 3px;
    }
    .herramienta h3 {
      display: flex;
      align-items: center;
      gap: var(--espacio-8);
      font-size: 19px;
      font-weight: 700;
      line-height: 1.25;
    }
    .flecha {
      margin-left: auto;
      color: var(--tono);
    }
    .herramienta p {
      color: var(--texto-meta);
      font-size: var(--texto-body-sm);
      line-height: 1.45;
    }
    /* Con la barra de arriba fija, la sección se detiene debajo de ella. */
    @media (max-width: 900px) {
      .por-que {
        scroll-margin-top: calc(var(--alto-barra-movil) + var(--espacio-16));
      }
    }
    @container contenido (max-width: 900px) {
      .rejilla {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
      .destacada {
        grid-row: auto;
        grid-column: 1 / -1;
      }
    }
    @container contenido (max-width: 560px) {
      .rejilla {
        grid-template-columns: 1fr;
      }
      .destacada {
        padding: 20px;
      }
      .destacada h3 {
        font-size: 21px;
      }
    }
  `,
})
export class PorQueElegir {
  private readonly catalogo = inject(CatalogoStore);

  protected readonly diferencia = DIFERENCIA;
  protected readonly herramientas = HERRAMIENTAS;
  protected readonly destacada = computed(() => destacadaDelInicio(this.catalogo.juegos().length));

  private readonly seccion = viewChild.required<ElementRef<HTMLElement>>('seccion');
  private readonly titulo = viewChild.required<ElementRef<HTMLElement>>('titulo');

  /** Baja a la sección y le pasa el foco al título, para que un lector de pantalla también
   * llegue. Con movimiento reducido baja de golpe. Con ?. porque el DOM de las pruebas no
   * implementa scrollIntoView. */
  protected bajar(): void {
    const suave = !(typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches);
    this.seccion().nativeElement.scrollIntoView?.({ behavior: suave ? 'smooth' : 'auto', block: 'start' });
    this.titulo().nativeElement.focus({ preventScroll: true });
  }
}
