import { FormularioAlta, Plataforma } from '../api/contrato';

export interface Opcion<T> {
  etiqueta: string;
  valor: T;
}

// Compras al año, no tamaño de la biblioteca: el formulario preguntaba una cosa y
// mandaba el número como si fuera la otra. El valor de cada opción es el punto medio
// del rango. Mismos rangos que valida la API en FormularioAlta (api/schemas.py).
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

/** Igual que con las horas: a la API viaja el punto medio (1, 4, 11 o 25) y lo declarado
 * fue un rango. "Compras alrededor de 4 juegos al año" es un dato que nadie dijo. */
export function rangoDeCompras(compras: number): string {
  if (compras <= 2) {
    return 'de cero a dos juegos al año';
  }
  if (compras <= 6) {
    return 'entre tres y seis juegos al año';
  }
  return compras <= 15 ? 'entre siete y quince juegos al año' : 'más de quince juegos al año';
}

/** El mismo rango en cifras, para cuando la línea tiene que caber en una ojeada:
 * "una de tus 3–6 compras del año". */
export function rangoDeComprasCorto(compras: number): string {
  if (compras <= 2) {
    return '0–2';
  }
  if (compras <= 6) {
    return '3–6';
  }
  return compras <= 15 ? '7–15' : 'más de 15';
}

/** El valor que viaja a la API es el punto medio del rango elegido (2, 6 o 15). Al
 * contarlo de vuelta hay que nombrar el rango: decir "con 2 h por semana" suena a un dato
 * que nadie declaró, porque lo que se eligió fue "menos de 4 h". */
export function rangoDeHoras(horas: number): string {
  if (horas <= 3) {
    return 'menos de 4 h';
  }
  return horas <= 9 ? 'entre 4 y 9 h' : '10 h o más';
}

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

/** Lo declarado por quien llena el formulario. Los cuatro primeros empiezan en null:
 * arrancar con respuestas puestas dejaba guardar un perfil que nadie eligió, y después la
 * ficha hablaba de "tus géneros" y "cómo juegas" sobre valores inventados por omisión. */
export interface ValoresPerfil {
  compras: number | null;
  horas: number | null;
  friccion: 1 | 2 | 3 | 4 | 5 | null;
  plataforma: Plataforma | null;
  generos: string[];
}

export const VALORES_VACIOS: ValoresPerfil = {
  compras: null,
  horas: null,
  friccion: null,
  plataforma: null,
  generos: [],
};

/** Los géneros son opcionales; las cuatro preguntas de una sola respuesta, no. */
export function estaCompleto(valores: ValoresPerfil): boolean {
  return (
    valores.compras !== null &&
    valores.horas !== null &&
    valores.friccion !== null &&
    valores.plataforma !== null
  );
}

/** Los géneros elegidos viajan en tags_preferidos: la API los valida y los normaliza,
 * pero el modelo no usa ningún dato del perfil (es un modelo de título); la plataforma
 * solo agrega la nota de plataforma a la predicción. */
export function formularioDesde(valores: ValoresPerfil): FormularioAlta {
  if (!estaCompleto(valores)) {
    throw new Error('El formulario está incompleto: faltan respuestas por declarar.');
  }
  return {
    compras_al_anio: valores.compras as number,
    horas_por_semana: valores.horas as number,
    tolerancia_friccion: valores.friccion as 1 | 2 | 3 | 4 | 5,
    tags_preferidos: valores.generos,
    tags_rechazados: [],
    plataforma: valores.plataforma as Plataforma,
  };
}
