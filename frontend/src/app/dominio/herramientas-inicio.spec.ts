import { DIFERENCIA, HERRAMIENTAS, destacadaDelInicio } from './herramientas-inicio';

function textos(): string[] {
  const destacada = destacadaDelInicio(123);
  return [
    DIFERENCIA,
    destacada.titulo,
    destacada.texto,
    destacada.aclaracion,
    destacada.accion,
    ...HERRAMIENTAS.flatMap((h) => [h.titulo, h.linea]),
  ];
}

describe('«¿Por qué elegir NexPlay?» del Inicio', () => {
  it('la destacada dice que es una señal comparativa y no una predicción', () => {
    const { aclaracion } = destacadaDelInicio(123);
    expect(aclaracion).toContain('señal comparativa');
    expect(aclaracion).toContain('no una predicción');
  });

  it('la acción lleva el número del catálogo y sin catálogo no lo inventa', () => {
    expect(destacadaDelInicio(123).accion).toBe('Explorar los 123 juegos');
    expect(destacadaDelInicio(0).accion).not.toMatch(/\d/);
  });

  it('cuatro herramientas, cada una a su vista', () => {
    expect(HERRAMIENTAS.map((h) => h.ruta)).toEqual(['/juego/1938010', '/nia', '/comparar', '/perfil']);
  });

  it('ningún tono es de riesgo y el perfil no mueve el riesgo', () => {
    for (const herramienta of HERRAMIENTAS) {
      expect(['explorar', 'nia', 'comparar', 'perfil']).toContain(herramienta.tono);
    }
    expect(HERRAMIENTAS.find((h) => h.id === 'perfil')!.linea).toContain('el riesgo no cambia');
  });

  it('habla con el vocabulario del proyecto', () => {
    for (const texto of textos()) {
      expect(texto.toLowerCase(), texto).not.toMatch(/abandono|banda/);
    }
  });
});
