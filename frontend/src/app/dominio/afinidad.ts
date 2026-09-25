/** Géneros del juego que el jugador declaró preferir. La API guarda los géneros en
 * minúsculas (_normalizar_tags), así que la comparación las ignora. Es solo afinidad:
 * el modelo no usa los gustos y el riesgo no cambia. */
export function generosEnComun(generosJuego: readonly string[], generosPreferidos: readonly string[]): string[] {
  const preferidos = new Set(generosPreferidos.map((g) => g.trim().toLowerCase()));
  return generosJuego.filter((genero) => preferidos.has(genero.trim().toLowerCase()));
}
