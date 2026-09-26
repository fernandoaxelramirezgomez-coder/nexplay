import {
  COMPRAS,
  FRICCION,
  HORAS,
  VALORES_VACIOS,
  ValoresPerfil,
  estaCompleto,
  formularioDesde,
  respuestasPerfil,
} from './opciones-perfil';

const DECLARADO: ValoresPerfil = { compras: 4, horas: 6, friccion: 3, plataforma: 'pc', generos: [] };

describe('opciones-perfil', () => {
  it('mantiene los rangos que valida la API', () => {
    expect(COMPRAS.map((o) => o.valor)).toEqual([1, 4, 11, 25]);
    expect(HORAS.map((o) => o.valor)).toEqual([2, 6, 15]);
    expect(FRICCION.map((o) => o.valor)).toEqual([1, 2, 3, 4, 5]);
  });

  it('el formulario empieza sin nada elegido', () => {
    expect(VALORES_VACIOS).toEqual({ compras: null, horas: null, friccion: null, plataforma: null, generos: [] });
    expect(estaCompleto(VALORES_VACIOS)).toBe(false);
  });

  it('está completo con las cuatro respuestas, aunque no haya géneros', () => {
    expect(estaCompleto(DECLARADO)).toBe(true);
    expect(estaCompleto({ ...DECLARADO, plataforma: null })).toBe(false);
    expect(estaCompleto({ ...DECLARADO, friccion: null })).toBe(false);
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

  it('se niega a armar un formulario a medias en vez de inventar valores', () => {
    expect(() => formularioDesde(VALORES_VACIOS)).toThrow();
    expect(() => formularioDesde({ ...DECLARADO, horas: null })).toThrow();
  });

  it('resume lo declarado en chips con los rangos elegidos, no con los puntos medios', () => {
    const valores = { compras: 4, horas: 6, friccion: 3 as const, plataforma: 'pc' as const, generos: ['Acción', 'Rol'] };
    expect(respuestasPerfil(valores).map((r) => (r.pregunta ? `${r.pregunta}: ${r.texto}` : r.texto))).toEqual([
      'Compras: 3–6 al año',
      'Tiempo: entre 4 y 9 h por semana',
      'Fricción: media',
      'PC',
      'Acción',
      'Rol',
    ]);
  });

  it('las preguntas sin responder no salen en el resumen', () => {
    expect(respuestasPerfil(VALORES_VACIOS)).toEqual([]);
  });
});
