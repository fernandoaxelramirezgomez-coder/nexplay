import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

/** El pie solo enlaza: el texto de la metodología vive en /como-funciona, una sola vez. */
@Component({
  selector: 'app-metodologia',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <a class="enlace toque-amplio" routerLink="/como-funciona" fragment="titulo-metodologia" data-testid="enlace-metodologia">
      Metodología: cómo se calcula el riesgo →
    </a>
  `,
  styles: `
    .enlace {
      color: var(--texto-meta);
      text-decoration: none;
      transition: color var(--duracion-rapida) var(--curva);
    }
    .enlace:hover {
      color: var(--texto);
    }
  `,
})
export class Metodologia {}
