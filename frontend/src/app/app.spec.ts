import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { App } from './app';
import { BarraStore } from './estado/barra-store';

describe('App (shell)', () => {
  beforeEach(async () => {
    localStorage.clear();
    document.documentElement.removeAttribute('data-tema');
    vi.stubGlobal('matchMedia', (consulta: string) => ({ matches: false, media: consulta }));
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideRouter([])],
    }).compileComponents();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('la navegación vive en la barra lateral, con las ocho secciones', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const html = fixture.nativeElement as HTMLElement;
    const enlaces = [...html.querySelectorAll('app-barra-lateral nav a.item')].map((a) => a.textContent?.trim());
    expect(enlaces).toEqual([
      'Inicio',
      'Explorar',
      'Comparar',
      'Nia',
      'Tu perfil',
      'Historial',
      'Panorama',
      'Cómo funciona',
    ]);
  });

  it('el pie enlaza a la metodología en vez de repetirla', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const html = fixture.nativeElement as HTMLElement;
    const enlace = html.querySelector('footer [data-testid="enlace-metodologia"]');
    expect(enlace?.getAttribute('href')).toContain('/como-funciona');
    expect(html.querySelector('footer [data-testid="metodologia"]')).toBeNull();
  });

  it('con el cajón abierto la página queda inerte y el velo la cierra', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const html = fixture.nativeElement as HTMLElement;
    const barra = TestBed.inject(BarraStore);
    const pagina = html.querySelector('[data-testid="shell"]')!;
    const hamburguesa = html.querySelector<HTMLButtonElement>('[data-testid="abrir-menu"]')!;

    expect(pagina.hasAttribute('inert')).toBe(false);
    expect(hamburguesa.getAttribute('aria-controls')).toBe('riel');

    hamburguesa.click();
    await fixture.whenStable();
    expect(barra.cajonAbierto()).toBe(true);
    expect(pagina.hasAttribute('inert')).toBe(true);
    expect(hamburguesa.getAttribute('aria-expanded')).toBe('true');

    html.querySelector<HTMLButtonElement>('[data-testid="velo-menu"]')!.click();
    await fixture.whenStable();
    expect(barra.cajonAbierto()).toBe(false);
    expect(pagina.hasAttribute('inert')).toBe(false);
    // El foco vuelve a donde estaba: al botón que abrió el cajón.
    expect(document.activeElement).toBe(hamburguesa);
  });
});
