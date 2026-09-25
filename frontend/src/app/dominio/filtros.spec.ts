import { filtrarJuegos } from './filtros';
import { juegoDePrueba } from './juego-prueba';

describe('filtrarJuegos', () => {
  const juegos = [
    juegoDePrueba({ appid: 1, nombre: 'DARK SOULS™ III', generos: ['Acción', 'Rol'] }),
    juegoDePrueba({ appid: 2, nombre: 'Half-Life 2', generos: ['Acción'] }),
    juegoDePrueba({ appid: 3, nombre: 'Stardew Valley', generos: ['Indie', 'Rol', 'Simuladores'] }),
  ];

  it('sin filtros devuelve todo', () => {
    expect(filtrarJuegos(juegos, { texto: '', genero: '' })).toHaveLength(3);
  });

  it('busca el texto como subcadena sin distinguir mayúsculas ni espacios de más', () => {
    expect(filtrarJuegos(juegos, { texto: '  dark ', genero: '' }).map((j) => j.appid)).toEqual([1]);
    expect(filtrarJuegos(juegos, { texto: 'LIFE', genero: '' }).map((j) => j.appid)).toEqual([2]);
  });

  it('filtra por género exacto', () => {
    expect(filtrarJuegos(juegos, { texto: '', genero: 'Rol' }).map((j) => j.appid)).toEqual([1, 3]);
  });

  it('combina texto y género', () => {
    expect(filtrarJuegos(juegos, { texto: 'valley', genero: 'Rol' }).map((j) => j.appid)).toEqual([3]);
    expect(filtrarJuegos(juegos, { texto: 'dark', genero: 'Indie' })).toEqual([]);
  });
});
