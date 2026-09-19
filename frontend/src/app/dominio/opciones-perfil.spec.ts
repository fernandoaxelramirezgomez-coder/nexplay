import { BIBLIOTECA, FRICCION, formularioDesde, HORAS, VALORES_POR_DEFECTO } from './opciones-perfil';

describe('opciones-perfil', () => {
  it('mantiene los rangos del formulario de Gradio', () => {
    expect(BIBLIOTECA.map((o) => o.valor)).toEqual([5, 20, 60, 150]);
    expect(HORAS.map((o) => o.valor)).toEqual([2, 6, 15]);
    expect(FRICCION.map((o) => o.valor)).toEqual([1, 2, 3, 4, 5]);
  });

  it('arma el FormularioAlta con los géneros en tags_preferidos', () => {
    expect(formularioDesde({ ...VALORES_POR_DEFECTO, generos: ['Acción', 'Rol'] })).toEqual({
      compras_al_anio: 20,
      horas_por_semana: 6,
      tolerancia_friccion: 3,
      tags_preferidos: ['Acción', 'Rol'],
      tags_rechazados: [],
      plataforma: 'pc',
    });
  });
});
