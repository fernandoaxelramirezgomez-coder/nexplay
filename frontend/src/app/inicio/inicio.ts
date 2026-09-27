import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';

import { Buscador } from '../catalogo/buscador';
import { destinoDeBusqueda } from '../dominio/busqueda';
import { ofertasDelInicio } from '../dominio/ofertas-inicio';
import { CatalogoStore } from '../estado/catalogo-store';
import { CarruselEjemplo } from './carrusel-ejemplo';
import { ComoLoSabemos } from './como-lo-sabemos';
import { Hallazgos } from './hallazgos';
import { PorQueElegir } from './por-que-elegir';

/** El inicio: qué es NexPlay y el buscador, por qué elegirlo, qué encontramos y cómo lo
 * sabemos. El catálogo con sus estantes vive en /explorar; aquí el buscador salta a una
 * ficha o al catálogo. */
@Component({
  selector: 'app-inicio',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Buscador, CarruselEjemplo, PorQueElegir, Hallazgos, ComoLoSabemos],
  templateUrl: './inicio.html',
  styleUrl: './inicio.css',
})
export class Inicio {
  protected readonly catalogo = inject(CatalogoStore);
  private readonly router = inject(Router);

  protected readonly texto = signal('');
  /** Lo que ofrecemos, en cuadritos bajo la descripción; el número de juegos es el del catálogo. */
  protected readonly ofertas = computed(() => ofertasDelInicio(this.catalogo.juegos().length));

  protected buscar(evento: Event): void {
    evento.preventDefault();
    const destino = destinoDeBusqueda(this.catalogo.juegos(), this.texto());
    this.router.navigate(destino.ruta, { queryParams: destino.parametros });
  }
}
