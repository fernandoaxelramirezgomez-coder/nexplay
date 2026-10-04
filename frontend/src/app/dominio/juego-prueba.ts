import { JuegoCatalogo, NivelRiesgo, NivelSenal, SenalPorNivel } from '../api/contrato';

/** Juego de catálogo para tests: valores reales de Wild Hearts, sobrescribibles. */
export function juegoDePrueba(cambios: Partial<JuegoCatalogo> = {}): JuegoCatalogo {
  return {
    appid: 1938010,
    nombre: 'WILD HEARTS™',
    plataformas: ['pc'],
    generos: ['Acción', 'Aventura'],
    metacritic: null,
    es_gratis: false,
    precio_final: 1599,
    moneda: 'MXN',
    fecha_lanzamiento: '16 FEB 2023',
    descripcion: 'Domina una tecnología ancestral para cazar bestias enormes.',
    portada_url: 'https://cdn.cloudflare.steamstatic.com/steam/apps/1938010/header.jpg',
    video_url: null,
    tienda_url: 'https://store.steampowered.com/app/1938010',
    banda_riesgo: 'alto',
    riesgo: 0.7424,
    ...cambios,
  };
}

function nivelDePrueba(nivel: NivelRiesgo, juegos: number, resenas: number, casos: number): NivelSenal {
  return { nivel, juegos, resenas, casos_senal: casos, tasa: casos / resenas };
}

/** La señal por nivel de /panorama para tests: los valores de data-v3, con los 40 externos. */
export function senalDePrueba(medioExternos = { resenas: 21098, casos: 344 }): SenalPorNivel[] {
  return [
    {
      corte: 'catalogo',
      juegos: 123,
      niveles: [
        nivelDePrueba('bajo', 43, 64896, 664),
        nivelDePrueba('medio', 37, 55796, 730),
        nivelDePrueba('alto', 43, 63675, 2732),
      ],
      cociente_alto_bajo: 4.1934,
      ic_inferior: null,
      ic_superior: null,
    },
    {
      corte: 'externos',
      juegos: 40,
      niveles: [
        nivelDePrueba('bajo', 13, 19698, 366),
        nivelDePrueba('medio', 14, medioExternos.resenas, medioExternos.casos),
        nivelDePrueba('alto', 13, 19599, 702),
      ],
      cociente_alto_bajo: 1.9277,
      ic_inferior: 0.8705,
      ic_superior: 3.5018,
    },
  ];
}
