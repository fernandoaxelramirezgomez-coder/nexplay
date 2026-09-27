/** Lo que ofrece NexPlay, en cuadritos de dos palabras bajo la descripción del Inicio. Solo
 * lo que es cierto: no hay cuentas ni cobro, y el riesgo ya está calculado cuando abres una
 * ficha, así que buscar un juego y ver su riesgo toma menos de un minuto. «Confidencial» no va: las preguntas a Nia se guardan 180 días para revisar votos. */
export interface Oferta {
  id: 'gratis' | 'sin-registro' | 'un-minuto' | 'juegos';
  texto: string;
  /** Cómo lo lee un lector de pantalla, cuando el texto lleva un símbolo. */
  lectura?: string;
  /** En lugar del icono de trazo, cuando el dueño pidió un emoji. */
  emoji?: string;
  /** El color de cada cuadrito: tonos de la paleta, nunca los del riesgo. */
  tono: 'inicio' | 'nia' | 'perfil' | 'neutro';
}

export function ofertasDelInicio(totalJuegos: number): Oferta[] {
  const ofertas: Oferta[] = [
    { id: 'gratis', texto: 'Gratis', tono: 'inicio' },
    { id: 'sin-registro', texto: 'Sin registro', tono: 'nia' },
    { id: 'un-minuto', texto: '<1 minuto', lectura: 'Menos de un minuto', emoji: '💬', tono: 'perfil' },
  ];
  // El número sale del catálogo que sirve la API; sin catálogo no se inventa.
  if (totalJuegos > 0) {
    ofertas.push({ id: 'juegos', texto: `${totalJuegos} juegos`, tono: 'neutro' });
  }
  return ofertas;
}
