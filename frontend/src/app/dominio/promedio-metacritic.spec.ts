import { juegoDePrueba } from './juego-prueba';
import { promedioMetacritic } from './promedio-metacritic';

describe('promedioMetacritic', () => {
  it('promedia solo los juegos con nota', () => {
    const juegos = [
      juegoDePrueba({ appid: 1, metacritic: 90 }),
      juegoDePrueba({ appid: 2, metacritic: 80 }),
      juegoDePrueba({ appid: 3, metacritic: null }),
    ];
    expect(promedioMetacritic(juegos)).toBe(85);
  });

  it('devuelve null si ningún juego tiene nota', () => {
    expect(promedioMetacritic([juegoDePrueba({ metacritic: null })])).toBeNull();
    expect(promedioMetacritic([])).toBeNull();
  });
});
