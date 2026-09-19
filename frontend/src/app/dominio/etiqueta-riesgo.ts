/** El rótulo dice de dónde sale la banda: sin perfil declarado, la predicción usa el
 * perfil neutro y llamarla "para tu perfil" sería falso. */
export function rotuloRiesgo(hayPerfilDeclarado: boolean): string {
  return hayPerfilDeclarado ? 'Riesgo para tu perfil' : 'Riesgo general';
}
