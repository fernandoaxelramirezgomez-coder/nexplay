import { JuegoCatalogo } from '../api/contrato';

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
