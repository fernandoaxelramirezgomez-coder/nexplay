/** «¿Por qué elegir NexPlay?», en el Inicio: lo que ningún otro sitio mide y las
 * herramientas para decidir. Solo lo que es cierto y con el vocabulario del proyecto: el
 * riesgo es una señal comparativa, nunca una predicción, y el perfil no lo mueve. */

/** El tono de cada tarjeta: el color de la vista a la que lleva, nunca los del riesgo. */
export type TonoHerramienta = 'inicio' | 'explorar' | 'nia' | 'comparar' | 'perfil';

export interface Destacada {
  titulo: string;
  texto: string;
  aclaracion: string;
  /** Lleva a /explorar. La acción principal del Inicio es el buscador del encabezado. */
  accion: string;
}

export interface Herramienta {
  id: 'motivos' | 'nia' | 'comparar' | 'perfil';
  titulo: string;
  linea: string;
  ruta: string;
  tono: TonoHerramienta;
}

/** WILD HEARTS™: en sus reseñas negativas lo que más sale es rendimiento. La tarjeta de
 * motivos lleva a su ficha como ejemplo. */
export const APPID_EJEMPLO_MOTIVOS = 1938010;

/** Lo que nos diferencia, en una línea: la nota general no ve las primeras dos horas. */
export const DIFERENCIA =
  'Steam te da una nota general; NexPlay mira las primeras dos horas, justo la ventana de reembolso.';

export function destacadaDelInicio(totalJuegos: number): Destacada {
  return {
    // Sin espacio que corte: «2» y «horas» siempre en el mismo renglón.
    titulo: 'Riesgo en las primeras 2\u00a0horas',
    texto:
      'Qué tanto tiende un juego a dejar reseñas negativas de quien jugó menos de 2\u00a0horas, frente al resto del catálogo.',
    aclaracion: 'Es una señal comparativa basada en reseñas, no una predicción de lo que sentirás.',
    // El número sale del catálogo que sirve la API; sin catálogo no se inventa.
    accion: totalJuegos > 0 ? `Explorar los ${totalJuegos} juegos` : 'Explorar el catálogo',
  };
}

export const HERRAMIENTAS: readonly Herramienta[] = [
  {
    id: 'motivos',
    titulo: 'Por qué se arrepienten',
    linea: 'Los motivos de sus reseñas negativas, como en WILD HEARTS™.',
    ruta: `/juego/${APPID_EJEMPLO_MOTIVOS}`,
    tono: 'explorar',
  },
  {
    id: 'nia',
    titulo: 'Nia, tu asistente',
    linea: 'Pregúntale lo que quieras; responde con los datos del juego.',
    ruta: '/nia',
    tono: 'nia',
  },
  {
    id: 'comparar',
    titulo: 'Compara lado a lado',
    linea: 'Hasta 4 juegos con el mismo criterio.',
    ruta: '/comparar',
    tono: 'comparar',
  },
  {
    id: 'perfil',
    titulo: 'Encaja contigo',
    linea: 'Qué tanto encaja con cómo juegas; el riesgo no cambia.',
    ruta: '/perfil',
    tono: 'perfil',
  },
];
