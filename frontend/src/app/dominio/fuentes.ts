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
  api: string;
  /** La línea corta del inicio. */
  que: string;
  /** Qué se toma, para la sección Fuentes. */
  toma: string;
  enlace: string;
  textoEnlace: string;
}

/** appdetails no tiene documentación oficial de Steam: se enlaza una respuesta real, con el
 * país y el idioma con que se descargó. La nota de Metacritic llega dentro de appdetails. */
export const ORIGENES: readonly Origen[] = [
  {
    clave: 'appreviews',
    quien: 'Steam',
    api: 'appreviews',
    que: 'Las reseñas, su voto y las horas que llevaba jugadas quien escribió cada una.',
    toma: 'El voto, las horas jugadas al escribir y el texto de cada reseña, que es de donde salen los motivos.',
    enlace: 'https://partner.steamgames.com/doc/store/getreviews',
    textoEnlace: 'Documentación de Steam',
  },
  {
    clave: 'appdetails',
    quien: 'Steam',
    api: 'appdetails',
    que: 'Precio, géneros, fecha de lanzamiento, descripción y tráileres de cada juego.',
    toma: 'Precio en México, gratuidad, descuento, géneros, fecha de lanzamiento, descripción y tráileres.',
    enlace: 'https://store.steampowered.com/api/appdetails?appids=1938010&cc=mx&l=spanish',
    textoEnlace: 'Ver una respuesta de ejemplo',
  },
  {
    clave: 'metacritic',
    quien: 'Metacritic',
    api: 'nota de la crítica',
    que: 'La calificación de la crítica; llega a través de appdetails de Steam.',
    toma: 'La nota de la crítica especializada, que Steam publica dentro de appdetails.',
    enlace: 'https://www.metacritic.com/',
    textoEnlace: 'metacritic.com',
  },
];

export interface Servicio {
  quien: string;
  para: string;
  que: string;
  enlace: string;
  textoEnlace: string;
}

/** Lo que usa la app sin ser fuente de datos. El perfil no viaja a OpenAI: api/nia.py lo
 * recibe por compatibilidad y no lo pone en el contexto. */
export const SERVICIOS: readonly Servicio[] = [
  {
    quien: 'OpenAI',
    para: 'Nia',
    que:
      'Redacta las respuestas de Nia. Recibe tu pregunta, la conversación y los datos del juego o del catálogo; tu perfil no. No entra al riesgo, y sin clave configurada Nia responde con reglas sobre los mismos datos.',
    enlace: 'https://openai.com/api/',
    textoEnlace: 'openai.com/api',
  },
  {
    quien: 'Chakra Petch, Inter y JetBrains Mono',
    para: 'Tipografías',
    que: 'Con licencia SIL Open Font License 1.1. Van dentro de la app: no se piden a otro servidor.',
    enlace: 'https://openfontlicense.org/',
    textoEnlace: 'openfontlicense.org',
  },
];
