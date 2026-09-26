import { juegoDePrueba } from './juego-prueba';
import {
  COMPRAS,
  FRICCION,
  GASTO,
  HORAS,
  VALORES_VACIOS,
  ValoresPerfil,
  estaCompleto,
  formularioDesde,
  juegosHastaTope,
  lineaPlataforma,
  preguntasPendientes,
  respuestasPerfil,
} from './opciones-perfil';

const DECLARADO: ValoresPerfil = { compras: 4, horas: 6, friccion: 3, gasto: 2, plataformas: ['pc'], generos: [] };

describe('opciones-perfil', () => {
  it('mantiene los rangos que valida la API', () => {
    expect(COMPRAS.map((o) => o.valor)).toEqual([1, 4, 11, 25]);
    expect(HORAS.map((o) => o.valor)).toEqual([2, 6, 15]);
    expect(FRICCION.map((o) => o.valor)).toEqual([1, 2, 3, 4, 5]);
    expect(GASTO.map((o) => o.valor)).toEqual([1, 2, 3, 4]);
  });

  it('el formulario empieza sin nada elegido', () => {
    expect(VALORES_VACIOS).toEqual({
      compras: null,
      horas: null,
      friccion: null,
      gasto: null,
      plataformas: [],
      generos: [],
    });
    expect(estaCompleto(VALORES_VACIOS)).toBe(false);
  });

  it('está completo con las cinco respuestas, aunque no haya géneros', () => {
    expect(estaCompleto(DECLARADO)).toBe(true);
    expect(estaCompleto({ ...DECLARADO, plataformas: [] })).toBe(false);
    expect(estaCompleto({ ...DECLARADO, gasto: null })).toBe(false);
    expect(estaCompleto({ ...DECLARADO, friccion: null })).toBe(false);
  });

  it('dice qué preguntas faltan, en el orden del formulario', () => {
    expect(preguntasPendientes({ ...DECLARADO, gasto: null, friccion: null })).toEqual([
      'cuánto pagas por juego',
      'tolerancia a la fricción',
    ]);
    expect(preguntasPendientes(VALORES_VACIOS)).toHaveLength(5);
  });

  it('arma el FormularioAlta con los géneros en tags_preferidos', () => {
    expect(formularioDesde({ ...DECLARADO, generos: ['Acción', 'Rol'] })).toEqual({
      compras_al_anio: 4,
      horas_por_semana: 6,
      tolerancia_friccion: 3,
      tags_preferidos: ['Acción', 'Rol'],
      tags_rechazados: [],
      plataforma: 'pc',
    });
  });

  it('a la API va una sola plataforma: PC si está marcada y, si no, la primera', () => {
    expect(formularioDesde({ ...DECLARADO, plataformas: ['xbox', 'pc'] }).plataforma).toBe('pc');
    expect(formularioDesde({ ...DECLARADO, plataformas: ['xbox', 'nintendo'] }).plataforma).toBe('xbox');
  });

  it('se niega a armar un formulario a medias en vez de inventar valores', () => {
    expect(() => formularioDesde(VALORES_VACIOS)).toThrow();
    expect(() => formularioDesde({ ...DECLARADO, horas: null })).toThrow();
  });

  it('resume lo declarado en chips con los rangos elegidos, no con los puntos medios', () => {
    const valores: ValoresPerfil = { ...DECLARADO, plataformas: ['pc', 'xbox'], generos: ['Acción', 'Rol'] };
    expect(respuestasPerfil(valores).map((r) => (r.pregunta ? `${r.pregunta}: ${r.texto}` : r.texto))).toEqual([
      'Compras: 3–6 al año',
      'Gasto: $200 a $500 por juego',
      'Tiempo: entre 4 y 9 h por semana',
      'Fricción: media',
      'PC',
      'Xbox',
      'Acción',
      'Rol',
    ]);
  });

  it('las preguntas sin responder no salen en el resumen', () => {
    expect(respuestasPerfil(VALORES_VACIOS)).toEqual([]);
  });

  it('la línea de plataforma solo sale con alguna consola y nombra todas las marcadas', () => {
    expect(lineaPlataforma(['pc'])).toBeNull();
    expect(lineaPlataforma([])).toBeNull();
    expect(lineaPlataforma(['xbox'])).toBe('Tu plataforma es Xbox; el riesgo se calcula con reseñas de Steam.');
    expect(lineaPlataforma(['xbox', 'pc'])).toBe('Juegas en PC y Xbox; el riesgo se calcula con reseñas de Steam.');
    expect(lineaPlataforma(['nintendo', 'playstation', 'pc'])).toBe(
      'Juegas en PC, PlayStation y Nintendo; el riesgo se calcula con reseñas de Steam.',
    );
  });

  it('cuenta los juegos que caben en cada tope: los gratuitos siempre, los sin precio solo sin tope', () => {
    const juegos = [
      juegoDePrueba({ appid: 1, es_gratis: true, precio_final: null }),
      juegoDePrueba({ appid: 2, precio_final: 150 }),
      juegoDePrueba({ appid: 3, precio_final: 450 }),
      juegoDePrueba({ appid: 4, precio_final: 1500 }),
      juegoDePrueba({ appid: 5, precio_final: null }),
    ];
    expect([1, 2, 3, 4].map((g) => juegosHastaTope(juegos, g as 1 | 2 | 3 | 4))).toEqual([2, 3, 3, 5]);
  });
});
