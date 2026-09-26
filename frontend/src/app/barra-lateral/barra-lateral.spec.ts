import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';

import { BarraLateral } from './barra-lateral';
import { BarraStore } from '../estado/barra-store';
import { TemaStore } from '../estado/tema-store';

/** Las rutas reales del sitio, vacías: routerLinkActive necesita que existan. */
@Component({ template: '' })
class Pagina {}

const RUTAS = [
  { path: '', component: Pagina },
  { path: 'explorar', component: Pagina },
  { path: 'comparar', component: Pagina },
  { path: 'nia', component: Pagina },
  { path: 'perfil', component: Pagina },
  { path: 'historial', component: Pagina },
  { path: 'panorama', component: Pagina },
  { path: 'como-funciona', component: Pagina },
];

function crear() {
  const fixture = TestBed.createComponent(BarraLateral);
  return { fixture, html: fixture.nativeElement as HTMLElement };
}

describe('BarraLateral', () => {
  beforeEach(async () => {
    localStorage.clear();
    document.documentElement.removeAttribute('data-tema');
    vi.stubGlobal('matchMedia', (consulta: string) => ({ matches: false, media: consulta }));
    await TestBed.configureTestingModule({
      imports: [BarraLateral],
      providers: [provideRouter(RUTAS)],
    }).compileComponents();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('agrupa las ocho secciones bajo sus rótulos', async () => {
    const { fixture, html } = crear();
    await fixture.whenStable();

    const rotulos = [...html.querySelectorAll('.grupo .rotulo-seccion')].map((p) => p.textContent?.trim());
    expect(rotulos).toEqual(['Principal', 'Tu actividad', 'Transparencia']);

    const enlaces = [...html.querySelectorAll('nav a.item')].map((a) => a.getAttribute('data-testid'));
    expect(enlaces).toEqual([
      'nav-inicio',
      'nav-explorar',
      'nav-comparar',
      'nav-nia',
      'nav-perfil',
      'nav-historial',
      'nav-panorama',
      'nav-como-funciona',
    ]);
  });

  it('marca con aria-current la sección abierta', async () => {
    const { fixture, html } = crear();
    await TestBed.inject(Router).navigateByUrl('/perfil');
    await fixture.whenStable();

    expect(html.querySelector('[data-testid="nav-perfil"]')?.getAttribute('aria-current')).toBe('page');
    expect(html.querySelector('[data-testid="nav-inicio"]')?.getAttribute('aria-current')).toBeNull();
    expect(html.querySelector('[data-testid="nav-explorar"]')?.getAttribute('aria-current')).toBeNull();
  });

  it('encoger la barra lo dice en aria-expanded y solo entonces hay title', async () => {
    const { fixture, html } = crear();
    await fixture.whenStable();
    const boton = html.querySelector<HTMLButtonElement>('[data-testid="colapsar-barra"]')!;
    const explorar = html.querySelector('[data-testid="nav-explorar"]')!;

    expect(boton.getAttribute('aria-expanded')).toBe('true');
    expect(boton.getAttribute('aria-label')).toBe('Encoger la barra lateral');
    expect(explorar.getAttribute('title')).toBeNull();

    boton.click();
    await fixture.whenStable();

    expect(TestBed.inject(BarraStore).expandida()).toBe(false);
    expect(boton.getAttribute('aria-expanded')).toBe('false');
    expect(boton.getAttribute('aria-label')).toBe('Ampliar la barra lateral');
    expect(explorar.getAttribute('title')).toBe('Explorar');
    // El nombre nunca se quita del DOM: encogida se esconde con CSS, no borrándolo.
    expect(explorar.textContent).toContain('Explorar');
  });

  it('el interruptor de tema es un switch que dice si el claro está puesto', async () => {
    const { fixture, html } = crear();
    await fixture.whenStable();
    const interruptor = html.querySelector<HTMLButtonElement>('[data-testid="cambiar-tema"]')!;

    expect(interruptor.getAttribute('role')).toBe('switch');
    expect(interruptor.getAttribute('aria-checked')).toBe('false');
    expect(interruptor.textContent).toContain('Modo claro');

    interruptor.click();
    await fixture.whenStable();

    expect(interruptor.getAttribute('aria-checked')).toBe('true');
    expect(TestBed.inject(TemaStore).tema()).toBe('claro');
    expect(document.documentElement.getAttribute('data-tema')).toBe('claro');
  });

  it('el cajón abierto se lleva el foco y se cierra con Escape o con un enlace', async () => {
    const { fixture, html } = crear();
    const barra = TestBed.inject(BarraStore);
    await fixture.whenStable();

    barra.abrirCajon();
    await fixture.whenStable();
    expect(document.activeElement).toBe(html.querySelector('[data-testid="cerrar-menu"]'));

    html.querySelector('nav')!.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    await fixture.whenStable();
    expect(barra.cajonAbierto()).toBe(false);

    barra.abrirCajon();
    await fixture.whenStable();
    html.querySelector<HTMLAnchorElement>('[data-testid="nav-comparar"]')!.click();
    await fixture.whenStable();
    expect(barra.cajonAbierto()).toBe(false);
  });
});
