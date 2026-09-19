import { ChangeDetectionStrategy, Component, input } from '@angular/core';

@Component({
  selector: 'app-ficha',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<h1>Segunda opinión</h1>
    <p class="meta mono">appid {{ appid() }}</p>`,
})
export class Ficha {
  readonly appid = input.required<string>();
}
