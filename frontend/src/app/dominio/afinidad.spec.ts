import { generosEnComun } from './afinidad';

describe('generosEnComun', () => {
  it('compara sin distinguir mayúsculas, porque /perfil devuelve los géneros en minúsculas', () => {
    expect(generosEnComun(['Acción', 'Aventura'], ['acción', 'rol'])).toEqual(['Acción']);
    expect(generosEnComun(['Free to Play'], ['free to play'])).toEqual(['Free to Play']);
  });

  it('devuelve los géneros con el formato del catálogo', () => {
    expect(generosEnComun(['Acción', 'Rol'], ['rol', 'acción'])).toEqual(['Acción', 'Rol']);
  });

  it('sin preferencias o sin coincidencias devuelve vacío', () => {
    expect(generosEnComun(['Acción'], [])).toEqual([]);
    expect(generosEnComun(['Acción'], ['estrategia'])).toEqual([]);
  });
});
