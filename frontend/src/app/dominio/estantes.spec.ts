import { agruparEnEstantes } from './estantes';
import { juegoDePrueba } from './juego-prueba';

describe('agruparEnEstantes', () => {
  const juegos = [
    juegoDePrueba({ appid: 1, banda_riesgo: 'bajo', riesgo: 0.2 }),
    juegoDePrueba({ appid: 2, banda_riesgo: 'bajo', riesgo: 0.08 }),
    juegoDePrueba({ appid: 3, banda_riesgo: 'medio', riesgo: 0.3 }),
    juegoDePrueba({ appid: 4, banda_riesgo: 'medio', riesgo: 0.4 }),
    juegoDePrueba({ appid: 5, banda_riesgo: 'alto', riesgo: 0.5 }),
    juegoDePrueba({ appid: 6, banda_riesgo: 'alto', riesgo: 0.9 }),
  ];

  it('devuelve los estantes en orden bajo, medio, alto', () => {
    expect(agruparEnEstantes(juegos).map((e) => e.banda)).toEqual(['bajo', 'medio', 'alto']);
  });

  it('ordena "bajo" ascendente y "medio" y "alto" descendente por score', () => {
    const [bajo, medio, alto] = agruparEnEstantes(juegos);
    expect(bajo.juegos.map((j) => j.appid)).toEqual([2, 1]);
    expect(medio.juegos.map((j) => j.appid)).toEqual([4, 3]);
    expect(alto.juegos.map((j) => j.appid)).toEqual([6, 5]);
  });

  it('conserva el orden de entrada ante empates (igual que sorted de Python)', () => {
    const empatados = [
      juegoDePrueba({ appid: 10, banda_riesgo: 'medio', riesgo: 0.3 }),
      juegoDePrueba({ appid: 11, banda_riesgo: 'medio', riesgo: 0.3 }),
    ];
    expect(agruparEnEstantes(empatados)[1].juegos.map((j) => j.appid)).toEqual([10, 11]);
  });

  it('deja estantes vacíos en vez de omitirlos', () => {
    const soloAltos = [juegoDePrueba({ banda_riesgo: 'alto' })];
    expect(agruparEnEstantes(soloAltos).map((e) => e.juegos.length)).toEqual([0, 0, 1]);
  });

  it('no modifica la lista de entrada', () => {
    const copia = [...juegos];
    agruparEnEstantes(juegos);
    expect(juegos).toEqual(copia);
  });
});
