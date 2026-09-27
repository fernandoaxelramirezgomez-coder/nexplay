import { filtrarJuegos, generosDeUrl, generosParaUrl } from './filtros';
import { juegoDePrueba } from './juego-prueba';

describe('filtrarJuegos', () => {
  const juegos = [
    juegoDePrueba({ appid: 1, nombre: 'DARK SOULS™ III', generos: ['Acción', 'Rol'] }),
    juegoDePrueba({ appid: 2, nombre: 'Half-Life 2', generos: ['Acción'] }),
    juegoDePrueba({ appid: 3, nombre: 'Stardew Valley', generos: ['Indie', 'Rol', 'Simuladores'] }),
  ];

  it('sin filtros devuelve todo', () => {
    expect(filtrarJuegos(juegos, { texto: '', generos: [] })).toHaveLength(3);
  });

  it('busca el texto como subcadena sin distinguir mayúsculas ni espacios de más', () => {
    expect(filtrarJuegos(juegos, { texto: '  dark ', generos: [] }).map((j) => j.appid)).toEqual([1]);
    expect(filtrarJuegos(juegos, { texto: 'LIFE', generos: [] }).map((j) => j.appid)).toEqual([2]);
  });

  it('filtra por género exacto', () => {
    expect(filtrarJuegos(juegos, { texto: '', generos: ['Rol'] }).map((j) => j.appid)).toEqual([1, 3]);
  });

  it('con varios géneros basta con tener uno', () => {
    expect(filtrarJuegos(juegos, { texto: '', generos: ['Indie', 'Acción'] }).map((j) => j.appid)).toEqual([1, 2, 3]);
    expect(filtrarJuegos(juegos, { texto: '', generos: ['Simuladores', 'Rol'] }).map((j) => j.appid)).toEqual([1, 3]);
  });

  it('los géneros van y vuelven de la URL separados por coma, sin repetidos', () => {
    expect(generosDeUrl('Acción,Free to Play, Acción')).toEqual(['Acción', 'Free to Play']);
    expect(generosDeUrl(undefined)).toEqual([]);
    expect(generosParaUrl(['Acción', 'Rol'])).toBe('Acción,Rol');
    expect(generosParaUrl([])).toBeNull();
  });

  it('combina texto y género', () => {
    expect(filtrarJuegos(juegos, { texto: 'valley', generos: ['Rol'] }).map((j) => j.appid)).toEqual([3]);
    expect(filtrarJuegos(juegos, { texto: 'dark', generos: ['Indie'] })).toEqual([]);
  });
});
