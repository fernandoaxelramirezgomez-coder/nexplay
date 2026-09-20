/** Texto del conteo público de utilidad de una segunda opinión. */
export function textoUtilidad(utiles: number, total: number): string {
  if (!total) {
    return 'Nadie la ha valorado todavía.';
  }
  if (total === 1) {
    return utiles === 1 ? '1 persona la encontró útil.' : '1 persona no la encontró útil.';
  }
  return `${utiles} de ${total} personas la encontraron útil.`;
}
