import { FormularioAlta, Plataforma } from '../api/contrato';

export interface Opcion<T> {
  etiqueta: string;
  valor: T;
}

// Compras al año, no tamaño de la biblioteca: el formulario preguntaba una cosa y
// mandaba el número como si fuera la otra. El valor de cada opción es el punto medio
// del rango. Mismos rangos que el formulario de Gradio (ui/app.py).
export const COMPRAS: Opcion<number>[] = [
  { etiqueta: 'Casi ninguno (0–2 al año)', valor: 1 },
  { etiqueta: 'Pocos (3–6 al año)', valor: 4 },
  { etiqueta: 'Varios (7–15 al año)', valor: 11 },
  { etiqueta: 'Muchos (más de 15 al año)', valor: 25 },
];

export const HORAS: Opcion<number>[] = [
  { etiqueta: 'Poca (menos de 4 h)', valor: 2 },
  { etiqueta: 'Media (4 a 9 h)', valor: 6 },
  { etiqueta: 'Alta (10 h o más)', valor: 15 },
];

export const FRICCION: Opcion<1 | 2 | 3 | 4 | 5>[] = [
  { etiqueta: 'Nula', valor: 1 },
  { etiqueta: 'Baja', valor: 2 },
  { etiqueta: 'Media', valor: 3 },
  { etiqueta: 'Alta', valor: 4 },
  { etiqueta: 'Muy alta', valor: 5 },
];

export const PLATAFORMAS: Opcion<Plataforma>[] = [
  { etiqueta: 'PC', valor: 'pc' },
  { etiqueta: 'PlayStation', valor: 'playstation' },
  { etiqueta: 'Xbox', valor: 'xbox' },
  { etiqueta: 'Nintendo', valor: 'nintendo' },
];

export interface ValoresPerfil {
  compras: number;
  horas: number;
  friccion: 1 | 2 | 3 | 4 | 5;
  plataforma: Plataforma;
  generos: string[];
}

export const VALORES_POR_DEFECTO: ValoresPerfil = {
  compras: 4,
  horas: 6,
  friccion: 3,
  plataforma: 'pc',
  generos: [],
};

/** Los géneros elegidos viajan en tags_preferidos: la API los valida y los normaliza,
 * pero el modelo no usa ningún dato del perfil (es un modelo de título); la plataforma
 * solo agrega la nota de plataforma a la predicción. */
export function formularioDesde(valores: ValoresPerfil): FormularioAlta {
  return {
    compras_al_anio: valores.compras,
    horas_por_semana: valores.horas,
    tolerancia_friccion: valores.friccion,
    tags_preferidos: valores.generos,
    tags_rechazados: [],
    plataforma: valores.plataforma,
  };
}
