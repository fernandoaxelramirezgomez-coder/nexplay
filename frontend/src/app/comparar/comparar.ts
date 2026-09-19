import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  selector: 'app-comparar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<h1>Comparar</h1>`,
})
export class Comparar {}
