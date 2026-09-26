import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

/** El pie solo enlaza: el texto de la metodología vive en /como-funciona, una sola vez. */
@Component({
  selector: 'app-metodologia',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <a class="compacto" data-tono="neutro" routerLink="/como-funciona" fragment="titulo-metodologia" data-testid="enlace-metodologia">
      Metodología: cómo se calcula el riesgo →
    </a>
  `,
  // Compacto y no enlace suelto: el pie va sobre la nebulosa, y el texto de color directo
  // sobre ella no llegaba a 4.5:1 en el tema claro.
})
export class Metodologia {}
