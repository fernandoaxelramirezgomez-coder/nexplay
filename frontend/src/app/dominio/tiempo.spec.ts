import { hace } from './tiempo';

const AHORA = new Date('2026-09-20T12:00:00Z');
const haceSegundos = (segundos: number) => new Date(AHORA.getTime() - segundos * 1000).toISOString();

describe('hace', () => {
  it('menos de un minuto', () => {
    expect(hace(haceSegundos(20), AHORA)).toBe('hace un momento');
  });

  it('minutos y horas, con singular y plural', () => {
    expect(hace(haceSegundos(60), AHORA)).toBe('hace 1 minuto');
    expect(hace(haceSegundos(60 * 5), AHORA)).toBe('hace 5 minutos');
    expect(hace(haceSegundos(3600), AHORA)).toBe('hace 1 hora');
    expect(hace(haceSegundos(3600 * 5), AHORA)).toBe('hace 5 horas');
  });

  it('días', () => {
    expect(hace(haceSegundos(86400), AHORA)).toBe('hace 1 día');
    expect(hace(haceSegundos(86400 * 3), AHORA)).toBe('hace 3 días');
  });

  it('más de un mes muestra la fecha', () => {
    expect(hace(haceSegundos(86400 * 40), AHORA)).toMatch(/2026/);
  });

  it('una fecha futura no dice "hace -1"', () => {
    expect(hace(haceSegundos(-120), AHORA)).toBe('hace un momento');
  });

  it('una fecha inválida no rompe', () => {
    expect(hace('no es fecha', AHORA)).toBe('');
  });
});
