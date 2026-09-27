import { inject } from '@angular/core';
import { Router, Routes } from '@angular/router';

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
  // Las tres vistas que salieron del menú en la reorganización a cinco: sus enlaces viejos
  // llevan a donde vive ahora su contenido, con el ancla que lo abre.
  {
    path: 'historial',
    redirectTo: () => inject(Router).createUrlTree(['/perfil'], { fragment: 'actividad' }),
  },
  {
    path: 'panorama',
    redirectTo: () => inject(Router).createUrlTree(['/'], { fragment: 'metodologia' }),
  },
  {
    path: 'como-funciona',
    redirectTo: () => inject(Router).createUrlTree(['/'], { fragment: 'metodologia' }),
  },
  { path: '**', redirectTo: '' },
];
