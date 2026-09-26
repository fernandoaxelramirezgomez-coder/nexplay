import { ChangeDetectionStrategy, Component, computed, inject, input, linkedSignal, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { JuegoCatalogo } from '../api/contrato';
import { PildoraBanda } from '../compartido/pildora-banda';
import { Portada } from '../compartido/portada';
import { filtrarJuegos } from '../dominio/filtros';
import { CatalogoStore } from '../estado/catalogo-store';
import { Nia } from './nia';

const MAXIMO_SUGERENCIAS = 12;

/** La página de Nia: la conversación con espacio propio. La API siempre responde sobre
 * un juego concreto, así que lo primero es elegirlo; el appid viaja en la URL para poder
 * llegar aquí desde una ficha. */
@Component({
  selector: 'app-nia-pagina',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, Nia, PildoraBanda, Portada],
  template: `
    <div class="nia-pagina" data-testid="nia-pagina">
      <header class="cabecera">
        <img class="avatar" src="nia/chat.png" alt="" width="200" height="233" />
        <div>
          <h1>Habla con Nia</h1>
          <p class="lectura entrada">
            Responde con los datos del catálogo: qué juegos hay y con qué riesgo, los motivos que más
            aparecen en sus reseñas, la crítica y el precio. Puedes fijar un juego o preguntar por
            todos. No recomienda comprar ni no comprar.
          </p>
        </div>
      </header>

      <div class="conversacion">
        @if (elegido(); as juego) {
          <aside class="juego panel-vidrio" data-testid="nia-juego">
            <a class="ficha" [routerLink]="['/juego', juego.appid]">
              <app-portada class="portada" [src]="juego.portada_url" />
              <span class="nombre">{{ juego.nombre }}</span>
            </a>
            <app-pildora-banda [banda]="juego.banda_riesgo" />
            <p class="meta">
              Nia responde con los datos de este juego. Suéltalo para volver a hablar de todo el catálogo.
            </p>
            <div class="acciones">
              <a class="boton-texto" [routerLink]="['/juego', juego.appid]">Ver su ficha completa →</a>
              <button type="button" class="boton-texto" data-testid="nia-cambiar" (click)="soltar()">
                Hablar de todo el catálogo
              </button>
            </div>
          </aside>
        } @else {
          <aside class="elegir panel-vidrio" data-testid="nia-elegir">
            <p class="meta">
              Estás hablando de los {{ catalogo.juegos()?.length ?? 0 }} juegos del catálogo. Si quieres
              centrarte en uno, elígelo aquí.
            </p>
          <label class="buscar">
            <span class="etiqueta">¿De qué juego quieres hablar?</span>
            <input
              type="search"
              autocomplete="off"
              placeholder="Busca por nombre…"
              data-testid="nia-buscar"
              [value]="texto()"
              (input)="texto.set($any($event.target).value)"
            />
          </label>
          <ul class="sugerencias" data-testid="nia-sugerencias">
            @for (juego of sugerencias(); track juego.appid) {
              <li>
                <button type="button" class="sugerencia" data-testid="nia-sugerencia" (click)="elegir(juego)">
                  <app-portada class="miniatura" [src]="juego.portada_url" />
                  <span class="datos">
                    <span class="nombre">{{ juego.nombre }}</span>
                    <app-pildora-banda [banda]="juego.banda_riesgo" />
                  </span>
                </button>
              </li>
            } @empty {
              @if (texto().trim()) {
                <li class="meta vacio" data-testid="nia-vacio">Ningún juego del catálogo se llama así.</li>
              }
            }
          </ul>
          </aside>
        }
        <div class="chat panel-vidrio">
          <app-nia
            [appid]="elegido()?.appid ?? null"
            [muestraTitulo]="false"
            [muestraIntro]="false"
            [llenaAlto]="true"
          />
        </div>
      </div>
    </div>
  `,
  styles: `
    .nia-pagina {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-24);
    }
    .cabecera {
      display: flex;
      align-items: center;
      gap: var(--espacio-24);
    }
    .avatar {
      width: 96px;
      height: auto;
      flex: none;
    }
    /* El juego a la izquierda y la conversación a la derecha: así el chat tiene el ancho
       que necesita y el juego del que se habla no se pierde al desplazarse. */
    .conversacion {
      display: grid;
      grid-template-columns: 260px minmax(0, 1fr);
      gap: var(--espacio-24);
      align-items: start;
    }
    .juego {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: var(--espacio-12);
      padding: var(--espacio-16);
      position: sticky;
      top: var(--espacio-16);
    }
    .juego .portada {
      width: 100%;
    }
    .juego .acciones {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: var(--espacio-4);
    }
    /* El panel mide lo que queda de pantalla y no 560 px fijos: en un portátil de 674 px
       el botón de preguntar se salía por abajo. 13rem es lo que ocupan el encabezado de la
       página, el aire de la barra superior y el pie. */
    .chat {
      display: flex;
      flex-direction: column;
      padding: var(--espacio-16) var(--espacio-24);
      min-height: min(560px, calc(100dvh - 13rem));
      max-height: calc(100dvh - 13rem);
    }
    .chat app-nia {
      display: flex;
      flex-direction: column;
      flex: 1;
      min-height: 0;
    }
    @container contenido (max-width: 760px) {
      .conversacion {
        grid-template-columns: 1fr;
      }
      .juego {
        position: static;
        flex-direction: row;
        align-items: center;
        flex-wrap: wrap;
      }
      .juego .portada {
        width: 140px;
      }
    }
    .ficha {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: var(--espacio-8);
      color: inherit;
      text-decoration: none;
    }
    .sugerencia {
      display: grid;
      grid-template-columns: 92px minmax(0, 1fr);
      align-items: center;
      gap: var(--espacio-12);
      color: inherit;
      text-decoration: none;
    }
    /* El nombre y la banda se apilan: la píldora no se encoge y en una columna de 280 px
       no cabe al lado de un nombre largo. */
    .datos {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: var(--espacio-4);
      min-width: 0;
    }
    .datos .nombre {
      overflow-wrap: anywhere;
    }
    .miniatura {
      width: 92px;
      flex: none;
    }
    .nombre {
      font-size: var(--texto-body-sm);
    }
    .elegir {
      display: flex;
      flex-direction: column;
      gap: var(--espacio-16);
    }
    .etiqueta {
      display: block;
      margin-bottom: var(--espacio-8);
      font-size: var(--texto-body-sm);
    }
    .buscar input {
      width: 100%;
      padding: var(--espacio-12) var(--espacio-16);
      border: 1px solid var(--borde-control);
      border-radius: var(--radio-pildora);
      background: var(--superficie-tarjeta);
      color: var(--texto);
      font: inherit;
    }
    .buscar input:focus-visible {
      border-color: var(--neon);
      outline: 2px solid var(--foco);
      outline-offset: 2px;
    }
    .sugerencias {
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: var(--espacio-8);
    }
    .sugerencia {
      width: 100%;
      padding: var(--espacio-8);
      border: 1px solid transparent;
      border-radius: var(--radio-tarjeta);
      background: none;
      cursor: pointer;
      text-align: start;
    }
    .sugerencia:hover {
      border-color: var(--borde-control);
      background: var(--superficie-tarjeta);
    }
    .vacio {
      grid-column: 1 / -1;
    }
    @media (max-width: 640px) {
      .cabecera {
        gap: var(--espacio-16);
      }
      .avatar {
        width: 64px;
      }
    }
  `,
})
export class NiaPagina {
  /** ?appid=: la ficha enlaza aquí con el juego ya elegido. */
  readonly appid = input<string>();

  protected readonly catalogo = inject(CatalogoStore);
  private readonly router = inject(Router);

  protected readonly texto = signal('');

  /** El juego de la URL, cuando el catálogo ya llegó: se lee de las dos fuentes a la vez
   * para que aterrizar en /nia?appid= antes de que cargue el catálogo también funcione. */
  private readonly deLaUrl = computed(() => {
    const numero = Number(this.appid());
    return Number.isInteger(numero) && numero > 0
      ? this.catalogo.porAppid().get(numero)
      : undefined;
  });

  protected readonly elegido = linkedSignal<JuegoCatalogo | undefined, JuegoCatalogo | undefined>({
    source: this.deLaUrl,
    computation: (juego) => juego,
  });

  /** Solo al teclear: el chat ya funciona sin elegir nada, así que una lista de 123
   * juegos abierta al entrar es una columna infinita al lado de la conversación. */
  protected readonly sugerencias = computed(() => {
    const texto = this.texto().trim();
    return texto ? filtrarJuegos(this.catalogo.juegos(), { texto, genero: '' }).slice(0, MAXIMO_SUGERENCIAS) : [];
  });

  protected elegir(juego: JuegoCatalogo): void {
    this.elegido.set(juego);
    this.router.navigate([], { queryParams: { appid: juego.appid }, replaceUrl: true });
  }

  protected soltar(): void {
    this.elegido.set(undefined);
    this.texto.set('');
    this.router.navigate([], { queryParams: { appid: null }, replaceUrl: true });
  }
}
