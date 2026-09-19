import { ChangeDetectionStrategy, Component, inject } from '@angular/core';

import { CatalogoStore } from '../estado/catalogo-store';

@Component({
  selector: 'app-catalogo',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <h1>Explorar</h1>
    @if (catalogo.error()) {
      <p data-testid="catalogo-error">No se pudo cargar el catálogo. Revisa que la API esté corriendo.</p>
    } @else if (catalogo.cargando()) {
      <p class="meta">Cargando catálogo…</p>
    } @else {
      <p class="meta mono" data-testid="catalogo-conteo">{{ catalogo.juegos().length }} juegos en el catálogo</p>
    }
  `,
})
export class Catalogo {
  protected readonly catalogo = inject(CatalogoStore);
}
