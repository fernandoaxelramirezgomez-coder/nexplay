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

  it('muestra la navegación a Explorar, Comparar y Tu perfil', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const html = fixture.nativeElement as HTMLElement;
    const enlaces = [...html.querySelectorAll('nav a')].map((a) => a.textContent?.trim());
    expect(enlaces).toEqual(['Explorar', 'Comparar', 'Tu perfil']);
  });

  it('incluye la metodología en el pie', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const html = fixture.nativeElement as HTMLElement;
    expect(html.querySelector('[data-testid="metodologia"]')?.textContent).toContain('arrepentimiento temprano');
  });
});
