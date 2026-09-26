import { FormularioAlta, JuegoCatalogo, Plataforma } from '../api/contrato';

/** Una respuesta del formulario, como tarjeta: el nombre corto, una línea de detalle, su
 * icono y, en la fricción, cuántas barras del medidor lleva. */
export interface Opcion<T> {
  etiqueta: string;
  valor: T;
  detalle?: string;
  icono?: string;
  nivel?: number;
}

// Compras al año, no tamaño de la biblioteca: el formulario preguntaba una cosa y
// mandaba el número como si fuera la otra. El valor de cada opción es el punto medio
// del rango. Mismos rangos que valida la API en FormularioAlta (api/schemas.py).
export const COMPRAS: Opcion<number>[] = [
  { etiqueta: 'Casi ninguno', detalle: '0 a 2 al año', icono: 'bolsa-1', valor: 1 },
  { etiqueta: 'Pocos', detalle: '3 a 6 al año', icono: 'bolsa-2', valor: 4 },
  { etiqueta: 'Varios', detalle: '7 a 15 al año', icono: 'bolsa-3', valor: 11 },
  { etiqueta: 'Muchos', detalle: 'más de 15 al año', icono: 'bolsa-4', valor: 25 },
];

export const HORAS: Opcion<number>[] = [
  { etiqueta: 'Poca', detalle: 'menos de 4 h', icono: 'reloj-1', valor: 2 },
  { etiqueta: 'Media', detalle: '4 a 9 h', icono: 'reloj-2', valor: 6 },
  { etiqueta: 'Alta', detalle: '10 h o más', icono: 'reloj-3', valor: 15 },
];

export type Gasto = 1 | 2 | 3 | 4;

/** Cuánto se paga por juego, en cuatro tramos hechos con el catálogo: hasta $200 hay 31
 * juegos (más 7 gratuitos), entre $200 y $500 hay 42, entre $500 y $1,000 hay 32 y más
 * arriba hay 9. Solo lo usan las sugerencias; a la API no viaja. */
export const GASTO: Opcion<Gasto>[] = [
  { etiqueta: 'Hasta $200', icono: 'moneda-1', valor: 1 },
  { etiqueta: '$200 a $500', icono: 'moneda-2', valor: 2 },
  { etiqueta: '$500 a $1,000', icono: 'moneda-3', valor: 3 },
  { etiqueta: 'Más de $1,000', icono: 'moneda-4', valor: 4 },
];

/** El tope de precio de cada tramo, en pesos; el último no tiene. */
export const TOPE_GASTO: Record<Gasto, number | null> = { 1: 200, 2: 500, 3: 1000, 4: null };

/** Cuántos juegos del catálogo caben en el tope de un tramo: los gratuitos siempre, los de
 * precio desconocido solo sin tope. Es el detalle de cada tarjeta del gasto. */
export function juegosHastaTope(juegos: readonly JuegoCatalogo[], gasto: Gasto): number {
  const tope = TOPE_GASTO[gasto];
  return juegos.filter((juego) => cabeEnTope(juego, tope)).length;
}

export function cabeEnTope(juego: JuegoCatalogo, tope: number | null): boolean {
  if (juego.es_gratis || tope === null) {
    return true;
  }
  return juego.precio_final !== null && juego.precio_final <= tope;
}

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
  { etiqueta: 'Nula', detalle: 'Lo dejo al primer tropiezo', nivel: 1, valor: 1 },
  { etiqueta: 'Baja', detalle: 'Poca paciencia', nivel: 2, valor: 2 },
  { etiqueta: 'Media', detalle: 'Aguanto un rato', nivel: 3, valor: 3 },
  { etiqueta: 'Alta', detalle: 'Le doy tiempo', nivel: 4, valor: 4 },
  { etiqueta: 'Muy alta', detalle: 'Aguanto casi todo', nivel: 5, valor: 5 },
];

export const PLATAFORMAS: Opcion<Plataforma>[] = [
  { etiqueta: 'PC', detalle: 'Steam', icono: 'pc', valor: 'pc' },
  { etiqueta: 'PlayStation', detalle: 'PS4 · PS5', icono: 'playstation', valor: 'playstation' },
  { etiqueta: 'Xbox', detalle: 'One · Series', icono: 'xbox', valor: 'xbox' },
  { etiqueta: 'Nintendo', detalle: 'Switch', icono: 'nintendo', valor: 'nintendo' },
];

/** Lo declarado por quien llena el formulario. Todo empieza vacío: arrancar con
 * respuestas puestas dejaba guardar un perfil que nadie eligió, y después la ficha
 * hablaba de "tus géneros" y "cómo juegas" sobre valores inventados por omisión. Las
 * plataformas son varias desde la 6C; el gasto es la pregunta nueva de la 6C. */
export interface ValoresPerfil {
  compras: number | null;
  horas: number | null;
  friccion: 1 | 2 | 3 | 4 | 5 | null;
  gasto: Gasto | null;
  plataformas: Plataforma[];
  generos: string[];
}

export const VALORES_VACIOS: ValoresPerfil = {
  compras: null,
  horas: null,
  friccion: null,
  gasto: null,
  plataformas: [],
  generos: [],
};

/** Las cinco preguntas que hacen falta, en el orden del formulario, con el nombre que usa
 * la barra de guardar para decir cuál falta. Los géneros son opcionales. */
const PREGUNTAS: { nombre: string; respondida: (v: ValoresPerfil) => boolean }[] = [
  { nombre: 'juegos que compras al año', respondida: (v) => v.compras !== null },
  { nombre: 'cuánto pagas por juego', respondida: (v) => v.gasto !== null },
  { nombre: 'horas por semana', respondida: (v) => v.horas !== null },
  { nombre: 'en qué juegas', respondida: (v) => v.plataformas.length > 0 },
  { nombre: 'tolerancia a la fricción', respondida: (v) => v.friccion !== null },
];

export const TOTAL_PREGUNTAS = PREGUNTAS.length;

export function preguntasPendientes(valores: ValoresPerfil): string[] {
  return PREGUNTAS.filter((pregunta) => !pregunta.respondida(valores)).map((pregunta) => pregunta.nombre);
}

export function estaCompleto(valores: ValoresPerfil): boolean {
  return preguntasPendientes(valores).length === 0;
}

/** Los géneros elegidos viajan en tags_preferidos: la API los valida y los normaliza,
 * pero el modelo no usa ningún dato del perfil (es un modelo de título). La API recibe una
 * sola plataforma, porque su contrato no cambió: PC si está marcada y, si no, la primera.
 * El gasto no viaja: solo lo usan las sugerencias. */
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
    plataforma: valores.plataformas.includes('pc') ? 'pc' : valores.plataformas[0],
  };
}

export interface RespuestaPerfil {
  /** De qué pregunta sale; las plataformas y los géneros van sin rótulo, uno por chip. */
  pregunta: string | null;
  texto: string;
}

/** Lo declarado, en chips cortos para la ficha: los rangos como se eligieron, sin los
 * puntos medios que viajan a la API. Las preguntas sin responder no salen. */
export function respuestasPerfil(valores: ValoresPerfil): RespuestaPerfil[] {
  const respuestas: RespuestaPerfil[] = [];
  if (valores.compras !== null) {
    respuestas.push({ pregunta: 'Compras', texto: `${rangoDeComprasCorto(valores.compras)} al año` });
  }
  const gasto = GASTO.find((opcion) => opcion.valor === valores.gasto);
  if (gasto) {
    respuestas.push({ pregunta: 'Gasto', texto: `${gasto.etiqueta} por juego` });
  }
  if (valores.horas !== null) {
    respuestas.push({ pregunta: 'Tiempo', texto: `${rangoDeHoras(valores.horas)} por semana` });
  }
  const friccion = FRICCION.find((opcion) => opcion.valor === valores.friccion);
  if (friccion) {
    respuestas.push({ pregunta: 'Fricción', texto: friccion.etiqueta.toLowerCase() });
  }
  const plataformas = PLATAFORMAS.filter((opcion) => valores.plataformas.includes(opcion.valor));
  return [
    ...respuestas,
    ...plataformas.map((opcion) => ({ pregunta: null, texto: opcion.etiqueta })),
    ...valores.generos.map((genero) => ({ pregunta: null, texto: genero })),
  ];
}

/** "PC y Xbox", "PC, PlayStation y Xbox". */
function enLista(nombres: string[]): string {
  return nombres.length === 1 ? nombres[0] : `${nombres.slice(0, -1).join(', ')} y ${nombres[nombres.length - 1]}`;
}

/** La línea de plataforma de la ficha: solo si se marcó alguna consola, porque el riesgo
 * se calcula con reseñas de Steam y en otra plataforma el juego es el mismo, las reseñas
 * no. Solo con PC no hay nada que aclarar. */
export function lineaPlataforma(plataformas: readonly Plataforma[]): string | null {
  const nombres = PLATAFORMAS.filter((opcion) => plataformas.includes(opcion.valor)).map((opcion) => opcion.etiqueta);
  if (!plataformas.some((plataforma) => plataforma !== 'pc')) {
    return null;
  }
  const quien = nombres.length === 1 ? `Tu plataforma es ${nombres[0]}` : `Juegas en ${enLista(nombres)}`;
  return `${quien}; el riesgo se calcula con reseñas de Steam.`;
}
