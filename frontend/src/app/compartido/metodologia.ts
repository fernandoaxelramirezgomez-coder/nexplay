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
      color: var(--enlace);
      text-decoration: underline;
      text-underline-offset: 4px;
    }
    .enlace:hover {
      text-decoration-thickness: 2px;
    }
  `,
})
export class Metodologia {}
