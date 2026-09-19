import { FormularioAlta, Plataforma } from '../api/contrato';

export interface Opcion<T> {
  etiqueta: string;
  valor: T;
}

// Mismos rangos que el formulario de Gradio (ui/app.py).
export const BIBLIOTECA: Opcion<number>[] = [
  { etiqueta: 'Estoy empezando (0–10 juegos)', valor: 5 },
  { etiqueta: 'Pequeña (11–30 juegos)', valor: 20 },
  { etiqueta: 'Mediana (31–100 juegos)', valor: 60 },
  { etiqueta: 'Grande (más de 100 juegos)', valor: 150 },
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
  biblioteca: number;
  horas: number;
  friccion: 1 | 2 | 3 | 4 | 5;
  plataforma: Plataforma;
  generos: string[];
}

export const VALORES_POR_DEFECTO: ValoresPerfil = {
  biblioteca: 20,
  horas: 6,
  friccion: 3,
  plataforma: 'pc',
  generos: [],
};

/** Los géneros elegidos viajan en tags_preferidos: la API los valida y los normaliza,
 * pero el modelo no los usa (solo lee compras_al_anio y plataforma). */
export function formularioDesde(valores: ValoresPerfil): FormularioAlta {
  return {
    compras_al_anio: valores.biblioteca,
    horas_por_semana: valores.horas,
    tolerancia_friccion: valores.friccion,
    tags_preferidos: valores.generos,
    tags_rechazados: [],
    plataforma: valores.plataforma,
  };
}
