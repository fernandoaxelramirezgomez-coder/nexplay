import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { Buscador } from '../catalogo/buscador';
import { CatalogoStore } from '../estado/catalogo-store';
import { Accesos } from './accesos';
import { CarruselEjemplo } from './carrusel-ejemplo';
import { FuentesDatos } from './fuentes-datos';

/** El inicio: qué es NexPlay y qué ofrece. El catálogo con sus estantes vive en
 * /explorar; aquí el buscador solo salta a una ficha o al catálogo completo. */
@Component({
  selector: 'app-inicio',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, Buscador, Accesos, CarruselEjemplo, FuentesDatos],
  templateUrl: './inicio.html',
  styleUrl: './inicio.css',
})
export class Inicio {
  protected readonly catalogo = inject(CatalogoStore);

  protected readonly texto = signal('');
}
