import { porcentaje, textoMetacritic, textoPrecio } from './formato';

describe('formato', () => {
  it('precio: gratis, conocido y desconocido', () => {
    expect(textoPrecio({ es_gratis: true, precio_final: null, moneda: null })).toBe('Gratis');
    expect(textoPrecio({ es_gratis: false, precio_final: 1599, moneda: 'MXN' })).toBe('$1,599.00 MXN');
    expect(textoPrecio({ es_gratis: false, precio_final: null, moneda: null })).toBe('Precio no disponible');
  });

  it('Metacritic con y sin nota', () => {
    expect(textoMetacritic(96)).toBe('Metacritic 96');
    expect(textoMetacritic(null)).toBe('Sin nota de Metacritic');
  });

  it('porcentaje entero', () => {
    expect(porcentaje(0.86)).toBe('86%');
    expect(porcentaje(0.07)).toBe('7%');
    expect(porcentaje(0.6554)).toBe('66%');
  });
});
