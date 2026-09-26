import { advertenciaNexplay, advertenciaSinCritica, lineaCritica, sentimientoSteam } from './critica';

describe('critica', () => {
  const wukong = { resenas_en_steam: 87051, positivas_en_steam: 81659, consenso: 'Very Positive' };

  it('saca el porcentaje positivo de Steam y su resumen en español', () => {
    expect(sentimientoSteam(wukong)).toEqual({ porcentaje: 94, total: 87051, etiqueta: 'Muy positivas' });
    expect(sentimientoSteam({ ...wukong, consenso: 'Mixed' })?.etiqueta).toBe('Variadas');
  });

  it('sin datos de Steam no inventa un porcentaje', () => {
    expect(sentimientoSteam(undefined)).toBeNull();
    expect(sentimientoSteam({ resenas_en_steam: null, positivas_en_steam: null, consenso: null })).toBeNull();
    expect(sentimientoSteam({ resenas_en_steam: 0, positivas_en_steam: 0, consenso: null })).toBeNull();
  });

  it('con Metacritic y Steam muestra los dos; sin Metacritic lo dice', () => {
    const steam = sentimientoSteam(wukong);
    expect(lineaCritica({ metacritic: 82 }, steam)).toBe('Metacritic 82 · Steam 94 % positivas (87,051 reseñas)');
    expect(lineaCritica({ metacritic: null }, steam)).toBe(
      'Sin crítica especializada · Steam 94 % positivas (87,051 reseñas)',
    );
    expect(lineaCritica({ metacritic: null }, null)).toBe('Sin crítica especializada');
  });

  it('la advertencia dice de dónde viene lo que se muestra', () => {
    expect(advertenciaSinCritica(87051)).toBe('Sin crítica especializada; esto viene de 87,051 reseñas de jugadores.');
    expect(advertenciaNexplay(1, 2)).toBe(
      'Sin crítica especializada; esto viene de 1 valoración y 2 comentarios en NexPlay.',
    );
    expect(advertenciaNexplay(0, 1)).toBe('Sin crítica especializada; esto viene de 1 comentario en NexPlay.');
  });
});
