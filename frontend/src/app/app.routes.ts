import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    title: 'NexPlay · Explorar',
    loadComponent: () => import('./catalogo/catalogo').then((m) => m.Catalogo),
  },
  {
    path: 'juego/:appid',
    title: 'NexPlay · Segunda opinión',
    loadComponent: () => import('./ficha/ficha').then((m) => m.Ficha),
  },
  {
    path: 'comparar',
    title: 'NexPlay · Comparar',
    loadComponent: () => import('./comparar/comparar').then((m) => m.Comparar),
  },
  {
    path: 'perfil',
    title: 'NexPlay · Tu perfil',
    loadComponent: () => import('./perfil/perfil').then((m) => m.Perfil),
  },
  { path: '**', redirectTo: '' },
];
