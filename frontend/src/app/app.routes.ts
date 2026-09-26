import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    title: 'NexPlay · Inicio',
    loadComponent: () => import('./inicio/inicio').then((m) => m.Inicio),
  },
  {
    path: 'explorar',
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
    path: 'nia',
    title: 'NexPlay · Nia',
    loadComponent: () => import('./chat/nia-pagina').then((m) => m.NiaPagina),
  },
  {
    path: 'perfil',
    title: 'NexPlay · Tu perfil',
    loadComponent: () => import('./perfil/perfil').then((m) => m.Perfil),
  },
  {
    path: 'historial',
    title: 'NexPlay · Tu historial',
    loadComponent: () => import('./historial/historial').then((m) => m.Historial),
  },
  {
    path: 'panorama',
    title: 'NexPlay · Panorama',
    loadComponent: () => import('./panorama/panorama').then((m) => m.Panorama),
  },
  {
    path: 'como-funciona',
    title: 'NexPlay · Cómo funciona',
    loadComponent: () => import('./como-funciona/como-funciona').then((m) => m.ComoFunciona),
  },
  { path: '**', redirectTo: '' },
];
