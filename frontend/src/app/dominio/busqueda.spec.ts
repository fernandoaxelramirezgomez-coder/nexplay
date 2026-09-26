import { destinoDeBusqueda } from './busqueda';
import { juegoDePrueba } from './juego-prueba';

describe('destinoDeBusqueda', () => {
  const juegos = [
    juegoDePrueba({ appid: 1938010, nombre: 'WILD HEARTS™' }),
    juegoDePrueba({ appid: 105600, nombre: 'Terraria' }),
  ];

  it('con el campo vacío lleva al catálogo, sin filtro', () => {
    expect(destinoDeBusqueda(juegos, '   ')).toEqual({ ruta: ['/explorar'] });
  });

  it('con el nombre exacto lleva a la ficha, sin importar mayúsculas ni la marca', () => {
    expect(destinoDeBusqueda(juegos, 'wild hearts')).toEqual({ ruta: ['/juego', 1938010] });
    expect(destinoDeBusqueda(juegos, ' Terraria ')).toEqual({ ruta: ['/juego', 105600] });
  });

  it('con un pedazo de nombre lleva al catálogo filtrado con lo escrito', () => {
    expect(destinoDeBusqueda(juegos, 'terra ')).toEqual({ ruta: ['/explorar'], parametros: { q: 'terra' } });
  });
});
