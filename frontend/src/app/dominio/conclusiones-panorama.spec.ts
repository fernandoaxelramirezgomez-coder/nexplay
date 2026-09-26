import { JuegoCatalogo, JuegoPanorama, NivelRiesgo } from '../api/contrato';
import {
  conclusionAnios,
  conclusionConsenso,
  conclusionGeneros,
  conclusionGratuitos,
  conclusionMotivoPorJuego,
  conclusionMotivos,
  conclusionPlaytime,
  conclusionPrecio,
  conclusionReparto,
  conclusionSenal,
  conclusionSinCritica,
} from './conclusiones-panorama';
import { juegoDePrueba } from './juego-prueba';
import { motivoPrincipalPorBanda } from './panorama';

let siguiente = 1;

/** Las conclusiones usan espacio duro antes de «%»; aquí se leen con espacio normal. */
function texto(frase: string): string {
  return frase.replaceAll('\u00a0', ' ');
}

function juego(banda: NivelRiesgo, cambios: Partial<JuegoCatalogo> = {}): JuegoCatalogo {
  return juegoDePrueba({ appid: siguiente++, banda_riesgo: banda, ...cambios });
}

function varios(cuantos: number, banda: NivelRiesgo, cambios: Partial<JuegoCatalogo> = {}): JuegoCatalogo[] {
  return Array.from({ length: cuantos }, () => juego(banda, cambios));
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

function mapa(filas: JuegoPanorama[]): Map<number, JuegoPanorama> {
  return new Map(filas.map((f) => [f.appid, f]));
}

describe('conclusiones de Panorama', () => {
  it('reparto: tercios, un nivel que pesa más y un corte de un solo nivel', () => {
    const catalogo = [...varios(43, 'bajo'), ...varios(37, 'medio'), ...varios(43, 'alto')];
    expect(texto(conclusionReparto(catalogo))).toBe('Tres tercios: 43 en bajo, 37 en medio y 43 en alto.');
    expect(texto(conclusionReparto([...varios(2, 'bajo'), ...varios(8, 'alto')]))).toBe(
      'Pesa más el riesgo alto: 2 en bajo, ninguno en medio y 8 en alto.',
    );
    expect(texto(conclusionReparto(varios(43, 'alto')))).toBe('Los 43 juegos del corte están en riesgo alto.');
    expect(texto(conclusionReparto(varios(1, 'medio')))).toBe('El único juego del corte está en riesgo medio.');
  });

  it('géneros: nombra todos los empatados arriba y abajo, con el porcentaje que se lee', () => {
    const juegos = [
      ...varios(6, 'alto', { generos: ['Casual'] }),
      ...varios(4, 'bajo', { generos: ['Casual'] }),
      ...varios(3, 'alto', { generos: ['Multijugador masivo'] }),
      ...varios(2, 'bajo', { generos: ['Multijugador masivo'] }),
      ...varios(1, 'alto', { generos: ['Estrategia'] }),
      ...varios(5, 'bajo', { generos: ['Estrategia'] }),
    ];
    expect(texto(conclusionGeneros(juegos, 5))).toBe(
      'Casual y Multijugador masivo tienen más juegos en riesgo alto (60 %); Estrategia, menos (17 %).',
    );
    expect(texto(conclusionGeneros(varios(3, 'alto', { generos: ['Rol'] }), 5))).toBe(
      'Ningún género llega a 5 juegos en este corte.',
    );
  });

  it('precio: la razón en palabras, sin redondear hacia arriba', () => {
    const juegos = [
      juego('bajo', { precio_final: 179.49 }),
      juego('medio', { precio_final: 359 }),
      juego('alto', { precio_final: 579.99 }),
    ];
    expect(texto(conclusionPrecio(juegos))).toBe('En riesgo alto la mediana es $579.99, más del triple de la de bajo ($179.49).');
    expect(texto(conclusionPrecio([juego('bajo', { precio_final: 200 }), juego('alto', { precio_final: 400 })]))).toBe(
      'En riesgo alto la mediana es $400.00, el doble de la de bajo ($200.00).',
    );
    expect(texto(conclusionPrecio([juego('medio', { precio_final: 359 })]))).toBe('La mediana es $359.00 en riesgo medio.');
    expect(texto(conclusionPrecio([juego('alto', { es_gratis: true, precio_final: null })]))).toBe(
      'Ningún juego de pago con precio conocido en este corte.',
    );
  });

  it('sin Metacritic: los sin nota y la señal entre los que sí tienen, subiendo por nivel', () => {
    const bajo = juego('bajo', { metacritic: 80 });
    const medio = juego('medio', { metacritic: 75 });
    const altoCon = juego('alto', { metacritic: 70 });
    const sinNota = varios(2, 'alto', { metacritic: null });
    const porAppid = mapa([
      fila(bajo.appid, { resenas: 10000, casos_senal: 102 }),
      fila(medio.appid, { resenas: 10000, casos_senal: 131 }),
      fila(altoCon.appid, { resenas: 10000, casos_senal: 252 }),
      ...sinNota.map((j) => fila(j.appid, { resenas: 100, casos_senal: 50 })),
    ]);
    expect(texto(conclusionSinCritica([bajo, medio, altoCon, ...sinNota], porAppid))).toBe(
      'Los 2 sin nota están en riesgo alto; entre los 3 con nota, la señal sigue subiendo por nivel: 1.02 → 1.31 → 2.52 %.',
    );
  });

  it('sin Metacritic: si en el corte no sube, no dice que sube', () => {
    const bajo = juego('bajo', { metacritic: 80 });
    const medio = juego('medio', { metacritic: 75 });
    const alto = juego('alto', { metacritic: 70 });
    const porAppid = mapa([
      fila(bajo.appid, { resenas: 1000, casos_senal: 30 }),
      fila(medio.appid, { resenas: 1000, casos_senal: 10 }),
      fila(alto.appid, { resenas: 1000, casos_senal: 20 }),
    ]);
    expect(texto(conclusionSinCritica([bajo, medio, alto], porAppid))).toBe(
      'Entre los 3 con nota, la señal por nivel es: 3.00 → 1.00 → 2.00 %.',
    );
    const soloAlto = varios(2, 'alto', { metacritic: null });
    expect(conclusionSinCritica(soloAlto, mapa(soloAlto.map((j) => fila(j.appid))))).toBe(
      'Los 2 sin nota están en riesgo alto.',
    );
  });

  it('gratuitos: cuenta por nivel y dice "ninguno"', () => {
    const juegos = [
      ...varios(4, 'bajo', { es_gratis: true }),
      ...varios(3, 'medio'),
      ...varios(3, 'alto', { es_gratis: true }),
    ];
    expect(texto(conclusionGratuitos(juegos))).toBe('Hay 7 gratuitos: 4 en bajo, ninguno en medio y 3 en alto.');
    expect(texto(conclusionGratuitos(varios(2, 'bajo')))).toBe('Ningún juego gratuito en este corte.');
  });

  it('años: los últimos diez desde el más reciente y el año con más', () => {
    const juegos = [
      ...varios(2, 'bajo', { fecha_lanzamiento: '1 ENE 2004' }),
      ...varios(3, 'bajo', { fecha_lanzamiento: '5 MAR 2023' }),
      ...varios(1, 'bajo', { fecha_lanzamiento: '9 SEP 2026' }),
    ];
    expect(texto(conclusionAnios(juegos))).toBe('4 de los 6 salieron de 2016 en adelante; 2023 es el año con más (3).');
    expect(texto(conclusionAnios(varios(2, 'alto', { fecha_lanzamiento: '16 FEB 2023' })))).toBe('Todos salieron en 2023.');
  });

  it('horas al reseñar: primer y último tramo', () => {
    expect(
      texto(conclusionPlaytime([
        { tramo: 'Menos de 2 h', cuantas: 7874, fraccion: 0.0427 },
        { tramo: '2 a 10 h', cuantas: 1, fraccion: 0.2194 },
        { tramo: 'Más de 50 h', cuantas: 1, fraccion: 0.3768 },
      ])),
    ).toBe('Solo el 4 % se escribió con menos de 2 h jugadas; el 38 %, con más de 50 h.');
  });

  it('señal por nivel: alto contra bajo, o lo que haya en el corte', () => {
    const bajo = juego('bajo');
    const alto = juego('alto');
    const porAppid = mapa([
      fila(bajo.appid, { resenas: 10000, casos_senal: 102 }),
      fila(alto.appid, { resenas: 10000, casos_senal: 429 }),
    ]);
    expect(texto(conclusionSenal([bajo, alto], porAppid))).toBe(
      'En riesgo alto, el 4.29 % de las reseñas trae señal; en bajo, el 1.02 %.',
    );
    expect(texto(conclusionSenal([alto], porAppid))).toBe('Con señal: el 4.29 % de las reseñas en riesgo alto.');
  });

  it('Steam: cuántos de riesgo alto tienen reseñas muy positivas', () => {
    const altos = varios(4, 'alto');
    const porAppid = mapa([
      fila(altos[0].appid, { consenso: 'Overwhelmingly Positive' }),
      fila(altos[1].appid, { consenso: 'Very Positive' }),
      fila(altos[2].appid, { consenso: 'Mixed' }),
      fila(altos[3].appid, { consenso: 'Mostly Positive' }),
    ]);
    expect(texto(conclusionConsenso(altos, porAppid))).toBe(
      '2 de los 4 juegos en riesgo alto tienen reseñas muy o extremadamente positivas en Steam.',
    );
    expect(texto(conclusionConsenso(varios(2, 'bajo'), porAppid))).toContain('No hay juegos en riesgo alto');
  });

  it('motivos: el primero y el segundo, con su porcentaje', () => {
    expect(
      texto(conclusionMotivos([
        { motivo: 'rendimiento', frecuencia: 0.4085 },
        { motivo: 'bugs', frecuencia: 0.2716 },
        { motivo: 'contenido', frecuencia: 0.2284 },
      ])),
    ).toBe('Rendimiento es lo más mencionado (41 %), seguido de bugs (27 %).');
    expect(texto(conclusionMotivos([]))).toBe('Ninguna reseña con señal nombra una de las seis categorías.');
  });

  it('motivo por juego: el que encabeza todos los niveles y sus empates', () => {
    const juegos = [
      ...varios(2, 'bajo'),
      juego('bajo', { appid: 900 }),
      juego('medio', { appid: 901 }),
      juego('medio', { appid: 902 }),
      juego('alto', { appid: 903 }),
      juego('alto', { appid: 904 }),
    ];
    const porAppid = mapa([
      ...juegos.map((j) => fila(j.appid, { motivo_principal: 'rendimiento' })),
      fila(900, { motivo_principal: 'bugs' }),
      fila(902, { motivo_principal: 'controles' }),
      fila(904, { motivo_principal: 'bugs' }),
    ]);
    expect(texto(conclusionMotivoPorJuego(motivoPrincipalPorBanda(juegos, porAppid)))).toBe(
      'Rendimiento encabeza los tres niveles; en medio empata con controles y en alto con bugs.',
    );
  });

  it('motivo por juego: sin uno en común, lo dice nivel por nivel', () => {
    const bajo = juego('bajo');
    const alto = juego('alto');
    const porAppid = mapa([fila(bajo.appid, { motivo_principal: 'controles' }), fila(alto.appid, { motivo_principal: 'bugs' })]);
    expect(texto(conclusionMotivoPorJuego(motivoPrincipalPorBanda([bajo, alto], porAppid)))).toBe(
      'El motivo que más juegos encabeza: controles en bajo y bugs en alto.',
    );
  });
});
