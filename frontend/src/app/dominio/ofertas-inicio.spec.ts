import { ofertasDelInicio } from './ofertas-inicio';

describe('ofertas del Inicio', () => {
  it('cuatro cuadritos de dos palabras como máximo, con el número del catálogo', () => {
    const ofertas = ofertasDelInicio(123);
    expect(ofertas.map((o) => o.texto)).toEqual(['Gratis', 'Sin registro', '<1 minuto', '123 juegos']);
    for (const oferta of ofertas) {
      expect(oferta.texto.split(' ').length, oferta.texto).toBeLessThanOrEqual(2);
    }
  });

  it('el símbolo se lee en palabras', () => {
    const minuto = ofertasDelInicio(123).find((o) => o.id === 'un-minuto')!;
    expect(minuto.lectura).toBe('Menos de un minuto');
  });

  it('sin catálogo no inventa cuántos juegos hay', () => {
    expect(ofertasDelInicio(0).map((o) => o.id)).toEqual(['gratis', 'sin-registro', 'un-minuto']);
  });

  it('ningún cuadrito usa un color del riesgo ni promete confidencialidad', () => {
    for (const oferta of ofertasDelInicio(123)) {
      expect(['inicio', 'nia', 'perfil', 'neutro']).toContain(oferta.tono);
      expect(oferta.texto.toLowerCase()).not.toContain('confidencial');
    }
  });
});
