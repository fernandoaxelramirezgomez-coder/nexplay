import { TestBed } from '@angular/core/testing';

import { ExplicacionJuego } from '../api/contrato';
import { MotivosBarras } from './motivos-barras';

function explicacion(cambios: Partial<ExplicacionJuego> = {}): ExplicacionJuego {
  return {
    appid: 1,
    nombre: 'Juego',
    motivos: [{ motivo: 'contenido', frecuencia: 1 }],
    n_casos: 5,
    pct_clasificados: 0.2,
    ...cambios,
  };
}

function montar(datos: ExplicacionJuego | undefined) {
  const fixture = TestBed.createComponent(MotivosBarras);
  fixture.componentRef.setInput('explicacion', datos);
  fixture.detectChanges();
  return fixture;
}

function texto(fixture: ReturnType<typeof montar>, id: string): string | null {
  const elemento = fixture.nativeElement.querySelector(`[data-testid="${id}"]`);
  return elemento && elemento.textContent.replace(/\s+/g, ' ').trim();
}

describe('MotivosBarras', () => {
  /** Hades: 5 casos, 20% clasificados. El "contenido 100%" salía de una sola reseña, y
   * una barra al 100% dibujada con esa una dice "todas" de una muestra de uno. */
  it('con una sola reseña clasificada no dibuja barras, nombra el motivo', () => {
    const fixture = montar(explicacion());
    expect(fixture.nativeElement.querySelector('.barra')).toBeNull();
    expect(texto(fixture, 'motivos-escueto')).toBe('Solo 1 reseña menciona un motivo: contenido.');
  });

  it('con dos clasificadas los nombra en plural y sin porcentajes', () => {
    const fixture = montar(
      explicacion({
        motivos: [
          { motivo: 'contenido', frecuencia: 1 },
          { motivo: 'bugs', frecuencia: 0.5 },
        ],
        n_casos: 10,
        pct_clasificados: 0.2,
      }),
    );
    expect(texto(fixture, 'motivos-escueto')).toBe('Solo 2 reseñas mencionan un motivo: contenido y bugs.');
    expect(fixture.nativeElement.textContent).not.toContain('%');
  });

  it('con tres o más clasificadas vuelven las barras, con su n', () => {
    const fixture = montar(explicacion({ n_casos: 15, pct_clasificados: 0.2 }));
    expect(fixture.nativeElement.querySelector('.barra')).not.toBeNull();
    expect(texto(fixture, 'motivos-escueto')).toBeNull();
    expect(texto(fixture, 'motivos-cuantas')).toContain('Sobre 3 reseñas clasificadas');
  });

  it('sin motivos lo dice con el número de casos, no con barras vacías', () => {
    const fixture = montar(explicacion({ motivos: [], n_casos: 2, pct_clasificados: 0 }));
    expect(fixture.nativeElement.textContent).toContain('muy pocas reseñas');
    expect(fixture.nativeElement.querySelector('.barra')).toBeNull();
  });
});
