import { Component, computed, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { Metodologia } from './compartido/metodologia';
import { CompararStore } from './estado/comparar-store';
import { PerfilStore } from './estado/perfil-store';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, Metodologia],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {
  protected readonly comparar = inject(CompararStore);
  protected readonly perfil = inject(PerfilStore);
  protected readonly parametrosComparar = computed(() =>
    this.comparar.cantidad() ? { appids: this.comparar.appids().join(',') } : {},
  );
}
