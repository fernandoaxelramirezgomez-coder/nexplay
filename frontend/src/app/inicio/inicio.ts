import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { Router } from '@angular/router';

import { Buscador } from '../catalogo/buscador';
import { destinoDeBusqueda } from '../dominio/busqueda';
import { CatalogoStore } from '../estado/catalogo-store';
import { Accesos } from './accesos';
import { CarruselEjemplo } from './carrusel-ejemplo';
import { FuentesDatos } from './fuentes-datos';

/** El inicio: qué es NexPlay y qué ofrece. El catálogo con sus estantes vive en
 * /explorar; aquí el buscador salta a una ficha o al catálogo. */
@Component({
  selector: 'app-inicio',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Buscador, Accesos, CarruselEjemplo, FuentesDatos],
  templateUrl: './inicio.html',
  styleUrl: './inicio.css',
})
export class Inicio {
  protected readonly catalogo = inject(CatalogoStore);
  private readonly router = inject(Router);

  protected readonly texto = signal('');

  protected buscar(evento: Event): void {
    evento.preventDefault();
    const destino = destinoDeBusqueda(this.catalogo.juegos(), this.texto());
    this.router.navigate(destino.ruta, { queryParams: destino.parametros });
  }
}
