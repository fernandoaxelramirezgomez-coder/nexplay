/** El promedio de estrellas con un decimal, redondeando la mitad hacia arriba: 4.25 → 4.3.
 * Se redondea sobre centésimas enteras para que 4.35 no salga 4.3 por cómo guarda los
 * decimales la máquina (4.35 * 10 = 43.49999…). */
export function redondearPromedio(promedio: number): number {
  return Math.round(Math.round(promedio * 100) / 10) / 10;
}

/** El resumen público de la calificación: "4.2 ★ · 15 valoraciones". */
export function textoCalificacion(promedio: number | null, total: number): string {
  if (!total || promedio === null) {
    return 'Nadie la ha calificado todavía.';
  }
  const estrellas = redondearPromedio(promedio).toFixed(1);
  return `${estrellas} ★ · ${total} ${total === 1 ? 'valoración' : 'valoraciones'}`;
}
