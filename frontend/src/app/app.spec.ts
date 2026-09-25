import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { App } from './app';

describe('App (shell)', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
      providers: [provideRouter([])],
    }).compileComponents();
  });

  it('muestra la navegación a Explorar, Comparar, Tu perfil y Cómo funciona', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const html = fixture.nativeElement as HTMLElement;
    const enlaces = [...html.querySelectorAll('nav a')].map((a) => a.textContent?.trim());
    expect(enlaces).toEqual(['Explorar', 'Comparar', 'Tu perfil', 'Cómo funciona']);
  });

  it('el pie enlaza a la metodología en vez de repetirla', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const html = fixture.nativeElement as HTMLElement;
    const enlace = html.querySelector('footer [data-testid="enlace-metodologia"]');
    expect(enlace?.getAttribute('href')).toContain('/como-funciona');
    expect(html.querySelector('footer [data-testid="metodologia"]')).toBeNull();
  });
});
