import { mesAnio, porcentaje, rangoDeFechas, textoMetacritic, textoPrecio } from './formato';

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

  it('mes y año, sin pasar por la zona horaria', () => {
    expect(mesAnio('2023-04-08')).toBe('abr 2023');
    expect(mesAnio('2026-01-01T00:30:00+00:00')).toBe('ene 2026');
    expect(mesAnio('')).toBe('');
  });

  it('rango de descarga sin repetir mes ni año', () => {
    expect(rangoDeFechas('2026-09-14', '2026-09-21')).toBe('del 14 al 21 sep 2026');
    expect(rangoDeFechas('2026-08-30', '2026-09-02')).toBe('del 30 ago al 2 sep 2026');
    expect(rangoDeFechas('2025-12-20', '2026-01-03')).toBe('del 20 dic 2025 al 3 ene 2026');
    expect(rangoDeFechas('2026-09-14', '2026-09-14')).toBe('el 14 sep 2026');
    expect(rangoDeFechas('', '')).toBe('');
  });
});
