import { JuegoCatalogo, JuegoPanorama, NivelRiesgo } from '../api/contrato';
import { juegoDePrueba } from './juego-prueba';
import {
  consensoPorBanda,
  gratuitosPorBanda,
  lanzamientosPorAnio,
  mediana,
  motivoPrincipalPorBanda,
  positivosEnBandaAlta,
  precioPorBanda,
  repartoDeBandas,
  riesgoPorGenero,
  senalPorBanda,
  sinCriticaPorBanda,
} from './panorama';

let siguiente = 1;
function juego(banda: NivelRiesgo, cambios: Partial<JuegoCatalogo> = {}): JuegoCatalogo {
  return juegoDePrueba({ appid: siguiente++, banda_riesgo: banda, ...cambios });
}

function fila(appid: number, cambios: Partial<JuegoPanorama> = {}): JuegoPanorama {
  return {
    appid,
    resenas: 100,
    casos_senal: 1,
    prevalencia: 0.01,
    resenas_en_steam: 1000,
    positivas_en_steam: 900,
    consenso: 'Very Positive',
    motivo_principal: 'rendimiento',
    horas_al_recomendar: 20,
    ...cambios,
  };
}

beforeEach(() => {
  siguiente = 1;
});

describe('repartoDeBandas', () => {
  it('cuenta las tres bandas, siempre en el mismo orden', () => {
    const reparto = repartoDeBandas([juego('alto'), juego('bajo'), juego('bajo'), juego('medio')]);
    expect(reparto.map((t) => t.banda)).toEqual(['bajo', 'medio', 'alto']);
    expect(reparto.map((t) => t.cuantos)).toEqual([2, 1, 1]);
    expect(reparto[0].fraccion).toBeCloseTo(0.5);
  });

  it('con el catálogo vacío no divide entre cero', () => {
    expect(repartoDeBandas([]).map((t) => t.fraccion)).toEqual([0, 0, 0]);
  });
});

describe('riesgoPorGenero', () => {
  it('deja fuera los géneros con menos juegos que el mínimo', () => {
    const juegos = [
      ...Array.from({ length: 5 }, () => juego('alto', { generos: ['Acción'] })),
      juego('bajo', { generos: ['Carreras'] }),
    ];
    const filas = riesgoPorGenero(juegos, 5);
    expect(filas.map((f) => f.genero)).toEqual(['Acción']);
    expect(filas[0]).toMatchObject({ total: 5, altos: 5, fraccion: 1 });
  });

  it('ordena por proporción y desempata por cuántos juegos hay', () => {
    const juegos = [
      juego('alto', { generos: ['Rol'] }),
      juego('bajo', { generos: ['Rol'] }),
      juego('alto', { generos: ['Indie'] }),
      juego('bajo', { generos: ['Indie'] }),
      juego('bajo', { generos: ['Indie'] }),
    ];
    const filas = riesgoPorGenero(juegos, 2);
    expect(filas.map((f) => f.genero)).toEqual(['Rol', 'Indie']);
  });
});

describe('mediana y precioPorBanda', () => {
  it('con un número par de valores promedia los dos de en medio', () => {
    expect(mediana([10, 20, 30, 40])).toBe(25);
    expect(mediana([30, 10, 20])).toBe(20);
    expect(mediana([])).toBeNull();
  });

  it('ignora los gratuitos y los de precio desconocido', () => {
    const filas = precioPorBanda([
      juego('bajo', { es_gratis: true, precio_final: null }),
      juego('bajo', { precio_final: 100 }),
      juego('bajo', { precio_final: 300 }),
      juego('medio', { precio_final: null }),
    ]);
    expect(filas[0]).toMatchObject({ banda: 'bajo', mediana: 200, cuantos: 2 });
    expect(filas[1]).toMatchObject({ banda: 'medio', mediana: null, cuantos: 0 });
  });
});

describe('sinCriticaPorBanda y gratuitosPorBanda', () => {
  it('cuentan sobre los juegos de su propia banda', () => {
    const juegos = [
      juego('alto', { metacritic: null, es_gratis: true }),
      juego('alto', { metacritic: 80, es_gratis: false }),
      juego('bajo', { metacritic: 90, es_gratis: false }),
    ];
    const sin = sinCriticaPorBanda(juegos).find((f) => f.banda === 'alto');
    expect(sin).toMatchObject({ total: 2, cuantos: 1, fraccion: 0.5 });
    const gratis = gratuitosPorBanda(juegos).find((f) => f.banda === 'bajo');
    expect(gratis).toMatchObject({ total: 1, cuantos: 0, fraccion: 0 });
  });
});

describe('lanzamientosPorAnio', () => {
  it('saca el año del texto de Steam y ordena de viejo a nuevo', () => {
    const filas = lanzamientosPorAnio([
      juego('bajo', { fecha_lanzamiento: '16 FEB 2023' }),
      juego('bajo', { fecha_lanzamiento: '2 DIC 2020' }),
      juego('bajo', { fecha_lanzamiento: '9 NOV 2023' }),
      juego('bajo', { fecha_lanzamiento: null }),
      juego('bajo', { fecha_lanzamiento: 'Próximamente' }),
    ]);
    expect(filas).toEqual([
      { anio: 2020, cuantos: 1 },
      { anio: 2023, cuantos: 2 },
    ]);
  });
});

describe('senalPorBanda', () => {
  it('suma reseñas y casos de los juegos de cada banda', () => {
    const alto = juego('alto');
    const bajo = juego('bajo');
    const filas = senalPorBanda(
      [alto, bajo],
      new Map([
        [alto.appid, fila(alto.appid, { resenas: 1000, casos_senal: 40 })],
        [bajo.appid, fila(bajo.appid, { resenas: 1000, casos_senal: 10 })],
      ]),
    );
    expect(filas.find((f) => f.banda === 'alto')).toMatchObject({ resenas: 1000, casos: 40, juegos: 1 });
    expect(filas.find((f) => f.banda === 'alto')!.prevalencia).toBeCloseTo(0.04);
    expect(filas.find((f) => f.banda === 'bajo')!.prevalencia).toBeCloseTo(0.01);
  });

  it('un juego sin fila en el panorama no cuenta ni como cero', () => {
    const solo = juego('medio');
    const filas = senalPorBanda([solo], new Map());
    expect(filas.find((f) => f.banda === 'medio')).toMatchObject({ resenas: 0, casos: 0, juegos: 0, prevalencia: 0 });
  });
});

describe('consensoPorBanda y positivosEnBandaAlta', () => {
  it('agrupa las etiquetas de Steam y traduce su nombre', () => {
    const a = juego('alto');
    const b = juego('alto');
    const c = juego('alto');
    const filas = consensoPorBanda(
      [a, b, c],
      new Map([
        [a.appid, fila(a.appid, { consenso: 'Mixed' })],
        [b.appid, fila(b.appid, { consenso: 'Mixed' })],
        [c.appid, fila(c.appid, { consenso: null })],
      ]),
    );
    const alto = filas.find((f) => f.banda === 'alto')!;
    expect(alto.total).toBe(3);
    expect(alto.tajadas).toEqual([
      { etiqueta: 'Variadas', valor: 2, tono: 3 },
      { etiqueta: 'Sin dato', valor: 1, tono: 5 },
    ]);
  });

  it('encuentra los juegos de riesgo alto que Steam tiene por muy positivos', () => {
    const a = juego('alto');
    const b = juego('alto');
    const c = juego('bajo');
    const positivos = positivosEnBandaAlta(
      [a, b, c],
      new Map([
        [a.appid, fila(a.appid, { consenso: 'Overwhelmingly Positive' })],
        [b.appid, fila(b.appid, { consenso: 'Mixed' })],
        [c.appid, fila(c.appid, { consenso: 'Overwhelmingly Positive' })],
      ]),
    );
    expect(positivos.map((j) => j.appid)).toEqual([a.appid]);
  });
});

describe('motivoPrincipalPorBanda', () => {
  it('cuenta juegos y no reseñas, y salta los que no tienen motivo', () => {
    const a = juego('alto');
    const b = juego('alto');
    const c = juego('alto');
    const filas = motivoPrincipalPorBanda(
      [a, b, c],
      new Map([
        [a.appid, fila(a.appid, { motivo_principal: 'rendimiento', resenas: 100000 })],
        [b.appid, fila(b.appid, { motivo_principal: 'bugs' })],
        [c.appid, fila(c.appid, { motivo_principal: null })],
      ]),
    );
    const alto = filas.find((f) => f.banda === 'alto')!;
    expect(alto.conMotivo).toBe(2);
    expect(alto.motivos).toEqual([
      { motivo: 'bugs', juegos: 1 },
      { motivo: 'rendimiento', juegos: 1 },
    ]);
  });
});
