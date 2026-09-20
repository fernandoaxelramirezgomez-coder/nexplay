import { ChangeDetectionStrategy, Component, computed, input, linkedSignal } from '@angular/core';

/** Cabecera de la ficha: Steam publica por appid una imagen de 616×353 con el arte y
 * el título del juego; si falta, se usa la portada del catálogo (460×215). Se prefiere
 * esta a library_hero.jpg, que está pensada para llevar el logo encima y recortada al
 * centro suele quedar casi vacía. */
@Component({
  selector: 'app-portada-ancha',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="marco" [class.cargando]="estado() === 'cargando'">
      <img
        [src]="fuente()"
        alt=""
        width="616"
        height="353"
        fetchpriority="high"
        (load)="estado.set('lista')"
        (error)="fallar()"
      />
    </div>
  `,
  styles: `
    .marco {
      aspect-ratio: 1200 / 340;
      max-height: 340px;
      border-radius: var(--radio-tarjeta);
      overflow: hidden;
      background: var(--superficie-tarjeta-hover);
    }
    .marco.cargando {
      animation: pulso 1.2s ease-in-out infinite;
    }
    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      /* 35%: con 'center' se corta el título de Wild Hearts y con 'top' el logo de
         Cyberpunk y media portada de GTA V (ver docs/capturas/angular). */
      object-position: center 35%;
      opacity: 1;
      transition: opacity var(--duracion) var(--curva);
    }
    .cargando img {
      opacity: 0;
    }
    @keyframes pulso {
      50% {
        opacity: 0.55;
      }
    }
  `,
})
export class PortadaAncha {
  readonly appid = input.required<number>();
  /** portada_url del catálogo: el respaldo si no hay imagen ancha. */
  readonly respaldo = input.required<string>();

  protected readonly estado = linkedSignal<number, 'cargando' | 'lista' | 'fallida'>({
    source: this.appid,
    computation: () => 'cargando',
  });

  protected readonly fuente = computed(() =>
    this.estado() === 'fallida'
      ? this.respaldo()
      : `https://cdn.cloudflare.steamstatic.com/steam/apps/${this.appid()}/capsule_616x353.jpg`,
  );

  protected fallar(): void {
    this.estado.set(this.estado() === 'fallida' ? 'lista' : 'fallida');
  }
}
