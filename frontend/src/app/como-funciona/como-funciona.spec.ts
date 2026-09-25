import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { ComoFunciona, PASOS } from './como-funciona';

/** Mismo criterio que reaccion-nia.spec.ts: describir, nunca prometer ni aconsejar la compra. */
const PROHIBIDO = ['confiable', 'fiable', 'confianza', 'seguro', 'buena compra', 'mala compra', 'abandono'];

describe('ComoFunciona', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ComoFunciona],
      providers: [provideRouter([])],
    }).compileComponents();
  });

  it('muestra los cuatro pasos, en orden', async () => {
    const fixture = TestBed.createComponent(ComoFunciona);
    await fixture.whenStable();
    const html = fixture.nativeElement as HTMLElement;
    const titulos = [...html.querySelectorAll('[data-testid="paso"] h2')].map((h) => h.textContent?.trim());
    expect(titulos).toEqual([
      'Buscar un juego',
      'Ver su banda y sus motivos',
      'Crear tu perfil (opcional)',
      'Preguntarle a Nia',
    ]);
  });

  it('la metodología vive aquí, con el vocabulario del proyecto', async () => {
    const fixture = TestBed.createComponent(ComoFunciona);
    await fixture.whenStable();
    const texto = (fixture.nativeElement as HTMLElement).querySelector('[data-testid="metodologia"]')?.textContent;
    expect(texto).toContain('arrepentimiento temprano');
    expect(texto).toContain('120 minutos');
    expect(texto).toContain('GroupKFold');
    expect(texto).toContain('PR-AUC');
  });

  it('los pasos no usan fórmulas prohibidas', () => {
    for (const paso of PASOS) {
      const todo = `${paso.titulo} ${paso.texto}`.toLowerCase();
      for (const frase of PROHIBIDO) {
        expect(todo, `"${paso.titulo}" dice "${frase}"`).not.toContain(frase);
      }
    }
  });
});
