import { juegoDePrueba } from './juego-prueba';
import { elegirTrailers } from './trailers';

describe('elegirTrailers', () => {
  const video = 'https://video.example/trailer.m3u8';
  const juegos = [
    juegoDePrueba({ appid: 1, banda_riesgo: 'alto', video_url: video }),
    juegoDePrueba({ appid: 2, banda_riesgo: 'bajo', video_url: video }),
    juegoDePrueba({ appid: 3, banda_riesgo: 'bajo', video_url: video }),
    juegoDePrueba({ appid: 4, banda_riesgo: 'bajo', video_url: video }),
    juegoDePrueba({ appid: 5, banda_riesgo: 'medio', video_url: null }),
    juegoDePrueba({ appid: 6, banda_riesgo: 'medio', video_url: video }),
    juegoDePrueba({ appid: 7, banda_riesgo: 'alto', video_url: video }),
  ];
  const resenas = new Map([
    [1, { resenas_en_steam: 10 }],
    [2, { resenas_en_steam: 500 }],
    [3, { resenas_en_steam: 900 }],
    [4, { resenas_en_steam: 100 }],
    [5, { resenas_en_steam: 99999 }],
    [6, { resenas_en_steam: 50 }],
    [7, { resenas_en_steam: null }],
  ]);

  it('toma por nivel, en orden bajo, medio, alto, los más reseñados en Steam', () => {
    expect(elegirTrailers(juegos, resenas).map((j) => j.appid)).toEqual([3, 2, 6, 1, 7]);
  });

  it('deja fuera a los juegos sin tráiler aunque sean los más reseñados', () => {
    expect(elegirTrailers(juegos, resenas).some((j) => j.appid === 5)).toBe(false);
  });

  it('sin la cifra de reseñas, el juego va al final de su nivel', () => {
    const alto = elegirTrailers(juegos, resenas).filter((j) => j.banda_riesgo === 'alto');
    expect(alto.map((j) => j.appid)).toEqual([1, 7]);
  });
});
