import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { Metodologia } from './compartido/metodologia';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, Metodologia],
  templateUrl: './app.html',
  styleUrl: './app.css',
})
export class App {}
