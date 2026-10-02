/** De dónde salen los datos y qué servicios usa la app. Lo leen el inicio y la sección
 * Fuentes de Cómo funciona: una sola lista, para que las dos digan lo mismo. */

/** Lo que el catálogo servido no sabe de sí mismo: con qué corte se entrenó el modelo.
 * Sale de docs/evidencia/README.md, que es la salida de esa validación; si algún día se
 * reentrena, estos números se actualizan ahí y aquí. */
export const ENTRENAMIENTO = {
  release: 'data-v1',
  juegos: 83,
  resenas: 123972,
  juegosPrueba: 40,
  prAuc: 0.0356,
  prAucTrivial: 0.0234,
};

export type ClaveOrigen = 'appreviews' | 'appdetails' | 'metacritic';

export interface Origen {
  clave: ClaveOrigen;
  quien: string;
  /** De qué parte de la fuente: «reseñas», «datos del juego». */
  sobre: string;
  /** Qué se toma, en una línea: el panel de fuentes es para leer de un vistazo. */
  da: string;
  enlace: string;
  textoEnlace: string;
}

/** appdetails no tiene documentación oficial de Steam: se enlaza una respuesta real, con el
 * país y el idioma con que se descargó. La nota de Metacritic llega dentro de appdetails. */
export const ORIGENES: readonly Origen[] = [
  {
    clave: 'appreviews',
    quien: 'Steam',
    sobre: 'reseñas',
    da: 'El voto, las horas jugadas y el texto de cada reseña.',
    enlace: 'https://partner.steamgames.com/doc/store/getreviews',
    textoEnlace: 'Documentación',
  },
  {
    clave: 'appdetails',
    quien: 'Steam',
    sobre: 'datos del juego',
    da: 'Precio en México, géneros, lanzamiento y tráileres.',
    enlace: 'https://store.steampowered.com/api/appdetails?appids=1938010&cc=mx&l=spanish',
    textoEnlace: 'Ejemplo',
  },
  {
    clave: 'metacritic',
    quien: 'Metacritic',
    sobre: 'crítica',
    da: 'La nota de la crítica, que llega con los datos de Steam.',
    enlace: 'https://www.metacritic.com/',
    textoEnlace: 'metacritic.com',
  },
];

export interface Servicio {
  quien: string;
  /** Lo que hace, en una frase que sigue al nombre. */
  que: string;
  enlace: string;
  textoEnlace: string;
}

/** Lo que usa la app sin ser fuente de datos. Del perfil, a Nia (y con IA, a OpenAI) solo
 * viajan los géneros declarados y la lista de sugerencias que el navegador ya calculó. */
export const SERVICIOS: readonly Servicio[] = [
  {
    quien: 'OpenAI',
    que:
      'redacta las respuestas de Nia con tu pregunta y los datos del juego, y el riesgo no pasa por ella. De tu perfil solo viajan tus géneros, para decirte cuáles coinciden con un juego: cuando Nia responde con IA, se envían a OpenAI junto con tu pregunta. El resto de tus respuestas no sale del navegador.',
    enlace: 'https://openai.com/api/',
    textoEnlace: 'openai.com',
  },
  {
    quien: 'Tipografías',
    que: 'Chakra Petch, Inter y JetBrains Mono, con licencia SIL OFL, van dentro de la app.',
    enlace: 'https://openfontlicense.org/',
    textoEnlace: 'SIL OFL',
  },
];
